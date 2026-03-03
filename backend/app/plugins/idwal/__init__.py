from typing import Dict, Any
import os
import aiohttp


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with Idwal vessel grading"""
    api_key = os.getenv("IDWAL_API_KEY")
    
    if not api_key or not fixture.imo_number:
        return {"error": "No API key or IMO"}
    
    try:
        base_url = os.getenv("IDWAL_API_URL", "https://api.idwal.com")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/vessels/{fixture.imo_number}/grade",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    enrichment = {
                        "grade": data.get("grade"),
                        "grade_band": data.get("band"),
                        "technical_score": data.get("technicalScore"),
                        "commercial_score": data.get("commercialScore"),
                        "inspection_score": data.get("inspectionScore"),
                        " vetting_score": data.get("vettingScore"),
                    }
                    
                    if fixture.enrichment_data is None:
                        fixture.enrichment_data = {}
                    fixture.enrichment_data["idwal"] = enrichment
                    
                    return enrichment
                elif resp.status == 404:
                    return {"error": "Vessel not found in Idwal"}
                else:
                    return {"error": f"Idwal API error: {resp.status}"}
    except Exception as e:
        return {"error": str(e)}


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}
