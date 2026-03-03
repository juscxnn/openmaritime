from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import async_session_maker
from app.models import PluginConfig
from app.models import User
from app.api.deps import get_current_user


router = APIRouter()


class PluginInfo(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    icon: str
    api_key_required: bool
    api_key_env: str
    hooks_available: List[str]
    is_builtin: bool


SEED_PLUGINS = [
    PluginInfo(
        name="rightship",
        display_name="RightShip",
        description="Safety scores, GHG ratings, and inspection data for vessels",
        category="Vessel Data",
        icon="shield",
        api_key_required=True,
        api_key_env="RIGHTSHIP_API_KEY",
        hooks_available=["on_fixture_enrich"],
        is_builtin=True,
    ),
    PluginInfo(
        name="marinetraffic",
        display_name="MarineTraffic",
        description="AIS positions, ETA, and vessel tracking",
        category="AIS & Position",
        icon="map-pin",
        api_key_required=True,
        api_key_env="MARINETRAFFIC_API_KEY",
        hooks_available=["on_fixture_enrich"],
        is_builtin=True,
    ),
    PluginInfo(
        name="veson",
        display_name="Veson IMOS",
        description="Bi-directional voyage sync with IMOS - create, retrieve, update voyages",
        category="Voyage Management",
        icon="ship",
        api_key_required=True,
        api_key_env="VESON_API_TOKEN",
        hooks_available=["on_fixture_enrich", "on_fix_now"],
        is_builtin=True,
    ),
    PluginInfo(
        name="signalocean",
        display_name="Signal Ocean",
        description="Market data, voyages, vessel positions, freight rates, and port congestion",
        category="Market Data",
        icon="trending-up",
        api_key_required=True,
        api_key_env="SIGNAL_OCEAN_API_KEY",
        hooks_available=["on_fixture_enrich"],
        is_builtin=True,
    ),
    PluginInfo(
        name="idwal",
        display_name="Idwal",
        description="Vessel grading (0-100), technical assessment, vetting, and inspection history",
        category="Vessel Data",
        icon="award",
        api_key_required=True,
        api_key_env="IDWAL_API_KEY",
        hooks_available=["on_fixture_enrich"],
        is_builtin=True,
    ),
    PluginInfo(
        name="zeronorth",
        display_name="ZeroNorth",
        description="Bunker optimization, voyage planning, CO2 emissions, CII calculations",
        category="Operations",
        icon="anchor",
        api_key_required=True,
        api_key_env="ZERONORTH_API_KEY",
        hooks_available=["on_fixture_enrich", "on_rank"],
        is_builtin=True,
    ),
    PluginInfo(
        name="laytime",
        display_name="Laytime Engine",
        description="Built-in NOR, SOF, and demurrage calculation",
        category="Calculations",
        icon="calculator",
        api_key_required=False,
        api_key_env="",
        hooks_available=["on_laytime_calculate"],
        is_builtin=True,
    ),
    PluginInfo(
        name="whisper",
        display_name="Whisper Voice",
        description="Local voice-to-fixture transcription using Whisper",
        category="AI/ML",
        icon="mic",
        api_key_required=False,
        api_key_env="",
        hooks_available=["on_voice_note"],
        is_builtin=True,
    ),
    PluginInfo(
        name="orbitmi",
        display_name="OrbitMI",
        description="Vessel efficiency scores, CII data, market comps",
        category="Vessel Data",
        icon="compass",
        api_key_required=True,
        api_key_env="ORBITMI_API_KEY",
        hooks_available=["on_fixture_enrich"],
        is_builtin=True,
    ),
    PluginInfo(
        name="abaixa",
        display_name="Abaixa",
        description="Terminal data, congestion, and port information",
        category="Port Data",
        icon="database",
        api_key_required=True,
        api_key_env="ABAIXA_API_KEY",
        hooks_available=["on_fixture_enrich"],
        is_builtin=True,
    ),
    PluginInfo(
        name="portcall",
        display_name="PortCall AI",
        description="ETA predictions and port congestion forecasting",
        category="Operations",
        icon="clock",
        api_key_required=True,
        api_key_env="PORTCALL_API_KEY",
        hooks_available=["on_fixture_enrich"],
        is_builtin=True,
    ),
]


@router.get("/", response_model=List[PluginInfo])
async def list_plugins():
    """List all available plugins"""
    return SEED_PLUGINS


@router.get("/{plugin_name}", response_model=PluginInfo)
async def get_plugin(plugin_name: str):
    """Get plugin details"""
    for plugin in SEED_PLUGINS:
        if plugin.name == plugin_name:
            return plugin
    raise HTTPException(status_code=404, detail="Plugin not found")


@router.get("/{plugin_name}/config")
async def get_plugin_config(
    plugin_name: str,
    db: AsyncSession = Depends(async_session_maker),
    current_user: User = Depends(get_current_user),
):
    """Get user configuration for a plugin"""
    result = await db.execute(
        select(PluginConfig).where(
            PluginConfig.plugin_name == plugin_name,
            PluginConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    
    plugin_info = next((p for p in SEED_PLUGINS if p.name == plugin_name), None)
    if not plugin_info:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {
        "plugin_name": plugin_name,
        "is_enabled": config.is_enabled if config else False,
        "api_key_configured": bool(config and config.config.get("api_key")),
        "config": {
            "api_key": "***" if config and config.config.get("api_key") else None,
        } if config else None,
    }


class PluginConfigRequest(BaseModel):
    api_key: Optional[str] = None
    is_enabled: bool = True
    config: Optional[Dict[str, Any]] = None


@router.post("/{plugin_name}/config")
async def configure_plugin(
    plugin_name: str,
    request: PluginConfigRequest,
    db: AsyncSession = Depends(async_session_maker),
    current_user: User = Depends(get_current_user),
):
    """Configure plugin for user"""
    plugin_info = next((p for p in SEED_PLUGINS if p.name == plugin_name), None)
    if not plugin_info:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    if plugin_info.api_key_required and not request.api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    result = await db.execute(
        select(PluginConfig).where(
            PluginConfig.plugin_name == plugin_name,
            PluginConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    
    config_data = request.config or {}
    if request.api_key:
        config_data["api_key"] = request.api_key
    
    if config:
        config.is_enabled = request.is_enabled
        config.config = config_data
    else:
        config = PluginConfig(
            user_id=current_user.id,
            plugin_name=plugin_name,
            config=config_data,
            is_enabled=request.is_enabled,
        )
        db.add(config)
    
    await db.commit()
    
    return {
        "status": "success",
        "message": f"API key configured for {plugin_info.display_name}",
        "plugin": plugin_name,
        "is_enabled": request.is_enabled,
    }


@router.get("/user/configs")
async def get_user_configs(
    db: AsyncSession = Depends(async_session_maker),
    current_user: User = Depends(get_current_user),
):
    """Get all plugin configs for current user"""
    result = await db.execute(
        select(PluginConfig).where(PluginConfig.user_id == current_user.id)
    )
    configs = result.scalars().all()
    
    config_map = {c.plugin_name: c for c in configs}
    
    return [
        {
            "plugin_name": p.name,
            "display_name": p.display_name,
            "description": p.description,
            "category": p.category,
            "icon": p.icon,
            "api_key_required": p.api_key_required,
            "is_enabled": config_map.get(p.name, PluginConfig(plugin_name=p.name, config={})).is_enabled if p.name in config_map else False,
            "api_key_configured": bool(config_map.get(p.name, PluginConfig(plugin_name=p.name, config={})).config.get("api_key")) if p.name in config_map else False,
        }
        for p in SEED_PLUGINS
    ]


@router.get("/categories")
async def list_categories():
    """List plugin categories"""
    categories = {}
    for plugin in SEED_PLUGINS:
        if plugin.category not in categories:
            categories[plugin.category] = []
        categories[plugin.category].append({
            "name": plugin.name,
            "display_name": plugin.display_name,
            "icon": plugin.icon,
        })
    return categories
