"""
Audit Logs API for OpenMaritime.

Provides endpoints for querying audit logs.
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User
from app.api.deps import get_db
from app.services.audit_service import audit_service
from app.api.auth import get_current_user


router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    actor_type: str
    actor_id: Optional[str]
    old_value: Optional[dict]
    new_value: Optional[dict]
    ip_address: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    actor_type: Optional[str] = None
    status: Optional[str] = None
    limit: int = 100
    offset: int = 0


@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action prefix"),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs for the current tenant"""
    
    # Get user's tenant
    tenant_id = getattr(current_user, 'tenant_id', None)
    if not tenant_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="No tenant found")
    
    # Convert user_id string to UUID if provided
    user_uuid = None
    if user_id:
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            pass
    
    logs = await audit_service.query_logs(
        db=db,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_uuid,
        actor_type=actor_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    
    return [
        AuditLogResponse(
            id=str(log.id),
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            actor_type=log.actor_type,
            actor_id=log.actor_id,
            old_value=log.old_value,
            new_value=log.new_value,
            ip_address=log.ip_address,
            status=log.status,
            error_message=log.error_message,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific audit log entry"""
    
    from sqlalchemy import select
    
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == UUID(log_id))
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    # Check tenant access
    tenant_id = getattr(current_user, 'tenant_id', None)
    if log.tenant_id != tenant_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return AuditLogResponse(
        id=str(log.id),
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        actor_type=log.actor_type,
        actor_id=log.actor_id,
        old_value=log.old_value,
        new_value=log.new_value,
        ip_address=log.ip_address,
        status=log.status,
        error_message=log.error_message,
        created_at=log.created_at.isoformat(),
    )
