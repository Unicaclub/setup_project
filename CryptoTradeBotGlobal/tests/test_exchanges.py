"""
Test suite for Exchange Adapters
Comprehensive tests for exchange integration functionality.
"""

import pytest
import asyncio
import json
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
import aiohttp

from src.adapters.exchanges.base_exchange import BaseExchange, OrderType, OrderSide, OrderStatus
from src.adapters.exchanges.binance_adapter import BinanceAdapter, BinanceConfig
from src.adapters.exchanges.coinbase_adapter import CoinbaseAdapter, CoinbaseConfig
from src.adapters.exchanges.kraken_adapter import KrakenAdapter, KrakenConfig
from src.core.exceptions import ExchangeError, AuthenticationError, RateLimitError


class TestBinanceAdapter:
    """Test cases for Binance exchange adapter"""
    
    @pytest.fixture
    def binance_config(self):
        """Create test Binance configuration"""
        return BinanceConfig(
            api_key="test_api_key",
            api_secret="test_api_secret",
            testnet=True
        )
    
    @pytest.fixture
    def binance_adapter(self, binance_config):
        """Create Binance adapter instance"""
        return BinanceAdapter(binance_config)
    
    @pytest.mark.asyncio
    async def test_binance_connect_success(self, binance_adapter):
        """Test successful connection to Binance"""
        with patch.object(binance_adapter, '_get_server_time', return_value=1234567890), \
             patch.object(binance_adapter, '_get_account_info', return_value={'accountType': 'SPOT'}), \
             patch('aiohttp.ClientSession') as mock_session:
            
            result = await binance_adapter.connect()
            assert result is True
            assert binance_adapter.session is not None
    
    @pytest.mark.asyncio
    async def test_binance_connect_failure(self, binance_adapter):
        """Test failed connection to Binance"""
        with patch.object(binance_adapter, '_get_server_time', side_effect=Exception("Connection failed")):
            result = await binance_adapter.connect()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_binance_get_ticker(self, binance_adapter):
        """Test getting ticker from Binance"""
        mock_response = {
            'symbol': 'BTCUSDT',
            'lastPrice': '50000.00',
            'bidPrice': '49950.00',
            'askPrice': '50050.00',
            'volume': '1000.00',
            'priceChangePercent': '2.50',
            'highPrice': '51000.00',
            'lowPrice': '49000.00',
            'closeTime': 1234567890000
        }
        
        with patch.object(binance_adapter, '_make_request', return_value=mock_response):
            ticker = await binance_adapter.get_ticker('BTCUSDT')
            
            assert ticker['symbol'] == 'BTCUSDT'
            assert ticker['price'] == Decimal('50000.00')
            assert ticker['bid'] == Decimal('49950.00')
            assert ticker['ask'] == Decimal('50050.00')
            assert ticker['volume'] == Decimal('1000.00')
    
    @pytest.mark.asyncio
    async def test_binance_get_orderbook(self, binance_adapter):
        """Test getting orderbook from Binance"""
        mock_response = {
            'bids': [['49900.00', '1.5'], ['49850.00', '2.0']],
            'asks': [['50100.00', '1.2'], ['50150.00', '1.8']]
        }
        
        with patch.object(binance_adapter, '_make_request', return_value=mock_response):
            orderbook = await binance_adapter.get_orderbook('BTCUSDT', 100)
            
            assert orderbook['symbol'] == 'BTCUSDT'
            assert len(orderbook['bids']) == 2
            assert len(orderbook['asks']) == 2
            assert orderbook['bids'][0] == [Decimal('49900.00'), Decimal('1.5')]
            assert orderbook['asks'][0] == [Decimal('50100.00'), Decimal('1.2')]
    
    @pytest.mark.asyncio
    async def test_binance_place_order(self, binance_adapter):
        """Test placing order on Binance"""
        mock_response = {
            'orderId': 123456,
            'clientOrderId': 'test_order_123',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'origQty': '0.1',
            'price': '50000.00',
            'status': 'NEW',
            'executedQty': '0.0',
            'transactTime': 1234567890000
        }
        
        with patch.object(binance_adapter, '_make_request', return_value=mock_response), \
             patch.object(binance_adapter, '_check_rate_limits'):
            
            order = await binance_adapter.place_order(
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000.00')
            )
            
            assert order['order_id'] == 123456
            assert order['symbol'] == 'BTCUSDT'
            assert order['side'] == OrderSide.BUY
            assert order['type'] == OrderType.LIMIT
            assert order['quantity'] == Decimal('0.1')
            assert order['price'] == Decimal('50000.00')
    
    @pytest.mark.asyncio
    async def test_binance_cancel_order(self, binance_adapter):
        """Test canceling order on Binance"""
        mock_response = {
            'orderId': 123456,
            'symbol': 'BTCUSDT',
            'status': 'CANCELED'
        }
        
        with patch.object(binance_adapter, '_make_request', return_value=mock_response):
            result = await binance_adapter.cancel_order('BTCUSDT', '123456')
            
            assert result['order_id'] == '123456'
            assert result['symbol'] == 'BTCUSDT'
            assert result['status'] == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_binance_rate_limiting(self, binance_adapter):
        """Test rate limiting functionality"""
        # Test request rate limiting
        binance_adapter.rate_limiter['requests_per_minute'] = 1200  # At limit
        
        with pytest.raises(RateLimitError):
            await binance_adapter._check_rate_limits('request')
    
    def test_binance_symbol_conversion(self, binance_adapter):
        """Test symbol format conversion"""
        # Test order type conversion
        assert binance_adapter._convert_order_type(OrderType.MARKET) == 'MARKET'
        assert binance_adapter._convert_order_type(OrderType.LIMIT) == 'LIMIT'
        
        # Test order status conversion
        assert binance_adapter._convert_order_status('NEW') == OrderStatus.PENDING
        assert binance_adapter._convert_order_status('FILLED') == OrderStatus.FILLED
        assert binance_adapter._convert_order_status('CANCELED') == OrderStatus.CANCELLED


