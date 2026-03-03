from celery import Celery
from celery.signals import worker_ready
import os
import asyncio

celery_app = Celery(
    "openmaritime",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.sync_emails": {"queue": "email"},
        "app.workers.tasks.extract_fixture": {"queue": "extraction"},
        "app.workers.tasks.enrich_fixture": {"queue": "enrichment"},
        "app.workers.tasks.rank_fixture": {"queue": "ranking"},
        "app.workers.tasks.broadcast_update": {"queue": "broadcast"},
    },
)


@celery_app.task(bind=True)
def sync_emails(self, user_id: str):
    """Sync emails and extract fixtures"""
    from app.services.email_sync import email_sync_service
    from app.main import async_session_maker
    
    async def _run():
        async with async_session_maker() as session:
            return await email_sync_service.sync_gmail(user_id, session)
    
    return asyncio.run(_run())


@celery_app.task(bind=True)
def extract_fixture(self, email_data: dict):
    """Extract fixture from email content"""
    from app.services.email_sync import EmailSyncService
    
    service = EmailSyncService()
    return service._parse_fixture_from_text(
        email_data.get("subject", ""),
        email_data.get("body", ""),
        email_data.get("from", ""),
        email_data.get("id", ""),
    )


@celery_app.task(bind=True)
def enrich_fixture(self, fixture_id: str):
    """Enrich fixture with all plugins"""
    from app.services.plugin_manager import plugin_manager
    from app.main import async_session_maker
    from sqlalchemy import select
    from app.models import Fixture
    
    async def _run():
        async with async_session_maker() as session:
            result = await session.execute(select(Fixture).where(Fixture.id == fixture_id))
            fixture = result.scalar_one_or_none()
            
            if not fixture:
                return {"error": "Fixture not found"}
            
            await plugin_manager.execute_hook("on_fixture_enrich", fixture)
            await session.commit()
            
            return {"fixture_id": fixture_id, "enrichment": fixture.enrichment_data}
    
    return asyncio.run(_run())


@celery_app.task(bind=True)
def rank_fixture(self, fixture_id: str):
    """Rank fixture using Wake AI"""
    from app.services.wake_ai import wake_ai_service
    from app.main import async_session_maker
    from sqlalchemy import select
    from app.models import Fixture
    
    async def _run():
        async with async_session_maker() as session:
            result = await session.execute(select(Fixture).where(Fixture.id == fixture_id))
            fixture = result.scalar_one_or_none()
            
            if not fixture:
                return {"error": "Fixture not found"}
            
            await wake_ai_service.score_fixture(fixture)
            await session.commit()
            
            return {
                "fixture_id": fixture_id,
                "wake_score": fixture.wake_score,
                "tce_estimate": fixture.tce_estimate,
                "market_diff": fixture.market_diff,
            }
    
    return asyncio.run(_run())


@celery_app.task(bind=True)
def process_fixture_pipeline(self, fixture_id: str):
    """Run full Wake AI pipeline for fixture"""
    from app.workers.tasks import enrich_fixture, rank_fixture
    
    chain = enrich_fixture.s(fixture_id) | rank_fixture.s(fixture_id)
    result = chain.apply_async()
    
    return {"task_id": result.id, "fixture_id": fixture_id}


@celery_app.task(bind=True)
def broadcast_update(self, event_type: str, data: dict):
    """Broadcast update via Socket.io"""
    from app.services.socket_service import socket_service
    
    asyncio.run(socket_service.broadcast(event_type, data))
    
    return {"broadcasted": event_type}


@celery_app.task(bind=True)
def kafka_ingest(self, fixture_data: dict):
    """Ingest fixture from Kafka stream"""
    from app.workers.tasks import process_fixture_pipeline
    from app.main import async_session_maker
    from app.models import Fixture
    from datetime import datetime
    
    async def _run():
        async with async_session_maker() as session:
            fixture = Fixture(
                user_id=fixture_data.get("user_id"),
                vessel_name=fixture_data.get("vessel_name", "Unknown"),
                imo_number=fixture_data.get("imo_number"),
                cargo_type=fixture_data.get("cargo_type", "General"),
                cargo_quantity=fixture_data.get("cargo_quantity", 0),
                cargo_unit=fixture_data.get("cargo_unit", "MT"),
                laycan_start=datetime.fromisoformat(fixture_data["laycan_start"]) if fixture_data.get("laycan_start") else datetime.utcnow(),
                laycan_end=datetime.fromisoformat(fixture_data["laycan_end"]) if fixture_data.get("laycan_end") else datetime.utcnow(),
                rate=fixture_data.get("rate"),
                port_loading=fixture_data.get("port_loading", "TBD"),
                port_discharge=fixture_data.get("port_discharge", "TBD"),
            )
            session.add(fixture)
            await session.commit()
            
            process_fixture_pipeline.delay(str(fixture.id))
            
            return {"fixture_id": str(fixture.id)}
    
    return asyncio.run(_run())


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Initialize Kafka consumer when worker is ready"""
    from app.workers.kafka_consumer import start_kafka_consumer
    start_kafka_consumer.delay()
