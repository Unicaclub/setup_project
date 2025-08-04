"""
Configuration management for CryptoLogger Pro Data Ingestion Service
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings with environment-based configuration"""
    
    # Service Configuration
    service_name: str = "data_ingestion"
    service_instance_id: str = Field(default_factory=lambda: os.urandom(8).hex())
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    workers: int = Field(default=4, env="WORKERS")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Security Configuration
    secret_key: str = Field(..., env="SECRET_KEY")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Database Configuration (TimescaleDB)
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_pool_size: int = Field(default=20, env="REDIS_POOL_SIZE")
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", 
        env="KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_topic_transactions: str = Field(
        default="crypto-transactions", 
        env="KAFKA_TOPIC_TRANSACTIONS"
    )
    kafka_topic_compliance_events: str = Field(
        default="compliance-events", 
        env="KAFKA_TOPIC_COMPLIANCE_EVENTS"
    )
    kafka_producer_batch_size: int = Field(default=16384, env="KAFKA_PRODUCER_BATCH_SIZE")
    kafka_producer_linger_ms: int = Field(default=10, env="KAFKA_PRODUCER_LINGER_MS")
    
    # Exchange API Configuration
    binance_api_key: Optional[str] = Field(default=None, env="BINANCE_API_KEY")
    binance_api_secret: Optional[str] = Field(default=None, env="BINANCE_API_SECRET")
    binance_testnet: bool = Field(default=True, env="BINANCE_TESTNET")
    
    coinbase_api_key: Optional[str] = Field(default=None, env="COINBASE_API_KEY")
    coinbase_api_secret: Optional[str] = Field(default=None, env="COINBASE_API_SECRET")
    coinbase_passphrase: Optional[str] = Field(default=None, env="COINBASE_PASSPHRASE")
    coinbase_sandbox: bool = Field(default=True, env="COINBASE_SANDBOX")
    
    kraken_api_key: Optional[str] = Field(default=None, env="KRAKEN_API_KEY")
    kraken_api_secret: Optional[str] = Field(default=None, env="KRAKEN_API_SECRET")
    
    # Rate Limiting Configuration
    rate_limit_requests_per_minute: int = Field(default=1000, env="RATE_LIMIT_RPM")
    rate_limit_burst_size: int = Field(default=100, env="RATE_LIMIT_BURST")
    
    # Monitoring Configuration
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Compliance Configuration
    compliance_enabled: bool = Field(default=True, env="COMPLIANCE_ENABLED")
    aml_threshold_amount: float = Field(default=10000.0, env="AML_THRESHOLD_AMOUNT")
    suspicious_activity_threshold: int = Field(default=5, env="SUSPICIOUS_ACTIVITY_THRESHOLD")
    
    # Multi-tenant Configuration
    tenant_isolation_enabled: bool = Field(default=True, env="TENANT_ISOLATION_ENABLED")
    default_tenant_rate_limit: int = Field(default=100, env="DEFAULT_TENANT_RATE_LIMIT")
    
    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = Field(default=5, env="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_recovery_timeout: int = Field(default=60, env="CIRCUIT_BREAKER_RECOVERY_TIMEOUT")
    circuit_breaker_expected_exception: str = Field(default="Exception", env="CIRCUIT_BREAKER_EXPECTED_EXCEPTION")
    
    # WebSocket Configuration
    websocket_reconnect_interval: int = Field(default=5, env="WEBSOCKET_RECONNECT_INTERVAL")
    websocket_max_reconnect_attempts: int = Field(default=10, env="WEBSOCKET_MAX_RECONNECT_ATTEMPTS")
    websocket_ping_interval: int = Field(default=30, env="WEBSOCKET_PING_INTERVAL")
    
    # Data Processing Configuration
    batch_processing_size: int = Field(default=1000, env="BATCH_PROCESSING_SIZE")
    processing_timeout: int = Field(default=30, env="PROCESSING_TIMEOUT")
    data_retention_days: int = Field(default=365, env="DATA_RETENTION_DAYS")
    
    @validator("allowed_origins", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse comma-separated origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment"""
        valid_environments = ["development", "staging", "production"]
        if v.lower() not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v.lower()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Environment-specific configurations
def get_database_config() -> dict:
    """Get database configuration"""
    settings = get_settings()
    return {
        "url": settings.database_url,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "echo": settings.debug,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }


def get_redis_config() -> dict:
    """Get Redis configuration"""
    settings = get_settings()
    return {
        "host": settings.redis_host,
        "port": settings.redis_port,
        "password": settings.redis_password,
        "db": settings.redis_db,
        "max_connections": settings.redis_pool_size,
        "retry_on_timeout": True,
        "decode_responses": True,
    }


def get_kafka_config() -> dict:
    """Get Kafka configuration"""
    settings = get_settings()
    return {
        "bootstrap_servers": settings.kafka_bootstrap_servers.split(","),
        "client_id": f"{settings.service_name}-{settings.service_instance_id}",
        "acks": "all",
        "retries": 3,
        "batch_size": settings.kafka_producer_batch_size,
        "linger_ms": settings.kafka_producer_linger_ms,
        "compression_type": "gzip",
        "max_in_flight_requests_per_connection": 1,
        "enable_idempotence": True,
    }


def get_exchange_configs() -> dict:
    """Get exchange API configurations"""
    settings = get_settings()
    return {
        "binance": {
            "api_key": settings.binance_api_key,
            "api_secret": settings.binance_api_secret,
            "testnet": settings.binance_testnet,
            "enabled": bool(settings.binance_api_key and settings.binance_api_secret),
        },
        "coinbase": {
            "api_key": settings.coinbase_api_key,
            "api_secret": settings.coinbase_api_secret,
            "passphrase": settings.coinbase_passphrase,
            "sandbox": settings.coinbase_sandbox,
            "enabled": bool(
                settings.coinbase_api_key 
                and settings.coinbase_api_secret 
                and settings.coinbase_passphrase
            ),
        },
        "kraken": {
            "api_key": settings.kraken_api_key,
            "api_secret": settings.kraken_api_secret,
            "enabled": bool(settings.kraken_api_key and settings.kraken_api_secret),
        },
    }
