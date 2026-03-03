"""
Veson IMOS Plugin - Voyage Management

Full async implementation for Veson IMOS API integration.
Provides voyage creation, retrieval, and status management.

API Endpoints:
- GET /voyages - List voyages
- POST /voyages - Create voyage from fixture
- GET /voyages/{id} - Get voyage details
- PUT /voyages/{id} - Update voyage status

Environment Variables:
- VESON_API_TOKEN: Veson IMOS API token
- VESON_API_URL: API base URL (default: https://api.veslink.com)
- VESON_TIMEOUT: Request timeout in seconds (default: 30)
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class VesonVoyageCreate(BaseModel):
    """Request model for creating a voyage"""
    vessel_imo: str = Field(..., description="Vessel IMO number")
    cargo_type: str = Field(..., description="Cargo type (e.g., CRUDE OIL, PRODUCTS)")
    cargo_quantity: Optional[float] = Field(None, description="Cargo quantity in MT")
    load_port: str = Field(..., description="Load port name")
    discharge_port: str = Field(..., description="Discharge port name")
    laycan_start: Optional[str] = Field(None, description="Laycan start date ISO format")
    laycan_end: Optional[str] = Field(None, description="Laycan end date ISO format")
    rate: Optional[float] = Field(None, description="Freight rate")
    currency: Optional[str] = Field("USD", description="Rate currency")
    charterer: Optional[str] = Field(None, description="Charterer name")
    owner: Optional[str] = Field(None, description="Owner name")
    broker: Optional[str] = Field(None, description="Broker name")
    status: Optional[str] = Field("PLANNING", description="Voyage status")


class VesonVoyageUpdate(BaseModel):
    """Request model for updating a voyage"""
    status: Optional[str] = Field(None, description="Voyage status")
    actual_load_date: Optional[str] = Field(None, description="Actual load date")
    actual_discharge_date: Optional[str] = Field(None, description="Actual discharge date")
    estimated_arrival: Optional[str] = Field(None, description="ETA at next port")
    actual_arrival: Optional[str] = Field(None, description="Actual arrival at port")
    bunkers_robed: Optional[float] = Field(None, description="Robbed bunkers quantity")
    speed_performance: Optional[float] = Field(None, description="Speed performance %")
    consumption_actual: Optional[float] = Field(None, description="Actual consumption")


class VesonVoyageResponse(BaseModel):
    """Response model for voyage data"""
    id: str
    voyage_number: Optional[str] = None
    vessel_imo: str
    vessel_name: Optional[str] = None
    cargo_type: str
    cargo_quantity: Optional[float] = None
    load_port: str
    discharge_port: str
    status: str
    laycan_start: Optional[str] = None
    laycan_end: Optional[str] = None
    rate: Optional[float] = None
    currency: Optional[str] = None
    charterer: Optional[str] = None
    owner: Optional[str] = None
    broker: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VesonVesselResponse(BaseModel):
    """Response model for vessel data"""
    imo: str
    name: Optional[str] = None
    vessel_type: Optional[str] = None
    year_built: Optional[int] = None
    dwt: Optional[float] = None
    flag: Optional[str] = None
    manager: Optional[str] = None


# ============================================================================
# Veson API Client
# ============================================================================

class VesonClient:
    """Async client for Veson IMOS API"""

    def __init__(self):
        self.api_token = os.getenv("VESON_API_TOKEN")
        self.base_url = os.getenv("VESON_API_URL", "https://api.veslink.com")
        self.timeout = int(os.getenv("VESON_TIMEOUT", "30"))
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Authorization": f"Token {self.api_token}",
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
        if not self.api_token:
            logger.error("VESON_API_TOKEN not configured")
            return {"error": "API token not configured"}

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

                if resp.status == 200 or resp.status == 201:
                    try:
                        return await resp.json()
                    except Exception:
                        return {"data": response_text}

                elif resp.status == 401:
                    logger.error("Veson API: Unauthorized - check API token")
                    return {"error": "Unauthorized - check API token"}

                elif resp.status == 404:
                    logger.warning(f"Veson API: Resource not found: {endpoint}")
                    return {"error": "Resource not found", "status": 404}

                elif resp.status == 429:
                    logger.warning("Veson API: Rate limit exceeded")
                    return {"error": "Rate limit exceeded"}

                else:
                    logger.error(
                        f"Veson API error: {resp.status} - {response_text[:200]}"
                    )
                    return {
                        "error": f"API error: {resp.status}",
                        "details": response_text[:500],
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Veson API connection error: {e}")
            return {"error": f"Connection error: {str(e)}"}

        except Exception as e:
            logger.exception(f"Unexpected error in Veson API call: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    # ========================================================================
    # Voyage Operations
    # ========================================================================

    async def list_voyages(
        self,
        vessel_imo: Optional[str] = None,
        status: Optional[str] = None,
        charterer: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List voyages from Veson IMOS.

        Args:
            vessel_imo: Filter by vessel IMO
            status: Filter by voyage status
            charterer: Filter by charterer
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dict with voyages list and pagination info
        """
        params = {
            "limit": limit,
            "offset": offset,
        }

        if vessel_imo:
            params["vesselImo"] = vessel_imo
        if status:
            params["status"] = status
        if charterer:
            params["charterer"] = charterer

        logger.info(f"Listing voyages with params: {params}")
        result = await self._request("GET", "/voyages", params=params)

        if "error" in result and result.get("status") == 404:
            return {"voyages": [], "total": 0, "limit": limit, "offset": offset}

        if "voyages" in result:
            return {
                "voyages": result.get("voyages", []),
                "total": len(result.get("voyages", [])),
                "limit": limit,
                "offset": offset,
            }

        return result

    async def get_voyage(self, voyage_id: str) -> Dict[str, Any]:
        """
        Get voyage details by ID.

        Args:
            voyage_id: Veson voyage ID

        Returns:
            Voyage details
        """
        logger.info(f"Fetching voyage: {voyage_id}")
        return await self._request("GET", f"/voyages/{voyage_id}")

    async def create_voyage(self, voyage: VesonVoyageCreate) -> Dict[str, Any]:
        """
        Create a new voyage in Veson IMOS.

        Args:
            voyage: Voyage creation data

        Returns:
            Created voyage details or error
        """
        logger.info(
            f"Creating voyage for vessel {voyage.vessel_imo}: "
            f"{voyage.load_port} -> {voyage.discharge_port}"
        )

        payload = voyage.model_dump(exclude_none=False)

        # Remove None values to keep payload clean
        payload = {k: v for k, v in payload.items() if v is not None}

        result = await self._request("POST", "/voyages", json_data=payload)

        if "error" not in result:
            logger.info(f"Voyage created successfully: {result.get('id')}")

        return result

    async def update_voyage(
        self, voyage_id: str, update: VesonVoyageUpdate
    ) -> Dict[str, Any]:
        """
        Update voyage status and details.

        Args:
            voyage_id: Veson voyage ID
            update: Update data

        Returns:
            Updated voyage details or error
        """
        logger.info(f"Updating voyage: {voyage_id}")

        payload = update.model_dump(exclude_none=False)
        payload = {k: v for k, v in payload.items() if v is not None}

        if not payload:
            return {"error": "No fields to update"}

        result = await self._request("PUT", f"/voyages/{voyage_id}", json_data=payload)

        if "error" not in result:
            logger.info(f"Voyage updated successfully: {voyage_id}")

        return result

    async def delete_voyage(self, voyage_id: str) -> Dict[str, Any]:
        """
        Delete a voyage (soft delete).

        Args:
            voyage_id: Veson voyage ID

        Returns:
            Deletion result
        """
        logger.info(f"Deleting voyage: {voyage_id}")
        return await self._request("DELETE", f"/voyages/{voyage_id}")

    # ========================================================================
    # Vessel Operations
    # ========================================================================

    async def get_vessel(self, imo: str) -> Dict[str, Any]:
        """
        Get vessel details by IMO.

        Args:
            imo: Vessel IMO number

        Returns:
            Vessel details
        """
        logger.info(f"Fetching vessel: {imo}")
        return await self._request("GET", f"/vessels/{imo}")

    async def list_vessels(
        self, name: Optional[str] = None, vessel_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List vessels in fleet.

        Args:
            name: Filter by vessel name
            vessel_type: Filter by vessel type

        Returns:
            List of vessels
        """
        params = {}
        if name:
            params["name"] = name
        if vessel_type:
            params["type"] = vessel_type

        logger.info(f"Listing vessels with params: {params}")
        return await self._request("GET", "/vessels", params=params)


# Global client instance
_veson_client: Optional[VesonClient] = None


async def get_veson_client() -> VesonClient:
    """Get or create Veson client singleton"""
    global _veson_client
    if _veson_client is None:
        _veson_client = VesonClient()
    return _veson_client


# ============================================================================
# Plugin Hooks
# ============================================================================


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """
    Enrich fixture with Veson IMOS vessel data.

    Hook: on_fixture_enrich
    """
    client = await get_veson_client()

    if not client.api_token:
        return {"error": "VESON_API_TOKEN not configured"}

    if not fixture.imo_number:
        return {"error": "No IMO number on fixture"}

    try:
        result = await client.get_vessel(fixture.imo_number)

        if "error" in result and result.get("status") == 404:
            return {"error": "Vessel not found in IMOS"}

        enrichment = {
            "veson_vessel": {
                "imo": result.get("imo"),
                "name": result.get("name"),
                "type": result.get("vesselType"),
                "year_built": result.get("yearBuilt"),
                "dwt": result.get("dwt"),
                "flag": result.get("flag"),
            }
        }

        if hasattr(fixture, "enrichment_data") and fixture.enrichment_data:
            fixture.enrichment_data["veson"] = enrichment
        else:
            if hasattr(fixture, "enrichment_data"):
                fixture.enrichment_data = {"veson": enrichment}

        return enrichment

    except Exception as e:
        logger.exception(f"Error enriching fixture with Veson: {e}")
        return {"error": str(e)}


async def create_voyage_from_fixture(fixture, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create voyage in Veson IMOS from fixture data.

    Hook: on_fix_now
    """
    client = await get_veson_client()

    if not client.api_token:
        return {"error": "VESON_API_TOKEN not configured"}

    try:
        voyage_data = VesonVoyageCreate(
            vessel_imo=fixture.imo_number,
            cargo_type=fixture.cargo_type,
            cargo_quantity=fixture.cargo_quantity,
            load_port=fixture.port_loading,
            discharge_port=fixture.port_discharge,
            laycan_start=(
                fixture.laycan_start.isoformat()
                if hasattr(fixture, "laycan_start") and fixture.laycan_start
                else None
            ),
            laycan_end=(
                fixture.laycan_end.isoformat()
                if hasattr(fixture, "laycan_end") and fixture.laycan_end
                else None
            ),
            rate=fixture.rate,
            currency=fixture.rate_currency or "USD",
            charterer=fixture.charterer,
            broker=fixture.broker,
        )

        # Merge additional payload fields
        for key, value in payload.items():
            if hasattr(voyage_data, key):
                setattr(voyage_data, key, value)

        result = await client.create_voyage(voyage_data)

        if "error" in result:
            return result

        return {
            "status": "created",
            "voyage_id": result.get("id"),
            "voyage_number": result.get("voyageNumber"),
            "data": result,
        }

    except Exception as e:
        logger.exception(f"Error creating voyage from fixture: {e}")
        return {"error": str(e)}


async def list_veson_voyages(
    vessel_imo: Optional[str] = None,
    status: Optional[str] = None,
    charterer: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List voyages from Veson IMOS.

    Used by API endpoint.
    """
    client = await get_veson_client()
    return await client.list_voyages(
        vessel_imo=vessel_imo,
        status=status,
        charterer=charterer,
        limit=limit,
        offset=offset,
    )


async def get_veson_voyage(voyage_id: str) -> Dict[str, Any]:
    """Get voyage details from Veson IMOS."""
    client = await get_veson_client()
    return await client.get_voyage(voyage_id)


async def update_veson_voyage(
    voyage_id: str,
    status: Optional[str] = None,
    actual_load_date: Optional[str] = None,
    actual_discharge_date: Optional[str] = None,
    estimated_arrival: Optional[str] = None,
    actual_arrival: Optional[str] = None,
    bunkers_robed: Optional[float] = None,
    speed_performance: Optional[float] = None,
    consumption_actual: Optional[float] = None,
) -> Dict[str, Any]:
    """Update voyage in Veson IMOS."""
    client = await get_veson_client()

    update = VesonVoyageUpdate(
        status=status,
        actual_load_date=actual_load_date,
        actual_discharge_date=actual_discharge_date,
        estimated_arrival=estimated_arrival,
        actual_arrival=actual_arrival,
        bunkers_robed=bunkers_robed,
        speed_performance=speed_performance,
        consumption_actual=consumption_actual,
    )

    return await client.update_voyage(voyage_id, update)


# Plugin hooks registry
hooks = {
    "on_fixture_enrich": on_fixture_enrich,
    "on_fix_now": create_voyage_from_fixture,
}


# Export models for external use
__all__ = [
    "VesonVoyageCreate",
    "VesonVoyageUpdate",
    "VesonVoyageResponse",
    "VesonVesselResponse",
    "VesonClient",
    "get_veson_client",
    "list_veson_voyages",
    "get_veson_voyage",
    "update_veson_voyage",
    "hooks",
]
