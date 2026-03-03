from typing import Dict, Any
import os
import aiohttp


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with ZeroNorth bunker optimization data"""
    api_key = os.getenv("ZERONORTH_API_KEY")
    
    if not api_key:
        return {"error": "No ZeroNorth API key"}
    
    try:
        base_url = os.getenv("ZERONORTH_API_URL", "https://api.zeronorth.com")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        enrichment = {}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/bunkers",
                params={
                    "port": fixture.port_loading,
                },
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    bunker_data = await resp.json()
                    enrichment["bunker_prices"] = bunker_data
            
            route_payload = {
                "from": fixture.port_loading,
                "to": fixture.port_discharge,
                "vessel_type": "vlcc",
            }
            
            async with session.post(
                f"{base_url}/voyage/optimize",
                json=route_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    opt_data = await resp.json()
                    enrichment["optimization"] = {
                        "distance_nm": opt_data.get("distance"),
                        "bunker_estimate": opt_data.get("bunkerConsumption"),
                        "co2_estimate": opt_data.get("co2Emissions"),
                    }
        
        if fixture.enrichment_data is None:
            fixture.enrichment_data = {}
        fixture.enrichment_data["zeronorth"] = enrichment
        
        return enrichment
    except Exception as e:
        return {"error": str(e)}


async def on_rank_adjust(fixture, base_score: float) -> float:
    """Adjust Wake Score based on bunker optimization"""
    if not fixture.enrichment_data or "zeronorth" not in fixture.enrichment_data:
        return base_score
    
    zeronorth = fixture.enrichment_data.get("zeronorth", {})
    optimization = zeronorth.get("optimization", {})
    
    bunker_estimate = optimization.get("bunker_estimate", 0)
    
    if bunker_estimate < 500:
        return base_score + 5
    elif bunker_estimate > 1000:
        return base_score - 5
    
    return base_score


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
    "on_rank": on_rank_adjust,
}
