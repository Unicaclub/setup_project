# CryptoTradeBotGlobal API Documentation

## Overview

CryptoTradeBotGlobal is a production-ready cryptocurrency trading system with enterprise-grade architecture, comprehensive risk management, and multi-exchange support.

## Architecture

### Core Components

#### 1. Trading Engine (`src/core/trading_engine.py`)
The main orchestration engine that coordinates all trading activities.

**Key Features:**
- Multi-exchange order routing
- Real-time portfolio management
- Strategy execution coordination
- Risk management integration

**Main Methods:**
```python
async def start() -> None
async def stop() -> None
async def execute_strategy(strategy_name: str, params: Dict) -> Dict
async def place_order(symbol: str, side: str, quantity: Decimal, price: Decimal) -> Dict
async def get_portfolio_status() -> Dict
```

#### 2. Risk Manager (`src/core/risk_manager.py`)
Comprehensive risk management system with financial safety controls.

**Key Features:**
- Position sizing with Kelly Criterion
- Dynamic stop-loss and take-profit
- Portfolio-level risk monitoring
- Drawdown protection
- Emergency stop conditions

**Main Methods:**
```python
async def validate_order(symbol: str, side: str, quantity: Decimal, price: Decimal, portfolio_value: Decimal, available_balance: Decimal) -> Tuple[bool, str, Decimal]
async def calculate_stop_loss_take_profit(symbol: str, side: str, entry_price: Decimal, volatility: Optional[Decimal] = None) -> Tuple[Decimal, Decimal]
async def assess_portfolio_risk(portfolio_value: Decimal) -> PortfolioRisk
async def check_emergency_stop(portfolio_value: Decimal) -> Tuple[bool, str]
```

#### 3. Exchange Adapters (`src/adapters/exchanges/`)
Production-ready adapters for major cryptocurrency exchanges.

**Supported Exchanges:**
- Binance (`binance_adapter.py`)
- Coinbase Pro (`coinbase_adapter.py`)
- Kraken (`kraken_adapter.py`)

**Common Interface:**
```python
async def connect() -> bool
async def disconnect() -> None
async def get_ticker(symbol: str) -> Dict[str, Any]
async def get_orderbook(symbol: str, limit: int = 100) -> Dict[str, Any]
async def place_order(symbol: str, side: OrderSide, order_type: OrderType, quantity: Decimal, price: Optional[Decimal] = None) -> Dict[str, Any]
async def cancel_order(symbol: str, order_id: str) -> Dict[str, Any]
async def get_order_status(symbol: str, order_id: str) -> Dict[str, Any]
async def get_account_balance() -> Dict[str, Decimal]
async def start_websocket_stream(symbol: str, callback) -> None
```

## Configuration

### Environment Variables (`.env`)

```bash
# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_TESTNET=true

COINBASE_API_KEY=your_coinbase_api_key
COINBASE_API_SECRET=your_coinbase_api_secret
COINBASE_PASSPHRASE=your_coinbase_passphrase
COINBASE_SANDBOX=true

KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_API_SECRET=your_kraken_api_secret

# Database
DATABASE_URL=postgresql://user:password@localhost/cryptobot

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading.log

# Risk Management
MAX_POSITION_SIZE_PERCENT=10.0
MAX_DAILY_LOSS_PERCENT=5.0
MAX_DRAWDOWN_PERCENT=15.0
```

### Risk Management Configuration (`config/risk_management.yaml`)

```yaml
risk_limits:
  max_position_size_percent: 10.0  # Max 10% of portfolio per position
  max_daily_loss_percent: 5.0     # Max 5% daily loss
  max_drawdown_percent: 15.0      # Max 15% drawdown
  max_leverage: 3.0               # Max 3x leverage
  max_open_positions: 10          # Max 10 open positions
  max_correlation_exposure: 30.0  # Max 30% in correlated assets
  stop_loss_percent: 2.0          # Default 2% stop loss
  take_profit_percent: 6.0        # Default 6% take profit
  min_risk_reward_ratio: 2.0      # Min 2:1 risk/reward
  max_consecutive_losses: 5       # Max 5 consecutive losses
  cooling_off_period_hours: 24    # 24h cooling off after max losses
```

### Exchange Configuration (`config/exchanges.yaml`)

```yaml
exchanges:
  binance:
    enabled: true
    testnet: true
    rate_limits:
      requests_per_minute: 1200
      orders_per_second: 10
      orders_per_day: 200000
    
  coinbase:
    enabled: true
    sandbox: true
    rate_limits:
      requests_per_second: 10
      private_requests_per_second: 5
    
  kraken:
    enabled: true
    rate_limits:
      requests_per_minute: 60
      orders_per_minute: 60
```

## Usage Examples

### Basic Trading Setup

```python
import asyncio
from decimal import Decimal
from src.core.trading_engine import TradingEngine
from src.core.risk_manager import RiskManager, RiskLimits
from src.adapters.exchanges.binance_adapter import BinanceAdapter, BinanceConfig

async def main():
    # Configure risk limits
    risk_limits = RiskLimits(
        max_position_size_percent=Decimal('5.0'),
        max_daily_loss_percent=Decimal('3.0'),
        max_drawdown_percent=Decimal('10.0')
    )
    
    # Initialize risk manager
    risk_manager = RiskManager(risk_limits)
    
    # Configure exchange
    binance_config = BinanceConfig(
        api_key="your_api_key",
        api_secret="your_api_secret",
        testnet=True
    )
    
    # Initialize exchange adapter
    exchange = BinanceAdapter(binance_config)
    
    # Initialize trading engine
    trading_engine = TradingEngine(
        exchanges={'binance': exchange},
        risk_manager=risk_manager
    )
    
    # Start trading
    await trading_engine.start()
    
    # Place a test order
    result = await trading_engine.place_order(
        symbol='BTCUSDT',
        side='BUY',
        quantity=Decimal('0.001'),
        price=Decimal('50000')
    )
    
    print(f"Order result: {result}")
    
    # Stop trading
    await trading_engine.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Risk Management Example

```python
from decimal import Decimal
from src.core.risk_manager import RiskManager, RiskLimits

