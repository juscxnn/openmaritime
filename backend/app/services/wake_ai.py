from typing import Optional, Dict, Any, List, Literal
import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WakeAIMultiAgent:
    """LangGraph-based multi-agent Wake AI system"""
    
    def __init__(self):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLAMA_MODEL", "llama3.1:70b")
        self.use_local = os.getenv("USE_LOCAL_LLAMA", "true").lower() == "true"
    
    async def run_pipeline(self, fixture_data: Dict[str, Any], market_context: str = "") -> Dict[str, Any]:
        """Run full Wake AI pipeline: extract → rank → reason → predict demurrage"""
        results = {
            "extraction": await self._extract_agent(fixture_data),
            "ranking": None,
            "reasoning": None,
            "demurrage_prediction": None,
        }
        
        ranking_result = await self._rank_agent(results["extraction"], market_context)
        results["ranking"] = ranking_result
        
        reason_result = await self._reason_agent(results["extraction"], ranking_result)
        results["reasoning"] = reason_result
        
        demurrage_result = await self._predict_demurrage_agent(results["extraction"])
        results["demurrage_prediction"] = demurrage_result
        
        return results
    
    async def _extract_agent(self, fixture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract agent - enriches raw fixture data with inferred fields"""
        prompt = f"""You are a maritime data extraction expert.
Extract and infer the following fields from fixture data:
- vessel_age_estimate (year built if unknown)
- cargo_category (crude/product/chem/dry/bulk)
- vessel_type (vlcc/suezmax/aframax/panamax/handy)
- route (short/long/vlgc)
- risk_factors (list of flags)
- completeness_score (0-100)

Input: {json.dumps(fixture_data, indent=2)}

Output JSON only:"""
        
        result = await self._call_llama(prompt)
        return {**fixture_data, **result}
    
    async def _rank_agent(self, fixture: Dict[str, Any], market_context: str) -> Dict[str, Any]:
        """Rank agent - calculates Wake Score using CoT"""
        
        prompt = f"""You are a senior charterer + TCE expert.
{market_context}

Steps to calculate score:
1. TCE delta %: compare rate to market index
2. Age adjustment: younger vessels score higher
3. Laycan urgency: closer = higher
4. Position bonus: vessel near load/discharge
5. Risk penalty: low safety score or poor GHG

Fixture: {json.dumps(fixture, indent=2)}

Output JSON:
{{
  "score": 0-100,
  "tce_delta_pct": number,
  "urgency": "high|medium|low",
  "position_bonus": number,
  "risk_penalty": number,
  "reason": "1-2 sentence explanation"
}}"""
        
        result = await self._call_llama(prompt)
        return result
    
    async def _reason_agent(self, fixture: Dict[str, Any], ranking: Dict[str, Any]) -> Dict[str, Any]:
        """Reason agent - provides detailed reasoning for ranking"""
        
        prompt = f"""You are a senior maritime analyst.
Given this fixture and ranking:

Fixture: {json.dumps(fixture, indent=2)}
Ranking: {json.dumps(ranking, indent=2)}

Provide:
- Key decision factors (bullet points)
- Risk flags (list)
- Opportunity notes
- Recommended actions

Output JSON:"""
        
        result = await self._call_llama(prompt)
        return result
    
    async def _predict_demurrage_agent(self, fixture: Dict[str, Any]) -> Dict[str, Any]:
        """Predict demurrage agent - estimates demurrage based on historical patterns"""
        
        prompt = f"""You are a laytime/demurrage expert.
Predict demurrage for this fixture:

Fixture: {json.dumps(fixture, indent=2)}

Consider:
- Port congestion (historical data)
- Weather patterns
- Vessel performance
- Charter party terms (if known)

Output JSON:
{{
  "predicted_demurrage_days": number,
  "confidence": "high|medium|low",
  "key_factors": ["..."],
  "risk_scenarios": ["..."]
}}"""
        
        result = await self._call_llama(prompt)
        return result
    
    async def _call_llama(self, prompt: str) -> Dict[str, Any]:
        """Call local Llama model"""
        try:
            import aiohttp
            
            full_prompt = f"""<|system|>
You are an expert maritime chartering AI assistant. Output valid JSON only.
<|user|>
{prompt}
<|assistant|>"""
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"temperature": 0.1}
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response = result.get("response", "")
                        return self._parse_json_response(response)
        except Exception as e:
            logger.warning(f"Llama call failed: {e}")
        
        return {"score": 50, "reason": "Fallback heuristic"}
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from Llama response"""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        return {}


class WakeAIService:
    """Legacy Wake AI service - now uses multi-agent"""
    
    def __init__(self):
        self.multi_agent = WakeAIMultiAgent()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLAMA_MODEL", "llama3.1:70b")
        self.use_local = os.getenv("USE_LOCAL_LLAMA", "true").lower() == "true"
    
    async def score_fixture(self, fixture) -> Any:
        """Score a fixture using Wake AI multi-agent"""
        
        from app.services.rag_service import rag_service
        
        fixture_dict = {
            "vessel_name": fixture.vessel_name,
            "imo_number": fixture.imo_number,
            "cargo_type": fixture.cargo_type,
            "cargo_quantity": fixture.cargo_quantity,
            "laycan_start": fixture.laycan_start.isoformat() if fixture.laycan_start else None,
            "laycan_end": fixture.laycan_end.isoformat() if fixture.laycan_end else None,
            "rate": fixture.rate,
            "port_loading": fixture.port_loading,
            "port_discharge": fixture.port_discharge,
        }
        
        market_context = await rag_service.get_market_context(fixture_dict)
        
        pipeline_results = await self.multi_agent.run_pipeline(fixture_dict, market_context)
        
        ranking = pipeline_results.get("ranking", {})
        
        fixture.wake_score = ranking.get("score", 50)
        fixture.tce_estimate = self._estimate_tce(fixture, ranking.get("tce_delta_pct", 0))
        fixture.market_diff = ranking.get("tce_delta_pct", 0)
        
        if fixture.enrichment_data is None:
            fixture.enrichment_data = {}
        fixture.enrichment_data["wake_ai"] = {
            "reason": ranking.get("reason", ""),
            "urgency": ranking.get("urgency", "medium"),
            "risk_flags": ranking.get("risk_flags", []),
            "demurrage_prediction": pipeline_results.get("demurrage_prediction", {}),
            "reasoning": pipeline_results.get("reasoning", {}),
        }
        
        return fixture
    
    async def score_fixtures_batch(self, fixtures: List, market_context: str = "") -> List:
        """Score multiple fixtures in batch"""
        scored = []
        for f in fixtures:
            await self.score_fixture(f)
            scored.append(f)
        return sorted(scored, key=lambda x: x.wake_score or 0, reverse=True)
    
    def _extract_features(self, fixture) -> Dict[str, Any]:
        """Extract scoring features from fixture"""
        now = datetime.utcnow()
        laycan_start = fixture.laycan_start if isinstance(fixture.laycan_start, datetime) else datetime.fromisoformat(str(fixture.laycan_start))
        laycan_days_left = (laycan_start - now).days if laycan_start > now else 0
        
        return {
            "vessel_age": 0,
            "laycan_urgency": laycan_days_left,
            "cargo_value": fixture.cargo_quantity * (fixture.rate or 0),
            "has_imo": bool(fixture.imo_number),
            "has_rate": bool(fixture.rate),
            "days_to_laycan": laycan_days_left,
            "rate_per_ton": fixture.rate or 0,
        }
    
    async def _llama_score(self, features: Dict[str, Any]) -> float:
        """Use local Llama for intelligent scoring"""
        try:
            import aiohttp
            
            prompt = f"""Given these fixture features, rate 0-100 for chartering priority:
{json.dumps(features, indent=2)}

Consider:
- Urgency (laycan closer = higher)
- Value (higher cargo value = higher)
- Completeness (having IMO/rate = higher)

Respond with only a number 0-100."""

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response = result.get("response", "50")
                        score = float("".join(filter(lambda x: x.isdigit() or x == ".", response.split("\n")[0])))
                        return min(100, max(0, score))
        except Exception as e:
            logger.warning(f"Llama scoring failed, using heuristic: {e}")
        
        return self._heuristic_score(features)
    
    def _heuristic_score(self, features: Dict[str, Any]) -> float:
        """Fallback heuristic scoring"""
        score = 50.0
        
        urgency = features.get("laycan_urgency", 10)
        if urgency <= 3:
            score += 20
        elif urgency <= 7:
            score += 10
        elif urgency > 14:
            score -= 10
        
        if features.get("has_imo"):
            score += 10
        if features.get("has_rate"):
            score += 15
        
        cargo_val = features.get("cargo_value", 0)
        if cargo_val > 1000000:
            score += 10
        
        return min(100, max(0, score))
    
    def _estimate_tce(self, fixture, tce_delta_pct: float) -> Optional[float]:
        """Estimate Time Charter Equivalent"""
        if not fixture.rate:
            return None
        
        distance_nm = 5000
        speed_knots = 12
        fuel_consumption = 30
        bunker_price = 600
            
        voyage_days = distance_nm / (speed_knots * 24)
        freight = fixture.rate * fixture.cargo_quantity
        bunker_cost = voyage_days * fuel_consumption * bunker_price
        
        port_days = 5
        daily_rate = 15000
        port_costs = port_days * daily_rate
        
        tce = (freight - bunker_cost - port_costs) / voyage_days
        return round(tce, 2)
    
    def _calculate_market_diff(self, tce: Optional[float]) -> Optional[float]:
        """Calculate market differential vs baseline"""
        if not tce:
            return None
        
        market_rate = 25000
        diff = ((tce - market_rate) / market_rate) * 100
        return round(diff, 2)
    
    async def rank_fixtures(self, fixtures: list) -> list:
        """Rank multiple fixtures by Wake Score"""
        scored = []
        for f in fixtures:
            await self.score_fixture(f)
            scored.append(f)
        
        return sorted(scored, key=lambda x: x.wake_score or 0, reverse=True)


wake_ai_service = WakeAIService()
