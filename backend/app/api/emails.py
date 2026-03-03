"""
Email API for OpenMaritime.

Provides endpoints for email management and fixture extraction.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_

from app.models import Fixture, User
from app.main import async_session_maker
from app.api.auth import get_current_user
from app.services.email_sync import email_sync_service


router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


class EmailMessageResponse(BaseModel):
    id: str
    thread_id: str
    subject: str
    from: str
    to: str
    body: str
    received_at: str
    tags: List[str]
    fixture_id: Optional[str]
    is_read: bool
    synced: bool


class EmailExtractRequest(BaseModel):
    email_id: str


class EmailExtractResponse(BaseModel):
    success: bool
    fixture_id: Optional[str]
    message: str


async def get_db():
    async with async_session_maker() as session:
        yield session


@router.get("/", response_model=List[EmailMessageResponse])
async def list_emails(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    sender: Optional[str] = Query(None, description="Filter by sender"),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List emails for the current user.
    
    In production, this would fetch from Gmail/IMAP via email_sync_service.
    For now, returns fixtures that have source_email_id set.
    """
    # Get fixtures that came from emails (they have source_email_id)
    query = select(Fixture).where(
        Fixture.user_id == current_user.id,
        Fixture.source_email_id.isnot(None)
    )
    
    if tag:
        # Filter by tags in enrichment data
        query = query.where(Fixture.enrichment_data['tags'].contains([tag]))
    
    if sender:
        query = query.where(Fixture.broker.ilike(f"%{sender}%"))
    
    if is_read is not None:
        # Track read status separately - for now skip this filter
        pass
    
    query = query.order_by(desc(Fixture.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    fixtures = result.scalars().all()
    
    # Convert fixtures to email-like response
    emails = []
    for f in fixtures:
        # Extract tags from enrichment_data if available
        tags = f.enrichment_data.get("auto_tags", []) if f.enrichment_data else []
        
        emails.append(EmailMessageResponse(
            id=f.source_email_id or str(f.id),
            thread_id=f.source_email_id or str(f.id),
            subject=f.source_subject or f"Vessel: {f.vessel_name}",
            from=f.broker or "unknown",
            to=current_user.email,
            body=f.raw_data.get("body", "") if f.raw_data else "",
            received_at=f.created_at.isoformat(),
            tags=tags,
            fixture_id=str(f.id),
            is_read=True,
            synced=True,
        ))
    
    return emails


@router.get("/{email_id}", response_model=EmailMessageResponse)
async def get_email(
    email_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific email by ID"""
    result = await db.execute(
        select(Fixture).where(
            Fixture.user_id == current_user.id,
            or_(
                Fixture.source_email_id == email_id,
                Fixture.id == UUID(email_id)
            )
        )
    )
    fixture = result.scalar_one_or_none()
    
    if not fixture:
        raise HTTPException(status_code=404, detail="Email not found")
    
    tags = fixture.enrichment_data.get("auto_tags", []) if fixture.enrichment_data else []
    
    return EmailMessageResponse(
        id=fixture.source_email_id or str(fixture.id),
        thread_id=fixture.source_email_id or str(fixture.id),
        subject=fixture.source_subject or f"Vessel: {fixture.vessel_name}",
        from=fixture.broker or "unknown",
        to=current_user.email,
        body=fixture.raw_data.get("body", "") if fixture.raw_data else "",
        received_at=fixture.created_at.isoformat(),
        tags=tags,
        fixture_id=str(fixture.id),
        is_read=True,
        synced=True,
    )


@router.post("/extract", response_model=EmailExtractResponse)
async def extract_fixture_from_email(
    request: EmailExtractRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract fixture data from an email.
    
    This triggers the AI extraction pipeline on the email content.
    """
    # Find the fixture associated with this email
    result = await db.execute(
        select(Fixture).where(
            Fixture.user_id == current_user.id,
            or_(
                Fixture.source_email_id == request.email_id,
                Fixture.id == UUID(request.email_id)
            )
        )
    )
    fixture = result.scalar_one_or_none()
    
    if not fixture:
        raise HTTPException(status_code=404, detail="Email/fixture not found")
    
    # Run the extraction agent
    from app.services.wake_ai import wake_ai_service
    
    try:
        await wake_ai_service.score_fixture(fixture)
        await db.commit()
        
        return EmailExtractResponse(
            success=True,
            fixture_id=str(fixture.id),
            message="Fixture extracted and scored successfully"
        )
    except Exception as e:
        return EmailExtractResponse(
            success=False,
            fixture_id=str(fixture.id),
            message=f"Extraction failed: {str(e)}"
        )


@router.post("/sync")
async def sync_emails(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger email sync for the current user.
    
    This would connect to Gmail/IMAP and sync new emails.
    """
    try:
        # Check if user has email sync configured
        from app.models import EmailSync
        
        result = await db.execute(
            select(EmailSync).where(
                EmailSync.user_id == current_user.id,
                EmailSync.is_active == True
            )
        )
        email_sync = result.scalar_one_or_none()
        
        if not email_sync:
            return {
                "status": "no_config",
                "message": "No email sync configured. Connect email in Settings."
            }
        
        # Trigger sync
        await email_sync_service.sync_gmail(current_user.id, db)
        
        return {
            "status": "success",
            "message": "Emails synced successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/tags/list")
async def list_email_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of all tags used in emails"""
    result = await db.execute(
        select(Fixture.enrichment_data['auto_tags']).where(
            Fixture.user_id == current_user.id,
            Fixture.source_email_id.isnot(None),
            Fixture.enrichment_data.isnot(None)
        )
    )
    
    all_tags = set()
    for row in result.all():
        if row[0]:
            all_tags.update(row[0])
    
    return {"tags": sorted(list(all_tags))}
