"""
Kafka client for CryptoLogger Pro Data Ingestion Service
Handles message publishing to Kafka topics with reliability and performance
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError, KafkaTimeoutError
from prometheus_client import Counter, Histogram, Gauge

from .config import get_kafka_config
from ..utils.circuit_breaker import CircuitBreaker
from ..utils.retry import async_retry


# Metrics
kafka_messages_sent = Counter(
    'kafka_messages_sent_total',
    'Total number of messages sent to Kafka',
    ['topic', 'status']
)

kafka_message_size = Histogram(
    'kafka_message_size_bytes',
    'Size of messages sent to Kafka',
    ['topic']
)

kafka_send_duration = Histogram(
    'kafka_send_duration_seconds',
    'Time taken to send messages to Kafka',
    ['topic']
)

kafka_connection_status = Gauge(
    'kafka_connection_status',
    'Kafka connection status (1=connected, 0=disconnected)'
)


class KafkaClient:
    """
    Async Kafka client with enterprise features:
    - Circuit breaker pattern
    - Automatic retries
    - Message batching
    - Compression
    - Metrics collection
    - Multi-tenant support
    """
    
    def __init__(self, bootstrap_servers: str, client_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.config = get_kafka_config()
        self.logger = logging.getLogger(__name__)
        
        # Kafka producer and consumer
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        
        # Circuit breaker for fault tolerance
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=KafkaError
        )
        
        # Connection state
        self.is_connected = False
        self.connection_lock = asyncio.Lock()
        
        # Message batching
        self.batch_queue: List[Dict[str, Any]] = []
        self.batch_lock = asyncio.Lock()
        self.batch_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.messages_sent = 0
        self.messages_failed = 0
        self.last_health_check = time.time()
    
    async def start(self) -> None:
        """Start Kafka producer and consumer"""
        async with self.connection_lock:
            if self.is_connected:
                return
            
            try:
                self.logger.info("Starting Kafka client...")
                
                # Initialize producer
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    client_id=self.client_id,
                    **self.config
                )
                
                await self.producer.start()
                
                # Start batch processing task
                self.batch_task = asyncio.create_task(self._batch_processor())
                
                self.is_connected = True
                kafka_connection_status.set(1)
                
                self.logger.info("Kafka client started successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to start Kafka client: {e}")
                kafka_connection_status.set(0)
                raise
    
    async def stop(self) -> None:
        """Stop Kafka producer and consumer"""
        async with self.connection_lock:
            if not self.is_connected:
                return
            
            try:
                self.logger.info("Stopping Kafka client...")
                
                # Cancel batch processing task
                if self.batch_task:
                    self.batch_task.cancel()
                    try:
                        await self.batch_task
                    except asyncio.CancelledError:
                        pass
                
                # Process remaining batched messages
                await self._flush_batch()
                
                # Stop producer
                if self.producer:
                    await self.producer.stop()
                
                # Stop consumer
                if self.consumer:
                    await self.consumer.stop()
                
                self.is_connected = False
                kafka_connection_status.set(0)
                
                self.logger.info("Kafka client stopped successfully")
                
            except Exception as e:
                self.logger.error(f"Error stopping Kafka client: {e}")
    
    @async_retry(max_attempts=3, delay=1.0, backoff=2.0)
    async def send_message(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        batch: bool = False
    ) -> bool:
        """
        Send message to Kafka topic
        
        Args:
            topic: Kafka topic name
            message: Message payload
            key: Message key for partitioning
            tenant_id: Tenant ID for multi-tenant support
            batch: Whether to batch this message
        
        Returns:
            bool: True if message sent successfully
        """
        if not self.is_connected:
            raise RuntimeError("Kafka client not connected")
        
        # Add metadata to message
        enriched_message = {
            **message,
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "service": "data_ingestion",
            "version": "1.0.0"
        }
        
        if batch:
            return await self._add_to_batch(topic, enriched_message, key)
        else:
            return await self._send_immediate(topic, enriched_message, key)
    
    async def _send_immediate(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """Send message immediately"""
        try:
            with kafka_send_duration.labels(topic=topic).time():
                # Serialize message
                message_bytes = json.dumps(message, default=str).encode('utf-8')
                key_bytes = key.encode('utf-8') if key else None
                
                # Record message size
                kafka_message_size.labels(topic=topic).observe(len(message_bytes))
                
                # Send message through circuit breaker
                await self.circuit_breaker.call(
                    self.producer.send_and_wait,
                    topic,
                    message_bytes,
                    key=key_bytes
                )
                
                # Update metrics
                kafka_messages_sent.labels(topic=topic, status='success').inc()
                self.messages_sent += 1
                
                self.logger.debug(f"Message sent to topic {topic}")
                return True
                
        except Exception as e:
            kafka_messages_sent.labels(topic=topic, status='error').inc()
            self.messages_failed += 1
            self.logger.error(f"Failed to send message to topic {topic}: {e}")
            raise
    
    async def _add_to_batch(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """Add message to batch queue"""
        async with self.batch_lock:
            self.batch_queue.append({
                'topic': topic,
                'message': message,
                'key': key,
                'timestamp': time.time()
            })
            
            # If batch is full, process immediately
            if len(self.batch_queue) >= self.config.get('batch_size', 100):
                await self._flush_batch()
            
            return True
    
    async def _batch_processor(self) -> None:
        """Background task to process batched messages"""
        while True:
            try:
                await asyncio.sleep(self.config.get('linger_ms', 10) / 1000)
                
                if self.batch_queue:
                    await self._flush_batch()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in batch processor: {e}")
    
    async def _flush_batch(self) -> None:
        """Flush all batched messages"""
        async with self.batch_lock:
            if not self.batch_queue:
                return
            
            batch = self.batch_queue.copy()
            self.batch_queue.clear()
        
        # Group messages by topic for efficient sending
        topic_batches = {}
        for item in batch:
            topic = item['topic']
            if topic not in topic_batches:
                topic_batches[topic] = []
            topic_batches[topic].append(item)
        
        # Send batches
        for topic, messages in topic_batches.items():
            try:
                await self._send_batch(topic, messages)
            except Exception as e:
                self.logger.error(f"Failed to send batch to topic {topic}: {e}")
    
    async def _send_batch(self, topic: str, messages: List[Dict[str, Any]]) -> None:
        """Send a batch of messages to a topic"""
        try:
            # Create batch of futures
            futures = []
            
            for item in messages:
                message_bytes = json.dumps(item['message'], default=str).encode('utf-8')
                key_bytes = item['key'].encode('utf-8') if item['key'] else None
                
                kafka_message_size.labels(topic=topic).observe(len(message_bytes))
                
                future = await self.producer.send(topic, message_bytes, key=key_bytes)
                futures.append(future)
            
            # Wait for all messages to be sent
            await asyncio.gather(*futures)
            
            # Update metrics
            kafka_messages_sent.labels(topic=topic, status='success').inc(len(messages))
            self.messages_sent += len(messages)
            
            self.logger.debug(f"Batch of {len(messages)} messages sent to topic {topic}")
            
        except Exception as e:
            kafka_messages_sent.labels(topic=topic, status='error').inc(len(messages))
            self.messages_failed += len(messages)
            raise
    
    async def send_transaction_event(
        self,
        transaction_data: Dict[str, Any],
        tenant_id: str
    ) -> bool:
        """Send transaction event to transactions topic"""
        return await self.send_message(
            topic="crypto-transactions",
            message=transaction_data,
            key=transaction_data.get('transaction_hash'),
            tenant_id=tenant_id,
            batch=True
        )
    
    async def send_compliance_event(
        self,
        compliance_data: Dict[str, Any],
        tenant_id: str
    ) -> bool:
        """Send compliance event to compliance topic"""
        return await self.send_message(
            topic="compliance-events",
            message=compliance_data,
            key=compliance_data.get('transaction_id'),
            tenant_id=tenant_id,
            batch=False  # Compliance events are high priority
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        current_time = time.time()
        
        health_status = {
            "status": "healthy" if self.is_connected else "unhealthy",
            "connected": self.is_connected,
            "messages_sent": self.messages_sent,
            "messages_failed": self.messages_failed,
            "batch_queue_size": len(self.batch_queue),
            "circuit_breaker_state": self.circuit_breaker.state,
            "last_check": current_time,
            "uptime": current_time - self.last_health_check
        }
        
        self.last_health_check = current_time
        return health_status
    
    @asynccontextmanager
    async def consumer_context(self, topics: List[str], group_id: str):
        """Context manager for Kafka consumer"""
        consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            client_id=f"{self.client_id}-consumer",
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        try:
            await consumer.start()
            yield consumer
        finally:
            await consumer.stop()
