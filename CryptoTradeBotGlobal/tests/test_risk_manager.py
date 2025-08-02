"""
Test suite for Risk Manager
Comprehensive tests for risk management functionality.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch

from src.core.risk_manager import (
    RiskManager, RiskLimits, RiskLevel, PositionRisk, PortfolioRisk
)
from src.core.exceptions import RiskManagementError, RiskLimitExceededError


class TestRiskManager:
    """Test cases for RiskManager class"""
    
    @pytest.fixture
    def risk_limits(self):
        """Create test risk limits"""
        return RiskLimits(
            max_position_size_percent=Decimal('10.0'),
            max_daily_loss_percent=Decimal('5.0'),
            max_drawdown_percent=Decimal('15.0'),
            max_open_positions=5,
            stop_loss_percent=Decimal('2.0'),
            take_profit_percent=Decimal('6.0'),
            min_risk_reward_ratio=Decimal('2.0'),
            max_consecutive_losses=3
        )
    
    @pytest.fixture
    def risk_manager(self, risk_limits):
        """Create RiskManager instance"""
        return RiskManager(risk_limits)
    
    @pytest.mark.asyncio
    async def test_validate_order_success(self, risk_manager):
        """Test successful order validation"""
        # Set daily start value
        risk_manager.set_daily_start_value(Decimal('10000'))
        
        # Test valid order
        is_valid, reason, adjusted_qty = await risk_manager.validate_order(
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            portfolio_value=Decimal('10000'),
            available_balance=Decimal('6000')
        )
        
        assert is_valid is True
        assert "successfully" in reason
        assert adjusted_qty == Decimal('0.1')
    
    @pytest.mark.asyncio
    async def test_validate_order_position_size_limit(self, risk_manager):
        """Test order validation with position size limit"""
        risk_manager.set_daily_start_value(Decimal('10000'))
        
        # Test order exceeding position size limit (10% of portfolio)
        is_valid, reason, adjusted_qty = await risk_manager.validate_order(
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal('0.5'),  # $25,000 position on $10,000 portfolio
            price=Decimal('50000'),
            portfolio_value=Decimal('10000'),
            available_balance=Decimal('30000')
        )
        
        assert is_valid is True  # Should adjust quantity
        assert adjusted_qty < Decimal('0.5')  # Should be adjusted down
        expected_max_qty = Decimal('10000') * Decimal('0.1') / Decimal('50000')  # 10% of portfolio
        assert abs(adjusted_qty - expected_max_qty) < Decimal('0.001')
    
    @pytest.mark.asyncio
    async def test_validate_order_insufficient_funds(self, risk_manager):
        """Test order validation with insufficient funds"""
        risk_manager.set_daily_start_value(Decimal('10000'))
        
        # Test order with insufficient funds
        is_valid, reason, adjusted_qty = await risk_manager.validate_order(
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal('1.0'),  # $50,000 position
            price=Decimal('50000'),
            portfolio_value=Decimal('10000'),
            available_balance=Decimal('1000')  # Only $1,000 available
        )
        
        assert is_valid is True  # Should adjust to available balance
        assert adjusted_qty == Decimal('1000') / Decimal('50000')  # Adjusted to available funds
    
    @pytest.mark.asyncio
    async def test_validate_order_max_positions(self, risk_manager):
        """Test order validation with maximum positions reached"""
        risk_manager.set_daily_start_value(Decimal('10000'))
        
        # Add maximum number of positions
        for i in range(5):  # max_open_positions = 5
            await risk_manager.update_position(
                symbol=f"SYMBOL{i}",
                size=Decimal('0.1'),
                entry_price=Decimal('100'),
                current_price=Decimal('100')
            )
        
        # Try to add another position
        is_valid, reason, adjusted_qty = await risk_manager.validate_order(
            symbol="NEWBTC",
            side="BUY",
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            portfolio_value=Decimal('10000'),
            available_balance=Decimal('6000')
        )
        
        assert is_valid is False
        assert "Maximum open positions" in reason
    
    @pytest.mark.asyncio
    async def test_calculate_stop_loss_take_profit(self, risk_manager):
        """Test stop loss and take profit calculation"""
        entry_price = Decimal('50000')
        
        # Test BUY order
        stop_loss, take_profit = await risk_manager.calculate_stop_loss_take_profit(
            symbol="BTCUSD",
            side="BUY",
            entry_price=entry_price
        )
        
        expected_stop_loss = entry_price * Decimal('0.98')  # 2% stop loss
        expected_take_profit = entry_price * Decimal('1.06')  # 6% take profit
        
        assert abs(stop_loss - expected_stop_loss) < Decimal('1')
        assert abs(take_profit - expected_take_profit) < Decimal('1')
        
        # Verify risk/reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / risk
        assert risk_reward_ratio >= Decimal('2.0')  # Minimum 2:1 ratio
    
    @pytest.mark.asyncio
    async def test_calculate_stop_loss_take_profit_with_volatility(self, risk_manager):
        """Test stop loss and take profit calculation with volatility adjustment"""
        entry_price = Decimal('50000')
        volatility = Decimal('0.5')  # High volatility
        
        stop_loss, take_profit = await risk_manager.calculate_stop_loss_take_profit(
            symbol="BTCUSD",
            side="BUY",
            entry_price=entry_price,
            volatility=volatility
        )
        
        # With high volatility, stops should be wider
        stop_loss_percent = abs((entry_price - stop_loss) / entry_price * 100)
        assert stop_loss_percent > Decimal('2.0')  # Should be wider than default 2%
    
    @pytest.mark.asyncio
    async def test_update_position(self, risk_manager):
        """Test position update functionality"""
        symbol = "BTCUSD"
        size = Decimal('0.1')
        entry_price = Decimal('50000')
        current_price = Decimal('51000')  # 2% gain
        
        await risk_manager.update_position(symbol, size, entry_price, current_price)
        
        assert symbol in risk_manager.positions
        position = risk_manager.positions[symbol]
        
        assert position.symbol == symbol
        assert position.size == size
        assert position.entry_price == entry_price
        assert position.current_price == current_price
        assert position.unrealized_pnl == (current_price - entry_price) * size
        assert position.risk_level == RiskLevel.MEDIUM  # 2% gain should be medium risk
    
    @pytest.mark.asyncio
    async def test_remove_position_profit(self, risk_manager):
        """Test position removal with profit"""
        symbol = "BTCUSD"
        
        # Add position first
        await risk_manager.update_position(symbol, Decimal('0.1'), Decimal('50000'), Decimal('51000'))
        
        # Remove with profit
        realized_pnl = Decimal('100')  # $100 profit
        await risk_manager.remove_position(symbol, realized_pnl)
        
        assert symbol not in risk_manager.positions
        assert risk_manager.consecutive_losses == 0  # Should reset on profit
        assert realized_pnl in risk_manager.daily_pnl_history
    
    @pytest.mark.asyncio
    async def test_remove_position_loss(self, risk_manager):
        """Test position removal with loss"""
        symbol = "BTCUSD"
        
        # Add position first
        await risk_manager.update_position(symbol, Decimal('0.1'), Decimal('50000'), Decimal('49000'))
        
        # Remove with loss
        realized_pnl = Decimal('-100')  # $100 loss
        await risk_manager.remove_position(symbol, realized_pnl)
        
        assert symbol not in risk_manager.positions
        assert risk_manager.consecutive_losses == 1  # Should increment on loss
        assert realized_pnl in risk_manager.daily_pnl_history
    
    @pytest.mark.asyncio
    async def test_assess_portfolio_risk(self, risk_manager):
        """Test portfolio risk assessment"""
        portfolio_value = Decimal('10000')
        risk_manager.set_daily_start_value(portfolio_value)
        
        # Add some positions
        await risk_manager.update_position("BTCUSD", Decimal('0.1'), Decimal('50000'), Decimal('51000'))
        await risk_manager.update_position("ETHUSD", Decimal('1.0'), Decimal('3000'), Decimal('2950'))
        
        portfolio_risk = await risk_manager.assess_portfolio_risk(portfolio_value)
        
        assert isinstance(portfolio_risk, PortfolioRisk)
        assert portfolio_risk.total_value == portfolio_value
        assert portfolio_risk.open_positions == 2
        assert portfolio_risk.total_exposure > 0
        assert portfolio_risk.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    @pytest.mark.asyncio
    async def test_check_emergency_stop_drawdown(self, risk_manager):
        """Test emergency stop due to maximum drawdown"""
        # Set high water mark
        risk_manager.portfolio_high_water_mark = Decimal('10000')
        risk_manager.set_daily_start_value(Decimal('10000'))
        
        # Current portfolio value represents 20% drawdown (exceeds 15% limit)
        current_value = Decimal('8000')
        
        should_stop, reason = await risk_manager.check_emergency_stop(current_value)
        
        assert should_stop is True
        assert "drawdown" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_check_emergency_stop_consecutive_losses(self, risk_manager):
        """Test emergency stop due to consecutive losses"""
        risk_manager.set_daily_start_value(Decimal('10000'))
        
        # Simulate consecutive losses
        for i in range(3):  # max_consecutive_losses = 3
            await risk_manager.remove_position(f"SYMBOL{i}", Decimal('-100'))
        
        should_stop, reason = await risk_manager.check_emergency_stop(Decimal('10000'))
        
        assert should_stop is True
        assert "consecutive losses" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_cooling_off_period(self, risk_manager):
        """Test cooling off period after consecutive losses"""
        risk_manager.set_daily_start_value(Decimal('10000'))
        
        # Simulate maximum consecutive losses
        for i in range(3):  # max_consecutive_losses = 3
            await risk_manager.remove_position(f"SYMBOL{i}", Decimal('-100'))
        
        # Try to validate order during cooling off period
        is_valid, reason, _ = await risk_manager.validate_order(
            symbol="BTCUSD",
            side="BUY",
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            portfolio_value=Decimal('10000'),
            available_balance=Decimal('6000')
        )
        
        assert is_valid is False
        assert "cooling off" in reason.lower()
    
    def test_risk_level_determination(self, risk_manager):
        """Test risk level determination logic"""
        # Test low risk
        risk_level = risk_manager._determine_portfolio_risk_level(
            current_drawdown=Decimal('1.0'),
            open_positions=2,
            correlation_risk=Decimal('10.0')
        )
        assert risk_level == RiskLevel.LOW
        
        # Test high risk
        risk_level = risk_manager._determine_portfolio_risk_level(
            current_drawdown=Decimal('8.0'),
            open_positions=9,
            correlation_risk=Decimal('30.0')
        )
        assert risk_level == RiskLevel.HIGH
        
        # Test critical risk
        risk_level = risk_manager._determine_portfolio_risk_level(
            current_drawdown=Decimal('12.0'),
            open_positions=10,
            correlation_risk=Decimal('35.0')
        )
        assert risk_level == RiskLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_kelly_criterion_position_sizing(self, risk_manager):
        """Test Kelly Criterion position sizing"""
        # This tests the internal _calculate_optimal_position_size method
        optimal_qty = await risk_manager._calculate_optimal_position_size(
            symbol="BTCUSD",
            intended_quantity=Decimal('1.0'),
            price=Decimal('50000'),
            portfolio_value=Decimal('100000')
        )
        
        # Kelly sizing should be conservative
        assert optimal_qty <= Decimal('1.0')  # Should not exceed intended quantity
        assert optimal_qty > Decimal('0')     # Should be positive
    
    @pytest.mark.asyncio
    async def test_var_calculation(self, risk_manager):
        """Test Value at Risk calculation"""
        # Add some PnL history
        pnl_history = [Decimal('100'), Decimal('-50'), Decimal('200'), Decimal('-150'), 
                      Decimal('75'), Decimal('-25'), Decimal('300'), Decimal('-200'),
                      Decimal('50'), Decimal('-100')]
        
        risk_manager.daily_pnl_history = pnl_history
        
        var_95 = await risk_manager._calculate_var_95(Decimal('10000'))
        
        assert var_95 >= Decimal('0')  # VaR should be positive
        assert isinstance(var_95, Decimal)
    
    @pytest.mark.asyncio
    async def test_sharpe_ratio_calculation(self, risk_manager):
        """Test Sharpe ratio calculation"""
        # Add some PnL history with positive average return
        pnl_history = [Decimal('100'), Decimal('50'), Decimal('200'), Decimal('75'), 
                      Decimal('150'), Decimal('25'), Decimal('300'), Decimal('125'),
                      Decimal('50'), Decimal('175')]
        
        risk_manager.daily_pnl_history = pnl_history
        
        sharpe_ratio = await risk_manager._calculate_sharpe_ratio()
        
        assert isinstance(sharpe_ratio, Decimal)
        # With positive returns, Sharpe ratio should be positive
        assert sharpe_ratio > Decimal('0')


@pytest.mark.asyncio
class TestRiskLimits:
    """Test cases for RiskLimits configuration"""
    
    def test_default_risk_limits(self):
        """Test default risk limits values"""
        limits = RiskLimits()
        
        assert limits.max_position_size_percent == Decimal('10.0')
        assert limits.max_daily_loss_percent == Decimal('5.0')
        assert limits.max_drawdown_percent == Decimal('15.0')
        assert limits.max_open_positions == 10
        assert limits.stop_loss_percent == Decimal('2.0')
        assert limits.take_profit_percent == Decimal('6.0')
        assert limits.min_risk_reward_ratio == Decimal('2.0')
        assert limits.max_consecutive_losses == 5
    
    def test_custom_risk_limits(self):
        """Test custom risk limits"""
        limits = RiskLimits(
            max_position_size_percent=Decimal('5.0'),
            max_daily_loss_percent=Decimal('3.0'),
            max_drawdown_percent=Decimal('10.0'),
            max_open_positions=3
        )
        
        assert limits.max_position_size_percent == Decimal('5.0')
        assert limits.max_daily_loss_percent == Decimal('3.0')
        assert limits.max_drawdown_percent == Decimal('10.0')
        assert limits.max_open_positions == 3


class TestPositionRisk:
    """Test cases for PositionRisk data class"""
    
    def test_position_risk_creation(self):
        """Test PositionRisk object creation"""
        position = PositionRisk(
            symbol="BTCUSD",
            size=Decimal('0.1'),
            entry_price=Decimal('50000'),
            current_price=Decimal('51000'),
            unrealized_pnl=Decimal('100'),
            risk_percent=Decimal('2.0'),
            risk_level=RiskLevel.MEDIUM
        )
        
        assert position.symbol == "BTCUSD"
        assert position.size == Decimal('0.1')
        assert position.entry_price == Decimal('50000')
        assert position.current_price == Decimal('51000')
        assert position.unrealized_pnl == Decimal('100')
        assert position.risk_percent == Decimal('2.0')
        assert position.risk_level == RiskLevel.MEDIUM


class TestPortfolioRisk:
    """Test cases for PortfolioRisk data class"""
    
    def test_portfolio_risk_creation(self):
        """Test PortfolioRisk object creation"""
        portfolio_risk = PortfolioRisk(
            total_value=Decimal('10000'),
            total_exposure=Decimal('8000'),
            unrealized_pnl=Decimal('200'),
            daily_pnl=Decimal('150'),
            max_drawdown=Decimal('500'),
            current_drawdown=Decimal('2.5'),
            var_95=Decimal('300'),
            sharpe_ratio=Decimal('1.5'),
            risk_level=RiskLevel.MEDIUM,
            open_positions=5,
            correlation_risk=Decimal('20.0')
        )
        
        assert portfolio_risk.total_value == Decimal('10000')
        assert portfolio_risk.total_exposure == Decimal('8000')
        assert portfolio_risk.unrealized_pnl == Decimal('200')
        assert portfolio_risk.daily_pnl == Decimal('150')
        assert portfolio_risk.max_drawdown == Decimal('500')
        assert portfolio_risk.current_drawdown == Decimal('2.5')
        assert portfolio_risk.var_95 == Decimal('300')
        assert portfolio_risk.sharpe_ratio == Decimal('1.5')
        assert portfolio_risk.risk_level == RiskLevel.MEDIUM
        assert portfolio_risk.open_positions == 5
        assert portfolio_risk.correlation_risk == Decimal('20.0')


if __name__ == "__main__":
    pytest.main([__file__])
