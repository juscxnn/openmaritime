import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.api import fixtures, plugins, enrichments, auth, marketplace
from app.models import Base
from app.services.plugin_manager import PluginManager


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./openmaritime.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

plugin_manager = PluginManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await plugin_manager.load_plugins()
    
    yield
    
    await engine.dispose()


app = FastAPI(
    title="OpenMaritime API",
    description="Open-source maritime chartering platform with Wake AI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(fixtures.router, prefix="/api/v1/fixtures", tags=["fixtures"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
app.include_router(enrichments.router, prefix="/api/v1/enrichments", tags=["enrichments"])
app.include_router(marketplace.router, prefix="/api/v1/marketplace", tags=["marketplace"])


@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "plugins_loaded": plugin_manager.get_plugin_count()}
