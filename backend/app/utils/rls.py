"""
Row Level Security (RLS) utilities for PostgreSQL.

This module provides utilities for setting RLS context in PostgreSQL
to enable multi-tenant data isolation.
"""
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def set_rls_context(
    session: AsyncSession,
    user_id: UUID,
    tenant_id: Optional[UUID] = None
) -> None:
    """
    Set the RLS context for the current session.
    
    This sets the PostgreSQL session variables that RLS policies
    use to filter data by user_id and tenant_id.
    
    Args:
        session: SQLAlchemy async session
        user_id: The current user's ID
        tenant_id: Optional tenant ID for multi-tenant RLS
    """
    await session.execute(
        text("SET app.current_user_id = :user_id"),
        {"user_id": str(user_id)}
    )
    
    if tenant_id:
        await session.execute(
            text("SET app.current_tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        )


async def clear_rls_context(session: AsyncSession) -> None:
    """
    Clear the RLS context for the current session.
    
    Args:
        session: SQLAlchemy async session
    """
    await session.execute(text("RESET app.current_user_id"))
    await session.execute(text("RESET app.current_tenant_id"))


@asynccontextmanager
async def rls_session(
    session: AsyncSession,
    user_id: UUID,
    tenant_id: Optional[UUID] = None
):
    """
    Context manager for setting RLS context for a session.
    
    Automatically clears the context when done.
    
    Example:
        async with rls_session(session, user.id, user.tenant_id):
            # RLS policies will filter data by user
            result = await session.execute(select(Fixture))
    """
    await set_rls_context(session, user_id, tenant_id)
    try:
        yield session
    finally:
        await clear_rls_context(session)


# Synchronous version for migrations and setup
def set_rls_context_sync(connection, user_id: UUID, tenant_id: Optional[UUID] = None):
    """
    Set RLS context for a synchronous connection.
    
    Used in migrations and initialization scripts.
    """
    connection.exec_driver_sql(
        text("SET app.current_user_id = :user_id"),
        {"user_id": str(user_id)}
    )
    if tenant_id:
        connection.exec_driver_sql(
            text("SET app.current_tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        )


def clear_rls_context_sync(connection):
    """Clear RLS context for a synchronous connection."""
    connection.exec_driver_sql(text("RESET app.current_user_id"))
    connection.exec_driver_sql(text("RESET app.current_tenant_id"))
