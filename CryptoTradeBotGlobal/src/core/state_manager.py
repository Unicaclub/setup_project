"""
CryptoTradeBotGlobal - State Management System
Enterprise-grade state persistence and recovery for trading operations
"""

import asyncio
import json
import logging
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
import pickle
import sqlite3
from datetime import datetime, timedelta

from .event_bus import EventBus, EventType, EventPriority, Event
from .performance_optimizer import profile
from config.settings import get_settings


@dataclass
class SystemState:
    """System state snapshot"""
    timestamp: float = field(default_factory=time.time)
    trading_engine_state: str = "stopped"
    active_orders: Dict[str, Any] = field(default_factory=dict)
    active_positions: Dict[str, Any] = field(default_factory=dict)
    portfolio_metrics: Dict[str, Any] = field(default_factory=dict)
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    configuration_hash: str = ""
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemState':
        return cls(**data)


class StateManager:
    """
    Enterprise-grade state management system
    
    Features:
    - Persistent state storage
    - Automatic state snapshots
    - State recovery on startup
    - State validation and integrity checks
    - Historical state tracking
    - Backup and restore capabilities
    """
    
    def __init__(self, event_bus: EventBus):
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus
        self.settings = get_settings()
        
        # State storage
        self.current_state = SystemState()
        self.state_history: List[SystemState] = []
        self.max_history_size = 1000
        
        # Persistence settings
        self.data_dir = Path(self.settings.data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.state_file = self.data_dir / "system_state.json"
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Database for historical data
        self.db_file = self.data_dir / "trading_history.db"
        self.db_connection: Optional[sqlite3.Connection] = None
        
        # Control flags
        self.running = False
        self.snapshot_interval = 30.0  # seconds
        self.backup_interval = 3600.0  # 1 hour
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Tasks
        self.snapshot_task: Optional[asyncio.Task] = None
        self.backup_task: Optional[asyncio.Task] = None
        
        # Initialize database
        self._init_database()
        
        # Subscribe to events
        self._setup_event_handlers()
    
    def _init_database(self):
        """Initialize SQLite database for historical data"""
        try:
            self.db_connection = sqlite3.connect(
                str(self.db_file), 
                check_same_thread=False,
                timeout=30.0
            )
            
            # Create tables
            self.db_connection.executescript("""
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    state_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS trading_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cpu_usage REAL,
                    memory_usage REAL,
                    event_processing_rate REAL,
                    average_latency REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp 
                ON state_snapshots(timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON trading_events(timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON trading_events(event_type);
                
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON performance_metrics(timestamp);
            """)
            
            self.db_connection.commit()
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            self.db_connection = None
    
    def _setup_event_handlers(self):
        """Setup event handlers for state tracking"""
        # Subscribe to all events for logging
        self.event_bus.subscribe_all(self._handle_event_for_logging, priority=10)
        
        # Subscribe to specific events for state updates
        self.event_bus.subscribe(EventType.ORDER_PLACED, self._handle_order_event)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_order_event)
        self.event_bus.subscribe(EventType.ORDER_CANCELLED, self._handle_order_event)
        self.event_bus.subscribe(EventType.POSITION_OPENED, self._handle_position_event)
        self.event_bus.subscribe(EventType.POSITION_CLOSED, self._handle_position_event)
        self.event_bus.subscribe(EventType.SYSTEM_STARTUP, self._handle_system_event)
        self.event_bus.subscribe(EventType.SYSTEM_SHUTDOWN, self._handle_system_event)
    
    async def start(self):
        """Start state management"""
        if self.running:
            return
        
        self.logger.info("Starting state manager...")
        self.running = True
        
        try:
            # Load previous state if exists
            await self._load_state()
            
            # Start periodic tasks
            self.snapshot_task = asyncio.create_task(self._snapshot_loop())
            self.backup_task = asyncio.create_task(self._backup_loop())
            
            self.logger.info("State manager started successfully")
            
        except Exception as e:
            self.running = False
            self.logger.error(f"Failed to start state manager: {e}")
            raise
    
    async def stop(self):
        """Stop state management"""
        if not self.running:
            return
        
        self.logger.info("Stopping state manager...")
        self.running = False
        
        try:
            # Cancel tasks
            if self.snapshot_task:
                self.snapshot_task.cancel()
            if self.backup_task:
                self.backup_task.cancel()
            
            # Wait for tasks to complete
            if self.snapshot_task:
                try:
                    await self.snapshot_task
                except asyncio.CancelledError:
                    pass
            
            if self.backup_task:
                try:
                    await self.backup_task
                except asyncio.CancelledError:
                    pass
            
            # Save final state
            await self._save_state()
            
            # Close database connection
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
            
            self.logger.info("State manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping state manager: {e}")
    
    @profile("state_manager.handle_event_logging")
    async def _handle_event_for_logging(self, event: Event):
        """Handle event for logging purposes"""
        if not self.db_connection:
            return
        
        try:
            # Store event in database
            self.db_connection.execute(
                """INSERT INTO trading_events 
                   (event_id, event_type, event_data, timestamp) 
                   VALUES (?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.event_type.value,
                    json.dumps(event.data),
                    event.timestamp
                )
            )
            self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to log event {event.event_id}: {e}")
    
    async def _handle_order_event(self, event: Event):
        """Handle order-related events"""
        try:
            order_data = event.data
            order_id = order_data.get('order_id')
            
            if not order_id:
                return
            
            with self.lock:
                if event.event_type == EventType.ORDER_PLACED:
                    self.current_state.active_orders[order_id] = order_data
                elif event.event_type in [EventType.ORDER_FILLED, EventType.ORDER_CANCELLED]:
                    self.current_state.active_orders.pop(order_id, None)
            
        except Exception as e:
            self.logger.error(f"Error handling order event: {e}")
    
    async def _handle_position_event(self, event: Event):
        """Handle position-related events"""
        try:
            position_data = event.data
            position_id = position_data.get('position_id')
            
            if not position_id:
                return
            
            with self.lock:
                if event.event_type == EventType.POSITION_OPENED:
                    self.current_state.active_positions[position_id] = position_data
                elif event.event_type == EventType.POSITION_CLOSED:
                    self.current_state.active_positions.pop(position_id, None)
            
        except Exception as e:
            self.logger.error(f"Error handling position event: {e}")
    
    async def _handle_system_event(self, event: Event):
        """Handle system-related events"""
        try:
            with self.lock:
                if event.event_type == EventType.SYSTEM_STARTUP:
                    self.current_state.trading_engine_state = "running"
                elif event.event_type == EventType.SYSTEM_SHUTDOWN:
                    self.current_state.trading_engine_state = "stopped"
            
        except Exception as e:
            self.logger.error(f"Error handling system event: {e}")
    
    async def _snapshot_loop(self):
        """Periodic state snapshot loop"""
        while self.running:
            try:
                await self._create_snapshot()
                await asyncio.sleep(self.snapshot_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in snapshot loop: {e}")
                await asyncio.sleep(5)
    
    async def _backup_loop(self):
        """Periodic backup loop"""
        while self.running:
            try:
                await self._create_backup()
                await asyncio.sleep(self.backup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in backup loop: {e}")
                await asyncio.sleep(60)
    
    @profile("state_manager.create_snapshot")
    async def _create_snapshot(self):
        """Create state snapshot"""
        try:
            with self.lock:
                # Update current state with latest data
                self.current_state.timestamp = time.time()
                
                # Get performance metrics if available
                try:
                    from .performance_optimizer import performance_optimizer
                    perf_report = performance_optimizer.get_performance_report()
                    self.current_state.performance_metrics = perf_report
                except Exception:
                    pass
                
                # Add to history
                snapshot = SystemState(**asdict(self.current_state))
                self.state_history.append(snapshot)
                
                # Limit history size
                if len(self.state_history) > self.max_history_size:
                    self.state_history.pop(0)
                
                # Store in database
                if self.db_connection:
                    self.db_connection.execute(
                        """INSERT INTO state_snapshots (timestamp, state_data) 
                           VALUES (?, ?)""",
                        (snapshot.timestamp, json.dumps(snapshot.to_dict()))
                    )
                    self.db_connection.commit()
            
            self.logger.debug("State snapshot created")
            
        except Exception as e:
            self.logger.error(f"Failed to create snapshot: {e}")
    
    async def _save_state(self):
        """Save current state to file"""
        try:
            with self.lock:
                state_data = self.current_state.to_dict()
                
                # Write to temporary file first
                temp_file = self.state_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
                
                # Atomic move
                temp_file.replace(self.state_file)
            
            self.logger.debug("State saved to file")
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    async def _load_state(self):
        """Load state from file"""
        try:
            if not self.state_file.exists():
                self.logger.info("No previous state file found")
                return
            
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
            
            with self.lock:
                self.current_state = SystemState.from_dict(state_data)
            
            self.logger.info("Previous state loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            # Continue with default state
    
    async def _create_backup(self):
        """Create backup of current state and database"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"state_backup_{timestamp}.json"
            
            # Backup state file
            if self.state_file.exists():
                with open(self.state_file, 'r') as src:
                    with open(backup_file, 'w') as dst:
                        dst.write(src.read())
            
            # Backup database
            if self.db_connection:
                db_backup_file = self.backup_dir / f"database_backup_{timestamp}.db"
                backup_conn = sqlite3.connect(str(db_backup_file))
                self.db_connection.backup(backup_conn)
                backup_conn.close()
            
            # Clean old backups (keep last 24 hours)
            await self._cleanup_old_backups()
            
            self.logger.debug(f"Backup created: {backup_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
    
    async def _cleanup_old_backups(self):
        """Clean up old backup files"""
        try:
            cutoff_time = time.time() - (24 * 3600)  # 24 hours ago
            
            for backup_file in self.backup_dir.glob("*_backup_*.json"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
            
            for backup_file in self.backup_dir.glob("*_backup_*.db"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
    
    def get_current_state(self) -> SystemState:
        """Get current system state"""
        with self.lock:
            return SystemState(**asdict(self.current_state))
    
    def get_state_history(self, hours: int = 1) -> List[SystemState]:
        """Get state history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            return [
                state for state in self.state_history
                if state.timestamp >= cutoff_time
            ]
    
    def get_trading_events(self, hours: int = 1, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get trading events from database"""
        if not self.db_connection:
            return []
        
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            if event_type:
                cursor = self.db_connection.execute(
                    """SELECT event_id, event_type, event_data, timestamp 
                       FROM trading_events 
                       WHERE timestamp >= ? AND event_type = ?
                       ORDER BY timestamp DESC""",
                    (cutoff_time, event_type)
                )
            else:
                cursor = self.db_connection.execute(
                    """SELECT event_id, event_type, event_data, timestamp 
                       FROM trading_events 
                       WHERE timestamp >= ?
                       ORDER BY timestamp DESC""",
                    (cutoff_time,)
                )
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'event_id': row[0],
                    'event_type': row[1],
                    'event_data': json.loads(row[2]),
                    'timestamp': row[3]
                })
            
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to get trading events: {e}")
            return []
    
    def get_performance_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get performance metrics history"""
        if not self.db_connection:
            return []
        
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            cursor = self.db_connection.execute(
                """SELECT timestamp, cpu_usage, memory_usage, 
                          event_processing_rate, average_latency
                   FROM performance_metrics 
                   WHERE timestamp >= ?
                   ORDER BY timestamp DESC""",
                (cutoff_time,)
            )
            
            metrics = []
            for row in cursor.fetchall():
                metrics.append({
                    'timestamp': row[0],
                    'cpu_usage': row[1],
                    'memory_usage': row[2],
                    'event_processing_rate': row[3],
                    'average_latency': row[4]
                })
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get performance history: {e}")
            return []
    
    async def restore_from_backup(self, backup_timestamp: str) -> bool:
        """Restore state from backup"""
        try:
            backup_file = self.backup_dir / f"state_backup_{backup_timestamp}.json"
            
            if not backup_file.exists():
                self.logger.error(f"Backup file not found: {backup_file}")
                return False
            
            # Load backup
            with open(backup_file, 'r') as f:
                state_data = json.load(f)
            
            with self.lock:
                self.current_state = SystemState.from_dict(state_data)
            
            # Save as current state
            await self._save_state()
            
            self.logger.info(f"State restored from backup: {backup_timestamp}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
            return False
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with self.lock:
            return {
                'current_state': self.current_state.to_dict(),
                'history_size': len(self.state_history),
                'database_connected': self.db_connection is not None,
                'running': self.running,
                'snapshot_interval': self.snapshot_interval,
                'backup_interval': self.backup_interval,
                'data_directory': str(self.data_dir),
                'state_file_exists': self.state_file.exists(),
                'backup_count': len(list(self.backup_dir.glob("*_backup_*.json")))
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'database_connected': self.db_connection is not None,
            'state_file_accessible': self.state_file.exists(),
            'backup_directory_accessible': self.backup_dir.exists(),
            'recent_snapshots': len([
                s for s in self.state_history 
                if s.timestamp > time.time() - 300  # Last 5 minutes
            ]),
            'system_stats': self.get_system_stats()
        }
