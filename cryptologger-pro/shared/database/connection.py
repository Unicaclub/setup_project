"""
Database connection layer for CryptoLogger Pro
Async SQLAlchemy with connection pooling, health checks, and multi-tenant support
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator, List
from urllib.parse import urlparse

import asyncpg
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from prometheus_client import Counter, Histogram, Gauge

from ..models.database import Base
from ...services.data_ingestion.src.utils.retry import async_retry
from ...services.data_ingestion.src.utils.circuit_breaker import CircuitBreaker

# Metrics
db_connections_total = Counter(
    'db_connections_total',
    'Total database connections created',
    ['status']
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query execution time',
    ['operation', 'table']
)

db_active_connections = Gauge(
    'db_active_connections',
    'Number of active database connections'
)

db_pool_size = Gauge(
    'db_pool_size',
    'Database connection pool size'
)

db_pool_checked_out = Gauge(
    'db_pool_checked_out',
    'Number of connections checked out from pool'
)


class DatabaseConfig:
    """Database configuration class"""
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 30,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False,
        echo_pool: bool = False
    ):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo
        self.echo_pool = echo_pool
        
        # Parse URL for connection details
        parsed = urlparse(database_url)
        self.host = parsed.hostname
        self.port = parsed.port or 5432
        self.database = parsed.path.lstrip('/')
        self.username = parsed.username
        self.password = parsed.password


class DatabaseManager:
    """
    Enterprise database manager with:
    - Async connection pooling
    - Health monitoring
    - Multi-tenant support
    - Circuit breaker protection
    - Automatic retries
    - Performance metrics
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Database engines
        self.async_engine: Optional[AsyncEngine] = None
        self.sync_engine = None
        
        # Session factories
        self.async_session_factory: Optional[async_sessionmaker] = None
        self.sync_session_factory = None
        
        # Circuit breaker for database operations
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(SQLAlchemyError, asyncpg.PostgresError),
            name="database"
        )
        
        # Health check state
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds
        self.is_healthy = False
        
        # Connection pool monitoring
        self._setup_pool_monitoring()
    
    async def initialize(self) -> None:
        """Initialize database connections and engines"""
        try:
            self.logger.info("Initializing database connections...")
            
            # Create async engine
            self.async_engine = create_async_engine(
                self.config.database_url.replace('postgresql://', 'postgresql+asyncpg://'),
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=self.config.pool_pre_ping,
                echo=self.config.echo,
                echo_pool=self.config.echo_pool,
                future=True
            )
            
            # Create sync engine for migrations and admin tasks
            self.sync_engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=self.config.pool_pre_ping,
                echo=self.config.echo,
                future=True
            )
            
            # Create session factories
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self.sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                expire_on_commit=False
            )
            
            # Test connection
            await self.health_check()
            
            self.logger.info("Database connections initialized successfully")
            db_connections_total.labels(status='success').inc()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            db_connections_total.labels(status='error').inc()
            raise
    
    async def close(self) -> None:
        """Close all database connections"""
        try:
            self.logger.info("Closing database connections...")
            
            if self.async_engine:
                await self.async_engine.dispose()
            
            if self.sync_engine:
                self.sync_engine.dispose()
            
            self.logger.info("Database connections closed")
            
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session with automatic cleanup
        
        Usage:
            async with db_manager.get_session() as session:
                result = await session.execute(query)
        """
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized")
        
        session = self.async_session_factory()
        try:
            db_active_connections.inc()
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
            db_active_connections.dec()
    
    @asynccontextmanager
    async def get_tenant_session(self, tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
        """
        Get tenant-isolated database session with RLS
        
        Args:
            tenant_id: Tenant UUID for row-level security
        """
        async with self.get_session() as session:
            # Set tenant context for RLS
            await session.execute(
                text("SET app.current_tenant_id = :tenant_id"),
                {"tenant_id": tenant_id}
            )
            yield session
    
    @async_retry(max_attempts=3, delay=1.0, backoff=2.0)
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive database health check
        
        Returns:
            Dict with health status and metrics
        """
        current_time = time.time()
        
        # Skip if recently checked
        if current_time - self.last_health_check < self.health_check_interval:
            return {"status": "healthy" if self.is_healthy else "unhealthy"}
        
        try:
            start_time = time.time()
            
            # Test async connection
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                health_result = result.scalar()
                
                if health_result != 1:
                    raise Exception("Health check query returned unexpected result")
            
            # Test TimescaleDB extension
            async with self.get_session() as session:
                result = await session.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
                )
                timescaledb_installed = result.scalar() is not None
            
            # Get connection pool stats
            pool_stats = self._get_pool_stats()
            
            # Calculate response time
            response_time = time.time() - start_time
            
            self.is_healthy = True
            self.last_health_check = current_time
            
            health_data = {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "timescaledb_enabled": timescaledb_installed,
                "pool_stats": pool_stats,
                "last_check": current_time
            }
            
            self.logger.debug(f"Database health check passed: {response_time:.3f}s")
            return health_data
            
        except Exception as e:
            self.is_healthy = False
            self.last_health_check = current_time
            
            self.logger.error(f"Database health check failed: {e}")
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": current_time
            }
    
    def _get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        if not self.async_engine:
            return {}
        
        pool = self.async_engine.pool
        
        stats = {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin()
        }
        
        # Update Prometheus metrics
        db_pool_size.set(stats["pool_size"])
        db_pool_checked_out.set(stats["checked_out"])
        
        return stats
    
    def _setup_pool_monitoring(self) -> None:
        """Setup connection pool event monitoring"""
        
        @event.listens_for(QueuePool, "connect")
        def on_connect(dbapi_conn, connection_record):
            """Handle new connection creation"""
            self.logger.debug("New database connection created")
            db_connections_total.labels(status='created').inc()
        
        @event.listens_for(QueuePool, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool"""
            db_active_connections.inc()
        
        @event.listens_for(QueuePool, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            """Handle connection checkin to pool"""
            db_active_connections.dec()
        
        @event.listens_for(QueuePool, "close")
        def on_close(dbapi_conn, connection_record):
            """Handle connection close"""
            self.logger.debug("Database connection closed")
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> Any:
        """
        Execute raw SQL query with circuit breaker protection
        
        Args:
            query: SQL query string
            params: Query parameters
            tenant_id: Optional tenant ID for RLS
            
        Returns:
            Query result
        """
        async def _execute():
            session_manager = (
                self.get_tenant_session(tenant_id) 
                if tenant_id 
                else self.get_session()
            )
            
            async with session_manager as session:
                result = await session.execute(text(query), params or {})
                return result
        
        return await self.circuit_breaker.call(_execute)
    
    async def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a specific table"""
        query = """
        SELECT 
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_tuples,
            n_dead_tup as dead_tuples,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables 
        WHERE tablename = :table_name
        """
        
        result = await self.execute_query(query, {"table_name": table_name})
        row = result.fetchone()
        
        if row:
            return dict(row._mapping)
        return {}
    
    async def get_hypertable_stats(self) -> List[Dict[str, Any]]:
        """Get TimescaleDB hypertable statistics"""
        query = """
        SELECT 
            hypertable_schema,
            hypertable_name,
            num_chunks,
            compression_enabled,
            compressed_chunks,
            uncompressed_chunks
        FROM timescaledb_information.hypertables
        """
        
        try:
            result = await self.execute_query(query)
            return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            self.logger.warning(f"Could not fetch hypertable stats: {e}")
            return []
    
    async def optimize_performance(self) -> Dict[str, Any]:
        """Run database performance optimization tasks"""
        optimizations = {}
        
        try:
            # Update table statistics
            await self.execute_query("ANALYZE;")
            optimizations["analyze"] = "completed"
            
            # Get slow query stats
            slow_queries = await self.execute_query("""
                SELECT query, calls, total_time, mean_time
                FROM pg_stat_statements 
                WHERE mean_time > 1000 
                ORDER BY mean_time DESC 
                LIMIT 10
            """)
            
            optimizations["slow_queries"] = [
                dict(row._mapping) for row in slow_queries.fetchall()
            ]
            
        except Exception as e:
            self.logger.error(f"Performance optimization error: {e}")
            optimizations["error"] = str(e)
        
        return optimizations


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


async def initialize_database(database_url: str, **kwargs) -> DatabaseManager:
    """
    Initialize global database manager
    
    Args:
        database_url: PostgreSQL connection URL
        **kwargs: Additional configuration options
        
    Returns:
        DatabaseManager instance
    """
    global db_manager
    
    config = DatabaseConfig(database_url, **kwargs)
    db_manager = DatabaseManager(config)
    await db_manager.initialize()
    
    return db_manager


async def get_database() -> DatabaseManager:
    """Get global database manager instance"""
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return db_manager


async def close_database() -> None:
    """Close global database manager"""
    global db_manager
    if db_manager:
        await db_manager.close()
        db_manager = None


# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    db = await get_database()
    async with db.get_session() as session:
        yield session


async def get_tenant_db_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for tenant-isolated database sessions"""
    db = await get_database()
    async with db.get_tenant_session(tenant_id) as session:
        yield session
