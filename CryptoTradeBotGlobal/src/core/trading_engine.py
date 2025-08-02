"""
CryptoTradeBotGlobal - Main Trading Engine
Enterprise-grade trading orchestration with institutional risk controls
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor

from .event_bus import EventBus, EventType, EventPriority, Event
from .performance_optimizer import performance_optimizer, profile
from config.settings import get_settings


class TradingState(Enum):
    """Trading engine states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(Enum):
    """Position side"""
    LONG = "long"
    SHORT = "short"


@dataclass
class TradingSignal:
    """Trading signal data structure"""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_name: str = ""
    symbol: str = ""
    side: PositionSide = PositionSide.LONG
    strength: float = 0.0  # Signal strength 0-1
    price: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal_id': self.signal_id,
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'side': self.side.value,
            'strength': self.strength,
            'price': self.price,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


@dataclass
class Order:
    """Order data structure"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: PositionSide = PositionSide.LONG
    order_type: OrderType = OrderType.MARKET
    quantity: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    exchange: str = ""
    strategy_name: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    filled_quantity: float = 0.0
    average_price: float = 0.0
    fees: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'status': self.status.value,
            'exchange': self.exchange,
            'strategy_name': self.strategy_name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'fees': self.fees,
            'metadata': self.metadata
        }


@dataclass
class Position:
    """Position data structure"""
    position_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: PositionSide = PositionSide.LONG
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    exchange: str = ""
    strategy_name: str = ""
    opened_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL"""
        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - current_price) * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'exchange': self.exchange,
            'strategy_name': self.strategy_name,
            'opened_at': self.opened_at,
            'updated_at': self.updated_at,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'metadata': self.metadata
        }


