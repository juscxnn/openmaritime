from typing import Dict, Any
import os
import aiohttp


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with Signal Ocean data"""
    api_key = os.getenv("SIGNAL_OCEAN_API_KEY")
    
    if not api_key:
        return {"error": "No Signal Ocean API key"}
    
    try:
        base_url = os.getenv("SIGNAL_OCEAN_API_URL", "https://api.signalocean.com")
        
        headers = {
            "Authorization": f"ApiKey {api_key}",
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
                        enrichment["vessel"] = {
                            "name": vessel_data.get("vesselName"),
                            "type": vessel_data.get("vesselType"),
                            "year_built": vessel_data.get("yearBuilt"),
                            "dwt": vessel_data.get("dwt"),
                        }
            
            async with session.get(
                f"{base_url}/voyages",
                params={
                    "loadPort": fixture.port_loading,
                    "dischargePort": fixture.port_discharge,
                    "cargoType": fixture.cargo_type,
                },
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    voyages_data = await resp.json()
                    enrichment["market_voyages"] = voyages_data[:5]
        
        if fixture.enrichment_data is None:
            fixture.enrichment_data = {}
        fixture.enrichment_data["signalocean"] = enrichment
        
        return enrichment
    except Exception as e:
        return {"error": str(e)}


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}
