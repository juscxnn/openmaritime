from typing import Dict, Any, Optional
import os
import aiohttp
import logging

logger = logging.getLogger(__name__)


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with Veson IMOS data"""
    api_token = os.getenv("VESON_API_TOKEN")
    
    if not api_token or not fixture.imo_number:
        return {"error": "No API token or IMO"}
    
    try:
        base_url = os.getenv("VESON_API_URL", "https://api.veslink.com")
        
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/vessels",
                params={"imo": fixture.imo_number},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"veson": data}
                elif resp.status == 404:
                    return {"error": "Vessel not found in IMOS"}
                else:
                    return {"error": f"Veson API error: {resp.status}"}
    except Exception as e:
        return {"error": str(e)}


async def create_voyage_from_fixture(fixture, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create voyage in Veson IMOS from fixture - for FIX NOW action"""
    api_token = os.getenv("VESON_API_TOKEN")
    
    if not api_token:
        return {"error": "No Veson API token"}
    
    try:
        base_url = os.getenv("VESON_API_URL", "https://api.veslink.com")
        
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        }
        
        voyage_payload = {
            "vessel_imo": fixture.imo_number,
            "cargo_type": fixture.cargo_type,
            "cargo_quantity": fixture.cargo_quantity,
            "load_port": fixture.port_loading,
            "discharge_port": fixture.port_discharge,
            "laycan_start": fixture.laycan_start.isoformat() if fixture.laycan_start else None,
            "laycan_end": fixture.laycan_end.isoformat() if fixture.laycan_end else None,
            "rate": fixture.rate,
            "currency": fixture.rate_currency,
            "charterer": fixture.charterer,
            **payload,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/voyages",
                json=voyage_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (200, 201):
                    return {"status": "created", "data": await resp.json()}
                else:
                    return {"error": f"Failed to create voyage: {resp.status}"}
    except Exception as e:
        return {"error": str(e)}


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
    "on_fix_now": create_voyage_from_fixture,
}
