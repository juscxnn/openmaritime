from typing import Dict, Any
import os
import aiohttp


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with MarineTraffic AIS position data"""
    api_key = os.getenv("MARINETRAFFIC_API_KEY")
    
    if not api_key or not fixture.imo_number:
        return {"error": "No API key or IMO"}
    
    try:
        url = f"https://services.marinetraffic.com/api/exportvesselpositions/{api_key}"
        params = {
            "timespan": 60,
            "imo": fixture.imo_number,
            "protocol": "json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                data = await response.json()
        
        if data:
            vessel = data[0]
            enrichment = {
                "lat": vessel.get("LAT"),
                "lon": vessel.get("LON"),
                "speed": vessel.get("SPEED"),
                "heading": vessel.get("HEADING"),
                "destination": vessel.get("DESTINATION"),
                "eta": vessel.get("ETA"),
                "last_update": vessel.get("LAST_UPDATE"),
            }
            
            if fixture.enrichment_data is None:
                fixture.enrichment_data = {}
            fixture.enrichment_data["position"] = enrichment
            
            return enrichment
        return {"error": "No data"}
    except Exception as e:
        return {"error": str(e)}


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}
