"""
Risk Management System for CryptoTradeBotGlobal
Production-ready risk management with comprehensive financial safety controls.
"""

import asyncio
import logging
import time
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .exceptions import (
    RiskManagementError, RiskLimitExceededError, PositionSizeError,
    MaxDrawdownError, InsufficientFundsError
)


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskLimits:
    """Risk limits configuration"""
    max_position_size_percent: Decimal = Decimal('10.0')  # Max 10% of portfolio per position
    max_daily_loss_percent: Decimal = Decimal('5.0')     # Max 5% daily loss
    max_drawdown_percent: Decimal = Decimal('15.0')      # Max 15% drawdown
    max_leverage: Decimal = Decimal('3.0')               # Max 3x leverage
    max_open_positions: int = 10                         # Max 10 open positions
    max_correlation_exposure: Decimal = Decimal('30.0')  # Max 30% in correlated assets
    stop_loss_percent: Decimal = Decimal('2.0')          # Default 2% stop loss
    take_profit_percent: Decimal = Decimal('6.0')        # Default 6% take profit
    min_risk_reward_ratio: Decimal = Decimal('2.0')      # Min 2:1 risk/reward
    max_consecutive_losses: int = 5                       # Max 5 consecutive losses
    cooling_off_period_hours: int = 24                   # 24h cooling off after max losses


@dataclass
class PositionRisk:
    """Position risk assessment"""
    symbol: str
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    risk_percent: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    risk_level: RiskLevel = RiskLevel.LOW


@dataclass
class PortfolioRisk:
    """Portfolio risk metrics"""
    total_value: Decimal
    total_exposure: Decimal
    unrealized_pnl: Decimal
    daily_pnl: Decimal
    max_drawdown: Decimal
    current_drawdown: Decimal
    var_95: Decimal  # Value at Risk 95%
    sharpe_ratio: Decimal
    risk_level: RiskLevel
    open_positions: int
    correlation_risk: Decimal


