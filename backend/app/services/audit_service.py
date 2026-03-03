"""
Audit logging service for OpenMaritime.

Provides structured logging for critical operations:
- Fixture changes
- AI decisions
- Plugin calls
- Authentication events
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models import AuditLog


class AuditService:
    """
    Service for creating and querying audit logs.
    """
    
    async def log(
        self,
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        actor_type: str = "user",
        actor_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        ai_model: Optional[str] = None,
        ai_prompt_tokens: Optional[int] = None,
        ai_completion_tokens: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry"""
        log_entry = AuditLog(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_type=actor_type,
            actor_id=actor_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            ai_model=ai_model,
            ai_prompt_tokens=ai_prompt_tokens,
            ai_completion_tokens=ai_completion_tokens,
            status=status,
            error_message=error_message,
        )
        
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        
        return log_entry
    
    async def log_fixture_change(
        self,
        db: AsyncSession,
        user_id: Optional[UUID],
        tenant_id: Optional[UUID],
        fixture_id: str,
        action: str,  # create, update, delete, enrich, rank, decide
        old_data: Optional[Dict] = None,
        new_data: Optional[Dict] = None,
        **kwargs,
    ):
        """Log fixture-related action"""
        # Strip sensitive data
        if old_data:
            old_data = self._sanitize_fixture(old_data)
        if new_data:
            new_data = self._sanitize_fixture(new_data)
        
        return await self.log(
            db=db,
            action=f"fixture.{action}",
            resource_type="fixture",
            resource_id=fixture_id,
            user_id=user_id,
            tenant_id=tenant_id,
            actor_type="user",
            old_value=old_data,
            new_value=new_data,
            **kwargs,
        )
    
    async def log_ai_decision(
        self,
        db: AsyncSession,
        user_id: Optional[UUID],
        tenant_id: Optional[UUID],
        fixture_id: str,
        agent_type: str,
        decision: Dict[str, Any],
        ai_model: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        **kwargs,
    ):
        """Log AI decision"""
        return await self.log(
            db=db,
            action=f"ai.{agent_type}.decision",
            resource_type="fixture",
            resource_id=fixture_id,
            user_id=user_id,
            tenant_id=tenant_id,
            actor_type="agent",
            actor_id=agent_type,
            new_value=decision,
            ai_model=ai_model,
            ai_prompt_tokens=prompt_tokens,
            ai_completion_tokens=completion_tokens,
            **kwargs,
        )
    
    async def log_plugin_call(
        self,
        db: AsyncSession,
        plugin_name: str,
        hook_name: str,
        status: str,
        user_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        fixture_id: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs,
    ):
        """Log plugin invocation"""
        return await self.log(
            db=db,
            action=f"plugin.{hook_name}",
            resource_type="plugin",
            resource_id=plugin_name,
            user_id=user_id,
            tenant_id=tenant_id,
            actor_type="plugin",
            actor_id=plugin_name,
            status=status,
            error_message=error,
            **kwargs,
        )
    
    async def log_auth_event(
        self,
        db: AsyncSession,
        action: str,  # login, logout, login_failed, password_change, etc.
        user_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs,
    ):
        """Log authentication event"""
        return await self.log(
            db=db,
            action=f"auth.{action}",
            resource_type="auth",
            resource_id=str(user_id) if user_id else None,
            user_id=user_id,
            tenant_id=tenant_id,
            actor_type="user" if user_id else "anonymous",
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            **kwargs,
        )
    
    async def log_api_call(
        self,
        db: AsyncSession,
        user_id: Optional[UUID],
        tenant_id: Optional[UUID],
        api_key_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        **kwargs,
    ):
        """Log API key usage"""
        return await self.log(
            db=db,
            action=f"api.{method.lower()}",
            resource_type="api",
            resource_id=endpoint,
            user_id=user_id,
            tenant_id=tenant_id,
            actor_type="api_key",
            actor_id=api_key_id,
            new_value={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
            status="success" if status_code < 400 else "failure",
            **kwargs,
        )
    
    async def query_logs(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        actor_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Query audit logs with filters"""
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        
        if action:
            query = query.where(AuditLog.action.like(f"{action}%"))
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if actor_type:
            query = query.where(AuditLog.actor_type == actor_type)
        if status:
            query = query.where(AuditLog.status == status)
        
        query = query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    def _sanitize_fixture(self, data: Dict) -> Dict:
        """Remove sensitive fields from fixture data"""
        if not data:
            return {}
        
        sensitive_fields = {"hashed_password", "access_token", "refresh_token", "api_key", "secret"}
        return {
            k: v for k, v in data.items()
            if k.lower() not in sensitive_fields
        }


audit_service = AuditService()