class RiskManager:
    """
    Enterprise-grade risk management system
    
    Features:
    - Portfolio risk limits
    - Position sizing
    - Stop-loss management
    - Drawdown protection
    - Real-time risk monitoring
    """
    
    def __init__(self, event_bus: EventBus):
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus
        self.settings = get_settings()
        
        # Risk limits from configuration
        self.max_portfolio_risk = self.settings.trading.max_daily_loss
        self.max_position_size = self.settings.trading.max_position_size
        self.max_drawdown = self.settings.trading.max_drawdown
        self.risk_per_trade = self.settings.trading.risk_per_trade
        
        # Current risk metrics
        self.current_portfolio_value = 10000.0  # Starting portfolio
        self.daily_pnl = 0.0
        self.max_daily_loss_reached = False
        self.current_drawdown = 0.0
        self.peak_portfolio_value = self.current_portfolio_value
        
        # Position tracking
        self.active_positions: Dict[str, Position] = {}
        self.daily_trades = 0
        self.risk_alerts: List[Dict[str, Any]] = []
        
        # Thread safety
        self.lock = threading.RLock()
    
    @profile("risk_manager.validate_signal")
    async def validate_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """Validate trading signal against risk parameters"""
        validation_result = {
            'approved': False,
            'reasons': [],
            'suggested_quantity': 0.0,
            'risk_score': 0.0
        }
        
        with self.lock:
            # Check if trading is allowed
            if self.max_daily_loss_reached:
                validation_result['reasons'].append("Daily loss limit reached")
                return validation_result
            
            # Check drawdown limit
            if self.current_drawdown >= self.max_drawdown:
                validation_result['reasons'].append("Maximum drawdown exceeded")
                return validation_result
            
            # Calculate position size
            suggested_quantity = self._calculate_position_size(signal)
            validation_result['suggested_quantity'] = suggested_quantity
            
            if suggested_quantity <= 0:
                validation_result['reasons'].append("Position size too small")
                return validation_result
            
            # Check position limits
            if suggested_quantity > self.max_position_size:
                validation_result['suggested_quantity'] = self.max_position_size
                validation_result['reasons'].append("Position size reduced to limit")
            
            # Check correlation limits (simplified)
            correlation_risk = self._check_correlation_risk(signal.symbol)
            if correlation_risk > 0.7:
                validation_result['reasons'].append("High correlation risk")
                validation_result['suggested_quantity'] *= 0.5  # Reduce size
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(signal, suggested_quantity)
            validation_result['risk_score'] = risk_score
            
            # Final approval
            if risk_score <= 0.8 and suggested_quantity > 0:
                validation_result['approved'] = True
            else:
                validation_result['reasons'].append("Risk score too high")
        
        return validation_result
    
    def _calculate_position_size(self, signal: TradingSignal) -> float:
        """Calculate appropriate position size based on risk parameters"""
        # Risk-based position sizing
        risk_amount = self.current_portfolio_value * self.risk_per_trade
        
        # Estimate stop loss distance (simplified)
        stop_loss_distance = signal.price * 0.03  # 3% stop loss
        
        if stop_loss_distance <= 0:
            return 0.0
        
        # Calculate quantity based on risk
        quantity = risk_amount / stop_loss_distance
        
        # Apply signal strength multiplier
        quantity *= signal.strength
        
        return max(0.0, quantity)
    
    def _check_correlation_risk(self, symbol: str) -> float:
        """Check correlation risk with existing positions"""
        # Simplified correlation check
        # In production, this would use actual correlation matrices
        similar_positions = 0
        total_positions = len(self.active_positions)
        
        for position in self.active_positions.values():
            if position.symbol.split('/')[0] == symbol.split('/')[0]:  # Same base currency
                similar_positions += 1
        
        if total_positions == 0:
            return 0.0
        
        return similar_positions / total_positions
    
    def _calculate_risk_score(self, signal: TradingSignal, quantity: float) -> float:
        """Calculate overall risk score for the signal"""
        # Multiple risk factors
        factors = []
        
        # Portfolio concentration risk
        position_value = signal.price * quantity
        concentration = position_value / self.current_portfolio_value
        factors.append(min(concentration * 2, 1.0))  # Cap at 1.0
        
        # Volatility risk (simplified)
        volatility_risk = 0.3  # Placeholder
        factors.append(volatility_risk)
        
        # Signal strength (inverse risk)
        signal_risk = 1.0 - signal.strength
        factors.append(signal_risk)
        
        # Current drawdown impact
        drawdown_risk = self.current_drawdown / self.max_drawdown
        factors.append(drawdown_risk)
        
        # Weighted average of risk factors
        weights = [0.3, 0.2, 0.3, 0.2]
        risk_score = sum(f * w for f, w in zip(factors, weights))
        
        return min(risk_score, 1.0)
    
    @profile("risk_manager.update_position")
    async def update_position(self, position: Position, current_price: float):
        """Update position with current market price"""
        with self.lock:
            position.current_price = current_price
            position.unrealized_pnl = position.calculate_pnl(current_price)
            position.updated_at = time.time()
            
            # Check stop loss
            if position.stop_loss:
                if ((position.side == PositionSide.LONG and current_price <= position.stop_loss) or
                    (position.side == PositionSide.SHORT and current_price >= position.stop_loss)):
                    
                    await self.event_bus.publish_event(
                        EventType.STOP_LOSS_TRIGGERED,
                        {
                            'position_id': position.position_id,
                            'symbol': position.symbol,
                            'current_price': current_price,
                            'stop_loss': position.stop_loss
                        },
                        priority=EventPriority.HIGH
                    )
            
            # Check take profit
            if position.take_profit:
                if ((position.side == PositionSide.LONG and current_price >= position.take_profit) or
                    (position.side == PositionSide.SHORT and current_price <= position.take_profit)):
                    
                    await self.event_bus.publish_event(
                        EventType.TAKE_PROFIT_TRIGGERED,
                        {
                            'position_id': position.position_id,
                            'symbol': position.symbol,
                            'current_price': current_price,
                            'take_profit': position.take_profit
                        },
                        priority=EventPriority.HIGH
                    )
    
    async def update_portfolio_metrics(self):
        """Update portfolio-level risk metrics"""
        with self.lock:
            # Calculate total unrealized PnL
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.active_positions.values())
            
            # Update current portfolio value
            current_value = self.current_portfolio_value + total_unrealized_pnl
            
            # Update peak value and drawdown
            if current_value > self.peak_portfolio_value:
                self.peak_portfolio_value = current_value
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = (self.peak_portfolio_value - current_value) / self.peak_portfolio_value
            
            # Check daily loss limit
            if abs(self.daily_pnl) >= self.max_portfolio_risk:
                self.max_daily_loss_reached = True
                await self.event_bus.publish_event(
                    EventType.RISK_LIMIT_EXCEEDED,
                    {
                        'type': 'daily_loss_limit',
                        'current_loss': self.daily_pnl,
                        'limit': self.max_portfolio_risk
                    },
                    priority=EventPriority.CRITICAL
                )
            
            # Check drawdown limit
            if self.current_drawdown >= self.max_drawdown:
                await self.event_bus.publish_event(
                    EventType.DRAWDOWN_ALERT,
                    {
                        'current_drawdown': self.current_drawdown,
                        'max_drawdown': self.max_drawdown,
                        'portfolio_value': current_value
                    },
                    priority=EventPriority.CRITICAL
                )
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        with self.lock:
            total_exposure = sum(abs(pos.quantity * pos.current_price) for pos in self.active_positions.values())
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.active_positions.values())
            
            return {
                'portfolio_value': self.current_portfolio_value + total_unrealized_pnl,
                'total_exposure': total_exposure,
                'daily_pnl': self.daily_pnl,
                'current_drawdown': self.current_drawdown,
                'max_daily_loss_reached': self.max_daily_loss_reached,
                'active_positions': len(self.active_positions),
                'daily_trades': self.daily_trades,
                'risk_utilization': total_exposure / self.current_portfolio_value if self.current_portfolio_value > 0 else 0
            }


