"""
Prompt templates service for OpenMaritime AI agents.

Manages prompt templates in database with filesystem fallback.
Allows tenant-specific customization of AI behavior.
"""
from typing import Dict, List, Optional, Any
from uuid import UUID
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.models import PromptTemplate

logger = logging.getLogger(__name__)

# Default prompts - seeded from filesystem
DEFAULT_PROMPTS = {
    "extraction": {
        "name": "default_extraction",
        "agent_type": "extraction",
        "system_prompt": "You are a maritime data extraction expert. Extract and standardize fixture fields from raw data.",
        "user_template": """Extract and infer the following fields from fixture data:
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

Input: {{input_data}}

Output JSON:""",
        "description": "Default extraction prompt for parsing raw fixture emails",
        "variables": {"input_data": "Raw email or fixture data"},
        "temperature": 0.1,
        "max_tokens": 2048,
    },
    "enrichment": {
        "name": "default_enrichment",
        "agent_type": "enrichment",
        "system_prompt": "You are a maritime data enrichment specialist. Determine which data sources to query for fixture enrichment.",
        "user_template": """Given fixture data, determine what enrichment sources to query:

Fixture: {{fixture_json}}

For each source (RightShip, MarineTraffic, Idwal, Signal Ocean, ZeroNorth), determine:
- relevance_score (0-1)
- priority (high/medium/low)
- expected_fields (list)

Output JSON with sources array:""",
        "description": "Default enrichment prompt for determining data sources",
        "variables": {"fixture_json": "Fixture data as JSON"},
        "temperature": 0.1,
        "max_tokens": 1024,
    },
    "ranking": {
        "name": "default_ranking",
        "agent_type": "ranking",
        "system_prompt": "You are a senior charterer + TCE expert. Calculate Wake Score for maritime fixtures.",
        "user_template": """MARKET CONTEXT:
{{market_context}}

Calculate ranking for this fixture following these steps:
1. TCE delta %: compare rate to market index
2. Age adjustment: younger vessels score higher
3. Laycan urgency: closer = higher (red <3d, yellow 3-7d, green >7d)
4. Position bonus: vessel near load/discharge ports
5. Risk penalty: low safety score or poor GHG
6. Completeness bonus: more fields = higher

Fixture: {{fixture_json}}
Enrichment: {{enrichment_json}}

Output JSON:
{
  "score": 0-100,
  "tce_delta_pct": number,
  "urgency": "high|medium|low",
  "urgency_days": number,
  "position_bonus": number,
  "risk_penalty": number,
  "completeness_bonus": number,
  "reason": "1-2 sentence explanation",
  "key_factors": ["factor1", "factor2", "factor3"]
}""",
        "description": "Default ranking prompt for Wake Score calculation",
        "variables": {
            "market_context": "Current market data and indices",
            "fixture_json": "Fixture data",
            "enrichment_json": "Enrichment data"
        },
        "temperature": 0.1,
        "max_tokens": 2048,
    },
    "prediction": {
        "name": "default_prediction",
        "agent_type": "prediction",
        "system_prompt": "You are a laytime/demurrage expert with 20 years experience. Predict demurrage for fixtures.",
        "user_template": """Predict demurrage for this fixture:
- Consider port congestion (historical)
- Weather patterns (seasonal)
- Vessel performance history
- Charter party terms (if inferable)

Fixture: {{fixture_json}}
Ranking: {{ranking_json}}

Output JSON:
{
  "predicted_demurrage_days": number,
  "demurrage_range": {"min": number, "max": number},
  "confidence": "high|medium|low",
  "confidence_factors": ["factor1", "factor2"],
  "key_risks": ["risk1", "risk2"],
  "historical_comparison": "similar fixture comparison",
  "seasonal_adjustment": number,
  "port_specific_factors": {{port_factors}}
}""",
        "description": "Default prediction prompt for demurrage forecasting",
        "variables": {
            "fixture_json": "Fixture data",
            "ranking_json": "Ranking data",
            "port_factors": "Port-specific factors object"
        },
        "temperature": 0.2,
        "max_tokens": 2048,
    },
    "decision": {
        "name": "default_decision",
        "agent_type": "decision",
        "system_prompt": "You are a senior decision-maker for maritime chartering. Make actionable recommendations.",
        "user_template": """Given all analysis, make a recommendation:

Fixture: {{fixture_json}}
Ranking Score: {{score}}/100 - {{reason}}
Prediction: {{demurrage}} days demurrage expected

Output JSON:
{
  "recommendation": "FIX NOW|EXPLORE|WAIT|ARCHIVE",
  "confidence": "high|medium|low",
  "auto_fix_eligible": boolean,
  "priority_score": number (1-10),
  "action_timeline": "immediate/within 24h/within 3d/this week",
  "key_decision_points": ["point1", "point2"],
  "auto_fix_recommended": boolean,
  "rationale": "detailed explanation"
}""",
        "description": "Default decision prompt for fixture recommendations",
        "variables": {
            "fixture_json": "Fixture data",
            "score": "Wake Score",
            "reason": "Score reasoning",
            "demurrage": "Demurrage prediction"
        },
        "temperature": 0.3,
        "max_tokens": 1024,
    },
}


