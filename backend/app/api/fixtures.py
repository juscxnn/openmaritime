from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models import Fixture, User
from app.main import async_session_maker
from app.services.wake_ai import WakeAIService


router = APIRouter()
wake_ai = WakeAIService()


class FixtureCreate(BaseModel):
    vessel_name: str
    imo_number: Optional[str] = None
    cargo_type: str
    cargo_quantity: float
    cargo_unit: str = "MT"
    laycan_start: str
    laycan_end: str
    rate: Optional[float] = None
    rate_currency: str = "USD"
    rate_unit: str = "/mt"
    port_loading: str
    port_discharge: str
    charterer: Optional[str] = None
    broker: Optional[str] = None
    source_email_id: Optional[str] = None
    source_subject: Optional[str] = None


class FixtureUpdate(BaseModel):
    vessel_name: Optional[str] = None
    cargo_type: Optional[str] = None
    rate: Optional[float] = None
    status: Optional[str] = None
    wake_score: Optional[float] = None


class FixtureResponse(BaseModel):
    id: str
    vessel_name: str
    imo_number: Optional[str]
    cargo_type: str
    cargo_quantity: float
    cargo_unit: str
    laycan_start: str
    laycan_end: str
    rate: Optional[float]
    rate_currency: str
    rate_unit: str
    port_loading: str
    port_discharge: str
    charterer: Optional[str]
    broker: Optional[str]
    status: str
    wake_score: Optional[float]
    tce_estimate: Optional[float]
    market_diff: Optional[float]
    enrichment_data: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


async def get_db():
    async with async_session_maker() as session:
        yield session


@router.get("/", response_model=List[FixtureResponse])
async def list_fixtures(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = "wake_score",
    sort_order: str = "desc",
):
    query = select(Fixture)
    
    if status:
        query = query.where(Fixture.status == status)
    
    if sort_by == "wake_score":
        query = query.order_by(desc(Fixture.wake_score) if sort_order == "desc" else Fixture.wake_score)
    elif sort_by == "created_at":
        query = query.order_by(desc(Fixture.created_at) if sort_order == "desc" else Fixture.created_at)
    else:
        query = query.order_by(desc(Fixture.created_at))
    
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    fixtures = result.scalars().all()
    
    return [
        FixtureResponse(
            id=str(f.id),
            vessel_name=f.vessel_name,
            imo_number=f.imo_number,
            cargo_type=f.cargo_type,
            cargo_quantity=f.cargo_quantity,
            cargo_unit=f.cargo_unit,
            laycan_start=f.laycan_start.isoformat(),
            laycan_end=f.laycan_end.isoformat(),
            rate=f.rate,
            rate_currency=f.rate_currency,
            rate_unit=f.rate_unit,
            port_loading=f.port_loading,
            port_discharge=f.port_discharge,
            charterer=f.charterer,
            broker=f.broker,
            status=f.status,
            wake_score=f.wake_score,
            tce_estimate=f.tce_estimate,
            market_diff=f.market_diff,
            enrichment_data=f.enrichment_data,
            created_at=f.created_at.isoformat(),
        )
        for f in fixtures
    ]


@router.get("/{fixture_id}", response_model=FixtureResponse)
async def get_fixture(fixture_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fixture).where(Fixture.id == UUID(fixture_id)))
    fixture = result.scalar_one_or_none()
    
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")
    
    return FixtureResponse(
        id=str(fixture.id),
        vessel_name=fixture.vessel_name,
        imo_number=fixture.imo_number,
        cargo_type=fixture.cargo_type,
        cargo_quantity=fixture.cargo_quantity,
        cargo_unit=fixture.cargo_unit,
        laycan_start=fixture.laycan_start.isoformat(),
        laycan_end=fixture.laycan_end.isoformat(),
        rate=fixture.rate,
        rate_currency=fixture.rate_currency,
        rate_unit=fixture.rate_unit,
        port_loading=fixture.port_loading,
        port_discharge=fixture.port_discharge,
        charterer=fixture.charterer,
        broker=fixture.broker,
        status=fixture.status,
        wake_score=fixture.wake_score,
        tce_estimate=fixture.tce_estimate,
        market_diff=fixture.market_diff,
        enrichment_data=fixture.enrichment_data,
        created_at=fixture.created_at.isoformat(),
    )


