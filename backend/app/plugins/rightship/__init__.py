from typing import Dict, Any
import os
import aiohttp


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with RightShip data"""
    api_key = os.getenv("RIGHTSHIP_API_KEY")
    
    if not api_key or not fixture.imo_number:
        return {"error": "No API key or IMO"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.rightship.com/vessels/summary",
                params={"imo": fixture.imo_number},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                data = await response.json()
        
        enrichment = {
            "safety_score": data.get("safety_score"),
            "ghg_rating": data.get("ghg_rating"),
            "inspection_status": data.get("inspection_status"),
            "last_inspection": data.get("last_inspection_date"),
        }
        
        if fixture.enrichment_data is None:
            fixture.enrichment_data = {}
        fixture.enrichment_data["rightship"] = enrichment
        
        return enrichment
    except Exception as e:
        return {"error": str(e)}


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}
