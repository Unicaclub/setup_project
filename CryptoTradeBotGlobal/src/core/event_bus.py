"""
CryptoTradeBotGlobal - Event Bus System
Enterprise-grade event-driven architecture for real-time trading
"""

import asyncio
import logging
import time
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json
import uuid
from datetime import datetime
import weakref
import threading
from concurrent.futures import ThreadPoolExecutor


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventType(Enum):
    """System event types"""
    # Market Data Events
    MARKET_DATA_RECEIVED = "market_data_received"
    PRICE_UPDATE = "price_update"
    ORDERBOOK_UPDATE = "orderbook_update"
    TRADE_EXECUTED = "trade_executed"
    
    # Trading Events
    SIGNAL_GENERATED = "signal_generated"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    
    # Risk Management Events
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"
    DRAWDOWN_ALERT = "drawdown_alert"
    
    # System Events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    HEALTH_CHECK = "health_check"
    ERROR_OCCURRED = "error_occurred"
    
    # Exchange Events
    EXCHANGE_CONNECTED = "exchange_connected"
    EXCHANGE_DISCONNECTED = "exchange_disconnected"
    EXCHANGE_ERROR = "exchange_error"
    
    # Strategy Events
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    STRATEGY_ERROR = "strategy_error"


@dataclass
class Event:
    """Event data structure"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'event_type': self.event_type.value,
            'data': self.data,
            'timestamp': self.timestamp,
            'event_id': self.event_id,
            'priority': self.priority.value,
            'source': self.source,
            'correlation_id': self.correlation_id,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(
            event_type=EventType(data['event_type']),
            data=data['data'],
            timestamp=data['timestamp'],
            event_id=data['event_id'],
            priority=EventPriority(data['priority']),
            source=data.get('source'),
            correlation_id=data.get('correlation_id'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3)
        )


class EventHandler:
    """Event handler wrapper"""
    
    def __init__(self, handler: Callable, priority: int = 0, async_handler: bool = False):
        self.handler = handler
        self.priority = priority
        self.async_handler = async_handler
        self.handler_id = str(uuid.uuid4())
        self.created_at = time.time()
        self.call_count = 0
        self.error_count = 0
        self.last_called = None
        self.last_error = None
    
    async def __call__(self, event: Event) -> Any:
        """Execute the handler"""
        try:
            self.call_count += 1
            self.last_called = time.time()
            
            if self.async_handler:
                return await self.handler(event)
            else:
                # Run sync handler in thread pool
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(executor, self.handler, event)
                    
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            raise


class EventBus:
    """
    Enterprise-grade event bus for real-time trading system
    
    Features:
    - Async/await support
    - Event prioritization
    - Dead letter queue
    - Event persistence
    - Handler metrics
    - Circuit breaker pattern
    - Event replay capability
    """
    
    def __init__(self, max_queue_size: int = 10000, enable_persistence: bool = True):
        self.logger = logging.getLogger(__name__)
        
        # Event handlers registry
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: List[EventHandler] = []
        
        # Event queues by priority
        self._event_queues: Dict[EventPriority, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=max_queue_size)
            for priority in EventPriority
        }
        
        # Dead letter queue for failed events
        self._dead_letter_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # Event processing control
        self._running = False
        self._processing_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Metrics and monitoring
        self._event_stats: Dict[EventType, Dict[str, int]] = defaultdict(
            lambda: {'published': 0, 'processed': 0, 'failed': 0}
        )
        self._handler_stats: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.max_queue_size = max_queue_size
        self.enable_persistence = enable_persistence
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        
        # Circuit breaker for handlers
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._circuit_breaker_threshold = 5  # failures
        self._circuit_breaker_timeout = 60  # seconds
        
        # Thread safety
        self._lock = threading.RLock()
    
    def subscribe(self, event_type: EventType, handler: Callable, 
                 priority: int = 0, async_handler: bool = None) -> str:
        """
        Subscribe to events
        
        Args:
            event_type: Type of event to subscribe to
            handler: Handler function
            priority: Handler priority (higher = executed first)
            async_handler: Whether handler is async (auto-detected if None)
            
        Returns:
            Handler ID for unsubscribing
        """
        if async_handler is None:
            async_handler = asyncio.iscoroutinefunction(handler)
        
        event_handler = EventHandler(handler, priority, async_handler)
        
        with self._lock:
            self._handlers[event_type].append(event_handler)
            # Sort by priority (descending)
            self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
            
            # Initialize handler stats
            self._handler_stats[event_handler.handler_id] = {
                'event_type': event_type.value,
                'priority': priority,
                'async': async_handler,
                'created_at': event_handler.created_at,
                'call_count': 0,
                'error_count': 0,
                'avg_execution_time': 0.0
            }
        
        self.logger.info(f"Subscribed handler {event_handler.handler_id} to {event_type.value}")
        return event_handler.handler_id
    
    def subscribe_all(self, handler: Callable, priority: int = 0, 
                     async_handler: bool = None) -> str:
        """Subscribe to all events (wildcard subscription)"""
        if async_handler is None:
            async_handler = asyncio.iscoroutinefunction(handler)
        
        event_handler = EventHandler(handler, priority, async_handler)
        
        with self._lock:
            self._wildcard_handlers.append(event_handler)
            self._wildcard_handlers.sort(key=lambda h: h.priority, reverse=True)
        
        self.logger.info(f"Subscribed wildcard handler {event_handler.handler_id}")
        return event_handler.handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe handler by ID"""
        with self._lock:
            # Remove from specific event handlers
            for event_type, handlers in self._handlers.items():
                self._handlers[event_type] = [
                    h for h in handlers if h.handler_id != handler_id
                ]
            
            # Remove from wildcard handlers
            self._wildcard_handlers = [
                h for h in self._wildcard_handlers if h.handler_id != handler_id
            ]
            
            # Remove stats
            if handler_id in self._handler_stats:
                del self._handler_stats[handler_id]
                self.logger.info(f"Unsubscribed handler {handler_id}")
                return True
        
        return False
    
    async def publish(self, event: Event) -> bool:
        """
        Publish event to the bus
        
        Args:
            event: Event to publish
            
        Returns:
            True if event was queued successfully
        """
        try:
            # Add to event history
            if self.enable_persistence:
                self._event_history.append(event)
                if len(self._event_history) > self._max_history_size:
                    self._event_history.pop(0)
            
            # Update stats
            self._event_stats[event.event_type]['published'] += 1
            
            # Queue event by priority
            queue = self._event_queues[event.priority]
            
            try:
                queue.put_nowait(event)
                self.logger.debug(f"Published event {event.event_id}: {event.event_type.value}")
                return True
            except asyncio.QueueFull:
                self.logger.error(f"Event queue full for priority {event.priority}")
                # Try to put in dead letter queue
                try:
                    self._dead_letter_queue.put_nowait(event)
                    self.logger.warning(f"Event {event.event_id} moved to dead letter queue")
                except asyncio.QueueFull:
                    self.logger.error(f"Dead letter queue full, dropping event {event.event_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error publishing event {event.event_id}: {e}")
            return False
    
    async def publish_event(self, event_type: EventType, data: Dict[str, Any],
                           priority: EventPriority = EventPriority.NORMAL,
                           source: Optional[str] = None,
                           correlation_id: Optional[str] = None) -> bool:
        """Convenience method to publish event"""
        event = Event(
            event_type=event_type,
            data=data,
            priority=priority,
            source=source,
            correlation_id=correlation_id
        )
        return await self.publish(event)
    
    async def start(self) -> None:
        """Start event processing"""
        if self._running:
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # Start processing tasks for each priority level
        for priority in EventPriority:
            task = asyncio.create_task(self._process_events(priority))
            self._processing_tasks.append(task)
        
        # Start dead letter queue processor
        dlq_task = asyncio.create_task(self._process_dead_letter_queue())
        self._processing_tasks.append(dlq_task)
        
        self.logger.info("Event bus started")
        
        # Publish startup event
        await self.publish_event(
            EventType.SYSTEM_STARTUP,
            {'timestamp': time.time()},
            priority=EventPriority.HIGH,
            source='event_bus'
        )
    
    async def stop(self) -> None:
        """Stop event processing"""
        if not self._running:
            return
        
        self.logger.info("Stopping event bus...")
        
        # Publish shutdown event
        await self.publish_event(
            EventType.SYSTEM_SHUTDOWN,
            {'timestamp': time.time()},
            priority=EventPriority.CRITICAL,
            source='event_bus'
        )
        
        self._running = False
        self._shutdown_event.set()
        
        # Cancel all processing tasks
        for task in self._processing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        
        self._processing_tasks.clear()
        self.logger.info("Event bus stopped")
    
    async def _process_events(self, priority: EventPriority) -> None:
        """Process events for a specific priority level"""
        queue = self._event_queues[priority]
        
        while self._running:
            try:
                # Wait for event or shutdown
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                await self._handle_event(event)
                queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in event processor for {priority}: {e}")
    
    async def _handle_event(self, event: Event) -> None:
        """Handle a single event"""
        start_time = time.time()
        
        try:
            # Get handlers for this event type
            handlers = self._handlers.get(event.event_type, []).copy()
            handlers.extend(self._wildcard_handlers.copy())
            
            if not handlers:
                self.logger.debug(f"No handlers for event {event.event_type.value}")
                return
            
            # Execute handlers
            for handler in handlers:
                if not self._is_circuit_breaker_open(handler.handler_id):
                    try:
                        await handler(event)
                        self._record_handler_success(handler.handler_id, start_time)
                    except Exception as e:
                        self._record_handler_error(handler.handler_id, e)
                        self.logger.error(f"Handler {handler.handler_id} failed: {e}")
            
            # Update event stats
            self._event_stats[event.event_type]['processed'] += 1
            
        except Exception as e:
            self.logger.error(f"Error handling event {event.event_id}: {e}")
            self._event_stats[event.event_type]['failed'] += 1
            
            # Retry logic
            if event.retry_count < event.max_retries:
                event.retry_count += 1
                await asyncio.sleep(2 ** event.retry_count)  # Exponential backoff
                await self.publish(event)
            else:
                # Move to dead letter queue
                try:
                    self._dead_letter_queue.put_nowait(event)
                except asyncio.QueueFull:
                    self.logger.error(f"Dead letter queue full, dropping event {event.event_id}")
    
    async def _process_dead_letter_queue(self) -> None:
        """Process dead letter queue"""
        while self._running:
            try:
                try:
                    event = await asyncio.wait_for(
                        self._dead_letter_queue.get(), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                self.logger.warning(f"Processing dead letter event {event.event_id}")
                # Could implement retry logic or special handling here
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in dead letter queue processor: {e}")
    
    def _is_circuit_breaker_open(self, handler_id: str) -> bool:
        """Check if circuit breaker is open for handler"""
        if handler_id not in self._circuit_breakers:
            return False
        
        breaker = self._circuit_breakers[handler_id]
        if breaker['state'] == 'open':
            if time.time() - breaker['opened_at'] > self._circuit_breaker_timeout:
                # Try to close circuit breaker
                breaker['state'] = 'half_open'
                return False
            return True
        
        return False
    
    def _record_handler_success(self, handler_id: str, start_time: float) -> None:
        """Record successful handler execution"""
        execution_time = time.time() - start_time
        
        if handler_id in self._handler_stats:
            stats = self._handler_stats[handler_id]
            stats['call_count'] += 1
            
            # Update average execution time
            total_time = stats['avg_execution_time'] * (stats['call_count'] - 1)
            stats['avg_execution_time'] = (total_time + execution_time) / stats['call_count']
        
        # Reset circuit breaker on success
        if handler_id in self._circuit_breakers:
            if self._circuit_breakers[handler_id]['state'] == 'half_open':
                self._circuit_breakers[handler_id]['state'] = 'closed'
                self._circuit_breakers[handler_id]['failure_count'] = 0
    
    def _record_handler_error(self, handler_id: str, error: Exception) -> None:
        """Record handler error and manage circuit breaker"""
        if handler_id in self._handler_stats:
            self._handler_stats[handler_id]['error_count'] += 1
        
        # Circuit breaker logic
        if handler_id not in self._circuit_breakers:
            self._circuit_breakers[handler_id] = {
                'state': 'closed',
                'failure_count': 0,
                'opened_at': None
            }
        
        breaker = self._circuit_breakers[handler_id]
        breaker['failure_count'] += 1
        
        if breaker['failure_count'] >= self._circuit_breaker_threshold:
            breaker['state'] = 'open'
            breaker['opened_at'] = time.time()
            self.logger.warning(f"Circuit breaker opened for handler {handler_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            'event_stats': dict(self._event_stats),
            'handler_stats': self._handler_stats.copy(),
            'queue_sizes': {
                priority.name: queue.qsize()
                for priority, queue in self._event_queues.items()
            },
            'dead_letter_queue_size': self._dead_letter_queue.qsize(),
            'circuit_breakers': self._circuit_breakers.copy(),
            'running': self._running,
            'handler_count': sum(len(handlers) for handlers in self._handlers.values()),
            'wildcard_handler_count': len(self._wildcard_handlers)
        }
    
    def get_event_history(self, event_type: Optional[EventType] = None,
                         limit: int = 100) -> List[Event]:
        """Get event history"""
        if event_type:
            events = [e for e in self._event_history if e.event_type == event_type]
        else:
            events = self._event_history.copy()
        
        return events[-limit:]
    
    async def replay_events(self, events: List[Event]) -> None:
        """Replay events"""
        self.logger.info(f"Replaying {len(events)} events")
        for event in events:
            event.event_id = str(uuid.uuid4())  # New ID for replay
            event.timestamp = time.time()
            await self.publish(event)
    
    def clear_history(self) -> None:
        """Clear event history"""
        self._event_history.clear()
        self.logger.info("Event history cleared")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            'status': 'healthy' if self._running else 'stopped',
            'uptime': time.time() - (self._handler_stats.get('system', {}).get('created_at', time.time())),
            'queue_health': {
                priority.name: {
                    'size': queue.qsize(),
                    'full': queue.full()
                }
                for priority, queue in self._event_queues.items()
            },
            'dead_letter_queue': {
                'size': self._dead_letter_queue.qsize(),
                'full': self._dead_letter_queue.full()
            },
            'active_handlers': len(self._handler_stats),
            'circuit_breakers_open': sum(
                1 for cb in self._circuit_breakers.values()
                if cb['state'] == 'open'
            )
        }
