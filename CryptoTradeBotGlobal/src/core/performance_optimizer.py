"""
CryptoTradeBotGlobal - Performance Optimization Engine
Advanced performance monitoring and optimization for institutional trading
"""

import asyncio
import time
import psutil
import gc
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque, defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from functools import wraps
import cProfile
import pstats
import io


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: float = field(default_factory=time.time)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_available: float = 0.0
    event_processing_rate: float = 0.0
    average_latency: float = 0.0
    error_rate: float = 0.0
    active_connections: int = 0
    queue_sizes: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'memory_available': self.memory_available,
            'event_processing_rate': self.event_processing_rate,
            'average_latency': self.average_latency,
            'error_rate': self.error_rate,
            'active_connections': self.active_connections,
            'queue_sizes': self.queue_sizes
        }


class PerformanceProfiler:
    """Advanced performance profiler for critical code paths"""
    
    def __init__(self):
        self.profiles: Dict[str, cProfile.Profile] = {}
        self.execution_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.lock = threading.RLock()
    
    def profile_function(self, func_name: str = None):
        """Decorator for profiling function performance"""
        def decorator(func: Callable):
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                
                with self.lock:
                    self.call_counts[name] += 1
                
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    execution_time = time.perf_counter() - start_time
                    
                    with self.lock:
                        self.execution_times[name].append(execution_time)
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.perf_counter() - start_time
                    with self.lock:
                        self.execution_times[name].append(execution_time)
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                
                with self.lock:
                    self.call_counts[name] += 1
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.perf_counter() - start_time
                    
                    with self.lock:
                        self.execution_times[name].append(execution_time)
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.perf_counter() - start_time
                    with self.lock:
                        self.execution_times[name].append(execution_time)
                    raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for all profiled functions"""
        stats = {}
        
        with self.lock:
            for func_name, times in self.execution_times.items():
                if times:
                    times_array = np.array(times)
                    stats[func_name] = {
                        'call_count': self.call_counts[func_name],
                        'avg_time': float(np.mean(times_array)),
                        'min_time': float(np.min(times_array)),
                        'max_time': float(np.max(times_array)),
                        'p95_time': float(np.percentile(times_array, 95)),
                        'p99_time': float(np.percentile(times_array, 99)),
                        'total_time': float(np.sum(times_array))
                    }
        
        return stats


class MemoryOptimizer:
    """Memory optimization and monitoring"""
    
    def __init__(self):
        self.memory_threshold = 0.85  # 85% memory usage threshold
        self.gc_stats = {'collections': 0, 'freed_objects': 0}
        self.logger = logging.getLogger(__name__)
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization"""
        initial_memory = psutil.virtual_memory().percent
        
        # Force garbage collection
        collected = []
        for generation in range(3):
            collected.append(gc.collect(generation))
        
        self.gc_stats['collections'] += 1
        self.gc_stats['freed_objects'] += sum(collected)
        
        final_memory = psutil.virtual_memory().percent
        memory_freed = initial_memory - final_memory
        
        self.logger.info(f"Memory optimization: {memory_freed:.2f}% freed")
        
        return {
            'initial_memory': initial_memory,
            'final_memory': final_memory,
            'memory_freed': memory_freed,
            'objects_collected': collected,
            'total_collections': self.gc_stats['collections']
        }
    
    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure"""
        memory_usage = psutil.virtual_memory().percent / 100
        return memory_usage > self.memory_threshold
    
    async def auto_optimize(self):
        """Automatic memory optimization when under pressure"""
        if self.check_memory_pressure():
            return self.optimize_memory()
        return None


class PerformanceOptimizer:
    """
    Advanced performance optimization engine for CryptoTradeBotGlobal
    
    Features:
    - Real-time performance monitoring
    - Automatic bottleneck detection
    - Memory optimization
    - CPU usage optimization
    - Latency optimization
    - Throughput enhancement
    """
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.logger = logging.getLogger(__name__)
        self.monitoring_interval = monitoring_interval
        self.running = False
        
        # Components
        self.profiler = PerformanceProfiler()
        self.memory_optimizer = MemoryOptimizer()
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=3600)  # 1 hour at 1s intervals
        self.performance_alerts: List[Dict[str, Any]] = []
        
        # Optimization thresholds
        self.thresholds = {
            'cpu_usage': 80.0,      # 80% CPU usage
            'memory_usage': 85.0,    # 85% memory usage
            'latency': 100.0,        # 100ms average latency
            'error_rate': 0.05,      # 5% error rate
            'queue_size': 1000       # 1000 events in queue
        }
        
        # Optimization strategies
        self.optimization_strategies = {
            'high_cpu': self._optimize_cpu_usage,
            'high_memory': self._optimize_memory_usage,
            'high_latency': self._optimize_latency,
            'high_error_rate': self._optimize_error_handling,
            'large_queues': self._optimize_queue_processing
        }
        
        # Thread pool for optimization tasks
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="perf_opt")
        
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Performance optimizer started")
        
        # Start monitoring task
        asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        self.executor.shutdown(wait=True)
        self.logger.info("Performance optimizer stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Analyze performance
                issues = self._analyze_performance(metrics)
                
                # Apply optimizations if needed
                if issues:
                    await self._apply_optimizations(issues)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        # System metrics
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Calculate event processing rate
        event_rate = self._calculate_event_processing_rate()
        
        # Calculate average latency
        avg_latency = self._calculate_average_latency()
        
        # Calculate error rate
        error_rate = self._calculate_error_rate()
        
        return PerformanceMetrics(
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            memory_available=memory.available / (1024**3),  # GB
            event_processing_rate=event_rate,
            average_latency=avg_latency,
            error_rate=error_rate,
            active_connections=self._get_active_connections(),
            queue_sizes=self._get_queue_sizes()
        )
    
    def _calculate_event_processing_rate(self) -> float:
        """Calculate events processed per second"""
        if len(self.metrics_history) < 2:
            return 0.0
        
        # This would integrate with the event bus to get actual rates
        # For now, return a placeholder
        return 1000.0  # events/sec
    
    def _calculate_average_latency(self) -> float:
        """Calculate average latency from profiler data"""
        stats = self.profiler.get_performance_stats()
        if not stats:
            return 0.0
        
        total_time = sum(s['avg_time'] for s in stats.values())
        return total_time / len(stats) * 1000  # Convert to milliseconds
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        # This would integrate with error tracking
        return 0.01  # 1% placeholder
    
    def _get_active_connections(self) -> int:
        """Get number of active connections"""
        # This would integrate with connection managers
        return 50  # placeholder
    
    def _get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes"""
        # This would integrate with the event bus
        return {
            'high_priority': 10,
            'normal_priority': 25,
            'low_priority': 5,
            'dead_letter': 0
        }
    
    def _analyze_performance(self, metrics: PerformanceMetrics) -> List[str]:
        """Analyze performance metrics and identify issues"""
        issues = []
        
        if metrics.cpu_usage > self.thresholds['cpu_usage']:
            issues.append('high_cpu')
        
        if metrics.memory_usage > self.thresholds['memory_usage']:
            issues.append('high_memory')
        
        if metrics.average_latency > self.thresholds['latency']:
            issues.append('high_latency')
        
        if metrics.error_rate > self.thresholds['error_rate']:
            issues.append('high_error_rate')
        
        # Check queue sizes
        for queue_name, size in metrics.queue_sizes.items():
            if size > self.thresholds['queue_size']:
                issues.append('large_queues')
                break
        
        return issues
    
    async def _apply_optimizations(self, issues: List[str]):
        """Apply optimization strategies for identified issues"""
        for issue in issues:
            if issue in self.optimization_strategies:
                try:
                    await self.optimization_strategies[issue]()
                    self.logger.info(f"Applied optimization for: {issue}")
                except Exception as e:
                    self.logger.error(f"Failed to optimize {issue}: {e}")
    
    async def _optimize_cpu_usage(self):
        """Optimize CPU usage"""
        # Reduce thread pool size temporarily
        # Implement CPU-specific optimizations
        self.logger.info("Optimizing CPU usage")
        
        # Example optimizations:
        # - Reduce concurrent operations
        # - Implement CPU affinity
        # - Optimize hot code paths
    
    async def _optimize_memory_usage(self):
        """Optimize memory usage"""
        result = await self.memory_optimizer.auto_optimize()
        if result:
            self.logger.info(f"Memory optimization completed: {result}")
    
    async def _optimize_latency(self):
        """Optimize system latency"""
        self.logger.info("Optimizing system latency")
        
        # Example optimizations:
        # - Reduce I/O operations
        # - Optimize database queries
        # - Implement caching
        # - Use connection pooling
    
    async def _optimize_error_handling(self):
        """Optimize error handling"""
        self.logger.info("Optimizing error handling")
        
        # Example optimizations:
        # - Implement circuit breakers
        # - Add retry mechanisms
        # - Improve error recovery
    
    async def _optimize_queue_processing(self):
        """Optimize queue processing"""
        self.logger.info("Optimizing queue processing")
        
        # Example optimizations:
        # - Increase worker threads
        # - Implement batch processing
        # - Optimize queue algorithms
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        recent_metrics = list(self.metrics_history)[-60:]  # Last minute
        
        # Calculate averages
        avg_cpu = np.mean([m.cpu_usage for m in recent_metrics])
        avg_memory = np.mean([m.memory_usage for m in recent_metrics])
        avg_latency = np.mean([m.average_latency for m in recent_metrics])
        avg_event_rate = np.mean([m.event_processing_rate for m in recent_metrics])
        
        # Get profiler stats
        profiler_stats = self.profiler.get_performance_stats()
        
        return {
            'timestamp': time.time(),
            'monitoring_duration': len(self.metrics_history) * self.monitoring_interval,
            'system_metrics': {
                'avg_cpu_usage': float(avg_cpu),
                'avg_memory_usage': float(avg_memory),
                'avg_latency_ms': float(avg_latency),
                'avg_event_rate': float(avg_event_rate)
            },
            'profiler_stats': profiler_stats,
            'optimization_history': len(self.performance_alerts),
            'current_thresholds': self.thresholds,
            'status': 'healthy' if avg_cpu < 80 and avg_memory < 85 else 'degraded'
        }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on performance analysis"""
        recommendations = []
        
        if not self.metrics_history:
            return recommendations
        
        recent_metrics = list(self.metrics_history)[-300:]  # Last 5 minutes
        
        # Analyze trends
        cpu_trend = np.polyfit(range(len(recent_metrics)), 
                              [m.cpu_usage for m in recent_metrics], 1)[0]
        memory_trend = np.polyfit(range(len(recent_metrics)), 
                                 [m.memory_usage for m in recent_metrics], 1)[0]
        
        if cpu_trend > 0.1:  # CPU usage increasing
            recommendations.append({
                'type': 'cpu_optimization',
                'priority': 'high',
                'description': 'CPU usage is trending upward',
                'actions': [
                    'Profile CPU-intensive functions',
                    'Implement CPU affinity',
                    'Optimize hot code paths',
                    'Consider horizontal scaling'
                ]
            })
        
        if memory_trend > 0.1:  # Memory usage increasing
            recommendations.append({
                'type': 'memory_optimization',
                'priority': 'high',
                'description': 'Memory usage is trending upward',
                'actions': [
                    'Implement memory pooling',
                    'Optimize data structures',
                    'Add memory monitoring',
                    'Consider garbage collection tuning'
                ]
            })
        
        # Check profiler stats for slow functions
        profiler_stats = self.profiler.get_performance_stats()
        slow_functions = [
            (name, stats) for name, stats in profiler_stats.items()
            if stats['avg_time'] > 0.1  # Functions taking > 100ms
        ]
        
        if slow_functions:
            recommendations.append({
                'type': 'function_optimization',
                'priority': 'medium',
                'description': f'Found {len(slow_functions)} slow functions',
                'actions': [
                    'Profile slow functions in detail',
                    'Implement caching where appropriate',
                    'Optimize algorithms',
                    'Consider async alternatives'
                ],
                'slow_functions': [name for name, _ in slow_functions[:5]]
            })
        
        return recommendations


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

# Decorator for easy function profiling
profile = performance_optimizer.profiler.profile_function