class RiskManager:
    """
    Comprehensive risk management system for cryptocurrency trading.
    
    Features:
    - Position sizing with Kelly Criterion
    - Dynamic stop-loss and take-profit
    - Portfolio-level risk monitoring
    - Drawdown protection
    - Correlation analysis
    - Real-time risk assessment
    """
    
    def __init__(self, risk_limits: RiskLimits):
        self.risk_limits = risk_limits
        self.logger = logging.getLogger(__name__)
        
        # Risk tracking
        self.positions: Dict[str, PositionRisk] = {}
        self.daily_pnl_history: List[Decimal] = []
        self.consecutive_losses = 0
        self.last_loss_time = 0
        self.portfolio_high_water_mark = Decimal('0')
        self.daily_start_value = Decimal('0')
        
        # Risk metrics cache
        self._risk_metrics_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 60  # 60 seconds cache TTL
        
        self.logger.info("Risk Manager initialized with comprehensive safety controls")
    
    async def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        portfolio_value: Decimal,
        available_balance: Decimal
    ) -> Tuple[bool, str, Decimal]:
        """
        Validate order against risk limits.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            price: Order price
            portfolio_value: Current portfolio value
            available_balance: Available balance for trading
            
        Returns:
            Tuple of (is_valid, reason, adjusted_quantity)
        """
        try:
            # Check if in cooling off period
            if self._is_in_cooling_off_period():
                return False, "In cooling off period after consecutive losses", Decimal('0')
            
            # Check maximum open positions
            if side.upper() == 'BUY' and len(self.positions) >= self.risk_limits.max_open_positions:
                return False, f"Maximum open positions ({self.risk_limits.max_open_positions}) reached", Decimal('0')
            
            # Calculate position value
            position_value = quantity * price
            
            # Check available balance
            if side.upper() == 'BUY' and position_value > available_balance:
                # Adjust quantity to available balance
                adjusted_quantity = (available_balance / price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
                if adjusted_quantity < quantity * Decimal('0.1'):  # Less than 10% of intended size
                    return False, "Insufficient funds for meaningful position", Decimal('0')
                quantity = adjusted_quantity
                position_value = quantity * price
            
            # Check position size limits
            position_percent = (position_value / portfolio_value) * 100
            if position_percent > self.risk_limits.max_position_size_percent:
                # Adjust quantity to max position size
                max_position_value = portfolio_value * (self.risk_limits.max_position_size_percent / 100)
                adjusted_quantity = (max_position_value / price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
                
                if adjusted_quantity < quantity * Decimal('0.5'):  # Less than 50% of intended size
                    return False, f"Position size exceeds {self.risk_limits.max_position_size_percent}% limit", Decimal('0')
                
                quantity = adjusted_quantity
                position_value = quantity * price
                self.logger.warning(f"Position size adjusted from {position_percent:.2f}% to {self.risk_limits.max_position_size_percent}%")
            
            # Check daily loss limits
            current_daily_pnl = await self._calculate_daily_pnl(portfolio_value)
            daily_loss_percent = abs(current_daily_pnl / self.daily_start_value * 100) if self.daily_start_value > 0 else Decimal('0')
            
            if current_daily_pnl < 0 and daily_loss_percent >= self.risk_limits.max_daily_loss_percent:
                return False, f"Daily loss limit ({self.risk_limits.max_daily_loss_percent}%) reached", Decimal('0')
            
            # Check correlation risk (simplified - would need market data for full implementation)
            correlation_risk = await self._calculate_correlation_risk(symbol, position_value, portfolio_value)
            if correlation_risk > self.risk_limits.max_correlation_exposure:
                return False, f"Correlation risk exceeds {self.risk_limits.max_correlation_exposure}% limit", Decimal('0')
            
            # Calculate optimal position size using Kelly Criterion
            optimal_quantity = await self._calculate_optimal_position_size(
                symbol, quantity, price, portfolio_value
            )
            
            if optimal_quantity < quantity:
                quantity = optimal_quantity
                self.logger.info(f"Position size optimized using Kelly Criterion: {quantity}")
            
            return True, "Order validated successfully", quantity
            
        except Exception as e:
            self.logger.error(f"Error validating order: {str(e)}")
            return False, f"Risk validation error: {str(e)}", Decimal('0')
    
    async def calculate_stop_loss_take_profit(
        self,
        symbol: str,
        side: str,
        entry_price: Decimal,
        volatility: Optional[Decimal] = None
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate dynamic stop-loss and take-profit levels.
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            entry_price: Entry price
            volatility: Asset volatility (optional)
            
        Returns:
            Tuple of (stop_loss_price, take_profit_price)
        """
        try:
            # Use volatility-adjusted stops if available
            if volatility:
                # Adjust stop loss based on volatility (higher volatility = wider stops)
                volatility_multiplier = min(Decimal('3.0'), max(Decimal('1.0'), volatility * 10))
                stop_loss_percent = self.risk_limits.stop_loss_percent * volatility_multiplier
                take_profit_percent = self.risk_limits.take_profit_percent * volatility_multiplier
            else:
                stop_loss_percent = self.risk_limits.stop_loss_percent
                take_profit_percent = self.risk_limits.take_profit_percent
            
            if side.upper() == 'BUY':
                stop_loss = entry_price * (1 - stop_loss_percent / 100)
                take_profit = entry_price * (1 + take_profit_percent / 100)
            else:  # SELL
                stop_loss = entry_price * (1 + stop_loss_percent / 100)
                take_profit = entry_price * (1 - take_profit_percent / 100)
            
            # Ensure minimum risk/reward ratio
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            risk_reward_ratio = reward / risk if risk > 0 else Decimal('0')
            
            if risk_reward_ratio < self.risk_limits.min_risk_reward_ratio:
                # Adjust take profit to meet minimum risk/reward ratio
                if side.upper() == 'BUY':
                    take_profit = entry_price + (risk * self.risk_limits.min_risk_reward_ratio)
                else:
                    take_profit = entry_price - (risk * self.risk_limits.min_risk_reward_ratio)
            
            return stop_loss, take_profit
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss/take profit: {str(e)}")
            # Return default values
            if side.upper() == 'BUY':
                return (
                    entry_price * Decimal('0.98'),  # 2% stop loss
                    entry_price * Decimal('1.06')   # 6% take profit
                )
            else:
                return (
                    entry_price * Decimal('1.02'),  # 2% stop loss
                    entry_price * Decimal('0.94')   # 6% take profit
                )
    
    async def update_position(
        self,
        symbol: str,
        size: Decimal,
        entry_price: Decimal,
        current_price: Decimal
    ) -> None:
        """Update position information for risk tracking"""
        try:
            unrealized_pnl = (current_price - entry_price) * size
            risk_percent = abs(unrealized_pnl / (entry_price * size)) * 100 if size > 0 else Decimal('0')
            
            # Determine risk level
            if risk_percent < 1:
                risk_level = RiskLevel.LOW
            elif risk_percent < 3:
                risk_level = RiskLevel.MEDIUM
            elif risk_percent < 5:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.CRITICAL
            
            self.positions[symbol] = PositionRisk(
                symbol=symbol,
                size=size,
                entry_price=entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                risk_percent=risk_percent,
                risk_level=risk_level
            )
            
        except Exception as e:
            self.logger.error(f"Error updating position {symbol}: {str(e)}")
    
    async def remove_position(self, symbol: str, realized_pnl: Decimal) -> None:
        """Remove position and update loss tracking"""
        try:
            if symbol in self.positions:
                del self.positions[symbol]
            
            # Track consecutive losses
            if realized_pnl < 0:
                self.consecutive_losses += 1
                self.last_loss_time = time.time()
            else:
                self.consecutive_losses = 0
            
            # Add to daily PnL history
            self.daily_pnl_history.append(realized_pnl)
            
            # Keep only last 30 days
            if len(self.daily_pnl_history) > 30:
                self.daily_pnl_history = self.daily_pnl_history[-30:]
            
        except Exception as e:
            self.logger.error(f"Error removing position {symbol}: {str(e)}")
    
    async def assess_portfolio_risk(self, portfolio_value: Decimal) -> PortfolioRisk:
        """
        Assess overall portfolio risk.
        
        Args:
            portfolio_value: Current portfolio value
            
        Returns:
            PortfolioRisk object with comprehensive risk metrics
        """
        try:
            # Check cache
            current_time = time.time()
            if (current_time - self._cache_timestamp) < self._cache_ttl and 'portfolio_risk' in self._risk_metrics_cache:
                return self._risk_metrics_cache['portfolio_risk']
            
            # Calculate total exposure
            total_exposure = sum(
                abs(pos.size * pos.current_price) for pos in self.positions.values()
            )
            
            # Calculate unrealized PnL
            unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            
            # Calculate daily PnL
            daily_pnl = await self._calculate_daily_pnl(portfolio_value)
            
            # Calculate drawdown
            if portfolio_value > self.portfolio_high_water_mark:
                self.portfolio_high_water_mark = portfolio_value
            
            current_drawdown = ((self.portfolio_high_water_mark - portfolio_value) / 
                              self.portfolio_high_water_mark * 100) if self.portfolio_high_water_mark > 0 else Decimal('0')
            
            # Calculate max drawdown from history
            max_drawdown = await self._calculate_max_drawdown()
            
            # Calculate VaR (simplified)
            var_95 = await self._calculate_var_95(portfolio_value)
            
            # Calculate Sharpe ratio (simplified)
            sharpe_ratio = await self._calculate_sharpe_ratio()
            
            # Calculate correlation risk
            correlation_risk = await self._calculate_total_correlation_risk(portfolio_value)
            
            # Determine overall risk level
            risk_level = self._determine_portfolio_risk_level(
                current_drawdown, len(self.positions), correlation_risk
            )
            
            portfolio_risk = PortfolioRisk(
                total_value=portfolio_value,
                total_exposure=total_exposure,
                unrealized_pnl=unrealized_pnl,
                daily_pnl=daily_pnl,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                var_95=var_95,
                sharpe_ratio=sharpe_ratio,
                risk_level=risk_level,
                open_positions=len(self.positions),
                correlation_risk=correlation_risk
            )
            
            # Cache result
            self._risk_metrics_cache['portfolio_risk'] = portfolio_risk
            self._cache_timestamp = current_time
            
            return portfolio_risk
            
        except Exception as e:
            self.logger.error(f"Error assessing portfolio risk: {str(e)}")
            raise RiskManagementError(f"Failed to assess portfolio risk: {str(e)}")
    
    async def check_emergency_stop(self, portfolio_value: Decimal) -> Tuple[bool, str]:
        """
        Check if emergency stop conditions are met.
        
        Args:
            portfolio_value: Current portfolio value
            
        Returns:
            Tuple of (should_stop, reason)
        """
        try:
            portfolio_risk = await self.assess_portfolio_risk(portfolio_value)
            
            # Check maximum drawdown
            if portfolio_risk.current_drawdown >= self.risk_limits.max_drawdown_percent:
                return True, f"Maximum drawdown ({self.risk_limits.max_drawdown_percent}%) exceeded"
            
            # Check daily loss limit
            daily_loss_percent = abs(portfolio_risk.daily_pnl / self.daily_start_value * 100) if self.daily_start_value > 0 else Decimal('0')
            if portfolio_risk.daily_pnl < 0 and daily_loss_percent >= self.risk_limits.max_daily_loss_percent:
                return True, f"Daily loss limit ({self.risk_limits.max_daily_loss_percent}%) exceeded"
            
            # Check consecutive losses
            if self.consecutive_losses >= self.risk_limits.max_consecutive_losses:
                return True, f"Maximum consecutive losses ({self.risk_limits.max_consecutive_losses}) reached"
            
            # Check critical risk level
            if portfolio_risk.risk_level == RiskLevel.CRITICAL:
                return True, "Portfolio risk level is CRITICAL"
            
            return False, "No emergency stop conditions met"
            
        except Exception as e:
            self.logger.error(f"Error checking emergency stop: {str(e)}")
            return True, f"Emergency stop due to risk assessment error: {str(e)}"
    
    def set_daily_start_value(self, value: Decimal) -> None:
        """Set the starting portfolio value for daily tracking"""
        self.daily_start_value = value
        self.logger.info(f"Daily start value set to: {value}")
    
    # Private helper methods
    
    def _is_in_cooling_off_period(self) -> bool:
        """Check if in cooling off period after consecutive losses"""
        if self.consecutive_losses < self.risk_limits.max_consecutive_losses:
            return False
        
        cooling_off_seconds = self.risk_limits.cooling_off_period_hours * 3600
        return (time.time() - self.last_loss_time) < cooling_off_seconds
    
    async def _calculate_daily_pnl(self, current_value: Decimal) -> Decimal:
        """Calculate daily PnL"""
        if self.daily_start_value == 0:
            return Decimal('0')
        return current_value - self.daily_start_value
    
    async def _calculate_correlation_risk(
        self, 
        symbol: str, 
        position_value: Decimal, 
        portfolio_value: Decimal
    ) -> Decimal:
        """Calculate correlation risk (simplified implementation)"""
        # This is a simplified implementation
        # In production, you would use actual correlation data
        
        # Assume high correlation for similar assets
        correlated_symbols = {
            'BTC': ['BTCUSD', 'BTCUSDT', 'BTCEUR'],
            'ETH': ['ETHUSD', 'ETHUSDT', 'ETHEUR', 'ETHBTC'],
            'LTC': ['LTCUSD', 'LTCUSDT', 'LTCBTC'],
        }
        
        base_asset = symbol[:3]
        correlated_exposure = position_value
        
        for pos_symbol, pos in self.positions.items():
            pos_base = pos_symbol[:3]
            if base_asset in correlated_symbols and pos_base in correlated_symbols[base_asset]:
                correlated_exposure += abs(pos.size * pos.current_price)
        
        return (correlated_exposure / portfolio_value) * 100 if portfolio_value > 0 else Decimal('0')
    
    async def _calculate_total_correlation_risk(self, portfolio_value: Decimal) -> Decimal:
        """Calculate total correlation risk across portfolio"""
        # Simplified implementation
        return Decimal('0')  # Would implement with real correlation matrix
    
    async def _calculate_optimal_position_size(
        self,
        symbol: str,
        intended_quantity: Decimal,
        price: Decimal,
        portfolio_value: Decimal
    ) -> Decimal:
        """Calculate optimal position size using Kelly Criterion (simplified)"""
        try:
            # Simplified Kelly Criterion implementation
            # In production, you would use historical win rate and average win/loss
            
            # Assume conservative parameters
            win_rate = Decimal('0.55')  # 55% win rate
            avg_win = Decimal('0.06')   # 6% average win
            avg_loss = Decimal('0.02')  # 2% average loss
            
            # Kelly percentage
            kelly_percent = win_rate - ((1 - win_rate) / (avg_win / avg_loss))
            
            # Cap at 25% of max position size for safety
            kelly_percent = min(kelly_percent, self.risk_limits.max_position_size_percent / 100 * Decimal('0.25'))
            
            # Calculate optimal position value
            optimal_position_value = portfolio_value * kelly_percent
            optimal_quantity = optimal_position_value / price
            
            return min(intended_quantity, optimal_quantity)
            
        except Exception as e:
            self.logger.error(f"Error calculating optimal position size: {str(e)}")
            return intended_quantity
    
    async def _calculate_max_drawdown(self) -> Decimal:
        """Calculate maximum drawdown from PnL history"""
        if not self.daily_pnl_history:
            return Decimal('0')
        
        # Simplified calculation
        cumulative_pnl = Decimal('0')
        peak = Decimal('0')
        max_dd = Decimal('0')
        
        for pnl in self.daily_pnl_history:
            cumulative_pnl += pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    async def _calculate_var_95(self, portfolio_value: Decimal) -> Decimal:
        """Calculate Value at Risk at 95% confidence level"""
        if not self.daily_pnl_history or len(self.daily_pnl_history) < 10:
            return Decimal('0')
        
        # Sort PnL history
        sorted_pnl = sorted(self.daily_pnl_history)
        
        # Get 5th percentile (95% VaR)
        index = int(len(sorted_pnl) * 0.05)
        var_95 = abs(sorted_pnl[index]) if index < len(sorted_pnl) else Decimal('0')
        
        return var_95
    
    async def _calculate_sharpe_ratio(self) -> Decimal:
        """Calculate Sharpe ratio (simplified)"""
        if not self.daily_pnl_history or len(self.daily_pnl_history) < 10:
            return Decimal('0')
        
        # Calculate average return and standard deviation
        avg_return = sum(self.daily_pnl_history) / len(self.daily_pnl_history)
        
        variance = sum((pnl - avg_return) ** 2 for pnl in self.daily_pnl_history) / len(self.daily_pnl_history)
        std_dev = variance.sqrt() if variance > 0 else Decimal('1')
        
        # Assume risk-free rate of 2% annually (simplified)
        risk_free_rate = Decimal('0.02') / 365  # Daily risk-free rate
        
        sharpe_ratio = (avg_return - risk_free_rate) / std_dev if std_dev > 0 else Decimal('0')
        
        return sharpe_ratio
    
    def _determine_portfolio_risk_level(
        self,
        current_drawdown: Decimal,
        open_positions: int,
        correlation_risk: Decimal
    ) -> RiskLevel:
        """Determine overall portfolio risk level"""
        risk_score = 0
        
        # Drawdown risk
        if current_drawdown > 10:
            risk_score += 3
        elif current_drawdown > 5:
            risk_score += 2
        elif current_drawdown > 2:
            risk_score += 1
        
        # Position concentration risk
        if open_positions > 8:
            risk_score += 2
        elif open_positions > 5:
            risk_score += 1
        
        # Correlation risk
        if correlation_risk > 25:
            risk_score += 2
        elif correlation_risk > 15:
            risk_score += 1
        
        # Consecutive losses risk
        if self.consecutive_losses >= 4:
            risk_score += 2
        elif self.consecutive_losses >= 2:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 6:
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
