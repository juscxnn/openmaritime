from typing import Dict, Any, List
import os
import aiohttp
from datetime import datetime, timedelta


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with port call predictions and ETA"""
    api_key = os.getenv("PORTCALL_API_KEY")
    
    if not api_key:
        return {"error": "No PortCall API key"}
    
    try:
        base_url = os.getenv("PORTCALL_API_URL", "https://api.portcall.ai")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        enrichment = {}
        
        async with aiohttp.ClientSession() as session:
            if fixture.imo_number:
                async with session.get(
                    f"{base_url}/vessels/{fixture.imo_number}/eta",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        eta_data = await resp.json()
                        enrichment["eta_prediction"] = {
                            "predicted_eta": eta_data.get("eta"),
                            "confidence": eta_data.get("confidence"),
                            "factors": eta_data.get("factors", []),
                            "berth_availability": eta_data.get("berthAvailability"),
                        }
                
                async with session.get(
                    f"{base_url}/vessels/{fixture.imo_number}/port-calls",
                    params={"limit": 5},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        history = await resp.json()
                        enrichment["port_call_history"] = history.get("calls", [])[:5]
            
            ports = [fixture.port_loading, fixture.port_discharge]
            port_forecasts = {}
            
            for port in ports:
                if port:
                    async with session.get(
                        f"{base_url}/ports/{port}/forecast",
                        params={"days": 7},
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            forecast = await resp.json()
                            key = f"{port}_forecast"
                            port_forecasts[key] = {
                                "congestion_level": forecast.get("congestionLevel"),
                                "avg_waiting_time": forecast.get("avgWaitingHours"),
                                "berth_availability": forecast.get("berthAvailability"),
                            }
            
            enrichment["port_forecasts"] = port_forecasts
        
        if fixture.enrichment_data is None:
            fixture.enrichment_data = {}
        fixture.enrichment_data["portcall"] = enrichment
        
        return enrichment
    except Exception as e:
        return {"error": str(e)}


async def predict_port_congestion(port: str, days_ahead: int = 7) -> Dict[str, Any]:
    """Predict port congestion for planning"""
    
    api_key = os.getenv("PORTCALL_API_KEY")
    if not api_key:
        return {"error": "No API key"}
    
    try:
        base_url = os.getenv("PORTCALL_API_URL", "https://api.portcall.ai")
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/ports/{port}/congestion-forecast",
                params={"days": days_ahead},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        return {"error": str(e)}


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}