# Initialize risk manager
risk_limits = RiskLimits()
risk_manager = RiskManager(risk_limits)

# Set daily start value for tracking
risk_manager.set_daily_start_value(Decimal('10000'))

# Validate an order
is_valid, reason, adjusted_qty = await risk_manager.validate_order(
    symbol="BTCUSD",
    side="BUY",
    quantity=Decimal('0.1'),
    price=Decimal('50000'),
    portfolio_value=Decimal('10000'),
    available_balance=Decimal('6000')
)

if is_valid:
    print(f"Order validated. Adjusted quantity: {adjusted_qty}")
else:
    print(f"Order rejected: {reason}")

# Calculate stop loss and take profit
stop_loss, take_profit = await risk_manager.calculate_stop_loss_take_profit(
    symbol="BTCUSD",
    side="BUY",
    entry_price=Decimal('50000')
)

print(f"Stop Loss: {stop_loss}, Take Profit: {take_profit}")

# Assess portfolio risk
portfolio_risk = await risk_manager.assess_portfolio_risk(Decimal('10000'))
print(f"Portfolio Risk Level: {portfolio_risk.risk_level}")
print(f"Current Drawdown: {portfolio_risk.current_drawdown}%")
```

### Exchange Adapter Example

```python
from src.adapters.exchanges.binance_adapter import BinanceAdapter, BinanceConfig
from src.adapters.exchanges.base_exchange import OrderSide, OrderType

# Configure and connect to Binance
config = BinanceConfig(
    api_key="your_api_key",
    api_secret="your_api_secret",
    testnet=True
)

adapter = BinanceAdapter(config)
await adapter.connect()

# Get market data
ticker = await adapter.get_ticker('BTCUSDT')
print(f"BTC Price: {ticker['price']}")

orderbook = await adapter.get_orderbook('BTCUSDT', 10)
print(f"Best Bid: {orderbook['bids'][0][0]}")
print(f"Best Ask: {orderbook['asks'][0][0]}")

# Place an order
order = await adapter.place_order(
    symbol='BTCUSDT',
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=Decimal('0.001'),
    price=Decimal('45000')
)

print(f"Order placed: {order['order_id']}")

# Check order status
status = await adapter.get_order_status('BTCUSDT', order['order_id'])
print(f"Order Status: {status['status']}")

# Cancel order if needed
if status['status'] == 'PENDING':
    cancel_result = await adapter.cancel_order('BTCUSDT', order['order_id'])
    print(f"Order cancelled: {cancel_result}")

await adapter.disconnect()
```

## Error Handling

The system uses a comprehensive exception hierarchy:

```python
from src.core.exceptions import (
    CryptoTradeBotError,      # Base exception
    ExchangeError,            # Exchange-related errors
    AuthenticationError,      # API authentication failures
    RateLimitError,          # Rate limit exceeded
    RiskManagementError,     # Risk management violations
    OrderError,              # Order-related errors
    ValidationError          # Data validation errors
)

try:
    await trading_engine.place_order(...)
except AuthenticationError:
    print("Invalid API credentials")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after}")
except RiskManagementError as e:
    print(f"Risk limit violation: {e.message}")
except ExchangeError as e:
    print(f"Exchange error: {e.message}")
```

## Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/

# Run specific test files
pytest tests/test_risk_manager.py
pytest tests/test_exchanges.py

# Run with coverage
pytest --cov=src tests/
```

## Security Best Practices

1. **API Key Management:**
   - Store API keys in environment variables
   - Use testnet/sandbox for development
   - Rotate keys regularly
   - Implement IP whitelisting

2. **Risk Management:**
   - Always validate orders through risk manager
   - Set conservative position sizes
   - Implement emergency stop conditions
   - Monitor drawdown continuously

3. **Error Handling:**
   - Log all trading activities
   - Implement circuit breakers
   - Handle network failures gracefully
   - Validate all external data

4. **Monitoring:**
   - Set up alerts for critical events
   - Monitor system health continuously
   - Track performance metrics
   - Implement audit trails

## Performance Optimization

1. **Connection Management:**
   - Use connection pooling
   - Implement WebSocket streams for real-time data
   - Cache frequently accessed data
   - Optimize API call frequency

2. **Risk Calculations:**
   - Cache risk metrics with TTL
   - Use efficient data structures
   - Minimize database queries
   - Implement async processing

3. **Order Management:**
   - Batch order operations when possible
   - Use exchange-specific optimizations
   - Implement order queuing
   - Monitor execution latency

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "src.main"]
```

### Environment Setup

```bash
# Production environment
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export DATABASE_URL=postgresql://...

# Start the application
python -m src.main
```

## Monitoring and Alerts

Set up monitoring for:
- Portfolio performance
- Risk metrics
- System health
- API connectivity
- Order execution latency
- Error rates

## Support and Maintenance

- Regular dependency updates
- Security patches
- Performance monitoring
- Backup strategies
- Disaster recovery plans

---

For more detailed information, refer to the source code documentation and inline comments.