class TestCoinbaseAdapter:
    """Test cases for Coinbase Pro exchange adapter"""
    
    @pytest.fixture
    def coinbase_config(self):
        """Create test Coinbase configuration"""
        return CoinbaseConfig(
            api_key="test_api_key",
            api_secret="dGVzdF9hcGlfc2VjcmV0",  # base64 encoded
            passphrase="test_passphrase",
            sandbox=True
        )
    
    @pytest.fixture
    def coinbase_adapter(self, coinbase_config):
        """Create Coinbase adapter instance"""
        return CoinbaseAdapter(coinbase_config)
    
    @pytest.mark.asyncio
    async def test_coinbase_connect_success(self, coinbase_adapter):
        """Test successful connection to Coinbase Pro"""
        with patch.object(coinbase_adapter, '_get_server_time', return_value='2023-01-01T00:00:00Z'), \
             patch.object(coinbase_adapter, '_get_accounts', return_value=[{'currency': 'USD', 'balance': '1000'}]), \
             patch('aiohttp.ClientSession') as mock_session:
            
            result = await coinbase_adapter.connect()
            assert result is True
            assert coinbase_adapter.session is not None
    
    @pytest.mark.asyncio
    async def test_coinbase_get_ticker(self, coinbase_adapter):
        """Test getting ticker from Coinbase Pro"""
        mock_response = {
            'price': '50000.00',
            'bid': '49950.00',
            'ask': '50050.00',
            'volume': '1000.00'
        }
        
        with patch.object(coinbase_adapter, '_make_request', return_value=mock_response):
            ticker = await coinbase_adapter.get_ticker('BTC-USD')
            
            assert ticker['symbol'] == 'BTC-USD'
            assert ticker['price'] == Decimal('50000.00')
            assert ticker['bid'] == Decimal('49950.00')
            assert ticker['ask'] == Decimal('50050.00')
            assert ticker['volume'] == Decimal('1000.00')
    
    @pytest.mark.asyncio
    async def test_coinbase_place_order_limit(self, coinbase_adapter):
        """Test placing limit order on Coinbase Pro"""
        mock_response = {
            'id': 'test-order-id',
            'side': 'buy',
            'type': 'limit',
            'size': '0.1',
            'price': '50000.00',
            'status': 'pending'
        }
        
        with patch.object(coinbase_adapter, '_make_request', return_value=mock_response), \
             patch.object(coinbase_adapter, '_check_rate_limits'):
            
            order = await coinbase_adapter.place_order(
                symbol='BTC-USD',
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000.00')
            )
            
            assert order['order_id'] == 'test-order-id'
            assert order['side'] == OrderSide.BUY
            assert order['type'] == OrderType.LIMIT
    
    @pytest.mark.asyncio
    async def test_coinbase_place_order_market_buy(self, coinbase_adapter):
        """Test placing market buy order on Coinbase Pro"""
        mock_response = {
            'id': 'test-order-id',
            'side': 'buy',
            'type': 'market',
            'funds': '5000.00',
            'status': 'pending'
        }
        
        with patch.object(coinbase_adapter, '_make_request', return_value=mock_response), \
             patch.object(coinbase_adapter, '_check_rate_limits'):
            
            order = await coinbase_adapter.place_order(
                symbol='BTC-USD',
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('0.1'),
                price=Decimal('50000.00')  # Used to calculate funds
            )
            
            assert order['order_id'] == 'test-order-id'
            assert order['side'] == OrderSide.BUY
            assert order['type'] == OrderType.MARKET
    
    def test_coinbase_symbol_formatting(self, coinbase_adapter):
        """Test symbol format conversion for Coinbase Pro"""
        # Test common conversions
        assert coinbase_adapter._format_symbol('BTCUSDT') == 'BTC-USD'
        assert coinbase_adapter._format_symbol('ETHUSD') == 'ETH-USD'
        assert coinbase_adapter._format_symbol('BTC-USD') == 'BTC-USD'  # Already formatted
        
        # Test order type conversion
        assert coinbase_adapter._convert_order_type(OrderType.MARKET) == 'market'
        assert coinbase_adapter._convert_order_type(OrderType.LIMIT) == 'limit'
        
        # Test order status conversion
        assert coinbase_adapter._convert_order_status('pending') == OrderStatus.PENDING
        assert coinbase_adapter._convert_order_status('done') == OrderStatus.FILLED
        assert coinbase_adapter._convert_order_status('cancelled') == OrderStatus.CANCELLED


