"""
ZeroNorth Plugin - Bunker Optimization & Emissions

Full async implementation for ZeroNorth API integration.
Provides bunker pricing, voyage optimization, and CO2 emissions.

API Endpoints:
- GET /bunkers - Bunker prices by port
- POST /voyage/optimize - Route optimization
- GET /emissions - CO2 calculations

Environment Variables:
- ZERONORTH_API_KEY: ZeroNorth API key
- ZERONORTH_API_URL: API base URL (default: https://api.zeronorth.com)
- ZERONORTH_TIMEOUT: Request timeout in seconds (default: 30)
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date

import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class ZeroNorthBunkerPrice(BaseModel):
    """Bunker price data"""
    port: Optional[str] = None
    port_code: Optional[str] = None
    mgo_price: Optional[float] = None
    mgo_price_currency: Optional[str] = None
    vlsfo_price: Optional[float] = None
    vlsfo_price_currency: Optional[str] = None
    hfo_price: Optional[float] = None
    hfo_price_currency: Optional[str] = None
    ulsfo_price: Optional[float] = None
    ulsfo_price_currency: Optional[str] = None
    lng_price: Optional[float] = None
    lng_price_currency: Optional[str] = None
    lng_cif: Optional[float] = None
    lng_mb: Optional[float] = None
    date: Optional[str] = None


class ZeroNorthVoyageOptimizationRequest(BaseModel):
    """Voyage optimization request"""
    from_port: str = Field(..., description="Origin port")
    to_port: str = Field(..., description="Destination port")
    vessel_type: str = Field(..., description="Vessel type (VLCC, SUEZMAX, etc.)")
    vessel_dwt: Optional[float] = Field(None, description="Vessel DWT")
    cargo_quantity: Optional[float] = Field(None, description="Cargo quantity in MT")
    departure_date: Optional[str] = Field(None, description="Departure date")
    speed_min: Optional[float] = Field(None, description="Minimum speed (knots)")
    speed_max: Optional[float] = Field(None, description="Maximum speed (knots)")
    bunkers_onboard: Optional[Dict[str, float]] = Field(
        None, description="Current bunker quantities by grade"
    )


class ZeroNorthVoyageOptimizationResponse(BaseModel):
    """Voyage optimization response"""
    route_id: Optional[str] = None
    distance_nm: Optional[float] = None
    distance_km: Optional[float] = None
    transit_time_days: Optional[float] = None
    bunker_consumption: Optional[Dict[str, float]] = None
    bunker_cost: Optional[float] = None
    co2_emissions: Optional[float] = None
    nox_emissions: Optional[float] = None
    sox_emissions: Optional[float] = None
    eexi: Optional[float] = None
    cii: Optional[float] = None
    cii_rating: Optional[str] = None
    optimal_speed: Optional[float] = None
    route_waypoints: Optional[List[Dict[str, Any]]] = None


class ZeroNorthEmissionsRequest(BaseModel):
    """CO2 emissions calculation request"""
    vessel_type: str = Field(..., description="Vessel type")
    distance_nm: Optional[float] = Field(None, description="Distance in nautical miles")
    fuel_type: Optional[str] = Field("VLSFO", description="Fuel type (MGO, VLSFO, HFO, LNG)")
    fuel_consumption: Optional[float] = Field(None, description="Fuel consumption in MT")
    cargo_quantity: Optional[float] = Field(None, description="Cargo quantity in MT")
    voyage_days: Optional[float] = Field(None, description="Voyage duration in days")


class ZeroNorthEmissionsResponse(BaseModel):
    """CO2 emissions response"""
    co2_kg: Optional[float] = None
    co2_tonnes: Optional[float] = None
    co2_per_tonne_mile: Optional[float] = None
    nox_kg: Optional[float] = None
    sox_kg: Optional[float] = None
    pm_kg: Optional[float] = None
    ghg_reduction_potential: Optional[float] = None
    eexi: Optional[float] = None
    cii: Optional[float] = None
    cii_rating: Optional[str] = None


class ZeroNorthVoyageStatus(BaseModel):
    """Voyage status and performance"""
    voyage_id: Optional[str] = None
    vessel_name: Optional[str] = None
    vessel_imo: Optional[str] = None
    status: Optional[str] = None
    from_port: Optional[str] = None
    to_port: Optional[str] = None
    eta: Optional[str] = None
    distance_remaining_nm: Optional[float] = None
    fuel_remaining_mt: Optional[float] = None
    fuel_consumed_mt: Optional[float] = None
    speed_actual_kn: Optional[float] = None
    speed_optimized_kn: Optional[float] = None


# ============================================================================
# ZeroNorth API Client
# ============================================================================

class ZeroNorthClient:
    """Async client for ZeroNorth API"""

    def __init__(self):
        self.api_key = os.getenv("ZERONORTH_API_KEY")
        self.base_url = os.getenv("ZERONORTH_API_URL", "https://api.zeronorth.com/v1")
        self.timeout = int(os.getenv("ZERONORTH_TIMEOUT", "30"))
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
            logger.error("ZERONORTH_API_KEY not configured")
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
                    logger.error("ZeroNorth API: Unauthorized - check API key")
                    return {"error": "Unauthorized - check API key"}

                elif resp.status == 403:
                    logger.error("ZeroNorth API: Forbidden - insufficient permissions")
                    return {"error": "Forbidden - insufficient permissions"}

                elif resp.status == 404:
                    logger.warning(f"ZeroNorth API: Resource not found: {endpoint}")
                    return {"error": "Resource not found", "status": 404}

                elif resp.status == 422:
                    logger.warning(f"ZeroNorth API: Validation error: {response_text}")
                    return {"error": "Validation error", "details": response_text}

                elif resp.status == 429:
                    logger.warning("ZeroNorth API: Rate limit exceeded")
                    return {"error": "Rate limit exceeded"}

                elif resp.status == 500:
                    logger.error("ZeroNorth API: Internal server error")
                    return {"error": "Internal server error"}

                else:
                    logger.error(
                        f"ZeroNorth API error: {resp.status} - {response_text[:200]}"
                    )
                    return {
                        "error": f"API error: {resp.status}",
                        "details": response_text[:500],
                    }

        except aiohttp.ClientError as e:
            logger.error(f"ZeroNorth API connection error: {e}")
            return {"error": f"Connection error: {str(e)}"}

        except Exception as e:
            logger.exception(f"Unexpected error in ZeroNorth API call: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    # ========================================================================
    # Bunker Operations
    # ========================================================================

    async def get_bunker_prices(
        self,
        port: Optional[str] = None,
        port_code: Optional[str] = None,
        date: Optional[str] = None,
        vessel_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get bunker prices by port.

        Args:
            port: Port name
            port_code: Port code (e.g., SGSIN, USHOU)
            date: Date for prices (ISO format), defaults to today
            vessel_type: Vessel type filter

        Returns:
            Bunker prices for the port
        """
        params = {}

        if port:
            params["port"] = port
        if port_code:
            params["portCode"] = port_code
        if date:
            params["date"] = date
        if vessel_type:
            params["vesselType"] = vessel_type

        logger.info(f"Fetching bunker prices: {params}")
        result = await self._request("GET", "/bunkers", params=params)

        if "error" in result and result.get("status") == 404:
            return {"bunkers": [], "port": port or port_code}

        return result

    async def get_bunker_prices_bulk(
        self, ports: List[str], date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get bunker prices for multiple ports.

        Args:
            ports: List of port names or codes
            date: Date for prices (ISO format)

        Returns:
            Bunker prices for all requested ports
        """
        params = {"ports": ",".join(ports)}

        if date:
            params["date"] = date

        logger.info(f"Fetching bulk bunker prices for {len(ports)} ports")
        return await self._request("GET", "/bunkers/bulk", params=params)

    async def get_historical_bunker_prices(
        self,
        port_code: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Get historical bunker prices for a port.

        Args:
            port_code: Port code
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            Historical bunker price data
        """
        params = {
            "portCode": port_code,
            "startDate": start_date,
            "endDate": end_date,
        }

        logger.info(f"Fetching historical bunker prices: {params}")
        return await self._request("GET", "/bunkers/history", params=params)

    # ========================================================================
    # Voyage Optimization
    # ========================================================================

    async def optimize_voyage(
        self,
        from_port: str,
        to_port: str,
        vessel_type: str,
        vessel_dwt: Optional[float] = None,
        cargo_quantity: Optional[float] = None,
        departure_date: Optional[str] = None,
        speed_min: Optional[float] = None,
        speed_max: Optional[float] = None,
        bunkers_onboard: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize voyage route for fuel efficiency.

        Args:
            from_port: Origin port
            to_port: Destination port
            vessel_type: Vessel type (VLCC, SUEZMAX, AFRAMAX, PANAMAX, HANDYSIZE)
            vessel_dwt: Vessel DWT
            cargo_quantity: Cargo quantity in MT
            departure_date: Departure date (ISO format)
            speed_min: Minimum speed (knots)
            speed_max: Maximum speed (knots)
            bunkers_onboard: Current bunker quantities by grade

        Returns:
            Optimized route with fuel consumption and emissions
        """
        payload = {
            "from": from_port,
            "to": to_port,
            "vesselType": vessel_type,
        }

        if vessel_dwt:
            payload["vesselDwt"] = vessel_dwt
        if cargo_quantity:
            payload["cargoQuantity"] = cargo_quantity
        if departure_date:
            payload["departureDate"] = departure_date
        if speed_min:
            payload["speedMin"] = speed_min
        if speed_max:
            payload["speedMax"] = speed_max
        if bunkers_onboard:
            payload["bunkersOnboard"] = bunkers_onboard

        logger.info(f"Optimizing voyage: {from_port} -> {to_port} ({vessel_type})")
        result = await self._request("POST", "/voyage/optimize", json_data=payload)

        return result

    async def get_voyage_plan(self, voyage_id: str) -> Dict[str, Any]:
        """
        Get detailed voyage plan.

        Args:
            voyage_id: Voyage plan ID

        Returns:
            Detailed voyage plan with waypoints
        """
        logger.info(f"Fetching voyage plan: {voyage_id}")
        return await self._request("GET", f"/voyage/{voyage_id}")

    async def create_voyage_plan(
        self,
        from_port: str,
        to_port: str,
        vessel_imo: str,
        departure_date: str,
        arrival_date: str,
    ) -> Dict[str, Any]:
        """
        Create a voyage:
            from_port plan.

        Args: Origin port
            to_port: Destination port
            vessel_imo: Vessel IMO
            departure_date: Departure date
            arrival_date: Arrival date

        Returns:
            Created voyage plan
        """
        payload = {
            "from": from_port,
            "to": to_port,
            "vesselImo": vessel_imo,
            "departureDate": departure_date,
            "arrivalDate": arrival_date,
        }

        logger.info(f"Creating voyage plan: {from_port} -> {to_port}")
        return await self._request("POST", "/voyage", json_data=payload)

    # ========================================================================
    # Emissions Calculations
    # ========================================================================

    async def calculate_emissions(
        self,
        vessel_type: str,
        distance_nm: Optional[float] = None,
        fuel_type: str = "VLSFO",
        fuel_consumption: Optional[float] = None,
        cargo_quantity: Optional[float] = None,
        voyage_days: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate CO2 and other emissions.

        Args:
            vessel_type: Vessel type
            distance_nm: Distance in nautical miles
            fuel_type: Fuel type (MGO, VLSFO, HFO, LNG, ULSFO)
            fuel_consumption: Fuel consumption in MT
            cargo_quantity: Cargo quantity in MT
            voyage_days: Voyage duration in days

        Returns:
            Emissions calculations
        """
        payload = {
            "vesselType": vessel_type,
            "fuelType": fuel_type,
        }

        if distance_nm:
            payload["distanceNm"] = distance_nm
        if fuel_consumption:
            payload["fuelConsumption"] = fuel_consumption
        if cargo_quantity:
            payload["cargoQuantity"] = cargo_quantity
        if voyage_days:
            payload["voyageDays"] = voyage_days

        logger.info(f"Calculating emissions for vessel type: {vessel_type}")
        result = await self._request("POST", "/emissions", json_data=payload)

        return result

    async def get_vessel_emissions(
        self,
        vessel_imo: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Get emissions data for a vessel over time.

        Args:
            vessel_imo: Vessel IMO
            start_date: Start date
            end_date: End date

        Returns:
            Vessel emissions history
        """
        params = {
            "vesselImo": vessel_imo,
            "startDate": start_date,
            "endDate": end_date,
        }

        logger.info(f"Fetching vessel emissions: {vessel_imo}")
        return await self._request("GET", "/emissions/vessel", params=params)

    async def calculate_cii(
        self,
        vessel_imo: str,
        vessel_type: str,
        dwt: float,
        annual_distance_nm: float,
        annual_fuel_consumption: float,
        fuel_type: str = "VLSFO",
    ) -> Dict[str, Any]:
        """
        Calculate CII (Carbon Intensity Indicator) rating.

        Args:
            vessel_imo: Vessel IMO
            vessel_type: Vessel type
            dwt: Deadweight tonnage
            annual_distance_nm: Annual distance in NM
            annual_fuel_consumption: Annual fuel consumption in MT
            fuel_type: Fuel type

        Returns:
            CII rating and score
        """
        payload = {
            "vesselImo": vessel_imo,
            "vesselType": vessel_type,
            "dwt": dwt,
            "annualDistanceNm": annual_distance_nm,
            "annualFuelConsumption": annual_fuel_consumption,
            "fuelType": fuel_type,
        }

        logger.info(f"Calculating CII for vessel: {vessel_imo}")
        return await self._request("POST", "/emissions/cii", json_data=payload)

    # ========================================================================
    # Vessel Operations
    # ========================================================================

    async def get_vessel_performance(
        self,
        vessel_imo: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Get vessel performance metrics.

        Args:
            vessel_imo: Vessel IMO
            start_date: Start date
            end_date: End date

        Returns:
            Vessel performance data
        """
        params = {
            "vesselImo": vessel_imo,
            "startDate": start_date,
            "endDate": end_date,
        }

        logger.info(f"Fetching vessel performance: {vessel_imo}")
        return await self._request("GET", "/vessel/performance", params=params)


# Global client instance
_zeronorth_client: Optional[ZeroNorthClient] = None


async def get_zeronorth_client() -> ZeroNorthClient:
    """Get or create ZeroNorth client singleton"""
    global _zeronorth_client
    if _zeronorth_client is None:
        _zeronorth_client = ZeroNorthClient()
    return _zeronorth_client


# ============================================================================
# Plugin Hooks
# ============================================================================


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """
    Enrich fixture with ZeroNorth bunker and optimization data.

    Hook: on_fixture_enrich
    """
    client = await get_zeronorth_client()

    if not client.api_key:
        return {"error": "ZERONORTH_API_KEY not configured"}

    enrichment = {}

    try:
        # Get bunker prices for load port
        bunker_result = await client.get_bunker_prices(
            port=fixture.port_loading,
        )

        if "error" not in bunker_result:
            enrichment["bunker_prices"] = bunker_result

        # Get voyage optimization
        vessel_type_map = {
            "crude": "VLCC",
            "product": "LR2",
            "chemical": "CHEMICAL",
            "lng": "LNG",
            "lpg": "LPG",
        }

        vessel_type = vessel_type_map.get(
            fixture.cargo_type.lower() if fixture.cargo_type else "", "VLCC"
        )

        opt_result = await client.optimize_voyage(
            from_port=fixture.port_loading,
            to_port=fixture.port_discharge,
            vessel_type=vessel_type,
            cargo_quantity=fixture.cargo_quantity if hasattr(fixture, "cargo_quantity") else None,
        )

        if "error" not in opt_result:
            enrichment["optimization"] = {
                "distance_nm": opt_result.get("distanceNm") or opt_result.get("distance_nm"),
                "distance_km": opt_result.get("distanceKm"),
                "transit_time_days": opt_result.get("transitTimeDays") or opt_result.get("transit_time_days"),
                "bunker_estimate": opt_result.get("bunkerConsumption") or opt_result.get("bunker_estimate"),
                "co2_estimate": opt_result.get("co2Emissions") or opt_result.get("co2_estimate"),
                "bunker_cost": opt_result.get("bunkerCost") or opt_result.get("bunker_cost"),
                "optimal_speed": opt_result.get("optimalSpeed"),
            }

        # Calculate emissions
        if "distance_nm" in enrichment.get("optimization", {}):
            dist = enrichment["optimization"]["distance_nm"]
            emit_result = await client.calculate_emissions(
                vessel_type=vessel_type,
                distance_nm=dist,
                fuel_type="VLSFO",
            )

            if "error" not in emit_result:
                enrichment["emissions"] = {
                    "co2_tonnes": emit_result.get("co2Tonnes") or emit_result.get("co2_tonnes"),
                    "co2_per_tonne_mile": emit_result.get("co2PerTonneMile"),
                    "cii": emit_result.get("cii"),
                    "cii_rating": emit_result.get("ciiRating"),
                }

        # Update fixture enrichment data
        if hasattr(fixture, "enrichment_data") and fixture.enrichment_data:
            fixture.enrichment_data["zeronorth"] = enrichment
        elif hasattr(fixture, "enrichment_data"):
            fixture.enrichment_data = {"zeronorth": enrichment}

        return enrichment

    except Exception as e:
        logger.exception(f"Error enriching fixture with ZeroNorth: {e}")
        return {"error": str(e)}


async def on_rank_adjust(fixture, base_score: float) -> float:
    """
    Adjust Wake Score based on bunker optimization.

    Hook: on_rank
    """
    if not hasattr(fixture, "enrichment_data") or not fixture.enrichment_data:
        return base_score

    zeronorth = fixture.enrichment_data.get("zeronorth", {})
    optimization = zeronorth.get("optimization", {})

    bunker_estimate = optimization.get("bunker_estimate", 0)

    if bunker_estimate and isinstance(bunker_estimate, dict):
        # Handle dict format (multiple fuel types)
        total_bunker = sum(bunker_estimate.values()) if bunker_estimate else 0
    else:
        total_bunker = float(bunker_estimate) if bunker_estimate else 0

    if total_bunker < 500:
        return base_score + 5
    elif total_bunker > 1500:
        return base_score - 5

    return base_score


# API endpoint helpers

async def get_bunker_prices(
    port: Optional[str] = None,
    port_code: Optional[str] = None,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get bunker prices from ZeroNorth."""
    client = await get_zeronorth_client()
    return await client.get_bunker_prices(port=port, port_code=port_code, date=date)


async def optimize_voyage(
    from_port: str,
    to_port: str,
    vessel_type: str,
    vessel_dwt: Optional[float] = None,
    cargo_quantity: Optional[float] = None,
    departure_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Optimize voyage from ZeroNorth."""
    client = await get_zeronorth_client()
    return await client.optimize_voyage(
        from_port=from_port,
        to_port=to_port,
        vessel_type=vessel_type,
        vessel_dwt=vessel_dwt,
        cargo_quantity=cargo_quantity,
        departure_date=departure_date,
    )


async def calculate_emissions(
    vessel_type: str,
    distance_nm: Optional[float] = None,
    fuel_type: str = "VLSFO",
    fuel_consumption: Optional[float] = None,
    cargo_quantity: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate emissions from ZeroNorth."""
    client = await get_zeronorth_client()
    return await client.calculate_emissions(
        vessel_type=vessel_type,
        distance_nm=distance_nm,
        fuel_type=fuel_type,
        fuel_consumption=fuel_consumption,
        cargo_quantity=cargo_quantity,
    )


# Plugin hooks registry
hooks = {
    "on_fixture_enrich": on_fixture_enrich,
    "on_rank": on_rank_adjust,
}


# Export models and client for external use
__all__ = [
    "ZeroNorthBunkerPrice",
    "ZeroNorthVoyageOptimizationRequest",
    "ZeroNorthVoyageOptimizationResponse",
    "ZeroNorthEmissionsRequest",
    "ZeroNorthEmissionsResponse",
    "ZeroNorthVoyageStatus",
    "ZeroNorthClient",
    "get_zeronorth_client",
    "get_bunker_prices",
    "optimize_voyage",
    "calculate_emissions",
    "hooks",
]
