from typing import Dict, Any
import os
import aiohttp


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """Enrich fixture with Abaixa port and terminal data"""
    api_key = os.getenv("ABAIXA_API_KEY")
    
    if not api_key:
        return {"error": "No Abaixa API key"}
    
    try:
        base_url = os.getenv("ABAIXA_API_URL", "https://api.abaixa.io")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        enrichment = {}
        
        async with aiohttp.ClientSession() as session:
            if fixture.port_loading:
                async with session.get(
                    f"{base_url}/terminals",
                    params={"port": fixture.port_loading},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        terminals = await resp.json()
                        enrichment["load_terminals"] = terminals.get("data", [])[:3]
            
            if fixture.port_discharge:
                async with session.get(
                    f"{base_url}/terminals",
                    params={"port": fixture.port_discharge},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        terminals = await resp.json()
                        enrichment["discharge_terminals"] = terminals.get("data", [])[:3]
            
            for port_key in ["port_loading", "port_discharge"]:
                port = getattr(fixture, port_key, None)
                if port:
                    async with session.get(
                        f"{base_url}/port/{port}/congestion",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            congestion = await resp.json()
                            key = "load_congestion" if port_key == "port_loading" else "discharge_congestion"
                            enrichment[key] = congestion
        
        if fixture.enrichment_data is None:
            fixture.enrichment_data = {}
        fixture.enrichment_data["abaixa"] = enrichment
        
        return enrichment
    except Exception as e:
        return {"error": str(e)}


hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}
