"""
Idwal Plugin - Vessel Grading

Full async implementation for Idwal API integration.
Provides vessel grading, technical assessments, and history.

API Endpoints:
- GET /vessels/{imo}/grade - Vessel grading
- GET /vessels/{imo}/history - Grading history

Environment Variables:
- IDWAL_API_KEY: Idwal API key
- IDWAL_API_URL: API base URL (default: https://api.idwal.com)
- IDWAL_TIMEOUT: Request timeout in seconds (default: 30)
"""
import os
import logging
from typing import Dict, Any, List, Optional

import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class IdwalVesselGrade(BaseModel):
    """Vessel grading response"""
    imo: int
    vessel_name: Optional[str] = None
    vessel_type: Optional[str] = None
    grade: Optional[int] = None  # 0-100 score
    grade_band: Optional[str] = None  # A, B, C, D
    technical_score: Optional[float] = None
    commercial_score: Optional[float] = None
    inspection_score: Optional[float] = None
    vetting_score: Optional[float] = None
    last_survey_date: Optional[str] = None
    next_survey_date: Optional[str] = None
    age_score: Optional[float] = None
    owner_score: Optional[float] = None
    manager_score: Optional[float] = None
    operator_score: Optional[float] = None
    flag_score: Optional[float] = None
    class_score: Optional[float] = None
    issued_date: Optional[str] = None
    expiry_date: Optional[str] = None


class IdwalGradeHistory(BaseModel):
    """Historical grading data"""
    imo: int
    history: List[Dict[str, Any]] = Field(default_factory=list)


class IdwalInspectionSummary(BaseModel):
    """Inspection summary data"""
    inspection_id: Optional[str] = None
    inspection_type: Optional[str] = None
    date: Optional[str] = None
    authority: Optional[str] = None
    deficiencies: Optional[int] = None
    detention: Optional[bool] = None
    rating: Optional[str] = None


class IdwalVettingDetail(BaseModel):
    """Detailed vetting information"""
    vetting_company: Optional[str] = None
    last_vetting: Optional[str] = None
    vetting_score: Optional[float] = None
    vetting_status: Optional[str] = None
    risk_score: Optional[float] = None
    detention_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class IdwalComparison(BaseModel):
    """Vessel comparison data"""
    vessel_imo: int
    peer_average: Optional[float] = None
    peer_count: Optional[int] = None
    percentile_rank: Optional[float] = None
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


# ============================================================================
# Idwal API Client
# ============================================================================