class PromptService:
    """
    Service for managing prompt templates.
    Uses database for storage with filesystem defaults.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
    
    async def initialize(self, db: AsyncSession):
        """Initialize prompts - seed defaults if empty"""
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.is_default == True))
        existing = result.scalars().all()
        
        if not existing:
            logger.info("Seeding default prompts...")
            for agent_type, prompt_data in DEFAULT_PROMPTS.items():
                prompt = PromptTemplate(
                    tenant_id=None,  # System default
                    name=prompt_data["name"],
                    agent_type=agent_type,
                    system_prompt=prompt_data["system_prompt"],
                    user_template=prompt_data["user_template"],
                    description=prompt_data.get("description"),
                    variables=prompt_data.get("variables"),
                    temperature=prompt_data.get("temperature", 0.1),
                    max_tokens=prompt_data.get("max_tokens", 2048),
                    is_default=True,
                    is_active=True,
                    version=1,
                )
                db.add(prompt)
            await db.commit()
            logger.info(f"Seeded {len(DEFAULT_PROMPTS)} default prompts")
        
        await self._refresh_cache(db)
    
    async def _refresh_cache(self, db: AsyncSession):
        """Refresh prompt cache from database"""
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.is_active == True))
        prompts = result.scalars().all()
        
        self._cache = {}
        for p in prompts:
            key = f"{p.tenant_id or 'system'}:{p.agent_type}"
            self._cache[key] = {
                "id": str(p.id),
                "name": p.name,
                "system_prompt": p.system_prompt,
                "user_template": p.user_template,
                "model": p.model,
                "temperature": p.temperature,
                "max_tokens": p.max_tokens,
                "variables": p.variables or {},
            }
    
    async def get_prompt(
        self,
        agent_type: str,
        tenant_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Get prompt template for agent type"""
        # Try tenant-specific first
        if tenant_id:
            key = f"{str(tenant_id)}:{agent_type}"
            if key in self._cache:
                return self._cache[key]
        
        # Fall back to system default
        key = f"system:{agent_type}"
        if key in self._cache:
            return self._cache[key]
        
        # Last resort: return filesystem default
        if agent_type in DEFAULT_PROMPTS:
            return DEFAULT_PROMPTS[agent_type]
        
        raise ValueError(f"No prompt found for agent type: {agent_type}")
    
    async def render_prompt(
        self,
        agent_type: str,
        variables: Dict[str, Any],
        tenant_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Render prompt with variables"""
        template = await self.get_prompt(agent_type, tenant_id, db)
        
        user_template = template["user_template"]
        # Simple variable substitution
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            if placeholder in user_template:
                if isinstance(var_value, (dict, list)):
                    user_template = user_template.replace(
                        placeholder,
                        json.dumps(var_value, indent=2)
                    )
                else:
                    user_template = user_template.replace(placeholder, str(var_value))
        
        return {
            "system_prompt": template["system_prompt"],
            "user_prompt": user_template,
            "model": template.get("model"),
            "temperature": template.get("temperature", 0.1),
            "max_tokens": template.get("max_tokens", 2048),
        }
    
    async def create_prompt(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        agent_type: str,
        name: str,
        system_prompt: str,
        user_template: str,
        description: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> PromptTemplate:
        """Create a new prompt template"""
        prompt = PromptTemplate(
            tenant_id=tenant_id,
            agent_type=agent_type,
            name=name,
            system_prompt=system_prompt,
            user_template=user_template,
            description=description,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            is_default=False,
            is_active=True,
            version=1,
        )
        db.add(prompt)
        
        try:
            await db.commit()
            await db.refresh(prompt)
            await self._refresh_cache(db)
            return prompt
        except IntegrityError:
            await db.rollback()
            raise ValueError(f"Prompt with name '{name}' already exists for this tenant")
    
    async def update_prompt(
        self,
        db: AsyncSession,
        prompt_id: UUID,
        **updates,
    ) -> PromptTemplate:
        """Update an existing prompt"""
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.id == prompt_id)
        )
        prompt = result.scalar_one_or_none()
        
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_id}")
        
        for key, value in updates.items():
            if hasattr(prompt, key):
                setattr(prompt, key, value)
        
        # Increment version
        prompt.version += 1
        
        await db.commit()
        await db.refresh(prompt)
        await self._refresh_cache(db)
        
        return prompt
    
    async def list_prompts(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        agent_type: Optional[str] = None,
    ) -> List[PromptTemplate]:
        """List prompt templates"""
        query = select(PromptTemplate)
        
        if tenant_id:
            query = query.where(PromptTemplate.tenant_id == tenant_id)
        
        if agent_type:
            query = query.where(PromptTemplate.agent_type == agent_type)
        
        result = await db.execute(query.order_by(PromptTemplate.agent_type, PromptTemplate.name))
        return result.scalars().all()


prompt_service = PromptService()
