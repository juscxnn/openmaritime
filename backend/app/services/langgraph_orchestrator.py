from typing import TypedDict, List, Optional, Any
from enum import Enum
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State passed between agents in the LangGraph pipeline"""
    raw_input: dict
    fixture_data: dict
    enrichment_data: dict
    ranking_data: dict
    prediction_data: dict
    decision_data: dict
    errors: List[str]
    metadata: dict


class AgentType(str, Enum):
    EXTRACTION = "extraction"
    ENRICHMENT = "enrichment"
    RANKING = "ranking"
    PREDICTION = "prediction"
    DECISION = "decision"


class BaseAgent:
    """Base class for all Wake AI agents"""
    
    def __init__(self, name: str, agent_type: AgentType):
        self.name = name
        self.agent_type = agent_type
        self.ollama_base_url = None
        self.model = None
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute agent logic - to be overridden by subclasses"""
        raise NotImplementedError
    
    async def call_llama(self, prompt: str) -> dict:
        """Call local Llama model"""
        try:
            import aiohttp
            
            full_prompt = f"""<|system|>
You are {self.name}, an expert maritime AI agent. Output valid JSON only.
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
                        "options": {"temperature": 0.1, "num_ctx": 8192}
                    },
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response = result.get("response", "")
                        return self._parse_json(response)
        except Exception as e:
            logger.warning(f"Llama call failed: {e}")
        
        return {}
    
    def _parse_json(self, response: str) -> dict:
        """Parse JSON from Llama response"""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        return {}


class ExtractionAgent(BaseAgent):
    """Extracts and enriches fixture data from raw input"""
    
    def __init__(self):
        super().__init__("Extraction Agent", AgentType.EXTRACTION)
    
    async def execute(self, state: AgentState) -> AgentState:
        raw = state.get("raw_input", {})
        
        prompt = f"""You are a maritime data extraction expert. Extract and standardize fixture fields.

Input raw data: {json.dumps(raw, indent=2)}

Extract and infer:
- vessel_name, imo_number, year_built (estimate if unknown)
- cargo_type, cargo_category (crude/product/chem/dry/bulk/lng/lpg)
- cargo_quantity, quantity_unit
- laycan_start, laycan_end (ISO format)
- rate, rate_currency, rate_unit
- port_loading, port_discharge (standardized names)
- vessel_type (vlcc/suezmax/aframax/panamax/handy/general)
- charterer, broker
- route_type (short/long/vlgc)
- risk_factors (list)
- completeness_score (0-100)

Output JSON:"""
        
        result = await self.call_llama(prompt)
        
        state["fixture_data"] = {**raw, **result}
        return state


class EnrichmentAgent(BaseAgent):
    """Enriches fixture with external data sources"""
    
    def __init__(self):
        super().__init__("Enrichment Agent", AgentType.ENRICHMENT)
    
    async def execute(self, state: AgentState) -> AgentState:
        fixture = state.get("fixture_data", {})
        enrichment = {}
        
        if fixture.get("imo_number"):
            enrichment["imo_verified"] = True
            enrichment["imo_valid"] = self._validate_imo(fixture["imo_number"])
        
        if fixture.get("port_loading"):
            enrichment["load_region"] = self._get_region(fixture["port_loading"])
        
        if fixture.get("port_discharge"):
            enrichment["discharge_region"] = self._get_region(fixture["port_discharge"])
        
        prompt = f"""Given fixture data, determine what enrichment sources to query:

Fixture: {json.dumps(fixture, indent=2)}

For each source (RightShip, MarineTraffic, Idwal, Signal Ocean), determine:
- relevance_score (0-1)
- priority (high/medium/low)
- expected_fields (list)

Output JSON with sources array:"""
        
        sources_result = await self.call_llama(prompt)
        
        enrichment["recommended_sources"] = sources_result.get("sources", [])
        
        state["enrichment_data"] = enrichment
        return state
    
    def _validate_imo(self, imo: str) -> bool:
        """Validate IMO number checksum"""
        if not imo or len(imo) != 7:
            return False
        try:
            digits = [int(d) for d in imo[:-1]]
            checksum = int(imo[-1])
            weighted_sum = sum(d * (i + 1) for i, d in enumerate(digits))
            return checksum == (weighted_sum % 10)
        except:
            return False
    
    def _get_region(self, port: str) -> str:
        """Determine port region"""
        port_lower = port.lower()
        
        me_regions = ["singapore", "jebel ali", "fujairah", "ras tanura", "khafji", "bushehr"]
        eu_regions = ["rotterdam", "antwerp", "hamburg", "le Havre", "amsterdam", "milford"]
        us_regions = ["houston", "new york", "los angeles", "corpus christi", "port author"]
        asia_regions = ["busan", "shanghai", "qingdao", "mumbai", "chennai", "tuticorin"]
        
        if any(r in port_lower for r in me_regions):
            return "MIDDLE_EAST"
        elif any(r in port_lower for r in eu_regions):
            return "EUROPE"
        elif any(r in port_lower for r in us_regions):
            return "US_GULF"
        elif any(r in port_lower for r in asia_regions):
            return "ASIA"
        
        return "OTHER"


class RankingAgent(BaseAgent):
    """Ranks fixtures using market context and AI"""
    
    def __init__(self):
        super().__init__("Ranking Agent", AgentType.RANKING)
    
    async def execute(self, state: AgentState) -> AgentState:
        fixture = state.get("fixture_data", {})
        enrichment = state.get("enrichment_data", {})
        
        from app.services.rag_service import rag_service
        
        market_context = await rag_service.get_market_context(fixture)
        
        prompt = f"""You are a senior charterer + TCE expert.

MARKET CONTEXT:
{market_context}

