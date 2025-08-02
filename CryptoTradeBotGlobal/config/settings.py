"""
CryptoTradeBotGlobal - Production Configuration System
Enterprise-grade configuration management with security and validation
"""

import os
from typing import Dict, List, Optional, Any
from pydantic import BaseSettings, Field, validator
from pydantic_settings import SettingsConfigDict
from enum import Enum
import yaml
from pathlib import Path


class Environment(str, Enum):
    """Environment types for deployment"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TradingMode(str, Enum):
    """Trading operation modes"""
    PAPER = "paper"          # Paper trading (simulation)
    LIVE = "live"            # Live trading with real money
    BACKTEST = "backtest"    # Historical backtesting


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="cryptobot", description="Database name")
    user: str = Field(default="cryptobot", description="Database user")
    password: str = Field(default="", description="Database password")
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=30, description="Max pool overflow")
    
    @property
    def url(self) -> str:
        """Generate database URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration for caching and pub/sub"""
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    max_connections: int = Field(default=50, description="Max connections")
    
    @property
    def url(self) -> str:
        """Generate Redis URL"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class SecuritySettings(BaseSettings):
    """Security and encryption settings"""
    model_config = SettingsConfigDict(env_prefix="SECURITY_")
    
    secret_key: str = Field(description="Application secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT expiration in hours")
    api_key_encryption_key: str = Field(description="API key encryption key")
    rate_limit_per_minute: int = Field(default=100, description="API rate limit per minute")
    
    @validator("secret_key", "api_key_encryption_key")
    def validate_keys(cls, v):
        if len(v) < 32:
            raise ValueError("Security keys must be at least 32 characters long")
        return v


class TradingSettings(BaseSettings):
    """Core trading configuration"""
    model_config = SettingsConfigDict(env_prefix="TRADING_")
    
    mode: TradingMode = Field(default=TradingMode.PAPER, description="Trading mode")
    base_currency: str = Field(default="USDT", description="Base trading currency")
    max_position_size: float = Field(default=1000.0, description="Maximum position size")
    max_daily_loss: float = Field(default=500.0, description="Maximum daily loss limit")
    max_drawdown: float = Field(default=0.15, description="Maximum drawdown (15%)")
    risk_per_trade: float = Field(default=0.02, description="Risk per trade (2%)")
    
    # Order execution settings
    order_timeout_seconds: int = Field(default=30, description="Order timeout in seconds")
    slippage_tolerance: float = Field(default=0.001, description="Slippage tolerance (0.1%)")
    min_order_size: float = Field(default=10.0, description="Minimum order size")
    
    # Strategy settings
    enabled_strategies: List[str] = Field(
        default=["trend_following", "mean_reversion"],
        description="List of enabled trading strategies"
    )
    
    @validator("max_drawdown", "risk_per_trade", "slippage_tolerance")
    def validate_percentages(cls, v):
        if not 0 < v < 1:
            raise ValueError("Percentage values must be between 0 and 1")
        return v


class ExchangeSettings(BaseSettings):
    """Exchange configuration"""
    model_config = SettingsConfigDict(env_prefix="EXCHANGE_")
    
    primary_exchange: str = Field(default="binance", description="Primary exchange")
    enabled_exchanges: List[str] = Field(
        default=["binance", "coinbase", "kraken"],
        description="List of enabled exchanges"
    )
    
    # Rate limiting
    requests_per_second: int = Field(default=10, description="Requests per second limit")
    burst_limit: int = Field(default=50, description="Burst request limit")
    
    # WebSocket settings
    websocket_timeout: int = Field(default=30, description="WebSocket timeout")
    reconnect_attempts: int = Field(default=5, description="Reconnection attempts")
    reconnect_delay: int = Field(default=5, description="Reconnection delay in seconds")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings"""
    model_config = SettingsConfigDict(env_prefix="MONITORING_")
    
    prometheus_port: int = Field(default=8000, description="Prometheus metrics port")
    health_check_interval: int = Field(default=30, description="Health check interval")
    alert_webhook_url: Optional[str] = Field(default=None, description="Alert webhook URL")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # Performance monitoring
    enable_profiling: bool = Field(default=False, description="Enable performance profiling")
    max_memory_usage_mb: int = Field(default=2048, description="Max memory usage in MB")
    max_cpu_usage_percent: int = Field(default=80, description="Max CPU usage percentage")


class APISettings(BaseSettings):
    """API server configuration"""
    model_config = SettingsConfigDict(env_prefix="API_")
    
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8080, description="API port")
    workers: int = Field(default=4, description="Number of worker processes")
    enable_docs: bool = Field(default=True, description="Enable API documentation")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")


class Settings(BaseSettings):
    """Main application settings"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Core settings
    app_name: str = Field(default="CryptoTradeBotGlobal", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)
    exchange: ExchangeSettings = Field(default_factory=ExchangeSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    api: APISettings = Field(default_factory=APISettings)
    
    # File paths
    config_dir: Path = Field(default=Path("config"), description="Configuration directory")
    data_dir: Path = Field(default=Path("data"), description="Data directory")
    logs_dir: Path = Field(default=Path("logs"), description="Logs directory")
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment-specific settings"""
        if v == Environment.PRODUCTION:
            # Additional production validations can be added here
            pass
        return v
    
    def load_exchange_configs(self) -> Dict[str, Any]:
        """Load exchange-specific configurations from YAML files"""
        exchange_config_file = self.config_dir / "exchanges.yaml"
        if exchange_config_file.exists():
            with open(exchange_config_file, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def load_strategy_configs(self) -> Dict[str, Any]:
        """Load strategy configurations from YAML files"""
        strategy_config_file = self.config_dir / "strategies.yaml"
        if strategy_config_file.exists():
            with open(strategy_config_file, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def load_risk_management_config(self) -> Dict[str, Any]:
        """Load risk management configuration"""
        risk_config_file = self.config_dir / "risk_management.yaml"
        if risk_config_file.exists():
            with open(risk_config_file, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing"""
        return self.environment == Environment.TESTING


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance"""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment and config files"""
    global settings
    settings = Settings()
    return settings


# Configuration validation
def validate_configuration():
    """Validate all configuration settings"""
    try:
        settings = get_settings()
        
        # Validate critical settings for production
        if settings.is_production:
            if not settings.security.secret_key:
                raise ValueError("SECRET_KEY must be set in production")
            if not settings.security.api_key_encryption_key:
                raise ValueError("API_KEY_ENCRYPTION_KEY must be set in production")
            if settings.trading.mode == TradingMode.LIVE and settings.debug:
                raise ValueError("Debug mode cannot be enabled in live trading")
        
        # Validate directories exist
        for directory in [settings.config_dir, settings.data_dir, settings.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        return True
        
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    # Configuration validation script
    if validate_configuration():
        print("✅ Configuration validation passed")
        settings = get_settings()
        print(f"Environment: {settings.environment}")
        print(f"Trading Mode: {settings.trading.mode}")
        print(f"Primary Exchange: {settings.exchange.primary_exchange}")
    else:
        print("❌ Configuration validation failed")
        exit(1)
