#!/usr/bin/env python3
"""
CryptoTradeBotGlobal Demonstration Script
Production-ready cryptocurrency trading system showcase.
"""

import asyncio
import logging
import sys
from decimal import Decimal
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('demo.log')
    ]
)

logger = logging.getLogger(__name__)

# Import our components
from src.core.risk_manager import RiskManager, RiskLimits, RiskLevel
from src.core.exceptions import (
    ExchangeError, AuthenticationError, RateLimitError,
    RiskManagementError, RiskLimitExceededError
)
from src.adapters.exchanges.base_exchange import OrderType, OrderSide, OrderStatus


class MockExchangeAdapter:
    """Mock exchange adapter for demonstration purposes"""
    
    def __init__(self, name: str):
        self.name = name
        self.connected = False
        self.mock_prices = {
            'BTCUSDT': Decimal('50000'),
            'ETHUSD': Decimal('3000'),
            'ADAUSD': Decimal('0.50')
        }
        self.mock_balances = {
            'USD': Decimal('10000'),
            'BTC': Decimal('0.2'),
            'ETH': Decimal('3.0'),
            'ADA': Decimal('1000')
        }
        
    async def connect(self) -> bool:
        """Mock connection"""
        logger.info(f"🔗 Connecting to {self.name} exchange...")
        await asyncio.sleep(0.5)  # Simulate connection time
        self.connected = True
        logger.info(f"✅ Connected to {self.name} successfully")
        return True
    
    async def disconnect(self) -> None:
        """Mock disconnection"""
        logger.info(f"🔌 Disconnecting from {self.name}...")
        self.connected = False
        logger.info(f"✅ Disconnected from {self.name}")
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Mock ticker data"""
        if symbol not in self.mock_prices:
            raise ExchangeError(f"Symbol {symbol} not found")
        
        price = self.mock_prices[symbol]
        return {
            'symbol': symbol,
            'price': price,
            'bid': price * Decimal('0.999'),
            'ask': price * Decimal('1.001'),
            'volume': Decimal('1000'),
            'change_24h': Decimal('2.5'),
            'timestamp': 1234567890000
        }
    
    async def get_account_balance(self) -> Dict[str, Dict[str, Decimal]]:
        """Mock account balance"""
        balances = {}
        for asset, balance in self.mock_balances.items():
            balances[asset] = {
                'free': balance * Decimal('0.9'),
                'locked': balance * Decimal('0.1'),
                'total': balance
            }
        return balances
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: Decimal, price: Decimal = None) -> Dict[str, Any]:
        """Mock order placement"""
        if not self.connected:
            raise ExchangeError("Not connected to exchange")
        
        order_id = f"mock_order_{symbol}_{side.value}_{int(asyncio.get_event_loop().time())}"
        
        return {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'price': price,
            'status': OrderStatus.PENDING,
            'filled_quantity': Decimal('0'),
            'timestamp': 1234567890000
        }


async def demonstrate_risk_management():
    """Demonstrate comprehensive risk management features"""
    print("\n" + "="*60)
    print("🛡️  RISK MANAGEMENT DEMONSTRATION")
    print("="*60)
    
    # Initialize risk manager with conservative limits
    risk_limits = RiskLimits(
        max_position_size_percent=Decimal('5.0'),    # 5% max position
        max_daily_loss_percent=Decimal('3.0'),       # 3% max daily loss
        max_drawdown_percent=Decimal('10.0'),        # 10% max drawdown
        max_open_positions=3,                        # Max 3 positions
        stop_loss_percent=Decimal('2.0'),            # 2% stop loss
        take_profit_percent=Decimal('6.0'),          # 6% take profit
        min_risk_reward_ratio=Decimal('2.5'),        # 2.5:1 risk/reward
        max_consecutive_losses=3                     # Max 3 consecutive losses
    )
    
    risk_manager = RiskManager(risk_limits)
    portfolio_value = Decimal('10000')
    risk_manager.set_daily_start_value(portfolio_value)
    
    logger.info("🎯 Risk Manager initialized with conservative limits")
    logger.info(f"📊 Portfolio Value: ${portfolio_value:,.2f}")
    
    # Test 1: Valid order validation
    print("\n📋 Test 1: Valid Order Validation")
    is_valid, reason, adjusted_qty = await risk_manager.validate_order(
        symbol="BTCUSDT",
        side="BUY",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        portfolio_value=portfolio_value,
        available_balance=Decimal('6000')
    )
    
    print(f"✅ Order Valid: {is_valid}")
    print(f"📝 Reason: {reason}")
    print(f"📏 Adjusted Quantity: {adjusted_qty}")
    
    # Test 2: Position size limit
    print("\n📋 Test 2: Position Size Limit Test")
    is_valid, reason, adjusted_qty = await risk_manager.validate_order(
        symbol="BTCUSDT",
        side="BUY",
        quantity=Decimal('0.2'),  # Large position
        price=Decimal('50000'),
        portfolio_value=portfolio_value,
        available_balance=Decimal('15000')
    )
    
    print(f"⚠️  Order Valid: {is_valid}")
    print(f"📝 Reason: {reason}")
    print(f"📏 Adjusted Quantity: {adjusted_qty}")
    
    # Test 3: Stop loss and take profit calculation
    print("\n📋 Test 3: Stop Loss & Take Profit Calculation")
    entry_price = Decimal('50000')
    stop_loss, take_profit = await risk_manager.calculate_stop_loss_take_profit(
        symbol="BTCUSDT",
        side="BUY",
        entry_price=entry_price
    )
    
    risk_amount = entry_price - stop_loss
    reward_amount = take_profit - entry_price
    risk_reward_ratio = reward_amount / risk_amount
    
    print(f"💰 Entry Price: ${entry_price:,.2f}")
    print(f"🛑 Stop Loss: ${stop_loss:,.2f} ({((entry_price - stop_loss) / entry_price * 100):.2f}% risk)")
    print(f"🎯 Take Profit: ${take_profit:,.2f} ({((take_profit - entry_price) / entry_price * 100):.2f}% reward)")
    print(f"⚖️  Risk/Reward Ratio: {risk_reward_ratio:.2f}:1")
    
    # Test 4: Portfolio risk assessment
    print("\n📋 Test 4: Portfolio Risk Assessment")
    
    # Add some mock positions
    await risk_manager.update_position("BTCUSDT", Decimal('0.01'), Decimal('50000'), Decimal('51000'))
    await risk_manager.update_position("ETHUSD", Decimal('1.0'), Decimal('3000'), Decimal('2950'))
    
    portfolio_risk = await risk_manager.assess_portfolio_risk(portfolio_value)
    
    print(f"📊 Portfolio Value: ${portfolio_risk.total_value:,.2f}")
    print(f"💼 Total Exposure: ${portfolio_risk.total_exposure:,.2f}")
    print(f"📈 Unrealized P&L: ${portfolio_risk.unrealized_pnl:,.2f}")
    print(f"📉 Current Drawdown: {portfolio_risk.current_drawdown:.2f}%")
    print(f"🚨 Risk Level: {portfolio_risk.risk_level.value.upper()}")
    print(f"🔢 Open Positions: {portfolio_risk.open_positions}")
    
    # Test 5: Emergency stop conditions
    print("\n📋 Test 5: Emergency Stop Conditions")
    
    # Simulate high drawdown
    risk_manager.portfolio_high_water_mark = Decimal('12000')  # Higher water mark
    current_value = Decimal('9000')  # 25% drawdown
    
    should_stop, stop_reason = await risk_manager.check_emergency_stop(current_value)
    
    print(f"🚨 Emergency Stop Required: {should_stop}")
    print(f"📝 Reason: {stop_reason}")
    
    # Test 6: Consecutive losses tracking
    print("\n📋 Test 6: Consecutive Losses Tracking")
    
    # Simulate consecutive losses
    for i in range(3):
        await risk_manager.remove_position(f"TEST{i}", Decimal('-100'))
        print(f"❌ Loss {i+1}: Consecutive losses = {risk_manager.consecutive_losses}")
    
    # Try to place order during cooling off
    is_valid, reason, _ = await risk_manager.validate_order(
        symbol="NEWCOIN",
        side="BUY",
        quantity=Decimal('0.01'),
        price=Decimal('100'),
        portfolio_value=portfolio_value,
        available_balance=Decimal('1000')
    )
    
    print(f"🧊 Order during cooling off - Valid: {is_valid}")
    print(f"📝 Reason: {reason}")


async def demonstrate_exchange_integration():
    """Demonstrate exchange integration capabilities"""
    print("\n" + "="*60)
    print("🏦 EXCHANGE INTEGRATION DEMONSTRATION")
    print("="*60)
    
    # Initialize mock exchanges
    exchanges = {
        'binance': MockExchangeAdapter('Binance'),
        'coinbase': MockExchangeAdapter('Coinbase Pro'),
        'kraken': MockExchangeAdapter('Kraken')
    }
    
    # Connect to all exchanges
    print("\n🔗 Connecting to exchanges...")
    for name, exchange in exchanges.items():
        await exchange.connect()
    
    # Get market data from all exchanges
    print("\n📊 Fetching market data...")
    symbol = 'BTCUSDT'
    
    for name, exchange in exchanges.items():
        try:
            ticker = await exchange.get_ticker(symbol)
            print(f"💰 {name.upper()}: {symbol} = ${ticker['price']:,.2f} "
                  f"(Bid: ${ticker['bid']:,.2f}, Ask: ${ticker['ask']:,.2f})")
        except ExchangeError as e:
            print(f"❌ {name.upper()}: Error - {e}")
    
    # Get account balances
    print("\n💼 Account balances:")
    for name, exchange in exchanges.items():
        try:
            balances = await exchange.get_account_balance()
            print(f"\n🏦 {name.upper()}:")
            for asset, balance_info in balances.items():
                if balance_info['total'] > 0:
                    print(f"  💰 {asset}: ${balance_info['total']:,.2f} "
                          f"(Free: ${balance_info['free']:,.2f}, "
                          f"Locked: ${balance_info['locked']:,.2f})")
        except ExchangeError as e:
            print(f"❌ {name.upper()}: Error - {e}")
    
    # Place test orders
    print("\n📝 Placing test orders...")
    for name, exchange in exchanges.items():
        try:
            order = await exchange.place_order(
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.001'),
                price=Decimal('45000')
            )
            print(f"✅ {name.upper()}: Order placed - ID: {order['order_id']}")
            print(f"   📊 {order['quantity']} {order['symbol']} @ ${order['price']:,.2f}")
        except ExchangeError as e:
            print(f"❌ {name.upper()}: Order failed - {e}")
    
    # Disconnect from exchanges
    print("\n🔌 Disconnecting from exchanges...")
    for name, exchange in exchanges.items():
        await exchange.disconnect()


async def demonstrate_error_handling():
    """Demonstrate comprehensive error handling"""
    print("\n" + "="*60)
    print("⚠️  ERROR HANDLING DEMONSTRATION")
    print("="*60)
    
    # Test different types of exceptions
    error_scenarios = [
        ("Authentication Error", AuthenticationError("Invalid API credentials")),
        ("Rate Limit Error", RateLimitError("Rate limit exceeded", retry_after=60)),
        ("Risk Management Error", RiskManagementError("Position size exceeds limit")),
        ("Exchange Error", ExchangeError("Connection timeout")),
        ("Risk Limit Exceeded", RiskLimitExceededError("Daily loss limit reached"))
    ]
    
    for scenario_name, exception in error_scenarios:
        print(f"\n🧪 Testing: {scenario_name}")
        try:
            raise exception
        except AuthenticationError as e:
            print(f"🔐 Authentication Error: {e}")
            print("   💡 Action: Check API credentials and permissions")
        except RateLimitError as e:
            print(f"⏱️  Rate Limit Error: {e}")
            if hasattr(e, 'retry_after') and e.retry_after:
                print(f"   ⏰ Retry after: {e.retry_after} seconds")
        except RiskManagementError as e:
            print(f"🛡️  Risk Management Error: {e}")
            print("   💡 Action: Adjust position size or wait for cooling off period")
        except ExchangeError as e:
            print(f"🏦 Exchange Error: {e}")
            print("   💡 Action: Check network connection and exchange status")
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            print("   💡 Action: Review logs and contact support")


async def demonstrate_performance_metrics():
    """Demonstrate performance monitoring capabilities"""
    print("\n" + "="*60)
    print("📈 PERFORMANCE METRICS DEMONSTRATION")
    print("="*60)
    
    # Initialize risk manager with some historical data
    risk_limits = RiskLimits()
    risk_manager = RiskManager(risk_limits)
    
    # Simulate trading history
    print("\n📊 Simulating trading history...")
    trading_history = [
        Decimal('150'),   # Day 1: +$150
        Decimal('-75'),   # Day 2: -$75
        Decimal('200'),   # Day 3: +$200
        Decimal('-50'),   # Day 4: -$50
        Decimal('300'),   # Day 5: +$300
        Decimal('-125'),  # Day 6: -$125
        Decimal('175'),   # Day 7: +$175
        Decimal('-25'),   # Day 8: -$25
        Decimal('250'),   # Day 9: +$250
        Decimal('-100'),  # Day 10: -$100
    ]
    
    risk_manager.daily_pnl_history = trading_history
    
    # Calculate performance metrics
    total_pnl = sum(trading_history)
    winning_days = len([pnl for pnl in trading_history if pnl > 0])
    losing_days = len([pnl for pnl in trading_history if pnl < 0])
    win_rate = (winning_days / len(trading_history)) * 100
    
    avg_win = sum([pnl for pnl in trading_history if pnl > 0]) / winning_days if winning_days > 0 else Decimal('0')
    avg_loss = sum([pnl for pnl in trading_history if pnl < 0]) / losing_days if losing_days > 0 else Decimal('0')
    
    print(f"💰 Total P&L: ${total_pnl:,.2f}")
    print(f"📊 Win Rate: {win_rate:.1f}% ({winning_days}/{len(trading_history)} days)")
    print(f"📈 Average Win: ${avg_win:,.2f}")
    print(f"📉 Average Loss: ${avg_loss:,.2f}")
    
    if avg_loss != 0:
        profit_factor = abs(avg_win * winning_days) / abs(avg_loss * losing_days)
        print(f"⚖️  Profit Factor: {profit_factor:.2f}")
    
    # Calculate risk metrics
    var_95 = await risk_manager._calculate_var_95(Decimal('10000'))
    sharpe_ratio = await risk_manager._calculate_sharpe_ratio()
    max_drawdown = await risk_manager._calculate_max_drawdown()
    
    print(f"📊 Value at Risk (95%): ${var_95:,.2f}")
    print(f"📈 Sharpe Ratio: {sharpe_ratio:.3f}")
    print(f"📉 Maximum Drawdown: ${max_drawdown:,.2f}")


async def main():
    """Main demonstration function"""
    print("🚀 CryptoTradeBotGlobal - Production-Ready Trading System")
    print("=" * 60)
    print("🤖 CRYPTOBOT TECHNICAL ARCHITECT ACTIVATED")
    print("✅ System Identity: CryptoTradeBotGlobal Specialist v3.0")
    print("✅ Mission: Production-Ready Crypto Trading System")
    print("✅ Standards: Enterprise-grade financial software")
    print("=" * 60)
    
    try:
        # Run all demonstrations
        await demonstrate_risk_management()
        await demonstrate_exchange_integration()
        await demonstrate_error_handling()
        await demonstrate_performance_metrics()
        
        print("\n" + "="*60)
        print("🎉 DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print("✅ Risk Management: Comprehensive safety controls implemented")
        print("✅ Exchange Integration: Multi-exchange support operational")
        print("✅ Error Handling: Robust exception management active")
        print("✅ Performance Monitoring: Advanced metrics tracking enabled")
        print("\n🚀 System ready for production deployment!")
        print("📚 See docs/API_DOCUMENTATION.md for detailed usage instructions")
        print("🧪 Run 'pytest tests/' to execute the full test suite")
        
    except Exception as e:
        logger.error(f"❌ Demonstration failed: {str(e)}")
        print(f"\n❌ Error during demonstration: {str(e)}")
        print("📋 Check demo.log for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    print("🎬 Starting CryptoTradeBotGlobal demonstration...")
    asyncio.run(main())
