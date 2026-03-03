from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Enrichment, Fixture
from app.main import async_session_maker


router = APIRouter()


class EnrichmentResponse(BaseModel):
    id: str
    fixture_id: str
    source: str
    data: dict
    fetched_at: str


async def get_db():
    async with async_session_maker() as session:
        yield session


@router.get("/fixture/{fixture_id}", response_model=List[EnrichmentResponse])
async def get_enrichments_for_fixture(fixture_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Enrichment).where(Enrichment.fixture_id == UUID(fixture_id))
    )
    enrichments = result.scalars().all()
    
    return [
        EnrichmentResponse(
            id=str(e.id),
            fixture_id=str(e.fixture_id),
            source=e.source,
            data=e.data,
            fetched_at=e.fetched_at.isoformat(),
        )
        for e in enrichments
    ]


@router.get("/{enrichment_id}", response_model=EnrichmentResponse)
async def get_enrichment(enrichment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Enrichment).where(Enrichment.id == UUID(enrichment_id))
    )
    enrichment = result.scalar_one_or_none()
    
    if not enrichment:
        raise HTTPException(status_code=404, detail="Enrichment not found")
    
    return EnrichmentResponse(
        id=str(enrichment.id),
        fixture_id=str(enrichment.fixture_id),
        source=enrichment.source,
        data=enrichment.data,
        fetched_at=enrichment.fetched_at.isoformat(),
    )
