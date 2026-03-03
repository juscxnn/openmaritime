from celery import Celery
import os
import json
import logging

logger = logging.getLogger(__name__)


def create_kafka_consumer():
    """Create Kafka consumer for high-volume fixture ingestion"""
    from kafka import KafkaConsumer
    
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("KAFKA_FIXTURES_TOPIC", "fixtures")
    
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="openmaritime-consumer",
        )
        return consumer
    except Exception as e:
        logger.error(f"Failed to create Kafka consumer: {e}")
        return None


def start_kafka_consumer():
    """Start Kafka consumer as background task"""
    from app.workers.tasks import kafka_ingest
    
    consumer = create_kafka_consumer()
    
    if not consumer:
        logger.warning("Kafka consumer not available, running in stub mode")
        return
    
    logger.info("Starting Kafka consumer...")
    
    try:
        for message in consumer:
            try:
                fixture_data = message.value
                logger.info(f"Received fixture from Kafka: {fixture_data.get('vessel_name')}")
                
                kafka_ingest.delay(fixture_data)
            except Exception as e:
                logger.error(f"Error processing Kafka message: {e}")
    except KeyboardInterrupt:
        logger.info("Kafka consumer stopped")
    finally:
        consumer.close()
