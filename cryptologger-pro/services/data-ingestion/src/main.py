"""
CryptoLogger Pro - Data Ingestion Service
Enterprise blockchain compliance monitoring platform
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import health, ingestion, webhooks
from core.config import get_settings
from core.kafka_client import KafkaClient
from core.redis_client import RedisClient
from core.exchange_manager import ExchangeManager
from utils.logger import setup_logging
from utils.metrics import setup_metrics


# Global instances
kafka_client: KafkaClient = None
redis_client: RedisClient = None
exchange_manager: ExchangeManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global kafka_client, redis_client, exchange_manager
    
    settings = get_settings()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize clients
        logger.info("Initializing data ingestion service...")
        
        # Initialize Kafka client
        kafka_client = KafkaClient(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id=f"data_ingestion-{settings.service_instance_id}"
        )
        await kafka_client.start()
        
        # Initialize Redis client
        redis_client = RedisClient(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db
        )
        await redis_client.connect()
        
        # Initialize Exchange Manager
        exchange_manager = ExchangeManager(
            kafka_client=kafka_client,
            redis_client=redis_client
        )
        await exchange_manager.initialize()
        
        # Store in app state
        app.state.kafka_client = kafka_client
        app.state.redis_client = redis_client
        app.state.exchange_manager = exchange_manager
        
        logger.info("Data ingestion service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down data ingestion service...")
        
        if exchange_manager:
            await exchange_manager.shutdown()
        if kafka_client:
            await kafka_client.stop()
        if redis_client:
            await redis_client.disconnect()
            
        logger.info("Data ingestion service shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    settings = get_settings()
    
    # Setup logging
    setup_logging(
        level=settings.log_level,
        service_name="data_ingestion"
    )
    
    # Create FastAPI app
    app = FastAPI(
        title="CryptoLogger Pro - Data Ingestion Service",
        description="Enterprise blockchain compliance monitoring - Real-time data ingestion",
        version="1.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Setup metrics
    setup_metrics(app)
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app)
    
    # Include routers
    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Data Ingestion"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
    
    return app


# Create app instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CryptoLogger Pro - Data Ingestion Service",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # Metrics are automatically exposed by instrumentator
    pass


if __name__ == "__main__":
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        workers=1 if settings.environment == "development" else settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True,
        loop="asyncio"
    )
