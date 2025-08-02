# Stubs mínimos para testes
class ErroConexao(Exception):
    pass
class ErroOrdem(Exception):
    pass
class ErroSaldo(Exception):
    pass
"""
Core Exception Classes for CryptoTradeBotGlobal
Production-ready exception handling for cryptocurrency trading system.
"""

from typing import Optional, Dict, Any


class CryptoTradeBotError(Exception):
    """Base exception class for all CryptoTradeBotGlobal errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class ExchangeError(CryptoTradeBotError):
    """Base exception for exchange-related errors"""
    pass


class AuthenticationError(ExchangeError):
    """Raised when API authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)


class RateLimitError(ExchangeError):
    """Raised when API rate limits are exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="RATE_LIMIT", **kwargs)
        self.retry_after = retry_after


class InsufficientFundsError(ExchangeError):
    """Raised when account has insufficient funds for operation"""
    
    def __init__(self, message: str = "Insufficient funds", required_amount: Optional[str] = None, 
                 available_amount: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="INSUFFICIENT_FUNDS", **kwargs)
        self.required_amount = required_amount
        self.available_amount = available_amount


class OrderError(ExchangeError):
    """Base exception for order-related errors"""
    pass


class InvalidOrderError(OrderError):
    """Raised when order parameters are invalid"""
    
    def __init__(self, message: str = "Invalid order parameters", **kwargs):
        super().__init__(message, error_code="INVALID_ORDER", **kwargs)


class OrderNotFoundError(OrderError):
    """Raised when requested order is not found"""
    
    def __init__(self, message: str = "Order not found", order_id: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="ORDER_NOT_FOUND", **kwargs)
        self.order_id = order_id


class OrderExecutionError(OrderError):
    """Raised when order execution fails"""
    
    def __init__(self, message: str = "Order execution failed", **kwargs):
        super().__init__(message, error_code="ORDER_EXECUTION_ERROR", **kwargs)


class MarketDataError(ExchangeError):
    """Raised when market data operations fail"""
    
    def __init__(self, message: str = "Market data error", **kwargs):
        super().__init__(message, error_code="MARKET_DATA_ERROR", **kwargs)


class ConnectionError(ExchangeError):
    """Raised when connection to exchange fails"""
    
    def __init__(self, message: str = "Connection failed", **kwargs):
        super().__init__(message, error_code="CONNECTION_ERROR", **kwargs)


class WebSocketError(ExchangeError):
    """Raised when WebSocket operations fail"""
    
    def __init__(self, message: str = "WebSocket error", **kwargs):
        super().__init__(message, error_code="WEBSOCKET_ERROR", **kwargs)


class StrategyError(CryptoTradeBotError):
    """Base exception for trading strategy errors"""
    pass


class StrategyInitializationError(StrategyError):
    """Raised when strategy initialization fails"""
    
    def __init__(self, message: str = "Strategy initialization failed", strategy_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="STRATEGY_INIT_ERROR", **kwargs)
        self.strategy_name = strategy_name


class StrategyExecutionError(StrategyError):
    """Raised when strategy execution fails"""
    
    def __init__(self, message: str = "Strategy execution failed", strategy_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="STRATEGY_EXEC_ERROR", **kwargs)
        self.strategy_name = strategy_name


class RiskManagementError(CryptoTradeBotError):
    """Base exception for risk management errors"""
    pass


class RiskLimitExceededError(RiskManagementError):
    """Raised when risk limits are exceeded"""
    
    def __init__(self, message: str = "Risk limit exceeded", limit_type: Optional[str] = None, 
                 current_value: Optional[float] = None, limit_value: Optional[float] = None, **kwargs):
        super().__init__(message, error_code="RISK_LIMIT_EXCEEDED", **kwargs)
        self.limit_type = limit_type
        self.current_value = current_value
        self.limit_value = limit_value


class PositionSizeError(RiskManagementError):
    """Raised when position size validation fails"""
    
    def __init__(self, message: str = "Invalid position size", **kwargs):
        super().__init__(message, error_code="POSITION_SIZE_ERROR", **kwargs)


class MaxDrawdownError(RiskManagementError):
    """Raised when maximum drawdown is exceeded"""
    
    def __init__(self, message: str = "Maximum drawdown exceeded", current_drawdown: Optional[float] = None, 
                 max_drawdown: Optional[float] = None, **kwargs):
        super().__init__(message, error_code="MAX_DRAWDOWN_EXCEEDED", **kwargs)
        self.current_drawdown = current_drawdown
        self.max_drawdown = max_drawdown


class ConfigurationError(CryptoTradeBotError):
    """Raised when configuration is invalid or missing"""
    
    def __init__(self, message: str = "Configuration error", config_key: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key


class ValidationError(CryptoTradeBotError):
    """Raised when data validation fails"""
    
    def __init__(self, message: str = "Validation failed", field_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_name = field_name


class DataError(CryptoTradeBotError):
    """Base exception for data-related errors"""
    pass


class DataNotFoundError(DataError):
    """Raised when requested data is not found"""
    
    def __init__(self, message: str = "Data not found", **kwargs):
        super().__init__(message, error_code="DATA_NOT_FOUND", **kwargs)


class DataCorruptionError(DataError):
    """Raised when data corruption is detected"""
    
    def __init__(self, message: str = "Data corruption detected", **kwargs):
        super().__init__(message, error_code="DATA_CORRUPTION", **kwargs)


class BacktestError(CryptoTradeBotError):
    """Base exception for backtesting errors"""
    pass


class BacktestDataError(BacktestError):
    """Raised when backtest data is invalid or insufficient"""
    
    def __init__(self, message: str = "Backtest data error", **kwargs):
        super().__init__(message, error_code="BACKTEST_DATA_ERROR", **kwargs)


class BacktestExecutionError(BacktestError):
    """Raised when backtest execution fails"""
    
    def __init__(self, message: str = "Backtest execution failed", **kwargs):
        super().__init__(message, error_code="BACKTEST_EXEC_ERROR", **kwargs)


class PortfolioError(CryptoTradeBotError):
    """Base exception for portfolio management errors"""
    pass


class PortfolioRebalanceError(PortfolioError):
    """Raised when portfolio rebalancing fails"""
    
    def __init__(self, message: str = "Portfolio rebalance failed", **kwargs):
        super().__init__(message, error_code="PORTFOLIO_REBALANCE_ERROR", **kwargs)


class AssetAllocationError(PortfolioError):
    """Raised when asset allocation is invalid"""
    
    def __init__(self, message: str = "Invalid asset allocation", **kwargs):
        super().__init__(message, error_code="ASSET_ALLOCATION_ERROR", **kwargs)


class SystemError(CryptoTradeBotError):
    """Base exception for system-level errors"""
    pass


class SystemShutdownError(SystemError):
    """Raised when system shutdown is required"""
    
    def __init__(self, message: str = "System shutdown required", **kwargs):
        super().__init__(message, error_code="SYSTEM_SHUTDOWN", **kwargs)


class HealthCheckError(SystemError):
    """Raised when system health check fails"""
    
    def __init__(self, message: str = "Health check failed", component: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="HEALTH_CHECK_FAILED", **kwargs)
        self.component = component


class ResourceError(SystemError):
    """Raised when system resources are insufficient"""
    
    def __init__(self, message: str = "Insufficient system resources", resource_type: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="RESOURCE_ERROR", **kwargs)
        self.resource_type = resource_type


# Exception mapping for external API errors
EXCHANGE_ERROR_MAPPING = {
    # Binance error codes
    -1000: InvalidOrderError,
    -1001: ConnectionError,
    -1002: AuthenticationError,
    -1003: RateLimitError,
    -1013: InvalidOrderError,
    -1021: AuthenticationError,
    -1022: AuthenticationError,
    -2010: OrderError,
    -2011: OrderNotFoundError,
    -2013: OrderNotFoundError,
    -2014: AuthenticationError,
    -2015: AuthenticationError,
    
    # Generic HTTP status codes
    400: InvalidOrderError,
    401: AuthenticationError,
    403: AuthenticationError,
    404: OrderNotFoundError,
    429: RateLimitError,
    500: ExchangeError,
    502: ConnectionError,
    503: ConnectionError,
    504: ConnectionError,
}


def map_exchange_error(error_code: int, message: str = None) -> ExchangeError:
    """
    Map exchange-specific error codes to appropriate exception classes.
    
    Args:
        error_code: Exchange-specific error code
        message: Error message
        
    Returns:
        Appropriate exception instance
    """
    exception_class = EXCHANGE_ERROR_MAPPING.get(error_code, ExchangeError)
    return exception_class(message or f"Exchange error: {error_code}")


def handle_exception_chain(exception: Exception) -> CryptoTradeBotError:
    """
    Convert any exception to a CryptoTradeBotError while preserving the original exception chain.
    
    Args:
        exception: Original exception
        
    Returns:
        CryptoTradeBotError instance
    """
    if isinstance(exception, CryptoTradeBotError):
        return exception
    
    # Map common exception types
    if isinstance(exception, (ConnectionRefusedError, ConnectionError)):
        return ConnectionError(str(exception))
    elif isinstance(exception, TimeoutError):
        return ConnectionError(f"Timeout: {str(exception)}")
    elif isinstance(exception, ValueError):
        return ValidationError(str(exception))
    elif isinstance(exception, KeyError):
        return DataNotFoundError(f"Missing key: {str(exception)}")
    else:
        return CryptoTradeBotError(f"Unexpected error: {str(exception)}")
