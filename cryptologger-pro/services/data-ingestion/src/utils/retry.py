"""
Retry utilities for CryptoLogger Pro
Provides robust retry mechanisms with exponential backoff
"""

import asyncio
import random
import time
from functools import wraps
from typing import Any, Callable, Optional, Type, Union, Tuple
import logging


class RetryError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
):
    """
    Async retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        exceptions: Exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                        
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        break
                    
                    # Calculate delay with exponential backoff
                    current_delay = delay * (backoff ** attempt)
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        current_delay *= (0.5 + random.random() * 0.5)
                    
                    logging.getLogger(__name__).warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.2f}s"
                    )
                    
                    await asyncio.sleep(current_delay)
            
            # All attempts failed
            raise RetryError(
                f"All {max_attempts} attempts failed for {func.__name__}. "
                f"Last error: {last_exception}"
            ) from last_exception
        
        return wrapper
    return decorator


def sync_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
):
    """
    Synchronous retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        exceptions: Exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    retry_stats.record_attempt(func.__name__, attempt + 1, True)
                    return result
                except exceptions as e:
                    retry_stats.record_attempt(func.__name__, attempt + 1, False)
                    last_exception = e
                    if attempt == max_attempts - 1:
                        # Última tentativa falhou
                        break
                    # Calcular delay com backoff exponencial
                    current_delay = delay * (backoff ** attempt)
                    # Adicionar jitter para evitar thundering herd
                    if jitter:
                        current_delay *= (0.5 + random.random() * 0.5)
                    logging.getLogger(__name__).warning(
                        f"Tentativa {attempt + 1}/{max_attempts} falhou para {func.__name__}: {e}. "
                        f"Retentando em {current_delay:.2f}s"
                    )
                    time.sleep(current_delay)
            # Todas as tentativas falharam
            raise RetryError(
                f"Todas as {max_attempts} tentativas falharam para {func.__name__}. "
                f"Último erro: {last_exception}"
            ) from last_exception
        return wrapper
    return decorator


class AsyncRetryManager:
    """
    Advanced retry manager with configurable strategies
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_strategy: str = "exponential",
        jitter: bool = True,
        exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
    ):
        """
        Initialize retry manager
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries
            max_delay: Maximum delay between retries
            backoff_strategy: Backoff strategy ('exponential', 'linear', 'fixed')
            jitter: Add random jitter to delays
            exceptions: Exception types to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_strategy = backoff_strategy
        self.jitter = jitter
        self.exceptions = exceptions
        self.logger = logging.getLogger(__name__)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt"""
        if self.backoff_strategy == "exponential":
            delay = self.base_delay * (2 ** attempt)
        elif self.backoff_strategy == "linear":
            delay = self.base_delay * (attempt + 1)
        elif self.backoff_strategy == "fixed":
            delay = self.base_delay
        else:
            raise ValueError(f"Unknown backoff strategy: {self.backoff_strategy}")
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RetryError: If all attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except self.exceptions as e:
                last_exception = e
                
                if attempt == self.max_attempts - 1:
                    break
                
                delay = self._calculate_delay(attempt)
                
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.max_attempts} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                
                await asyncio.sleep(delay)
        
        # All attempts failed
        raise RetryError(
            f"All {self.max_attempts} attempts failed for {func.__name__}. "
            f"Last error: {last_exception}"
        ) from last_exception
    
    def __call__(self, func: Callable) -> Callable:
        """Use as decorator"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.execute(func, *args, **kwargs)
        return wrapper


class RetryStats:
    """Track retry statistics"""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.retry_counts = {}
        self.last_reset = time.time()
    
    def record_attempt(self, func_name: str, attempt: int, success: bool):
        """Record retry attempt"""
        self.total_attempts += 1
        
        if success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1
        
        if func_name not in self.retry_counts:
            self.retry_counts[func_name] = {"attempts": 0, "successes": 0, "failures": 0}
        
        self.retry_counts[func_name]["attempts"] += 1
        if success:
            self.retry_counts[func_name]["successes"] += 1
        else:
            self.retry_counts[func_name]["failures"] += 1
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        uptime = time.time() - self.last_reset
        
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": (
                self.successful_attempts / self.total_attempts 
                if self.total_attempts > 0 else 0
            ),
            "uptime_seconds": uptime,
            "attempts_per_second": self.total_attempts / uptime if uptime > 0 else 0,
            "function_stats": self.retry_counts
        }
    
    def reset(self):
        """Reset statistics"""
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.retry_counts = {}
        self.last_reset = time.time()


# Global retry statistics
retry_stats = RetryStats()


def with_retry_stats(func: Callable) -> Callable:
    """Decorator to track retry statistics"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        attempt = 1
        success = False
        
        try:
            result = await func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            raise
        finally:
            retry_stats.record_attempt(func.__name__, attempt, success)
    
    return wrapper
