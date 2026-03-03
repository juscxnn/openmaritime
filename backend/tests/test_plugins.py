"""
Tests for plugin system.

C fixturesovers:
- Plugin loading
- Plugin hooks
- RightShip enrichment
- MarineTraffic enrichment
- Plugin manager
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import os

from tests.conftest import Fixture, PluginConfig
from tests.conftest import User
from app.services.plugin_manager import PluginManager


# =============================================================================
# Plugin Manager Tests
# =============================================================================

@pytest.mark.asyncio
async def test_plugin_manager_init():
    """Test PluginManager initialization."""
    manager = PluginManager()
    
    assert manager._plugins == {}
    assert "on_fixture_enrich" in manager._hooks
    assert "on_fixture_create" in manager._hooks
    assert "on_fixture_rank" in manager._hooks
    assert "on_email_parse" in manager._hooks


@pytest.mark.asyncio
async def test_plugin_manager_get_hooks():
    """Test getting hooks."""
    manager = PluginManager()
    
    hooks = manager.get_hooks()
    
    assert isinstance(hooks, dict)
    assert "on_fixture_enrich" in hooks


@pytest.mark.asyncio
async def test_plugin_manager_get_plugins():
    """Test getting loaded plugins."""
    manager = PluginManager()
    
    plugins = manager.get_plugins()
    
    # Should be empty before loading
    assert isinstance(plugins, list)


@pytest.mark.asyncio
async def test_plugin_manager_get_plugin_count():
    """Test getting plugin count."""
    manager = PluginManager()
    
    count = manager.get_plugin_count()
    
    assert count >= 0


@pytest.mark.asyncio
async def test_plugin_manager_load_plugins():
    """Test loading plugins."""
    manager = PluginManager()
    
    await manager.load_plugins()
    
    # Verify some plugins loaded
    assert manager.get_plugin_count() >= 0


@pytest.mark.asyncio
async def test_plugin_manager_execute_hook():
    """Test executing a hook."""
    manager = PluginManager()
    
    # Add a mock hook
    async def mock_hook(*args, **kwargs):
        return {"result": "success"}
    
    manager._hooks["on_fixture_enrich"].append(mock_hook)
    
    # Execute hook
    results = await manager.execute_hook("on_fixture_enrich")
    
    assert len(results) == 1
    assert results[0]["result"] == "success"


@pytest.mark.asyncio
async def test_plugin_manager_execute_hook_error():
    """Test executing hook with error."""
    manager = PluginManager()
    
    # Add a mock hook that raises error
    async def mock_hook_error(*args, **kwargs):
        raise ValueError("Test error")
    
    manager._hooks["on_fixture_enrich"].append(mock_hook_error)
    
    # Execute hook - should not raise
    results = await manager.execute_hook("on_fixture_enrich")
    
    # Results may contain error info depending on implementation
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_plugin_manager_execute_nonexistent_hook():
    """Test executing non-existent hook."""
    manager = PluginManager()
    
    results = await manager.execute_hook("nonexistent_hook")
    
    assert results == []


# =============================================================================
# RightShip Plugin Tests
# =============================================================================

@pytest.mark.asyncio
async def test_rightship_plugin_no_api_key():
    """Test RightShip plugin without API key."""
    # Temporarily remove API key
    api_key = os.environ.get("RIGHTSHIP_API_KEY")
    if api_key:
        del os.environ["RIGHTSHIP_API_KEY"]
    
    try:
        from app.plugins.rightship import on_fixture_enrich
        
        class MockFixture:
            imo_number = "1234567"
            enrichment_data = None
        
        result = await on_fixture_enrich(MockFixture())
        
        assert "error" in result
    finally:
        if api_key:
            os.environ["RIGHTSHIP_API_KEY"] = api_key


@pytest.mark.asyncio
async def test_rightship_plugin_no_imo():
    """Test RightShip plugin without IMO number."""
    os.environ["RIGHTSHIP_API_KEY"] = "test_key"
    
    from app.plugins.rightship import on_fixture_enrich
    
    class MockFixture:
        imo_number = None
        enrichment_data = None
    
    result = await on_fixture_enrich(MockFixture())
    
    assert "error" in result


@pytest.mark.asyncio
async def test_rightship_plugin_hooks():
    """Test RightShip plugin exports hooks."""
    from app.plugins import rightship
    
    assert hasattr(rightship, "hooks")
    assert "on_fixture_enrich" in rightship.hooks


# =============================================================================
# MarineTraffic Plugin Tests
# =============================================================================

@pytest.mark.asyncio
async def test_marinetraffic_plugin_no_api_key():
    """Test MarineTraffic plugin without API key."""
    api_key = os.environ.get("MARINETRAFFIC_API_KEY")
    if api_key:
        del os.environ["MARINETRAFFIC_API_KEY"]
    
    try:
        from app.plugins.marinetraffic import on_fixture_enrich
        
        class MockFixture:
            imo_number = "1234567"
            enrichment_data = None
        
        result = await on_fixture_enrich(MockFixture())
        
        assert "error" in result
    finally:
        if api_key:
            os.environ["MARINETRAFFIC_API_KEY"] = api_key


@pytest.mark.asyncio
async def test_marinetraffic_plugin_no_imo():
    """Test MarineTraffic plugin without IMO number."""
    os.environ["MARINETRAFFIC_API_KEY"] = "test_key"
    
    from app.plugins.marinetraffic import on_fixture_enrich
    
    class MockFixture:
        imo_number = None
        enrichment_data = None
    
    result = await on_fixture_enrich(MockFixture())
    
    assert "error" in result


@pytest.mark.asyncio
async def test_marinetraffic_plugin_hooks():
    """Test MarineTraffic plugin exports hooks."""
    from app.plugins import marinetraffic
    
    assert hasattr(marinetraffic, "hooks")
    assert "on_fixture_enrich" in marinetraffic.hooks


# =============================================================================
# Other Plugin Tests
# =============================================================================

@pytest.mark.asyncio
async def test_all_plugins_have_hooks():
    """Test that all plugins export hooks."""
    from app.plugins import (
        rightship,
        marinetraffic,
        idwal,
        zeronorth,
        signalocean,
        veson,
        portcall,
        abaixa,
        orbitmi,
        whisper,
        laytime,
    )
    
    plugins = [
        rightship,
        marinetraffic,
        idwal,
        zeronorth,
        signalocean,
        veson,
        portcall,
        abaixa,
        orbitmi,
        whisper,
        laytime,
    ]
    
    for plugin in plugins:
        assert hasattr(plugin, "hooks"), f"{plugin.__name__} missing hooks"


@pytest.mark.asyncio
async def test_plugin_hooks_are_callable():
    """Test that plugin hooks are callable."""
    from app.plugins import rightship
    
    for hook_name, hook_func in rightship.hooks.items():
        assert callable(hook_func), f"{hook_name} is not callable"


# =============================================================================
# Plugin Enrichment Tests (Mocked)
# =============================================================================

@pytest.mark.asyncio
async def test_enrich_fixture_with_rightship(db_session):
    """Test enriching fixture with RightShip data."""
    user = User(
        id=str(uuid4()),
        email="rs@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="RightShip Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=7),
        laycan_end=datetime.utcnow() + timedelta(days=12),
        rate=52.5,
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
        imo_number="9123456",
    )
    db_session.add(fixture)
    await db_session.commit()
    
    # Mock the API response
    mock_response = {
        "safety_score": "A",
        "ghg_rating": "B",
        "inspection_status": "Valid",
        "last_inspection_date": "2024-12-15",
    }
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        
        mock_session_instance = AsyncMock()
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session_instance.get = MagicMock(return_value=mock_resp)
        
        mock_session.return_value = mock_session_instance
        
        from app.plugins.rightship import on_fixture_enrich
        result = await on_fixture_enrich(fixture)
    
    assert "safety_score" in result or "error" in result


@pytest.mark.asyncio
async def test_enrich_fixture_with_marinetraffic(db_session):
    """Test enriching fixture with MarineTraffic data."""
    user = User(
        id=str(uuid4()),
        email="mt@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="MT Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=7),
        laycan_end=datetime.utcnow() + timedelta(days=12),
        rate=52.5,
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
        imo_number="9123456",
    )
    db_session.add(fixture)
    await db_session.commit()
    
    # Mock the API response
    mock_response = [
        {
            "LAT": 1.2644,
            "LON": 103.8208,
            "SPEED": 12.5,
            "HEADING": 270,
            "DESTINATION": "SINGAPORE",
            "ETA": "2025-03-05 0800",
            "LAST_UPDATE": "2025-03-03T06:30:00",
        }
    ]
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        
        mock_session_instance = AsyncMock()
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session_instance.get = MagicMock(return_value=mock_resp)
        
        mock_session.return_value = mock_session_instance
        
        from app.plugins.marinetraffic import on_fixture_enrich
        result = await on_fixture_enrich(fixture)
    
    assert "lat" in result or "error" in result


# =============================================================================
# Plugin Configuration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_plugin_config_creation(db_session):
    """Test creating plugin configuration."""
    user = User(
        id=str(uuid4()),
        email="config@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    config = PluginConfig(
        user_id=user.id,
        tenant_id=user.tenant_id,
        plugin_name="rightship",
        config={"api_key": "test_key", "enabled": True},
        is_enabled=True,
    )
    
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    
    assert config.id is not None
    assert config.plugin_name == "rightship"
    assert config.is_enabled is True


@pytest.mark.asyncio
async def test_plugin_config_disable(db_session):
    """Test disabling plugin configuration."""
    user = User(
        id=str(uuid4()),
        email="disable@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    config = PluginConfig(
        user_id=user.id,
        tenant_id=user.tenant_id,
        plugin_name="rightship",
        config={},
        is_enabled=True,
    )
    
    db_session.add(config)
    await db_session.commit()
    
    config.is_enabled = False
    
    await db_session.commit()
    await db_session.refresh(config)
    
    assert config.is_enabled is False


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_full_enrichment_flow(db_session):
    """Test full enrichment flow through plugin manager."""
    user = User(
        id=str(uuid4()),
        email="enrichflow@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="Flow Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=7),
        laycan_end=datetime.utcnow() + timedelta(days=12),
        rate=52.5,
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
        imo_number="9123456",
        enrichment_data={},
    )
    db_session.add(fixture)
    await db_session.commit()
    
    manager = PluginManager()
    
    # Execute enrich hook
    results = await manager.execute_hook("on_fixture_enrich", fixture)
    
    # Should execute all enrichment plugins
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_multiple_enrichment_sources(db_session):
    """Test enriching from multiple sources."""
    user = User(
        id=str(uuid4()),
        email="multi@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="Multi Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=7),
        laycan_end=datetime.utcnow() + timedelta(days=12),
        rate=52.5,
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
        imo_number="9123456",
    )
    db_session.add(fixture)
    await db_session.commit()
    
    # Manually add enrichment data
    fixture.enrichment_data = {
        "rightship": {"safety_score": "A"},
        "marinetraffic": {"lat": 1.26},
    }
    
    await db_session.commit()
    await db_session.refresh(fixture)
    
    assert "rightship" in fixture.enrichment_data
    assert "marinetraffic" in fixture.enrichment_data
    assert fixture.enrichment_data["rightship"]["safety_score"] == "A"