Calculate ranking for this fixture following these steps:
1. TCE delta %: compare rate to market index
2. Age adjustment: younger vessels score higher
3. Laycan urgency: closer = higher (red <3d, yellow 3-7d, green >7d)
4. Position bonus: vessel near load/discharge ports
5. Risk penalty: low safety score or poor GHG
6. Completeness bonus: more fields = higher

Fixture: {json.dumps(fixture, indent=2)}
Enrichment: {json.dumps(enrichment, indent=2)}

Output JSON:
{{
  "score": 0-100,
  "tce_delta_pct": number,
  "urgency": "high|medium|low",
  "urgency_days": number,
  "position_bonus": number,
  "risk_penalty": number,
  "completeness_bonus": number,
  "reason": "1-2 sentence explanation",
  "key_factors": ["factor1", "factor2", "factor3"]
}}"""
        
        result = await self.call_llama(prompt)
        
        state["ranking_data"] = result
        return state


class PredictionAgent(BaseAgent):
    """Predicts demurrage and market trends"""
    
    def __init__(self):
        super().__init__("Prediction Agent", AgentType.PREDICTION)
    
    async def execute(self, state: AgentState) -> AgentState:
        fixture = state.get("fixture_data", {})
        ranking = state.get("ranking_data", {})
        
        prompt = f"""You are a laytime/demurrage expert with 20 years experience.

Predict demurrage for this fixture:
- Consider port congestion (historical)
- Weather patterns (seasonal)
- Vessel performance history
- Charter party terms (if inferable)

Fixture: {json.dumps(fixture, indent=2)}
Ranking: {json.dumps(ranking, indent=2)}

Output JSON:
{{
  "predicted_demurrage_days": number,
  "demurrage_range": {{"min": number, "max": number}},
  "confidence": "high|medium|low",
  "confidence_factors": ["factor1", "factor2"],
  "key_risks": ["risk1", "risk2"],
  "historical_comparison": "similar fixture comparison",
  "seasonal_adjustment": number,
  "port_specific_factors": {{"port": "factor"}}
}}"""
        
        result = await self.call_llama(prompt)
        
        state["prediction_data"] = result
        return state


class DecisionAgent(BaseAgent):
    """Makes final decision on fixture action"""
    
    def __init__(self):
        super().__init__("Decision Agent", AgentType.DECISION)
    
    async def execute(self, state: AgentState) -> AgentState:
        fixture = state.get("fixture_data", {})
        ranking = state.get("ranking_data", {})
        prediction = state.get("prediction_data", {})
        
        prompt = f"""You are a senior decision-maker for maritime chartering.

Given all analysis, make a recommendation:

Fixture: {json.dumps(fixture, indent=2)}
Ranking Score: {ranking.get('score', 0)}/100 - {ranking.get('reason', '')}
Prediction: {prediction.get('predicted_demurrage_days', 0)} days demurrage expected

Output JSON:
{{
  "recommendation": "FIX NOW|EXPLORE|WAIT|ARCHIVE",
  "confidence": "high|medium|auto_fix_eligible": boolean,
  "priority_score": number (1-10),
  "action_timeline": "immediate/within 24h/within 3d/this week",
  "key_decision_points": ["point1", "point2"],
  "auto_fix_recommended": boolean,
  "rationale": "detailed explanation"
}}"""
        
        result = await self.call_llama(prompt)
        
        state["decision_data"] = result
        return state


class LangGraphOrchestrator:
    """LangGraph-style orchestrator for Wake AI pipeline"""
    
    def __init__(self):
        self.agents = {
            AgentType.EXTRACTION: ExtractionAgent(),
            AgentType.ENRICHMENT: EnrichmentAgent(),
            AgentType.RANKING: RankingAgent(),
            AgentType.PREDICTION: PredictionAgent(),
            AgentType.DECISION: DecisionAgent(),
        }
        
        import os
        for agent in self.agents.values():
            agent.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            agent.model = os.getenv("LLAMA_MODEL", "llama3.1:70b")
    
    async def run_pipeline(
        self,
        raw_input: dict,
        user_id: str = None,
        enable_auto_fix: bool = False,
    ) -> AgentState:
        """Run full Wake AI pipeline through all agents"""
        
        state: AgentState = {
            "raw_input": raw_input,
            "fixture_data": {},
            "enrichment_data": {},
            "ranking_data": {},
            "prediction_data": {},
            "decision_data": {},
            "errors": [],
            "metadata": {
                "user_id": user_id,
                "enable_auto_fix": enable_auto_fix,
                "started_at": datetime.utcnow().isoformat(),
            }
        }
        
        try:
            state = await self._run_agent(AgentType.EXTRACTION, state)
            state = await self._run_agent(AgentType.ENRICHMENT, state)
            state = await self._run_agent(AgentType.RANKING, state)
            state = await self._run_agent(AgentType.PREDICTION, state)
            state = await self._run_agent(AgentType.DECISION, state)
            
            state["metadata"]["completed_at"] = datetime.utcnow().isoformat()
            
            if enable_auto_fix and state.get("decision_data", {}).get("auto_fix_recommended"):
                await self._trigger_auto_fix(state)
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            state["errors"].append(str(e))
        
        return state
    
    async def _run_agent(self, agent_type: AgentType, state: AgentState) -> AgentState:
        """Run a single agent"""
        agent = self.agents.get(agent_type)
        if not agent:
            return state
        
        logger.info(f"Running agent: {agent.name}")
        state = await agent.execute(state)
        
        return state
    
    async def _trigger_auto_fix(self, state: AgentState):
        """Trigger automatic FIX NOW action"""
        logger.info("Auto-FIX triggered for fixture")
        
        from app.services.notification_service import notification_service
        await notification_service.send_auto_fix_alert(state)


langgraph_orchestrator = LangGraphOrchestrator()
