"""
Binance Exchange Adapter
Production-ready implementation for Binance cryptocurrency exchange integration.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode

import aiohttp
import websockets
from dataclasses import dataclass

from .base_exchange import BaseExchange, OrderType, OrderSide, OrderStatus
from ...core.exceptions import ExchangeError, AuthenticationError, RateLimitError


@dataclass
class BinanceConfig:
    """Binance-specific configuration"""
    api_key: str
    api_secret: str
    testnet: bool = False
    base_url: str = "https://api.binance.com"
    ws_url: str = "wss://stream.binance.com:9443/ws/"
    rate_limit_requests_per_minute: int = 1200
    rate_limit_orders_per_second: int = 10
    rate_limit_orders_per_day: int = 200000


class BinanceAdapter(BaseExchange):
    """
    Production-ready Binance exchange adapter with comprehensive functionality.
    
    Features:
    - REST API integration with authentication
    - WebSocket real-time data streams
    - Order management with validation
    - Rate limiting and error handling
    - Security best practices
    """
    
    def __init__(self, config: BinanceConfig):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.rate_limiter = self._init_rate_limiter()
        
        # Binance-specific endpoints
        self.endpoints = {
            'ticker': '/api/v3/ticker/24hr',
            'orderbook': '/api/v3/depth',
            'klines': '/api/v3/klines',
            'account': '/api/v3/account',
            'order': '/api/v3/order',
            'orders': '/api/v3/allOrders',
            'open_orders': '/api/v3/openOrders',
            'exchange_info': '/api/v3/exchangeInfo',
            'server_time': '/api/v3/time'
        }
        
        if config.testnet:
            self.config.base_url = "https://testnet.binance.vision"
            self.config.ws_url = "wss://testnet.binance.vision/ws/"
    
    def _init_rate_limiter(self) -> Dict[str, Any]:
        """Initialize rate limiting counters"""
        return {
            'requests_per_minute': 0,
            'orders_per_second': 0,
            'orders_per_day': 0,
            'last_minute_reset': time.time(),
            'last_second_reset': time.time(),
            'last_day_reset': time.time()
        }
    
    async def connect(self) -> bool:
        """
        Establish connection to Binance API and validate credentials.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'X-MBX-APIKEY': self.config.api_key}
            )
            
            # Test connectivity and validate API key
            server_time = await self._get_server_time()
            account_info = await self._get_account_info()
            
            self.logger.info(f"Connected to Binance API. Server time: {server_time}")
            self.logger.info(f"Account status: {account_info.get('accountType', 'Unknown')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Binance: {str(e)}")
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
                
            self.logger.info("Disconnected from Binance API")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {str(e)}")
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24hr ticker price change statistics.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Dict containing ticker information
        """
        try:
            params = {'symbol': symbol.upper()}
            response = await self._make_request('GET', self.endpoints['ticker'], params)
            
            return {
                'symbol': response['symbol'],
                'price': Decimal(response['lastPrice']),
                'bid': Decimal(response['bidPrice']),
                'ask': Decimal(response['askPrice']),
                'volume': Decimal(response['volume']),
                'change_24h': Decimal(response['priceChangePercent']),
                'high_24h': Decimal(response['highPrice']),
                'low_24h': Decimal(response['lowPrice']),
                'timestamp': int(response['closeTime'])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting ticker for {symbol}: {str(e)}")
            raise ExchangeError(f"Failed to get ticker: {str(e)}")
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of entries to return (5, 10, 20, 50, 100, 500, 1000, 5000)
            
        Returns:
            Dict containing orderbook data
        """
        try:
            params = {
                'symbol': symbol.upper(),
                'limit': min(limit, 5000)  # Binance max limit
            }
            
            response = await self._make_request('GET', self.endpoints['orderbook'], params)
            
            return {
                'symbol': symbol.upper(),
                'bids': [[Decimal(price), Decimal(qty)] for price, qty in response['bids']],
                'asks': [[Decimal(price), Decimal(qty)] for price, qty in response['asks']],
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
        Place a new order on Binance.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            order_type: Order type (MARKET/LIMIT/STOP_LOSS/etc.)
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            time_in_force: Time in force (GTC, IOC, FOK)
            
        Returns:
            Dict containing order information
        """
        try:
            await self._check_rate_limits('order')
            
            params = {
                'symbol': symbol.upper(),
                'side': side.value,
                'type': self._convert_order_type(order_type),
                'quantity': str(quantity),
                'timeInForce': time_in_force,
                'timestamp': int(time.time() * 1000)
            }
            
            if order_type in [OrderType.LIMIT, OrderType.STOP_LOSS_LIMIT]:
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                params['price'] = str(price)
            
            # Add stop price for stop orders
            if 'stopPrice' in kwargs:
                params['stopPrice'] = str(kwargs['stopPrice'])
            
            response = await self._make_request('POST', self.endpoints['order'], params, signed=True)
            
            return {
                'order_id': response['orderId'],
                'client_order_id': response['clientOrderId'],
                'symbol': response['symbol'],
                'side': OrderSide(response['side']),
                'type': self._convert_binance_order_type(response['type']),
                'quantity': Decimal(response['origQty']),
                'price': Decimal(response['price']) if response['price'] != '0.00000000' else None,
                'status': self._convert_order_status(response['status']),
                'filled_quantity': Decimal(response['executedQty']),
                'timestamp': response['transactTime']
            }
            
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            raise ExchangeError(f"Failed to place order: {str(e)}")
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            params = {
                'symbol': symbol.upper(),
                'orderId': order_id,
                'timestamp': int(time.time() * 1000)
            }
            
            response = await self._make_request('DELETE', self.endpoints['order'], params, signed=True)
            
            return {
                'order_id': response['orderId'],
                'symbol': response['symbol'],
                'status': self._convert_order_status(response['status'])
            }
            
        except Exception as e:
            self.logger.error(f"Error canceling order {order_id}: {str(e)}")
            raise ExchangeError(f"Failed to cancel order: {str(e)}")
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order"""
        try:
            params = {
                'symbol': symbol.upper(),
                'orderId': order_id,
                'timestamp': int(time.time() * 1000)
            }
            
            response = await self._make_request('GET', self.endpoints['order'], params, signed=True)
            
            return {
                'order_id': response['orderId'],
                'symbol': response['symbol'],
                'side': OrderSide(response['side']),
                'type': self._convert_binance_order_type(response['type']),
                'quantity': Decimal(response['origQty']),
                'price': Decimal(response['price']) if response['price'] != '0.00000000' else None,
                'status': self._convert_order_status(response['status']),
                'filled_quantity': Decimal(response['executedQty']),
                'timestamp': response['time']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting order status: {str(e)}")
            raise ExchangeError(f"Failed to get order status: {str(e)}")
    
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balances for all assets"""
        try:
            account_info = await self._get_account_info()
            balances = {}
            
            for balance in account_info['balances']:
                asset = balance['asset']
                free = Decimal(balance['free'])
                locked = Decimal(balance['locked'])
                total = free + locked
                
                if total > 0:
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total
                    }
            
            return balances
            
        except Exception as e:
            self.logger.error(f"Error getting account balance: {str(e)}")
            raise ExchangeError(f"Failed to get account balance: {str(e)}")
    
    async def start_websocket_stream(self, symbol: str, callback) -> None:
        """Start WebSocket stream for real-time data"""
        try:
            stream_name = f"{symbol.lower()}@ticker"
            ws_url = f"{self.config.ws_url}{stream_name}"
            
            async with websockets.connect(ws_url) as websocket:
                self.ws_connections[symbol] = websocket
                self.logger.info(f"Started WebSocket stream for {symbol}")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
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
        signed: bool = False
    ) -> Dict[str, Any]:
        """Make HTTP request to Binance API with proper authentication and rate limiting"""
        if not self.session:
            raise ExchangeError("Not connected to exchange")
        
        await self._check_rate_limits('request')
        
        url = f"{self.config.base_url}{endpoint}"
        params = params or {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            signature = hmac.new(
                self.config.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            params['signature'] = signature
        
        try:
            if method == 'GET':
                async with self.session.get(url, params=params) as response:
                    return await self._handle_response(response)
            elif method == 'POST':
                async with self.session.post(url, data=params) as response:
                    return await self._handle_response(response)
            elif method == 'DELETE':
                async with self.session.delete(url, data=params) as response:
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
                return data
            elif response.status == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status == 401:
                raise AuthenticationError("Invalid API credentials")
            else:
                error_msg = data.get('msg', f'HTTP {response.status}')
                raise ExchangeError(f"API error: {error_msg}")
                
        except json.JSONDecodeError:
            text = await response.text()
            raise ExchangeError(f"Invalid JSON response: {text}")
    
    async def _check_rate_limits(self, operation_type: str) -> None:
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Reset counters if time windows have passed
        if current_time - self.rate_limiter['last_minute_reset'] >= 60:
            self.rate_limiter['requests_per_minute'] = 0
            self.rate_limiter['last_minute_reset'] = current_time
        
        if current_time - self.rate_limiter['last_second_reset'] >= 1:
            self.rate_limiter['orders_per_second'] = 0
            self.rate_limiter['last_second_reset'] = current_time
        
        if current_time - self.rate_limiter['last_day_reset'] >= 86400:
            self.rate_limiter['orders_per_day'] = 0
            self.rate_limiter['last_day_reset'] = current_time
        
        # Check limits
        if operation_type == 'request':
            if self.rate_limiter['requests_per_minute'] >= self.config.rate_limit_requests_per_minute:
                raise RateLimitError("Request rate limit exceeded")
            self.rate_limiter['requests_per_minute'] += 1
        
        elif operation_type == 'order':
            if self.rate_limiter['orders_per_second'] >= self.config.rate_limit_orders_per_second:
                await asyncio.sleep(1)  # Wait for next second
            if self.rate_limiter['orders_per_day'] >= self.config.rate_limit_orders_per_day:
                raise RateLimitError("Daily order limit exceeded")
            
            self.rate_limiter['orders_per_second'] += 1
            self.rate_limiter['orders_per_day'] += 1
    
    async def _get_server_time(self) -> int:
        """Get Binance server time"""
        response = await self._make_request('GET', self.endpoints['server_time'])
        return response['serverTime']
    
    async def _get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return await self._make_request('GET', self.endpoints['account'], signed=True)
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert internal order type to Binance format"""
        mapping = {
            OrderType.MARKET: 'MARKET',
            OrderType.LIMIT: 'LIMIT',
            OrderType.STOP_LOSS: 'STOP_LOSS',
            OrderType.STOP_LOSS_LIMIT: 'STOP_LOSS_LIMIT',
            OrderType.TAKE_PROFIT: 'TAKE_PROFIT',
            OrderType.TAKE_PROFIT_LIMIT: 'TAKE_PROFIT_LIMIT'
        }
        return mapping.get(order_type, 'LIMIT')
    
    def _convert_binance_order_type(self, binance_type: str) -> OrderType:
        """Convert Binance order type to internal format"""
        mapping = {
            'MARKET': OrderType.MARKET,
            'LIMIT': OrderType.LIMIT,
            'STOP_LOSS': OrderType.STOP_LOSS,
            'STOP_LOSS_LIMIT': OrderType.STOP_LOSS_LIMIT,
            'TAKE_PROFIT': OrderType.TAKE_PROFIT,
            'TAKE_PROFIT_LIMIT': OrderType.TAKE_PROFIT_LIMIT
        }
        return mapping.get(binance_type, OrderType.LIMIT)
    
    def _convert_order_status(self, binance_status: str) -> OrderStatus:
        """Convert Binance order status to internal format"""
        mapping = {
            'NEW': OrderStatus.PENDING,
            'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
            'FILLED': OrderStatus.FILLED,
            'CANCELED': OrderStatus.CANCELLED,
            'REJECTED': OrderStatus.REJECTED,
            'EXPIRED': OrderStatus.EXPIRED
        }
        return mapping.get(binance_status, OrderStatus.PENDING)
