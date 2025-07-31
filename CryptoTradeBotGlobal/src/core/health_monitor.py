"""
CryptoTradeBotGlobal - Health Monitoring System
Enterprise-grade system health monitoring and alerting
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json

from .event_bus import EventBus, EventType, EventPriority, Event
from .performance_optimizer import profile
from config.settings import get_settings


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class HealthMetric:
    """Health metric data structure"""
    name: str
    value: float
    threshold_warning: float
    threshold_critical: float
    unit: str = ""
    timestamp: float = field(default_factory=time.time)
    
    @property
    def status(self) -> HealthStatus:
        """Get health status based on thresholds"""
        if self.value >= self.threshold_critical:
            return HealthStatus.CRITICAL
        elif self.value >= self.threshold_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'threshold_warning': self.threshold_warning,
            'threshold_critical': self.threshold_critical,
            'unit': self.unit,
            'timestamp': self.timestamp,
            'status': self.status.value
        }


@dataclass
class HealthAlert:
    """Health alert data structure"""
    alert_id: str
    component: str
    metric_name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'component': self.component,
            'metric_name': self.metric_name,
            'severity': self.severity.value,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'timestamp': self.timestamp,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }


class ComponentHealthChecker:
    """Base class for component health checkers"""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = logging.getLogger(f"{__name__}.{component_name}")
    
    async def check_health(self) -> Dict[str, HealthMetric]:
        """Check component health - to be implemented by subclasses"""
        raise NotImplementedError


class SystemHealthChecker(ComponentHealthChecker):
    """System resource health checker"""
    
    def __init__(self):
        super().__init__("system")
    
    async def check_health(self) -> Dict[str, HealthMetric]:
        """Check system health metrics"""
        metrics = {}
        
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=0.1)
            metrics['cpu_usage'] = HealthMetric(
                name='cpu_usage',
                value=cpu_usage,
                threshold_warning=70.0,
                threshold_critical=90.0,
                unit='%'
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = HealthMetric(
                name='memory_usage',
                value=memory.percent,
                threshold_warning=80.0,
                threshold_critical=95.0,
                unit='%'
            )
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            metrics['disk_usage'] = HealthMetric(
                name='disk_usage',
                value=disk_usage,
                threshold_warning=80.0,
                threshold_critical=95.0,
                unit='%'
            )
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()[0]  # 1-minute load average
                cpu_count = psutil.cpu_count()
                load_percentage = (load_avg / cpu_count) * 100
                metrics['load_average'] = HealthMetric(
                    name='load_average',
                    value=load_percentage,
                    threshold_warning=70.0,
                    threshold_critical=90.0,
                    unit='%'
                )
            except (AttributeError, OSError):
                # Not available on Windows
                pass
            
            # Network connections
            connections = len(psutil.net_connections())
            metrics['network_connections'] = HealthMetric(
                name='network_connections',
                value=connections,
                threshold_warning=1000,
                threshold_critical=2000,
                unit='count'
            )
            
        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
        
        return metrics


class EventBusHealthChecker(ComponentHealthChecker):
    """Event bus health checker"""
    
    def __init__(self, event_bus: EventBus):
        super().__init__("event_bus")
        self.event_bus = event_bus
    
    async def check_health(self) -> Dict[str, HealthMetric]:
        """Check event bus health metrics"""
        metrics = {}
        
        try:
            health_data = await self.event_bus.health_check()
            stats = self.event_bus.get_stats()
            
            # Queue sizes
            total_queue_size = sum(
                health_data['queue_health'][priority]['size']
                for priority in health_data['queue_health']
            )
            
            metrics['queue_size'] = HealthMetric(
                name='queue_size',
                value=total_queue_size,
                threshold_warning=5000,
                threshold_critical=8000,
                unit='events'
            )
            
            # Dead letter queue size
            metrics['dead_letter_queue_size'] = HealthMetric(
                name='dead_letter_queue_size',
                value=health_data['dead_letter_queue']['size'],
                threshold_warning=100,
                threshold_critical=500,
                unit='events'
            )
            
            # Circuit breakers open
            metrics['circuit_breakers_open'] = HealthMetric(
                name='circuit_breakers_open',
                value=health_data['circuit_breakers_open'],
                threshold_warning=1,
                threshold_critical=3,
                unit='count'
            )
            
            # Event processing rate (if available)
            if 'event_stats' in stats:
                total_processed = sum(
                    event_stats.get('processed', 0)
                    for event_stats in stats['event_stats'].values()
                )
                metrics['events_processed'] = HealthMetric(
                    name='events_processed',
                    value=total_processed,
                    threshold_warning=0,  # More is better
                    threshold_critical=0,
                    unit='count'
                )
            
        except Exception as e:
            self.logger.error(f"Error checking event bus health: {e}")
        
        return metrics


class TradingEngineHealthChecker(ComponentHealthChecker):
    """Trading engine health checker"""
    
    def __init__(self, trading_engine=None):
        super().__init__("trading_engine")
        self.trading_engine = trading_engine
    
    async def check_health(self) -> Dict[str, HealthMetric]:
        """Check trading engine health metrics"""
        metrics = {}
        
        try:
            if not self.trading_engine:
                return metrics
            
            stats = self.trading_engine.get_trading_stats()
            
            # Success rate
            success_rate = stats.get('success_rate', 0) * 100
            metrics['success_rate'] = HealthMetric(
                name='success_rate',
                value=success_rate,
                threshold_warning=70.0,  # Below 70% is warning
                threshold_critical=50.0,  # Below 50% is critical
                unit='%'
            )
            
            # Active orders
            active_orders = stats.get('active_orders', 0)
            metrics['active_orders'] = HealthMetric(
                name='active_orders',
                value=active_orders,
                threshold_warning=50,
                threshold_critical=100,
                unit='count'
            )
            
            # Active positions
            active_positions = stats.get('active_positions', 0)
            metrics['active_positions'] = HealthMetric(
                name='active_positions',
                value=active_positions,
                threshold_warning=20,
                threshold_critical=50,
                unit='count'
            )
            
            # Risk metrics
            risk_metrics = stats.get('risk_metrics', {})
            if risk_metrics:
                # Portfolio risk utilization
                risk_utilization = risk_metrics.get('risk_utilization', 0) * 100
                metrics['risk_utilization'] = HealthMetric(
                    name='risk_utilization',
                    value=risk_utilization,
                    threshold_warning=80.0,
                    threshold_critical=95.0,
                    unit='%'
                )
                
                # Current drawdown
                current_drawdown = risk_metrics.get('current_drawdown', 0) * 100
                metrics['current_drawdown'] = HealthMetric(
                    name='current_drawdown',
                    value=current_drawdown,
                    threshold_warning=10.0,
                    threshold_critical=15.0,
                    unit='%'
                )
            
        except Exception as e:
            self.logger.error(f"Error checking trading engine health: {e}")
        
        return metrics


class HealthMonitor:
    """
    Enterprise-grade health monitoring system
    
    Features:
    - Multi-component health monitoring
    - Real-time alerting
    - Health history tracking
    - Configurable thresholds
    - Alert management
    - Health dashboards
    """
    
    def __init__(self, event_bus: EventBus, check_interval: int = 30):
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus
        self.settings = get_settings()
        self.check_interval = check_interval
        
        # Health checkers
        self.health_checkers: Dict[str, ComponentHealthChecker] = {}
        self.setup_health_checkers()
        
        # Health data storage
        self.current_health: Dict[str, Dict[str, HealthMetric]] = {}
        self.health_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Alert management
        self.active_alerts: Dict[str, HealthAlert] = {}
        self.alert_history: List[HealthAlert] = []
        self.alert_callbacks: List[Callable] = []
        
        # Control flags
        self.running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Performance tracking
        self.checks_performed = 0
        self.alerts_generated = 0
        self.last_check_time = 0.0
    
    def setup_health_checkers(self):
        """Setup health checkers for different components"""
        # System health checker
        self.health_checkers['system'] = SystemHealthChecker()
        
        # Event bus health checker
        self.health_checkers['event_bus'] = EventBusHealthChecker(self.event_bus)
        
        # Trading engine health checker will be added when available
        # self.health_checkers['trading_engine'] = TradingEngineHealthChecker()
    
    def add_health_checker(self, name: str, checker: ComponentHealthChecker):
        """Add a custom health checker"""
        self.health_checkers[name] = checker
        self.logger.info(f"Added health checker: {name}")
    
    def add_alert_callback(self, callback: Callable[[HealthAlert], None]):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    async def start(self):
        """Start health monitoring"""
        if self.running:
            return
        
        self.logger.info("Starting health monitor...")
        self.running = True
        
        try:
            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            self.logger.info("Health monitor started successfully")
            
        except Exception as e:
            self.running = False
            self.logger.error(f"Failed to start health monitor: {e}")
            raise
    
    async def stop(self):
        """Stop health monitoring"""
        if not self.running:
            return
        
        self.logger.info("Stopping health monitor...")
        self.running = False
        
        try:
            # Cancel monitoring task
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("Health monitor stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping health monitor: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    @profile("health_monitor.perform_health_check")
    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        start_time = time.time()
        
        try:
            health_snapshot = {
                'timestamp': start_time,
                'components': {}
            }
            
            # Check each component
            for component_name, checker in self.health_checkers.items():
                try:
                    component_metrics = await checker.check_health()
                    
                    with self.lock:
                        self.current_health[component_name] = component_metrics
                    
                    health_snapshot['components'][component_name] = {
                        name: metric.to_dict()
                        for name, metric in component_metrics.items()
                    }
                    
                    # Check for alerts
                    await self._check_for_alerts(component_name, component_metrics)
                    
                except Exception as e:
                    self.logger.error(f"Error checking {component_name} health: {e}")
                    health_snapshot['components'][component_name] = {'error': str(e)}
            
            # Store health snapshot
            with self.lock:
                self.health_history.append(health_snapshot)
                if len(self.health_history) > self.max_history_size:
                    self.health_history.pop(0)
            
            # Update performance metrics
            self.checks_performed += 1
            self.last_check_time = time.time() - start_time
            
            # Publish health check event
            await self.event_bus.publish_event(
                EventType.HEALTH_CHECK,
                {
                    'overall_status': self._get_overall_status().value,
                    'components_checked': len(self.health_checkers),
                    'alerts_active': len(self.active_alerts),
                    'check_duration': self.last_check_time
                },
                priority=EventPriority.LOW
            )
            
        except Exception as e:
            self.logger.error(f"Error performing health check: {e}")
    
    async def _check_for_alerts(self, component_name: str, metrics: Dict[str, HealthMetric]):
        """Check metrics for alert conditions"""
        for metric_name, metric in metrics.items():
            alert_key = f"{component_name}.{metric_name}"
            
            # Check if we need to create an alert
            if metric.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
                if alert_key not in self.active_alerts:
                    # Create new alert
                    severity = AlertSeverity.WARNING if metric.status == HealthStatus.WARNING else AlertSeverity.CRITICAL
                    threshold = metric.threshold_warning if metric.status == HealthStatus.WARNING else metric.threshold_critical
                    
                    alert = HealthAlert(
                        alert_id=f"{alert_key}_{int(time.time())}",
                        component=component_name,
                        metric_name=metric_name,
                        severity=severity,
                        message=f"{component_name}.{metric_name} is {metric.status.value}: {metric.value}{metric.unit} (threshold: {threshold}{metric.unit})",
                        value=metric.value,
                        threshold=threshold
                    )
                    
                    with self.lock:
                        self.active_alerts[alert_key] = alert
                        self.alert_history.append(alert)
                        self.alerts_generated += 1
                    
                    # Notify callbacks
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            self.logger.error(f"Error in alert callback: {e}")
                    
                    # Publish alert event
                    await self.event_bus.publish_event(
                        EventType.ERROR_OCCURRED,
                        {
                            'alert_type': 'health_alert',
                            'component': component_name,
                            'metric': metric_name,
                            'severity': severity.value,
                            'message': alert.message,
                            'value': metric.value,
                            'threshold': threshold
                        },
                        priority=EventPriority.HIGH if severity == AlertSeverity.CRITICAL else EventPriority.NORMAL
                    )
                    
                    self.logger.warning(f"Health alert: {alert.message}")
            
            else:
                # Check if we need to resolve an alert
                if alert_key in self.active_alerts:
                    alert = self.active_alerts[alert_key]
                    alert.resolved = True
                    
                    with self.lock:
                        del self.active_alerts[alert_key]
                    
                    self.logger.info(f"Health alert resolved: {component_name}.{metric_name}")
    
    def _get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""
        if not self.current_health:
            return HealthStatus.UNKNOWN
        
        has_critical = False
        has_warning = False
        
        for component_metrics in self.current_health.values():
            for metric in component_metrics.values():
                if metric.status == HealthStatus.CRITICAL:
                    has_critical = True
                elif metric.status == HealthStatus.WARNING:
                    has_warning = True
        
        if has_critical:
            return HealthStatus.CRITICAL
        elif has_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        with self.lock:
            overall_status = self._get_overall_status()
            
            component_status = {}
            for component_name, metrics in self.current_health.items():
                component_health = HealthStatus.HEALTHY
                component_metrics = {}
                
                for metric_name, metric in metrics.items():
                    component_metrics[metric_name] = metric.to_dict()
                    if metric.status == HealthStatus.CRITICAL:
                        component_health = HealthStatus.CRITICAL
                    elif metric.status == HealthStatus.WARNING and component_health != HealthStatus.CRITICAL:
                        component_health = HealthStatus.WARNING
                
                component_status[component_name] = {
                    'status': component_health.value,
                    'metrics': component_metrics
                }
            
            return {
                'overall_status': overall_status.value,
                'timestamp': time.time(),
                'components': component_status,
                'active_alerts': len(self.active_alerts),
                'monitoring_stats': {
                    'checks_performed': self.checks_performed,
                    'alerts_generated': self.alerts_generated,
                    'last_check_duration': self.last_check_time,
                    'running': self.running
                }
            }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        with self.lock:
            return [alert.to_dict() for alert in self.active_alerts.values()]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            return [
                alert.to_dict() for alert in self.alert_history
                if alert.timestamp >= cutoff_time
            ]
    
    def get_health_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get health history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            return [
                snapshot for snapshot in self.health_history
                if snapshot['timestamp'] >= cutoff_time
            ]
    
    def acknowledge_alert(self, alert_key: str) -> bool:
        """Acknowledge an active alert"""
        with self.lock:
            if alert_key in self.active_alerts:
                self.active_alerts[alert_key].acknowledged = True
                self.logger.info(f"Alert acknowledged: {alert_key}")
                return True
            return False
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        with self.lock:
            return {
                'running': self.running,
                'check_interval': self.check_interval,
                'checks_performed': self.checks_performed,
                'alerts_generated': self.alerts_generated,
                'active_alerts': len(self.active_alerts),
                'health_checkers': list(self.health_checkers.keys()),
                'last_check_duration': self.last_check_time,
                'health_history_size': len(self.health_history),
                'alert_history_size': len(self.alert_history)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the health monitor itself"""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'last_check_age': time.time() - (self.health_history[-1]['timestamp'] if self.health_history else 0),
            'monitoring_stats': self.get_monitoring_stats(),
            'overall_system_status': self._get_overall_status().value
        }
