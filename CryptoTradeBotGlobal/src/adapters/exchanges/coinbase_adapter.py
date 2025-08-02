"""
Coinbase Pro Exchange Adapter
Production-ready implementation for Coinbase Pro cryptocurrency exchange integration.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import aiohttp
import websockets
from dataclasses import dataclass

from .base_exchange import BaseExchange, OrderType, OrderSide, OrderStatus
from ...core.exceptions import ExchangeError, AuthenticationError, RateLimitError


@dataclass
class CoinbaseConfig:
    """Coinbase Pro-specific configuration"""
    api_key: str
    api_secret: str
    passphrase: str
    sandbox: bool = False
    base_url: str = "https://api.pro.coinbase.com"
    ws_url: str = "wss://ws-feed.pro.coinbase.com"
    rate_limit_requests_per_second: int = 10
    rate_limit_private_requests_per_second: int = 5


class CoinbaseAdapter(BaseExchange):
    """
    Production-ready Coinbase Pro exchange adapter with comprehensive functionality.
    
    Features:
    - REST API integration with authentication
    - WebSocket real-time data streams
    - Order management with validation
    - Rate limiting and error handling
    - Security best practices
    """
    
    def __init__(self, config: CoinbaseConfig):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.rate_limiter = self._init_rate_limiter()
        
        # Coinbase Pro-specific endpoints
        self.endpoints = {
            'products': '/products',
            'ticker': '/products/{product_id}/ticker',
            'orderbook': '/products/{product_id}/book',
            'candles': '/products/{product_id}/candles',
            'accounts': '/accounts',
            'orders': '/orders',
            'order': '/orders/{order_id}',
            'fills': '/fills',
            'time': '/time'
        }
        
        if config.sandbox:
            self.config.base_url = "https://api-public.sandbox.pro.coinbase.com"
            self.config.ws_url = "wss://ws-feed-public.sandbox.pro.coinbase.com"
    
    def _init_rate_limiter(self) -> Dict[str, Any]:
        """Initialize rate limiting counters"""
        return {
            'public_requests': 0,
            'private_requests': 0,
            'last_public_reset': time.time(),
            'last_private_reset': time.time()
        }
    
    async def connect(self) -> bool:
        """
        Establish connection to Coinbase Pro API and validate credentials.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Test connectivity and validate API key
            server_time = await self._get_server_time()
            accounts = await self._get_accounts()
            
            self.logger.info(f"Connected to Coinbase Pro API. Server time: {server_time}")
            self.logger.info(f"Found {len(accounts)} accounts")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Coinbase Pro: {str(e)}")
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
                
            self.logger.info("Disconnected from Coinbase Pro API")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {str(e)}")
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a product.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC-USD')
            
        Returns:
            Dict containing ticker information
        """
        try:
            product_id = self._format_symbol(symbol)
            endpoint = self.endpoints['ticker'].format(product_id=product_id)
            response = await self._make_request('GET', endpoint)
            
            return {
                'symbol': symbol.upper(),
                'price': Decimal(response['price']),
                'bid': Decimal(response['bid']),
                'ask': Decimal(response['ask']),
                'volume': Decimal(response['volume']),
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting ticker for {symbol}: {str(e)}")
            raise ExchangeError(f"Failed to get ticker: {str(e)}")
    
    async def get_orderbook(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        """
        Get order book for a product.
        
        Args:
            symbol: Trading pair symbol
            limit: Depth level (1, 2, or 3)
            
        Returns:
            Dict containing orderbook data
        """
        try:
            product_id = self._format_symbol(symbol)
            level = min(3, max(1, (limit // 50) + 1))  # Convert limit to level
            
            endpoint = self.endpoints['orderbook'].format(product_id=product_id)
            params = {'level': level}
            
            response = await self._make_request('GET', endpoint, params)
            
            return {
                'symbol': symbol.upper(),
                'bids': [[Decimal(price), Decimal(size)] for price, size, _ in response.get('bids', [])],
                'asks': [[Decimal(price), Decimal(size)] for price, size, _ in response.get('asks', [])],
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
        Place a new order on Coinbase Pro.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            order_type: Order type (MARKET/LIMIT)
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            time_in_force: Time in force (GTC, IOC, FOK, GTT)
            
        Returns:
            Dict containing order information
        """
        try:
            await self._check_rate_limits('private')
            
            product_id = self._format_symbol(symbol)
            
            order_data = {
                'product_id': product_id,
                'side': side.value.lower(),
                'type': self._convert_order_type(order_type),
                'time_in_force': time_in_force
            }
            
            if order_type == OrderType.MARKET:
                if side == OrderSide.BUY:
                    # For market buy orders, specify funds (quote currency amount)
                    if price:
                        order_data['funds'] = str(quantity * price)
                    else:
                        raise ValueError("Price required for market buy orders to calculate funds")
                else:
                    # For market sell orders, specify size (base currency amount)
                    order_data['size'] = str(quantity)
            else:
                # For limit orders
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                order_data['size'] = str(quantity)
                order_data['price'] = str(price)
            
            response = await self._make_request('POST', self.endpoints['orders'], data=order_data, signed=True)
            
            return {
                'order_id': response['id'],
                'symbol': symbol.upper(),
                'side': OrderSide(response['side'].upper()),
                'type': self._convert_coinbase_order_type(response['type']),
                'quantity': Decimal(response.get('size', '0')),
                'price': Decimal(response['price']) if response.get('price') else None,
                'status': self._convert_order_status(response['status']),
                'filled_quantity': Decimal(response.get('filled_size', '0')),
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            raise ExchangeError(f"Failed to place order: {str(e)}")
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            endpoint = self.endpoints['order'].format(order_id=order_id)
            response = await self._make_request('DELETE', endpoint, signed=True)
            
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
            endpoint = self.endpoints['order'].format(order_id=order_id)
            response = await self._make_request('GET', endpoint, signed=True)
            
            return {
                'order_id': response['id'],
                'symbol': symbol.upper(),
                'side': OrderSide(response['side'].upper()),
                'type': self._convert_coinbase_order_type(response['type']),
                'quantity': Decimal(response.get('size', '0')),
                'price': Decimal(response['price']) if response.get('price') else None,
                'status': self._convert_order_status(response['status']),
                'filled_quantity': Decimal(response.get('filled_size', '0')),
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting order status: {str(e)}")
            raise ExchangeError(f"Failed to get order status: {str(e)}")
    
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balances for all assets"""
        try:
            accounts = await self._get_accounts()
            balances = {}
            
            for account in accounts:
                currency = account['currency']
                available = Decimal(account['available'])
                hold = Decimal(account['hold'])
                total = available + hold
                
                if total > 0:
                    balances[currency] = {
                        'free': available,
                        'locked': hold,
                        'total': total
                    }
            
            return balances
            
        except Exception as e:
            self.logger.error(f"Error getting account balance: {str(e)}")
            raise ExchangeError(f"Failed to get account balance: {str(e)}")
    
    async def start_websocket_stream(self, symbol: str, callback) -> None:
        """Start WebSocket stream for real-time data"""
        try:
            product_id = self._format_symbol(symbol)
            
            subscribe_message = {
                "type": "subscribe",
                "product_ids": [product_id],
                "channels": ["ticker", "level2"]
            }
            
            async with websockets.connect(self.config.ws_url) as websocket:
                self.ws_connections[symbol] = websocket
                await websocket.send(json.dumps(subscribe_message))
                
                self.logger.info(f"Started WebSocket stream for {symbol}")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get('type') in ['ticker', 'l2update']:
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
        """Make HTTP request to Coinbase Pro API with proper authentication and rate limiting"""
        if not self.session:
            raise ExchangeError("Not connected to exchange")
        
        request_type = 'private' if signed else 'public'
        await self._check_rate_limits(request_type)
        
        url = f"{self.config.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if signed:
            timestamp = str(time.time())
            body = json.dumps(data) if data else ''
            message = timestamp + method + endpoint + body
            
            signature = base64.b64encode(
                hmac.new(
                    base64.b64decode(self.config.api_secret),
                    message.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')
            
            headers.update({
                'CB-ACCESS-KEY': self.config.api_key,
                'CB-ACCESS-SIGN': signature,
                'CB-ACCESS-TIMESTAMP': timestamp,
                'CB-ACCESS-PASSPHRASE': self.config.passphrase
            })
        
        try:
            if method == 'GET':
                async with self.session.get(url, params=params, headers=headers) as response:
                    return await self._handle_response(response)
            elif method == 'POST':
                async with self.session.post(url, json=data, headers=headers) as response:
                    return await self._handle_response(response)
            elif method == 'DELETE':
                async with self.session.delete(url, headers=headers) as response:
                    return await self._handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {str(e)}")
            raise ExchangeError(f"Request failed: {str(e)}")
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response and check for errors"""
        try:
            if response.status == 200:
                return await response.json()
            elif response.status == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status == 401:
                raise AuthenticationError("Invalid API credentials")
            else:
                try:
                    error_data = await response.json()
                    error_msg = error_data.get('message', f'HTTP {response.status}')
                except:
                    error_msg = f'HTTP {response.status}'
                raise ExchangeError(f"API error: {error_msg}")
                
        except json.JSONDecodeError:
            text = await response.text()
            raise ExchangeError(f"Invalid JSON response: {text}")
    
    async def _check_rate_limits(self, request_type: str) -> None:
        """Check and enforce rate limits"""
        current_time = time.time()
        
        if request_type == 'public':
            if current_time - self.rate_limiter['last_public_reset'] >= 1:
                self.rate_limiter['public_requests'] = 0
                self.rate_limiter['last_public_reset'] = current_time
            
            if self.rate_limiter['public_requests'] >= self.config.rate_limit_requests_per_second:
                await asyncio.sleep(1)
            
            self.rate_limiter['public_requests'] += 1
        
        else:  # private
            if current_time - self.rate_limiter['last_private_reset'] >= 1:
                self.rate_limiter['private_requests'] = 0
                self.rate_limiter['last_private_reset'] = current_time
            
            if self.rate_limiter['private_requests'] >= self.config.rate_limit_private_requests_per_second:
                await asyncio.sleep(1)
            
            self.rate_limiter['private_requests'] += 1
    
    async def _get_server_time(self) -> str:
        """Get Coinbase Pro server time"""
        response = await self._make_request('GET', self.endpoints['time'])
        return response['iso']
    
    async def _get_accounts(self) -> List[Dict[str, Any]]:
        """Get account information"""
        return await self._make_request('GET', self.endpoints['accounts'], signed=True)
    
    def _format_symbol(self, symbol: str) -> str:
        """Convert symbol format to Coinbase Pro format (e.g., BTCUSDT -> BTC-USD)"""
        symbol = symbol.upper()
        if '-' in symbol:
            return symbol
        
        # Common conversions
        if symbol.endswith('USDT'):
            base = symbol[:-4]
            return f"{base}-USD"
        elif symbol.endswith('USD'):
            base = symbol[:-3]
            return f"{base}-USD"
        elif symbol.endswith('BTC'):
            base = symbol[:-3]
            return f"{base}-BTC"
        elif symbol.endswith('ETH'):
            base = symbol[:-3]
            return f"{base}-ETH"
        else:
            # Default assumption: last 3 characters are quote currency
            if len(symbol) > 3:
                base = symbol[:-3]
                quote = symbol[-3:]
                return f"{base}-{quote}"
            return symbol
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert internal order type to Coinbase Pro format"""
        mapping = {
            OrderType.MARKET: 'market',
            OrderType.LIMIT: 'limit',
            OrderType.STOP_LOSS: 'stop',
            OrderType.STOP_LOSS_LIMIT: 'stop'
        }
        return mapping.get(order_type, 'limit')
    
    def _convert_coinbase_order_type(self, coinbase_type: str) -> OrderType:
        """Convert Coinbase Pro order type to internal format"""
        mapping = {
            'market': OrderType.MARKET,
            'limit': OrderType.LIMIT,
            'stop': OrderType.STOP_LOSS
        }
        return mapping.get(coinbase_type, OrderType.LIMIT)
    
    def _convert_order_status(self, coinbase_status: str) -> OrderStatus:
        """Convert Coinbase Pro order status to internal format"""
        mapping = {
            'pending': OrderStatus.PENDING,
            'open': OrderStatus.PENDING,
            'active': OrderStatus.PENDING,
            'done': OrderStatus.FILLED,
            'cancelled': OrderStatus.CANCELLED,
            'rejected': OrderStatus.REJECTED
        }
        return mapping.get(coinbase_status, OrderStatus.PENDING)