@router.post("/", response_model=FixtureResponse)
async def create_fixture(fixture: FixtureCreate, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    
    db_fixture = Fixture(
        vessel_name=fixture.vessel_name,
        imo_number=fixture.imo_number,
        cargo_type=fixture.cargo_type,
        cargo_quantity=fixture.cargo_quantity,
        cargo_unit=fixture.cargo_unit,
        laycan_start=datetime.fromisoformat(fixture.laycan_start),
        laycan_end=datetime.fromisoformat(fixture.laycan_end),
        rate=fixture.rate,
        rate_currency=fixture.rate_currency,
        rate_unit=fixture.rate_unit,
        port_loading=fixture.port_loading,
        port_discharge=fixture.port_discharge,
        charterer=fixture.charterer,
        broker=fixture.broker,
        source_email_id=fixture.source_email_id,
        source_subject=fixture.source_subject,
    )
    
    db.add(db_fixture)
    await db.commit()
    await db.refresh(db_fixture)
    
    scored = await wake_ai.score_fixture(db_fixture)
    
    return FixtureResponse(
        id=str(db_fixture.id),
        vessel_name=db_fixture.vessel_name,
        imo_number=db_fixture.imo_number,
        cargo_type=db_fixture.cargo_type,
        cargo_quantity=db_fixture.cargo_quantity,
        cargo_unit=db_fixture.cargo_unit,
        laycan_start=db_fixture.laycan_start.isoformat(),
        laycan_end=db_fixture.laycan_end.isoformat(),
        rate=db_fixture.rate,
        rate_currency=db_fixture.rate_currency,
        rate_unit=db_fixture.rate_unit,
        port_loading=db_fixture.port_loading,
        port_discharge=db_fixture.port_discharge,
        charterer=db_fixture.charterer,
        broker=db_fixture.broker,
        status=db_fixture.status,
        wake_score=db_fixture.wake_score,
        tce_estimate=db_fixture.tce_estimate,
        market_diff=db_fixture.market_diff,
        enrichment_data=db_fixture.enrichment_data,
        created_at=db_fixture.created_at.isoformat(),
    )


@router.post("/{fixture_id}/rank")
async def rank_fixture(fixture_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fixture).where(Fixture.id == UUID(fixture_id)))
    fixture = result.scalar_one_or_none()
    
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")
    
    scored = await wake_ai.score_fixture(fixture)
    await db.commit()
    
    return {"wake_score": scored.wake_score, "tce_estimate": scored.tce_estimate, "market_diff": scored.market_diff}


@router.post("/{fixture_id}/enrich")
async def enrich_fixture(fixture_id: str, db: AsyncSession = Depends(get_db)):
    from app.services.plugin_manager import plugin_manager
    
    result = await db.execute(select(Fixture).where(Fixture.id == UUID(fixture_id)))
    fixture = result.scalar_one_or_none()
    
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")
    
    await plugin_manager.execute_hook("on_fixture_enrich", fixture)
    await db.commit()
    await db.refresh(fixture)
    
    return {"enrichment_data": fixture.enrichment_data}


@router.patch("/{fixture_id}", response_model=FixtureResponse)
async def update_fixture(
    fixture_id: str,
    update: FixtureUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Fixture).where(Fixture.id == UUID(fixture_id)))
    fixture = result.scalar_one_or_none()
    
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")
    
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(fixture, field, value)
    
    await db.commit()
    await db.refresh(fixture)
    
    return FixtureResponse(
        id=str(fixture.id),
        vessel_name=fixture.vessel_name,
        imo_number=fixture.imo_number,
        cargo_type=fixture.cargo_type,
        cargo_quantity=fixture.cargo_quantity,
        cargo_unit=fixture.cargo_unit,
        laycan_start=fixture.laycan_start.isoformat(),
        laycan_end=fixture.laycan_end.isoformat(),
        rate=fixture.rate,
        rate_currency=fixture.rate_currency,
        rate_unit=fixture.rate_unit,
        port_loading=fixture.port_loading,
        port_discharge=fixture.port_discharge,
        charterer=fixture.charterer,
        broker=fixture.broker,
        status=fixture.status,
        wake_score=fixture.wake_score,
        tce_estimate=fixture.tce_estimate,
        market_diff=fixture.market_diff,
        enrichment_data=fixture.enrichment_data,
        created_at=fixture.created_at.isoformat(),
    )


@router.delete("/{fixture_id}")
async def delete_fixture(fixture_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fixture).where(Fixture.id == UUID(fixture_id)))
    fixture = result.scalar_one_or_none()
    
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")
    
    await db.delete(fixture)
    await db.commit()
    
    return {"status": "deleted"}
