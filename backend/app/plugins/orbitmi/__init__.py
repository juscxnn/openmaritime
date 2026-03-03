from typing import Dict, Any
import os
import aiohttp


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with OrbitMI data"""
    api_key = os.getenv("ORBITMI_API_KEY")
    
    if not api_key:
        return {"error": "No OrbitMI API key"}
    
    try:
        base_url = os.getenv("ORBITMI_API_URL", "https://api.orbitmi.com")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        enrichment = {}
        
        async with aiohttp.ClientSession() as session:
            if fixture.imo_number:
                async with session.get(
                    f"{base_url}/vessels/{fixture.imo_number}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        vessel_data = await resp.json()
                        enrichment["orbitmi"] = {
                            "vessel_id": vessel_data.get("id"),
                            "name": vessel_data.get("name"),
                            "type": vessel_data.get("vesselType"),
                            "age": vessel_data.get("age"),
                            "efficiency_score": vessel_data.get("efficiencyScore"),
                            "carbon_intensity": vessel_data.get("carbonIntensity"),
                            "last_cii": vessel_data.get("lastCii"),
                            "predicted_cii": vessel_data.get("predictedCii"),
                        }
            
            async with session.get(
                f"{base_url}/market/fixtures",
                params={
                    "cargo": fixture.cargo_type,
                    "from": fixture.port_loading,
                    "to": fixture.port_discharge,
                },
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    market_data = await resp.json()
                    enrichment["market_comps"] = market_data.get("fixtures", [])[:5]
        
        if fixture.enrichment_data is None:
            fixture.enrichment_data = {}
        fixture.enrichment_data["orbitmi"] = enrichment
        
        return enrichment
    except Exception as e:
        return {"error": str(e)}


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}
