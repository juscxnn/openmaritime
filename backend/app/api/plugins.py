from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.plugin_manager import plugin_manager


router = APIRouter()


class PluginInfo(BaseModel):
    name: str
    hooks: List[str]
    status: str = "loaded"


@router.get("/", response_model=List[PluginInfo])
async def list_plugins():
    plugins = plugin_manager.get_plugins()
    hooks = plugin_manager.get_hooks()
    
    return [
        PluginInfo(
            name=name,
            hooks=[h for h, count in hooks.items() if count > 0],
            status="loaded",
        )
        for name in plugins
    ]


@router.get("/{plugin_name}")
async def get_plugin(plugin_name: str):
    plugins = plugin_manager.get_plugins()
    if plugin_name not in plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {"name": plugin_name, "status": "loaded"}


@router.post("/{plugin_name}/enable")
async def enable_plugin(plugin_name: str):
    plugins = plugin_manager.get_plugins()
    if plugin_name not in plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {"name": plugin_name, "status": "enabled"}


@router.post("/{plugin_name}/disable")
async def disable_plugin(plugin_name: str):
    plugins = plugin_manager.get_plugins()
    if plugin_name not in plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {"name": plugin_name, "status": "disabled"}


@router.post("/{plugin_name}/config")
async def configure_plugin(plugin_name: str, config: Dict[str, Any]):
    return {"name": plugin_name, "config": config, "status": "configured"}