class TestKrakenAdapter:
    """Test cases for Kraken exchange adapter"""
    
    @pytest.fixture
    def kraken_config(self):
        """Create test Kraken configuration"""
        return KrakenConfig(
            api_key="test_api_key",
            api_secret="dGVzdF9hcGlfc2VjcmV0"  # base64 encoded
        )
    
    @pytest.fixture
    def kraken_adapter(self, kraken_config):
        """Create Kraken adapter instance"""
        return KrakenAdapter(kraken_config)
    
    @pytest.mark.asyncio
    async def test_kraken_connect_success(self, kraken_adapter):
        """Test successful connection to Kraken"""
        with patch.object(kraken_adapter, '_get_server_time', return_value=1234567890), \
             patch.object(kraken_adapter, '_get_account_balance', return_value={'ZUSD': '1000.0'}), \
             patch.object(kraken_adapter, '_load_asset_pairs'), \
             patch('aiohttp.ClientSession') as mock_session:
            
            result = await kraken_adapter.connect()
            assert result is True
            assert kraken_adapter.session is not None
    
    @pytest.mark.asyncio
    async def test_kraken_get_ticker(self, kraken_adapter):
        """Test getting ticker from Kraken"""
        mock_response = {
            'result': {
                'XBTUSD': {
                    'c': ['50000.00', '1'],  # Last trade
                    'b': ['49950.00', '1', '1'],  # Best bid
                    'a': ['50050.00', '1', '1'],  # Best ask
                    'v': ['100.0', '1000.0'],  # Volume
                    'p': ['1.5', '2.5'],  # Price change
                    'h': ['51000.0', '51500.0'],  # High
                    'l': ['49000.0', '48500.0']   # Low
                }
            }
        }
        
        with patch.object(kraken_adapter, '_make_request', return_value=mock_response), \
             patch.object(kraken_adapter, '_format_symbol', return_value='XBTUSD'):
            
            ticker = await kraken_adapter.get_ticker('BTCUSD')
            
            assert ticker['symbol'] == 'BTCUSD'
            assert ticker['price'] == Decimal('50000.00')
            assert ticker['bid'] == Decimal('49950.00')
            assert ticker['ask'] == Decimal('50050.00')
    
    @pytest.mark.asyncio
    async def test_kraken_place_order(self, kraken_adapter):
        """Test placing order on Kraken"""
        mock_response = {
            'result': {
                'txid': ['test-order-id-123']
            }
        }
        
        with patch.object(kraken_adapter, '_make_request', return_value=mock_response), \
             patch.object(kraken_adapter, '_check_rate_limits'), \
             patch.object(kraken_adapter, '_format_symbol', return_value='XBTUSD'):
            
            order = await kraken_adapter.place_order(
                symbol='BTCUSD',
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000.00')
            )
            
            assert order['order_id'] == 'test-order-id-123'
            assert order['symbol'] == 'BTCUSD'
            assert order['side'] == OrderSide.BUY
            assert order['type'] == OrderType.LIMIT
    
    @pytest.mark.asyncio
    async def test_kraken_get_order_status(self, kraken_adapter):
        """Test getting order status from Kraken"""
        mock_response = {
            'result': {
                'test-order-id': {
                    'descr': {
                        'type': 'buy',
                        'ordertype': 'limit',
                        'price': '50000.00'
                    },
                    'vol': '0.1',
                    'vol_exec': '0.05',
                    'status': 'open',
                    'opentm': 1234567890.123
                }
            }
        }
        
        with patch.object(kraken_adapter, '_make_request', return_value=mock_response):
            order_status = await kraken_adapter.get_order_status('BTCUSD', 'test-order-id')
            
            assert order_status['order_id'] == 'test-order-id'
            assert order_status['side'] == OrderSide.BUY
            assert order_status['type'] == OrderType.LIMIT
            assert order_status['quantity'] == Decimal('0.1')
            assert order_status['filled_quantity'] == Decimal('0.05')
            assert order_status['status'] == OrderStatus.PENDING
    
    def test_kraken_symbol_formatting(self, kraken_adapter):
        """Test symbol format conversion for Kraken"""
        # Test common conversions
        assert kraken_adapter._format_symbol('BTCUSD') == 'XBTUSD'
        assert kraken_adapter._format_symbol('ETHUSD') == 'ETHUSD'
        
        # Test asset name conversion
        assert kraken_adapter._convert_kraken_asset('XXBT') == 'BTC'
        assert kraken_adapter._convert_kraken_asset('ZUSD') == 'USD'
        assert kraken_adapter._convert_kraken_asset('XETH') == 'ETH'
        
        # Test order type conversion
        assert kraken_adapter._convert_order_type(OrderType.MARKET) == 'market'
        assert kraken_adapter._convert_order_type(OrderType.LIMIT) == 'limit'
        assert kraken_adapter._convert_order_type(OrderType.STOP_LOSS) == 'stop-loss'