class IdwalClient:
    """Async client for Idwal API"""

    def __init__(self):
        self.api_key = os.getenv("IDWAL_API_KEY")
        self.base_url = os.getenv("IDWAL_API_URL", "https://api.idwal.com/v1")
        self.timeout = int(os.getenv("IDWAL_TIMEOUT", "30"))
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._session

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make API request with error handling"""
        if not self.api_key:
            logger.error("IDWAL_API_KEY not configured")
            return {"error": "API key not configured"}

        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with session.request(
                method,
                url,
                params=params,
                json=json_data,
            ) as resp:
                response_text = await resp.text()

                if resp.status == 200:
                    try:
                        return await resp.json()
                    except Exception:
                        return {"data": response_text}

                elif resp.status == 201:
                    try:
                        return await resp.json()
                    except Exception:
                        return {"status": "created"}

                elif resp.status == 401:
                    logger.error("Idwal API: Unauthorized - check API key")
                    return {"error": "Unauthorized - check API key"}

                elif resp.status == 403:
                    logger.error("Idwal API: Forbidden - insufficient permissions")
                    return {"error": "Forbidden - insufficient permissions"}

                elif resp.status == 404:
                    logger.warning(f"Idwal API: Resource not found: {endpoint}")
                    return {"error": "Resource not found", "status": 404}

                elif resp.status == 422:
                    logger.warning(f"Idwal API: Validation error: {response_text}")
                    return {"error": "Validation error", "details": response_text}

                elif resp.status == 429:
                    logger.warning("Idwal API: Rate limit exceeded")
                    return {"error": "Rate limit exceeded"}

                elif resp.status == 500:
                    logger.error("Idwal API: Internal server error")
                    return {"error": "Internal server error"}

                else:
                    logger.error(
                        f"Idwal API error: {resp.status} - {response_text[:200]}"
                    )
                    return {
                        "error": f"API error: {resp.status}",
                        "details": response_text[:500],
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Idwal API connection error: {e}")
            return {"error": f"Connection error: {str(e)}"}

        except Exception as e:
            logger.exception(f"Unexpected error in Idwal API call: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    # ========================================================================
    # Vessel Grading
    # ========================================================================

    async def get_vessel_grade(
        self,
        imo: int,
        include_comparison: bool = False,
        include_inspections: bool = False,
    ) -> Dict[str, Any]:
        """
        Get vessel grading by IMO.

        Args:
            imo: Vessel IMO number
            include_comparison: Include peer comparison
            include_inspections: Include inspection details

        Returns:
            Vessel grade data
        """
        if not isinstance(imo, int):
            try:
                imo = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        params = {}
        if include_comparison:
            params["comparison"] = "true"
        if include_inspections:
            params["inspections"] = "true"

        logger.info(f"Fetching vessel grade: {imo}")
        return await self._request("GET", f"/vessels/{imo}/grade", params=params)

    async def get_vessel_history(
        self,
        imo: int,
        years: int = 2,
    ) -> Dict[str, Any]:
        """
        Get vessel grading history.

        Args:
            imo: Vessel IMO number
            years: Number of years of history

        Returns:
            Historical grading data
        """
        if not isinstance(imo, int):
            try:
                imo = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        params = {"years": years}

        logger.info(f"Fetching vessel grading history: {imo}, years: {years}")
        return await self._request("GET", f"/vessels/{imo}/history", params=params)

    async def get_vessel_details(self, imo: int) -> Dict[str, Any]:
        """
        Get detailed vessel information.

        Args:
            imo: Vessel IMO number

        Returns:
            Detailed vessel data
        """
        if not isinstance(imo, int):
            try:
                IMO = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        logger.info(f"Fetching vessel details: {imo}")
        return await self._request("GET", f"/vessels/{imo}")

    # ========================================================================
    # Vetting Operations
    # ========================================================================

    async def get_vetting_details(self, imo: int) -> Dict[str, Any]:
        """
        Get detailed vetting information.

        Args:
            imo: Vessel IMO number

        Returns:
            Vetting details including risk scores
        """
        if not isinstance(imo, int):
            try:
                IMO = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        logger.info(f"Fetching vetting details: {imo}")
        return await self._request("GET", f"/vessels/{imo}/vetting")

    async def get_detention_history(self, imo: int) -> Dict[str, Any]:
        """
        Get vessel detention history.

        Args:
            imo: Vessel IMO number

        Returns:
            Detention history
        """
        if not isinstance(imo, int):
            try:
                IMO = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        logger.info(f"Fetching detention history: {imo}")
        return await self._request("GET", f"/vessels/{imo}/detentions")

    # ========================================================================
    # Inspections
    # ========================================================================

    async def get_inspections(
        self,
        imo: int,
        inspection_type: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get vessel inspection history.

        Args:
            imo: Vessel IMO number
            inspection_type: Filter by type (PSC, SIRE, CDI, etc.)
            limit: Maximum results

        Returns:
            Inspection history
        """
        if not isinstance(imo, int):
            try:
                IMO = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        params = {"limit": limit}
        if inspection_type:
            params["type"] = inspection_type

        logger.info(f"Fetching inspections: {imo}")
        return await self._request("GET", f"/vessels/{imo}/inspections", params=params)

    # ========================================================================
    # Fleet Operations
    # ========================================================================

    async def get_fleet_grade(
        self,
        vessel_types: Optional[List[str]] = None,
        flags: Optional[List[str]] = None,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get fleet average grades.

        Args:
            vessel_types: Filter by vessel types
            flags: Filter by flags
            age_min: Minimum vessel age
            age_max: Maximum vessel age

        Returns:
            Fleet grade statistics
        """
        params = {}

        if vessel_types:
            params["vesselTypes"] = ",".join(vessel_types)
        if flags:
            params["flags"] = ",".join(flags)
        if age_min:
            params["ageMin"] = age_min
        if age_max:
            params["ageMax"] = age_max

        logger.info(f"Fetching fleet grades: {params}")
        return await self._request("GET", "/fleet/grades", params=params)

    async def search_vessels(
        self,
        grade_min: Optional[int] = None,
        grade_max: Optional[int] = None,
        vessel_type: Optional[str] = None,
        age_max: Optional[int] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Search vessels by grade criteria.

        Args:
            grade_min: Minimum grade (0-100)
            grade_max: Maximum grade (0-100)
            vessel_type: Vessel type
            age_max: Maximum vessel age
            limit: Maximum results

        Returns:
            List of matching vessels
        """
        params = {"limit": limit}

        if grade_min is not None:
            params["gradeMin"] = grade_min
        if grade_max is not None:
            params["gradeMax"] = grade_max
        if vessel_type:
            params["vesselType"] = vessel_type
        if age_max:
            params["ageMax"] = age_max

        logger.info(f"Searching vessels: {params}")
        return await self._request("GET", "/vessels/search", params=params)

    # ========================================================================
    # Market Analysis
    # ========================================================================

    async def get_market_comps(
        self,
        imo: int,
        criteria: str = "similar",
    ) -> Dict[str, Any]:
        """
        Get comparable vessels for market analysis.

        Args:
            imo: Reference vessel IMO
            criteria: Comparison criteria (similar, same_owner, same_manager)

        Returns:
            Comparable vessels
        """
        if not isinstance(imo, int):
            try:
                IMO = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        params = {"criteria": criteria}

        logger.info(f"Fetching market comps for: {imo}")
        return await self._request("GET", f"/vessels/{imo}/comps", params=params)


# Global client instance
_idwal_client: Optional[IdwalClient] = None


async def get_idwal_client() -> IdwalClient:
    """Get or create Idwal client singleton"""
    global _idwal_client
    if _idwal_client is None:
        _idwal_client = IdwalClient()
    return _idwal_client


# ============================================================================
# Plugin Hooks
# ============================================================================


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """
    Enrich fixture with Idwal vessel grading.

    Hook: on_fixture_enrich
    """
    client = await get_idwal_client()

    if not client.api_key:
        return {"error": "IDWAL_API_KEY not configured"}

    if not fixture.imo_number:
        return {"error": "No IMO number on fixture"}

    try:
        # Convert IMO to int
        try:
            imo = int(fixture.imo_number)
        except (ValueError, TypeError):
            return {"error": "Invalid IMO number format"}

        # Get vessel grade
        grade_result = await client.get_vessel_grade(
            imo,
            include_comparison=True,
            include_inspections=True,
        )

        if "error" in grade_result and grade_result.get("status") == 404:
            return {"error": "Vessel not found in Idwal database"}

        if "error" in grade_result:
            return grade_result

        # Transform to enrichment format
        enrichment = {
            "grade": grade_result.get("grade"),
            "grade_band": grade_result.get("gradeBand") or grade_result.get("grade_band"),
            "technical_score": grade_result.get("technicalScore") or grade_result.get("technical_score"),
            "commercial_score": grade_result.get("commercialScore") or grade_result.get("commercial_score"),
            "inspection_score": grade_result.get("inspectionScore") or grade_result.get("inspection_score"),
            "vetting_score": grade_result.get("vettingScore") or grade_result.get("vetting_score"),
            "vessel_type": grade_result.get("vesselType") or grade_result.get("vessel_type"),
            "vessel_name": grade_result.get("vesselName") or grade_result.get("vessel_name"),
            "age_score": grade_result.get("ageScore") or grade_result.get("age_score"),
            "owner_score": grade_result.get("ownerScore") or grade_result.get("owner_score"),
            "manager_score": grade_result.get("managerScore") or grade_result.get("manager_score"),
            "flag_score": grade_result.get("flagScore") or grade_result.get("flag_score"),
            "class_score": grade_result.get("classScore") or grade_result.get("class_score"),
        }

        # Add peer comparison if available
        if "comparison" in grade_result:
            enrichment["peer_comparison"] = grade_result.get("comparison")

        # Add inspections if available
        if "inspections" in grade_result:
            enrichment["recent_inspections"] = grade_result.get("inspections")

        # Update fixture enrichment data
        if hasattr(fixture, "enrichment_data") and fixture.enrichment_data:
            fixture.enrichment_data["idwal"] = enrichment
        elif hasattr(fixture, "enrichment_data"):
            fixture.enrichment_data = {"idwal": enrichment}

        return enrichment

    except Exception as e:
        logger.exception(f"Error enriching fixture with Idwal: {e}")
        return {"error": str(e)}


# API endpoint helpers

async def get_vessel_grade(
    imo: int,
    include_comparison: bool = False,
    include_inspections: bool = False,
) -> Dict[str, Any]:
    """Get vessel grade from Idwal."""
    client = await get_idwal_client()
    return await client.get_vessel_grade(
        imo,
        include_comparison=include_comparison,
        include_inspections=include_inspections,
    )


async def get_vessel_history(imo: int, years: int = 2) -> Dict[str, Any]:
    """Get vessel grading history from Idwal."""
    client = await get_idwal_client()
    return await client.get_vessel_history(imo, years=years)


async def get_vetting_details(imo: int) -> Dict[str, Any]:
    """Get vetting details from Idwal."""
    client = await get_idwal_client()
    return await client.get_vetting_details(imo)


async def get_inspections(
    imo: int,
    inspection_type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get inspection history from Idwal."""
    client = await get_idwal_client()
    return await client.get_inspections(imo, inspection_type=inspection_type, limit=limit)


# Plugin hooks registry
hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}


# Export models and client for external use
__all__ = [
    "IdwalVesselGrade",
    "IdwalGradeHistory",
    "IdwalInspectionSummary",
    "IdwalVettingDetail",
    "IdwalComparison",
    "IdwalClient",
    "get_idwal_client",
    "get_vessel_grade",
    "get_vessel_history",
    "get_vetting_details",
    "get_inspections",
    "hooks",
]
