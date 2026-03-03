"""
OpenMaritime FastAPI Application

Production setup with Alembic migrations and RLS support.
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.db import async_session_maker, engine
from app.models import Base
from app.services.plugin_manager import PluginManager
from app.prompts.service import prompt_service
from app.api import fixtures, plugins, enrichments, auth, marketplace, voice
from app.api.emails import router as emails_router
from app.api.metrics import router as metrics_router
from app.api.audit import router as audit_router
from app.api.chat import router as chat_router
from app.middleware.metrics import MetricsMiddleware

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite+aiosqlite:///./openmaritime.db"
)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

plugin_manager = PluginManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    For PostgreSQL, this sets the RLS context based on the current user.
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_with_rls(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Database session with RLS context set.
    
    Extracts user_id from the request state and sets RLS context.
    """
    # For PostgreSQL, set RLS context if available
    if DATABASE_URL.startswith("postgresql"):
        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        
        if user_id:
            await db.execute(
                text("SET app.current_user_id = :user_id"),
                {"user_id": str(user_id)}
            )
            if tenant_id:
                await db.execute(
                    text("SET app.current_tenant_id = :tenant_id"),
                    {"tenant_id": str(tenant_id)}
                )
    
    yield db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    
    In production, uses Alembic for migrations.
    In development with SQLite, uses create_all.
    """
    is_postgres = DATABASE_URL.startswith("postgresql")
    
    if is_postgres:
        # Production: Log a reminder about Alembic migrations
        # Migrations should be run separately: alembic upgrade head
        print("PostgreSQL detected. Run 'alembic upgrade head' for migrations.")
    else:
        # Development: Try to create tables, but don't fail if they use PostgreSQL-specific features
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"Warning: Could not create SQLite tables: {e}")
            print("Using demo mode - database features unavailable")
    
    try:
        await plugin_manager.load_plugins()
    except Exception as e:
        print(f"Warning: Could not load plugins: {e}")
    
    # Skip prompt service initialization if no database
    if not DATABASE_URL.startswith("sqlite"):
        try:
            async with async_session_maker() as session:
                await prompt_service.initialize(session)
        except Exception as e:
            print(f"Warning: Could not initialize prompts: {e}")
    
    yield
    
    await engine.dispose()


app = FastAPI(
    title="OpenMaritime API",
    description="Open-source maritime chartering platform with Wake AI",
    version="0.1.0",
    lifespan=lifespan,
)

# Add metrics middleware first (before CORS)
app.add_middleware(MetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(fixtures.router, prefix="/api/v1/fixtures", tags=["fixtures"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
app.include_router(enrichments.router, prefix="/api/v1/enrichments", tags=["enrichments"])
app.include_router(marketplace.router, prefix="/api/v1/marketplace", tags=["marketplace"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(emails_router, tags=["emails"])
app.include_router(metrics_router, prefix="/api/v1", tags=["observability"])
app.include_router(audit_router, tags=["audit"])


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy", 
        "plugins_loaded": plugin_manager.get_plugin_count(),
        "database": "postgres" if DATABASE_URL.startswith("postgresql") else "sqlite"
    }


@app.get("/")
async def root():
    return {
        "name": "OpenMaritime API",
        "version": "0.1.0",
        "docs": "/docs"
    }