class TestBaseExchange:
    """Test cases for BaseExchange abstract class"""
    
    def test_order_enums(self):
        """Test order-related enums"""
        # Test OrderType enum
        assert OrderType.MARKET.value == 'MARKET'
        assert OrderType.LIMIT.value == 'LIMIT'
        assert OrderType.STOP_LOSS.value == 'STOP_LOSS'
        
        # Test OrderSide enum
        assert OrderSide.BUY.value == 'BUY'
        assert OrderSide.SELL.value == 'SELL'
        
        # Test OrderStatus enum
        assert OrderStatus.PENDING.value == 'PENDING'
        assert OrderStatus.FILLED.value == 'FILLED'
        assert OrderStatus.CANCELLED.value == 'CANCELLED'
        assert OrderStatus.REJECTED.value == 'REJECTED'


class TestExchangeErrorHandling:
    """Test cases for exchange error handling"""
    
    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """Test authentication error handling"""
        config = BinanceConfig(api_key="invalid", api_secret="invalid", testnet=True)
        adapter = BinanceAdapter(config)
        
        # Mock HTTP response with 401 status
        mock_response = Mock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={'msg': 'Invalid API key'})
        
        with pytest.raises(AuthenticationError):
            await adapter._handle_response(mock_response)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test rate limit error handling"""
        config = BinanceConfig(api_key="test", api_secret="test", testnet=True)
        adapter = BinanceAdapter(config)
        
        # Mock HTTP response with 429 status
        mock_response = Mock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={'msg': 'Rate limit exceeded'})
        
        with pytest.raises(RateLimitError):
            await adapter._handle_response(mock_response)
    
    @pytest.mark.asyncio
    async def test_generic_exchange_error(self):
        """Test generic exchange error handling"""
        config = BinanceConfig(api_key="test", api_secret="test", testnet=True)
        adapter = BinanceAdapter(config)
        
        # Mock HTTP response with 500 status
        mock_response = Mock()
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value={'msg': 'Internal server error'})
        
        with pytest.raises(ExchangeError):
            await adapter._handle_response(mock_response)


class TestExchangeIntegration:
    """Integration tests for exchange adapters"""
    
    @pytest.mark.asyncio
    async def test_exchange_lifecycle(self):
        """Test complete exchange lifecycle"""
        config = BinanceConfig(api_key="test", api_secret="test", testnet=True)
        adapter = BinanceAdapter(config)
        
        # Mock all required methods
        with patch.object(adapter, '_get_server_time', return_value=1234567890), \
             patch.object(adapter, '_get_account_info', return_value={'accountType': 'SPOT'}), \
             patch('aiohttp.ClientSession') as mock_session:
            
            # Test connection
            connected = await adapter.connect()
            assert connected is True
            
            # Test disconnection
            await adapter.disconnect()
            assert adapter.session is None
    
    @pytest.mark.asyncio
    async def test_websocket_stream_mock(self):
        """Test WebSocket stream functionality (mocked)"""
        config = BinanceConfig(api_key="test", api_secret="test", testnet=True)
        adapter = BinanceAdapter(config)
        
        # Mock callback function
        callback = AsyncMock()
        
        # Mock websockets.connect
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
            mock_websocket.__aexit__ = AsyncMock(return_value=None)
            mock_websocket.__aiter__ = AsyncMock(return_value=iter(['{"test": "data"}']))
            mock_connect.return_value = mock_websocket
            
            # This would normally run indefinitely, so we'll just test the setup
            try:
                await asyncio.wait_for(
                    adapter.start_websocket_stream('BTCUSDT', callback),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                pass  # Expected for this test
            
            # Verify WebSocket connection was attempted
            mock_connect.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