class TradingEngine:
    """
    Main trading engine orchestrating all trading operations
    
    Features:
    - Signal processing and validation
    - Order management and execution
    - Position tracking and management
    - Risk management integration
    - Performance monitoring
    - Multi-strategy coordination
    """
    
    def __init__(self, event_bus: EventBus):
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus
        self.settings = get_settings()
        
        # Engine state
        self.state = TradingState.STOPPED
        self.start_time: Optional[float] = None
        
        # Components
        self.risk_manager = RiskManager(event_bus)
        
        # Data storage
        self.active_orders: Dict[str, Order] = {}
        self.active_positions: Dict[str, Position] = {}
        self.completed_orders: List[Order] = []
        self.closed_positions: List[Position] = []
        
        # Performance tracking
        self.signals_processed = 0
        self.orders_placed = 0
        self.successful_trades = 0
        self.failed_trades = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Subscribe to events
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers"""
        self.event_bus.subscribe(EventType.SIGNAL_GENERATED, self._handle_signal)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_order_filled)
        self.event_bus.subscribe(EventType.PRICE_UPDATE, self._handle_price_update)
        self.event_bus.subscribe(EventType.STOP_LOSS_TRIGGERED, self._handle_stop_loss)
        self.event_bus.subscribe(EventType.TAKE_PROFIT_TRIGGERED, self._handle_take_profit)
    
    async def start(self):
        """Start the trading engine"""
        if self.state != TradingState.STOPPED:
            self.logger.warning("Trading engine already running")
            return
        
        self.logger.info("Starting trading engine...")
        self.state = TradingState.STARTING
        
        try:
            # Start performance monitoring
            await performance_optimizer.start_monitoring()
            
            # Reset daily metrics if needed
            await self._reset_daily_metrics_if_needed()
            
            self.state = TradingState.RUNNING
            self.start_time = time.time()
            
            self.logger.info("Trading engine started successfully")
            
            # Publish startup event
            await self.event_bus.publish_event(
                EventType.SYSTEM_STARTUP,
                {
                    'component': 'trading_engine',
                    'timestamp': self.start_time,
                    'mode': self.settings.trading.mode.value
                },
                priority=EventPriority.HIGH
            )
            
        except Exception as e:
            self.state = TradingState.ERROR
            self.logger.error(f"Failed to start trading engine: {e}")
            raise
    
    async def stop(self):
        """Stop the trading engine"""
        if self.state == TradingState.STOPPED:
            return
        
        self.logger.info("Stopping trading engine...")
        self.state = TradingState.STOPPING
        
        try:
            # Cancel all pending orders
            await self._cancel_all_pending_orders()
            
            # Close all positions if configured
            if self.settings.trading.mode.value != "live":  # Don't auto-close in live mode
                await self._close_all_positions()
            
            # Stop performance monitoring
            await performance_optimizer.stop_monitoring()
            
            self.state = TradingState.STOPPED
            self.logger.info("Trading engine stopped")
            
            # Publish shutdown event
            await self.event_bus.publish_event(
                EventType.SYSTEM_SHUTDOWN,
                {
                    'component': 'trading_engine',
                    'timestamp': time.time(),
                    'uptime': time.time() - (self.start_time or 0)
                },
                priority=EventPriority.HIGH
            )
            
        except Exception as e:
            self.state = TradingState.ERROR
            self.logger.error(f"Error stopping trading engine: {e}")
            raise
    
    @profile("trading_engine.handle_signal")
    async def _handle_signal(self, event: Event):
        """Handle trading signal"""
        try:
            signal_data = event.data
            signal = TradingSignal(
                strategy_name=signal_data.get('strategy_name', ''),
                symbol=signal_data.get('symbol', ''),
                side=PositionSide(signal_data.get('side', 'long')),
                strength=signal_data.get('strength', 0.0),
                price=signal_data.get('price', 0.0),
                metadata=signal_data.get('metadata', {})
            )
            
            self.signals_processed += 1
            
            # Validate signal with risk manager
            validation = await self.risk_manager.validate_signal(signal)
            
            if validation['approved']:
                # Create and place order
                order = await self._create_order_from_signal(signal, validation['suggested_quantity'])
                await self._place_order(order)
            else:
                self.logger.info(f"Signal rejected: {validation['reasons']}")
                
        except Exception as e:
            self.logger.error(f"Error handling signal: {e}")
    
    async def _create_order_from_signal(self, signal: TradingSignal, quantity: float) -> Order:
        """Create order from validated signal"""
        order = Order(
            symbol=signal.symbol,
            side=signal.side,
            order_type=OrderType.MARKET,  # Default to market orders
            quantity=quantity,
            price=signal.price,
            exchange=self.settings.exchange.primary_exchange,
            strategy_name=signal.strategy_name,
            metadata=signal.metadata
        )
        
        # Add stop loss and take profit based on strategy
        if signal.side == PositionSide.LONG:
            order.metadata['stop_loss'] = signal.price * 0.97  # 3% stop loss
            order.metadata['take_profit'] = signal.price * 1.06  # 6% take profit
        else:
            order.metadata['stop_loss'] = signal.price * 1.03
            order.metadata['take_profit'] = signal.price * 0.94
        
        return order
    
    @profile("trading_engine.place_order")
    async def _place_order(self, order: Order):
        """Place order on exchange"""
        try:
            with self.lock:
                self.active_orders[order.order_id] = order
                self.orders_placed += 1
            
            # In production, this would integrate with exchange adapters
            # For now, simulate order placement
            order.status = OrderStatus.SUBMITTED
            
            self.logger.info(f"Order placed: {order.order_id} - {order.symbol} {order.side.value} {order.quantity}")
            
            # Publish order placed event
            await self.event_bus.publish_event(
                EventType.ORDER_PLACED,
                order.to_dict(),
                priority=EventPriority.NORMAL
            )
            
            # Simulate order fill (in production, this comes from exchange)
            if self.settings.trading.mode.value == "paper":
                await asyncio.sleep(0.1)  # Simulate network delay
                await self._simulate_order_fill(order)
                
        except Exception as e:
            order.status = OrderStatus.REJECTED
            self.logger.error(f"Failed to place order {order.order_id}: {e}")
    
    async def _simulate_order_fill(self, order: Order):
        """Simulate order fill for paper trading"""
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_price = order.price or 0.0
        order.updated_at = time.time()
        
        # Publish order filled event
        await self.event_bus.publish_event(
            EventType.ORDER_FILLED,
            order.to_dict(),
            priority=EventPriority.NORMAL
        )
    
    async def _handle_order_filled(self, event: Event):
        """Handle order filled event"""
        try:
            order_data = event.data
            order_id = order_data.get('order_id')
            
            if order_id not in self.active_orders:
                return
            
            order = self.active_orders[order_id]
            
            # Create or update position
            await self._update_position_from_order(order)
            
            # Move to completed orders
            with self.lock:
                del self.active_orders[order_id]
                self.completed_orders.append(order)
                self.successful_trades += 1
            
            self.logger.info(f"Order filled: {order_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling order fill: {e}")
    
    async def _update_position_from_order(self, order: Order):
        """Update position from filled order"""
        position_key = f"{order.symbol}_{order.strategy_name}"
        
        with self.lock:
            if position_key in self.active_positions:
                # Update existing position
                position = self.active_positions[position_key]
                # Position update logic would go here
            else:
                # Create new position
                position = Position(
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.filled_quantity,
                    entry_price=order.average_price,
                    current_price=order.average_price,
                    exchange=order.exchange,
                    strategy_name=order.strategy_name,
                    stop_loss=order.metadata.get('stop_loss'),
                    take_profit=order.metadata.get('take_profit')
                )
                
                self.active_positions[position_key] = position
                self.risk_manager.active_positions[position_key] = position
                
                # Publish position opened event
                await self.event_bus.publish_event(
                    EventType.POSITION_OPENED,
                    position.to_dict(),
                    priority=EventPriority.NORMAL
                )
    
    async def _handle_price_update(self, event: Event):
        """Handle price update event"""
        try:
            price_data = event.data
            symbol = price_data.get('symbol')
            price = price_data.get('price')
            
            if not symbol or not price:
                return
            
            # Update positions with new price
            for position in self.active_positions.values():
                if position.symbol == symbol:
                    await self.risk_manager.update_position(position, price)
            
            # Update portfolio metrics
            await self.risk_manager.update_portfolio_metrics()
            
        except Exception as e:
            self.logger.error(f"Error handling price update: {e}")
    
    async def _handle_stop_loss(self, event: Event):
        """Handle stop loss triggered event"""
        try:
            position_id = event.data.get('position_id')
            # Create market order to close position
            # Implementation would go here
            self.logger.info(f"Stop loss triggered for position {position_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling stop loss: {e}")
    
    async def _handle_take_profit(self, event: Event):
        """Handle take profit triggered event"""
        try:
            position_id = event.data.get('position_id')
            # Create market order to close position
            # Implementation would go here
            self.logger.info(f"Take profit triggered for position {position_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling take profit: {e}")
    
    async def _cancel_all_pending_orders(self):
        """Cancel all pending orders"""
        pending_orders = [order for order in self.active_orders.values() 
                         if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]]
        
        for order in pending_orders:
            order.status = OrderStatus.CANCELLED
            order.updated_at = time.time()
            
            await self.event_bus.publish_event(
                EventType.ORDER_CANCELLED,
                order.to_dict(),
                priority=EventPriority.NORMAL
            )
        
        self.logger.info(f"Cancelled {len(pending_orders)} pending orders")
    
    async def _close_all_positions(self):
        """Close all active positions"""
        for position in list(self.active_positions.values()):
            # Create closing order
            closing_order = Order(
                symbol=position.symbol,
                side=PositionSide.SHORT if position.side == PositionSide.LONG else PositionSide.LONG,
                order_type=OrderType.MARKET,
                quantity=position.quantity,
                exchange=position.exchange,
                strategy_name=position.strategy_name
            )
            
            await self._place_order(closing_order)
        
        self.logger.info(f"Initiated closing of {len(self.active_positions)} positions")
    
    async def _reset_daily_metrics_if_needed(self):
        """Reset daily metrics if new day"""
        # Implementation for daily reset logic
        pass
    
    def get_trading_stats(self) -> Dict[str, Any]:
        """Get trading statistics"""
        with self.lock:
            uptime = time.time() - (self.start_time or time.time())
            
            return {
                'state': self.state.value,
                'uptime_seconds': uptime,
                'signals_processed': self.signals_processed,
                'orders_placed': self.orders_placed,
                'successful_trades': self.successful_trades,
                'failed_trades': self.failed_trades,
                'active_orders': len(self.active_orders),
                'active_positions': len(self.active_positions),
                'success_rate': self.successful_trades / max(1, self.successful_trades + self.failed_trades),
                'risk_metrics': self.risk_manager.get_risk_metrics()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            'status': 'healthy' if self.state == TradingState.RUNNING else self.state.value,
            'uptime': time.time() - (self.start_time or time.time()),
            'components': {
                'risk_manager': 'healthy',
                'event_bus': 'healthy',
                'performance_optimizer': 'healthy'
            },
            'trading_stats': self.get_trading_stats()
        }
