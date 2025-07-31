"""
Kraken Exchange Adapter
Production-ready implementation for Kraken cryptocurrency exchange integration.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from decimal import Decimal
from typing import Dict, List, Optional, Any

import aiohttp
import websockets
from dataclasses import dataclass

from .base_exchange import BaseExchange, OrderType, OrderSide, OrderStatus
from ...core.exceptions import ExchangeError, AuthenticationError, RateLimitError


@dataclass
class KrakenConfig:
    """Kraken-specific configuration"""
    api_key: str
    api_secret: str
    base_url: str = "https://api.kraken.com"
    ws_url: str = "wss://ws.kraken.com"
    rate_limit_requests_per_minute: int = 60
    rate_limit_orders_per_minute: int = 60


class KrakenAdapter(BaseExchange):
    """
    Production-ready Kraken exchange adapter with comprehensive functionality.
    
    Features:
    - REST API integration with authentication
    - WebSocket real-time data streams
    - Order management with validation
    - Rate limiting and error handling
    - Security best practices
    """
    
    def __init__(self, config: KrakenConfig):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.rate_limiter = self._init_rate_limiter()
        self.asset_pairs = {}  # Cache for asset pair information
        
        # Kraken-specific endpoints
        self.endpoints = {
            'server_time': '/0/public/Time',
            'asset_pairs': '/0/public/AssetPairs',
            'ticker': '/0/public/Ticker',
            'orderbook': '/0/public/Depth',
            'ohlc': '/0/public/OHLC',
            'account_balance': '/0/private/Balance',
            'trade_balance': '/0/private/TradeBalance',
            'open_orders': '/0/private/OpenOrders',
            'closed_orders': '/0/private/ClosedOrders',
            'add_order': '/0/private/AddOrder',
            'cancel_order': '/0/private/CancelOrder',
            'query_orders': '/0/private/QueryOrders'
        }
    
    def _init_rate_limiter(self) -> Dict[str, Any]:
        """Initialize rate limiting counters"""
        return {
            'requests_per_minute': 0,
            'orders_per_minute': 0,
            'last_minute_reset': time.time(),
            'api_counter': 0  # Kraken uses a counter-based rate limiting system
        }
    
    async def connect(self) -> bool:
        """
        Establish connection to Kraken API and validate credentials.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Test connectivity and validate API key
            server_time = await self._get_server_time()
            balance = await self._get_account_balance()
            
            # Load asset pairs for symbol conversion
            await self._load_asset_pairs()
            
            self.logger.info(f"Connected to Kraken API. Server time: {server_time}")
            self.logger.info(f"Account has {len(balance)} assets")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Kraken: {str(e)}")
            if self.session:
                await self.session.close()
            return False
    
    async def disconnect(self) -> None:
        """Close all connections and cleanup resources"""
        try:
            # Close WebSocket connections
            for ws in self.ws_connections.values():
                await ws.close()
            self.ws_connections.clear()
            
            # Close HTTP session
            if self.session:
                await self.session.close()
                self.session = None
                
            self.logger.info("Disconnected from Kraken API")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {str(e)}")
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a pair.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSD')
            
        Returns:
            Dict containing ticker information
        """
        try:
            kraken_pair = self._format_symbol(symbol)
            params = {'pair': kraken_pair}
            response = await self._make_request('GET', self.endpoints['ticker'], params)
            
            ticker_data = response['result'][kraken_pair]
            
            return {
                'symbol': symbol.upper(),
                'price': Decimal(ticker_data['c'][0]),  # Last trade price
                'bid': Decimal(ticker_data['b'][0]),    # Best bid price
                'ask': Decimal(ticker_data['a'][0]),    # Best ask price
                'volume': Decimal(ticker_data['v'][1]), # 24h volume
                'change_24h': Decimal(ticker_data['p'][1]), # 24h price change percentage
                'high_24h': Decimal(ticker_data['h'][1]),   # 24h high
                'low_24h': Decimal(ticker_data['l'][1]),    # 24h low
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting ticker for {symbol}: {str(e)}")
            raise ExchangeError(f"Failed to get ticker: {str(e)}")
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get order book for a pair.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of entries to return (max 500)
            
        Returns:
            Dict containing orderbook data
        """
        try:
            kraken_pair = self._format_symbol(symbol)
            params = {
                'pair': kraken_pair,
                'count': min(limit, 500)  # Kraken max limit
            }
            
            response = await self._make_request('GET', self.endpoints['orderbook'], params)
            orderbook_data = response['result'][kraken_pair]
            
            return {
                'symbol': symbol.upper(),
                'bids': [[Decimal(price), Decimal(volume)] for price, volume, _ in orderbook_data['bids']],
                'asks': [[Decimal(price), Decimal(volume)] for price, volume, _ in orderbook_data['asks']],
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting orderbook for {symbol}: {str(e)}")
            raise ExchangeError(f"Failed to get orderbook: {str(e)}")
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        time_in_force: str = 'GTC',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Place a new order on Kraken.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            order_type: Order type (MARKET/LIMIT)
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            time_in_force: Time in force (GTC, IOC, FOK)
            
        Returns:
            Dict containing order information
        """
        try:
            await self._check_rate_limits('order')
            
            kraken_pair = self._format_symbol(symbol)
            
            order_data = {
                'pair': kraken_pair,
                'type': side.value.lower(),
                'ordertype': self._convert_order_type(order_type),
                'volume': str(quantity)
            }
            
            if order_type == OrderType.LIMIT:
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                order_data['price'] = str(price)
            
            # Add time in force if not GTC
            if time_in_force != 'GTC':
                order_data['timeinforce'] = time_in_force
            
            # Add stop price for stop orders
            if 'stopPrice' in kwargs:
                order_data['price2'] = str(kwargs['stopPrice'])
            
            response = await self._make_request('POST', self.endpoints['add_order'], data=order_data, signed=True)
            
            order_ids = response['result']['txid']
            order_id = order_ids[0] if order_ids else None
            
            return {
                'order_id': order_id,
                'symbol': symbol.upper(),
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'price': price,
                'status': OrderStatus.PENDING,
                'filled_quantity': Decimal('0'),
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            raise ExchangeError(f"Failed to place order: {str(e)}")
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            order_data = {'txid': order_id}
            response = await self._make_request('POST', self.endpoints['cancel_order'], data=order_data, signed=True)
            
            return {
                'order_id': order_id,
                'symbol': symbol.upper(),
                'status': OrderStatus.CANCELLED
            }
            
        except Exception as e:
            self.logger.error(f"Error canceling order {order_id}: {str(e)}")
            raise ExchangeError(f"Failed to cancel order: {str(e)}")
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order"""
        try:
            order_data = {'txid': order_id}
            response = await self._make_request('POST', self.endpoints['query_orders'], data=order_data, signed=True)
            
            if order_id not in response['result']:
                raise ExchangeError(f"Order {order_id} not found")
            
            order_info = response['result'][order_id]
            
            return {
                'order_id': order_id,
                'symbol': symbol.upper(),
                'side': OrderSide(order_info['descr']['type'].upper()),
                'type': self._convert_kraken_order_type(order_info['descr']['ordertype']),
                'quantity': Decimal(order_info['vol']),
                'price': Decimal(order_info['descr']['price']) if order_info['descr']['price'] else None,
                'status': self._convert_order_status(order_info['status']),
                'filled_quantity': Decimal(order_info['vol_exec']),
                'timestamp': int(float(order_info['opentm']) * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting order status: {str(e)}")
            raise ExchangeError(f"Failed to get order status: {str(e)}")
    
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balances for all assets"""
        try:
            balance_data = await self._get_account_balance()
            balances = {}
            
            for asset, balance in balance_data.items():
                # Convert Kraken asset names to standard format
                standard_asset = self._convert_kraken_asset(asset)
                balance_decimal = Decimal(balance)
                
                if balance_decimal > 0:
                    balances[standard_asset] = {
                        'free': balance_decimal,  # Kraken doesn't separate free/locked in balance endpoint
                        'locked': Decimal('0'),
                        'total': balance_decimal
                    }
            
            return balances
            
        except Exception as e:
            self.logger.error(f"Error getting account balance: {str(e)}")
            raise ExchangeError(f"Failed to get account balance: {str(e)}")
    
    async def start_websocket_stream(self, symbol: str, callback) -> None:
        """Start WebSocket stream for real-time data"""
        try:
            kraken_pair = self._format_symbol(symbol)
            
            # Connect to WebSocket
            async with websockets.connect(self.config.ws_url) as websocket:
                self.ws_connections[symbol] = websocket
                
                # Subscribe to ticker and book data
                subscribe_message = {
                    "event": "subscribe",
                    "pair": [kraken_pair],
                    "subscription": {"name": "ticker"}
                }
                
                await websocket.send(json.dumps(subscribe_message))
                self.logger.info(f"Started WebSocket stream for {symbol}")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if isinstance(data, list) and len(data) > 3:
                            # Process ticker data
                            await callback(data)
                    except Exception as e:
                        self.logger.error(f"Error processing WebSocket message: {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"WebSocket connection error for {symbol}: {str(e)}")
            raise ExchangeError(f"Failed to start WebSocket stream: {str(e)}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        signed: bool = False
    ) -> Dict[str, Any]:
        """Make HTTP request to Kraken API with proper authentication and rate limiting"""
        if not self.session:
            raise ExchangeError("Not connected to exchange")
        
        await self._check_rate_limits('request')
        
        url = f"{self.config.base_url}{endpoint}"
        headers = {'User-Agent': 'CryptoTradeBotGlobal/1.0'}
        
        if signed:
            if not data:
                data = {}
            
            # Add nonce
            data['nonce'] = str(int(time.time() * 1000000))
            
            # Create signature
            postdata = urllib.parse.urlencode(data)
            encoded = (str(data['nonce']) + postdata).encode()
            message = endpoint.encode() + hashlib.sha256(encoded).digest()
            
            signature = hmac.new(
                base64.b64decode(self.config.api_secret),
                message,
                hashlib.sha512
            )
            
            headers.update({
                'API-Key': self.config.api_key,
                'API-Sign': base64.b64encode(signature.digest()).decode()
            })
        
        try:
            if method == 'GET':
                async with self.session.get(url, params=params, headers=headers) as response:
                    return await self._handle_response(response)
            elif method == 'POST':
                async with self.session.post(url, data=data, headers=headers) as response:
                    return await self._handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {str(e)}")
            raise ExchangeError(f"Request failed: {str(e)}")
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response and check for errors"""
        try:
            data = await response.json()
            
            if response.status == 200:
                if 'error' in data and data['error']:
                    error_msg = ', '.join(data['error'])
                    if 'EAPI:Rate limit exceeded' in error_msg:
                        raise RateLimitError("Rate limit exceeded")
                    elif 'EAPI:Invalid key' in error_msg:
                        raise AuthenticationError("Invalid API key")
                    else:
                        raise ExchangeError(f"API error: {error_msg}")
                return data
            elif response.status == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status == 401:
                raise AuthenticationError("Invalid API credentials")
            else:
                raise ExchangeError(f"HTTP {response.status}")
                
        except json.JSONDecodeError:
            text = await response.text()
            raise ExchangeError(f"Invalid JSON response: {text}")
    
    async def _check_rate_limits(self, operation_type: str) -> None:
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Reset counters if time window has passed
        if current_time - self.rate_limiter['last_minute_reset'] >= 60:
            self.rate_limiter['requests_per_minute'] = 0
            self.rate_limiter['orders_per_minute'] = 0
            self.rate_limiter['last_minute_reset'] = current_time
        
        # Check limits
        if operation_type == 'request':
            if self.rate_limiter['requests_per_minute'] >= self.config.rate_limit_requests_per_minute:
                raise RateLimitError("Request rate limit exceeded")
            self.rate_limiter['requests_per_minute'] += 1
        
        elif operation_type == 'order':
            if self.rate_limiter['orders_per_minute'] >= self.config.rate_limit_orders_per_minute:
                raise RateLimitError("Order rate limit exceeded")
            self.rate_limiter['orders_per_minute'] += 1
    
    async def _get_server_time(self) -> int:
        """Get Kraken server time"""
        response = await self._make_request('GET', self.endpoints['server_time'])
        return response['result']['unixtime']
    
    async def _get_account_balance(self) -> Dict[str, str]:
        """Get account balance"""
        response = await self._make_request('POST', self.endpoints['account_balance'], signed=True)
        return response['result']
    
    async def _load_asset_pairs(self) -> None:
        """Load asset pair information for symbol conversion"""
        try:
            response = await self._make_request('GET', self.endpoints['asset_pairs'])
            self.asset_pairs = response['result']
        except Exception as e:
            self.logger.warning(f"Failed to load asset pairs: {str(e)}")
    
    def _format_symbol(self, symbol: str) -> str:
        """Convert symbol format to Kraken format"""
        symbol = symbol.upper()
        
        # Check if already in Kraken format
        if symbol in self.asset_pairs:
            return symbol
        
        # Common conversions
        conversions = {
            'BTCUSDT': 'XBTUSD',
            'BTCUSD': 'XBTUSD',
            'ETHUSDT': 'ETHUSD',
            'ETHUSD': 'ETHUSD',
            'ETHBTC': 'ETHXBT',
            'LTCUSD': 'LTCUSD',
            'LTCBTC': 'LTCXBT',
            'XRPUSD': 'XRPUSD',
            'XRPBTC': 'XRPXBT',
            'ADAUSD': 'ADAUSD',
            'ADABTC': 'ADAXBT'
        }
        
        if symbol in conversions:
            return conversions[symbol]
        
        # Try to find matching pair in asset_pairs
        for pair_name, pair_info in self.asset_pairs.items():
            if pair_info.get('altname') == symbol:
                return pair_name
        
        # Default: return as-is
        return symbol
    
    def _convert_kraken_asset(self, kraken_asset: str) -> str:
        """Convert Kraken asset name to standard format"""
        conversions = {
            'XXBT': 'BTC',
            'XBT': 'BTC',
            'XETH': 'ETH',
            'XLTC': 'LTC',
            'XXRP': 'XRP',
            'XREP': 'REP',
            'ZUSD': 'USD',
            'ZEUR': 'EUR',
            'ZGBP': 'GBP',
            'ZJPY': 'JPY'
        }
        
        return conversions.get(kraken_asset, kraken_asset)
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert internal order type to Kraken format"""
        mapping = {
            OrderType.MARKET: 'market',
            OrderType.LIMIT: 'limit',
            OrderType.STOP_LOSS: 'stop-loss',
            OrderType.STOP_LOSS_LIMIT: 'stop-loss-limit',
            OrderType.TAKE_PROFIT: 'take-profit',
            OrderType.TAKE_PROFIT_LIMIT: 'take-profit-limit'
        }
        return mapping.get(order_type, 'limit')
    
    def _convert_kraken_order_type(self, kraken_type: str) -> OrderType:
        """Convert Kraken order type to internal format"""
        mapping = {
            'market': OrderType.MARKET,
            'limit': OrderType.LIMIT,
            'stop-loss': OrderType.STOP_LOSS,
            'stop-loss-limit': OrderType.STOP_LOSS_LIMIT,
            'take-profit': OrderType.TAKE_PROFIT,
            'take-profit-limit': OrderType.TAKE_PROFIT_LIMIT
        }
        return mapping.get(kraken_type, OrderType.LIMIT)
    
    def _convert_order_status(self, kraken_status: str) -> OrderStatus:
        """Convert Kraken order status to internal format"""
        mapping = {
            'pending': OrderStatus.PENDING,
            'open': OrderStatus.PENDING,
            'closed': OrderStatus.FILLED,
            'canceled': OrderStatus.CANCELLED,
            'expired': OrderStatus.EXPIRED
        }
        return mapping.get(kraken_status, OrderStatus.PENDING)
