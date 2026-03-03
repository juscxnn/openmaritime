"""
Signal Ocean Plugin - Market Data

Full async implementation for Signal Ocean API integration.
Provides vessel details, market voyages, and freight rates.

API Endpoints:
- GET /vessels/{imo} - Vessel details
- GET /voyages - Market voyages by cargo/route
- GET /freight-rates - Current freight rates

Environment Variables:
- SIGNAL_OCEAN_API_KEY: Signal Ocean API key
- SIGNAL_OCEAN_API_URL: API base URL (default: https://api.signalocean.com)
- SIGNAL_OCEAN_TIMEOUT: Request timeout in seconds (default: 30)
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

class SignalOceanVesselResponse(BaseModel):
    """Response model for vessel details"""
    imo: int
    vessel_name: Optional[str] = None
    vessel_type: Optional[str] = None
    vessel_type_id: Optional[int] = None
    year_built: Optional[int] = None
    dwt: Optional[float] = None
    flag: Optional[str] = None
    flag_code: Optional[str] = None
    status: Optional[str] = None
    commercial_operator: Optional[str] = None
    technical_manager: Optional[str] = None
    eta: Optional[str] = None
    destination: Optional[str] = None
    last_port: Optional[str] = None
    next_port: Optional[str] = None


class SignalOceanVoyage(BaseModel):
    """Market voyage data"""
    voyage_id: Optional[int] = None
    load_port: Optional[str] = None
    load_area: Optional[str] = None
    discharge_port: Optional[str] = None
    discharge_area: Optional[str] = None
    cargo_type: Optional[str] = None
    cargo_type_id: Optional[int] = None
    quantity: Optional[float] = None
    rate: Optional[float] = None
    rate_currency: Optional[str] = None
    rate_unit: Optional[str] = None
    laycan_start: Optional[str] = None
    laycan_end: Optional[str] = None
    charterer: Optional[str] = None
    vessel_name: Optional[str] = None
    vessel_imo: Optional[int] = None
    vessel_type: Optional[str] = None
    status: Optional[str] = None


class SignalOceanFreightRate(BaseModel):
    """Freight rate data"""
    route_id: Optional[int] = None
    load_port: Optional[str] = None
    load_area: Optional[str] = None
    discharge_port: Optional[str] = None
    discharge_area: Optional[str] = None
    vessel_type: Optional[str] = None
    vessel_type_id: Optional[int] = None
    rate: Optional[float] = None
    rate_currency: Optional[str] = None
    rate_unit: Optional[str] = None
    ws_points: Optional[float] = None
    bunker_price: Optional[float] = None
    time_created: Optional[str] = None


class SignalOceanVoyagesFilter(BaseModel):
    """Filter parameters for voyages"""
    load_port: Optional[str] = Field(None, description="Load port name or code")
    discharge_port: Optional[str] = Field(None, description="Discharge port name or code")
    cargo_type: Optional[str] = Field(None, description="Cargo type")
    vessel_type: Optional[str] = Field(None, description="Vessel type")
    charterer: Optional[str] = Field(None, description="Charterer name")
    laycan_start: Optional[str] = Field(None, description="Laycan start date")
    laycan_end: Optional[str] = Field(None, description="Laycan end date")
    status: Optional[str] = Field(None, description="Voyage status")


class SignalOceanFreightRatesFilter(BaseModel):
    """Filter parameters for freight rates"""
    load_port: Optional[str] = Field(None, description="Load port or area")
    discharge_port: Optional[str] = Field(None, description="Discharge port or area")
    vessel_type: Optional[str] = Field(None, description="Vessel type")
    cargo_type: Optional[str] = Field(None, description="Cargo type")


# ============================================================================
# Signal Ocean API Client
# ============================================================================

class SignalOceanClient:
    """Async client for Signal Ocean API"""

    def __init__(self):
        self.api_key = os.getenv("SIGNAL_OCEAN_API_KEY")
        self.base_url = os.getenv(
            "SIGNAL_OCEAN_API_URL", "https://api.signalocean.com/v1"
        )
        self.timeout = int(os.getenv("SIGNAL_OCEAN_TIMEOUT", "30"))
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Authorization": f"ApiKey {self.api_key}",
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
            logger.error("SIGNAL_OCEAN_API_KEY not configured")
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

                elif resp.status == 401:
                    logger.error("Signal Ocean API: Unauthorized - check API key")
                    return {"error": "Unauthorized - check API key"}

                elif resp.status == 403:
                    logger.error("Signal Ocean API: Forbidden - insufficient permissions")
                    return {"error": "Forbidden - insufficient permissions"}

                elif resp.status == 404:
                    logger.warning(f"Signal Ocean API: Resource not found: {endpoint}")
                    return {"error": "Resource not found", "status": 404}

                elif resp.status == 429:
                    logger.warning("Signal Ocean API: Rate limit exceeded")
                    return {"error": "Rate limit exceeded"}

                elif resp.status == 500:
                    logger.error("Signal Ocean API: Internal server error")
                    return {"error": "Internal server error"}

                else:
                    logger.error(
                        f"Signal Ocean API error: {resp.status} - {response_text[:200]}"
                    )
                    return {
                        "error": f"API error: {resp.status}",
                        "details": response_text[:500],
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Signal Ocean API connection error: {e}")
            return {"error": f"Connection error: {str(e)}"}

        except Exception as e:
            logger.exception(f"Unexpected error in Signal Ocean API call: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    # ========================================================================
    # Vessel Operations
    # ========================================================================

    async def get_vessel(self, imo: int) -> Dict[str, Any]:
        """
        Get vessel details by IMO number.

        Args:
            imo: Vessel IMO number

        Returns:
            Vessel details including current position
        """
        logger.info(f"Fetching vessel details for IMO: {imo}")

        if not isinstance(imo, int):
            try:
                imo = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        result = await self._request("GET", f"/vessels/{imo}")

        if "error" in result and result.get("status") == 404:
            return {"error": "Vessel not found"}

        return result

    async def get_vessel_position(self, imo: int) -> Dict[str, Any]:
        """
        Get current vessel position and AIS data.

        Args:
            imo: Vessel IMO number

        Returns:
            Current position, speed, heading, ETA
        """
        logger.info(f"Fetching vessel position for IMO: {imo}")

        if not isinstance(imo, int):
            try:
                imo = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        return await self._request("GET", f"/vessels/{imo}/position")

    async def get_vessel_history(self, imo: int, days: int = 30) -> Dict[str, Any]:
        """
        Get vessel historical data.

        Args:
            imo: Vessel IMO number
            days: Number of days of history

        Returns:
            Historical port calls and positions
        """
        logger.info(f"Fetching vessel history for IMO: {imo}, days: {days}")

        if not isinstance(imo, int):
            try:
                IMO = int(imo)
            except (ValueError, TypeError):
                return {"error": "Invalid IMO number"}

        params = {"days": days}
        return await self._request("GET", f"/vessels/{imo}/history", params=params)

    async def search_vessels(
        self,
        name: Optional[str] = None,
        vessel_type: Optional[str] = None,
        dwt_min: Optional[float] = None,
        dwt_max: Optional[float] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Search vessels by various criteria.

        Args:
            name: Vessel name (partial match)
            vessel_type: Vessel type
            dwt_min: Minimum DWT
            dwt_max: Maximum DWT
            limit: Maximum results

        Returns:
            List of matching vessels
        """
        params = {"limit": limit}

        if name:
            params["name"] = name
        if vessel_type:
            params["vesselType"] = vessel_type
        if dwt_min:
            params["dwtMin"] = dwt_min
        if dwt_max:
            params["dwtMax"] = dwt_max

        logger.info(f"Searching vessels with params: {params}")
        return await self._request("GET", "/vessels", params=params)

    # ========================================================================
    # Market Voyages
    # ========================================================================

    async def get_market_voyages(
        self,
        load_port: Optional[str] = None,
        discharge_port: Optional[str] = None,
        cargo_type: Optional[str] = None,
        vessel_type: Optional[str] = None,
        charterer: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get market voyages by cargo type and route.

        Args:
            load_port: Load port name or code
            discharge_port: Discharge port name or code
            cargo_type: Cargo type (e.g., CRUDE, PRODUCTS, DIRTY)
            vessel_type: Vessel type
            charterer: Charterer name
            status: Voyage status (OPEN, FIXED, COMPLETED)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of market voyages
        """
        params = {
            "limit": limit,
            "offset": offset,
        }

        if load_port:
            params["loadPort"] = load_port
        if discharge_port:
            params["dischargePort"] = discharge_port
        if cargo_type:
            params["cargoType"] = cargo_type
        if vessel_type:
            params["vesselType"] = vessel_type
        if charterer:
            params["charterer"] = charterer
        if status:
            params["status"] = status

        logger.info(f"Fetching market voyages: {params}")
        result = await self._request("GET", "/voyages", params=params)

        if "error" in result and result.get("status") == 404:
            return {"voyages": [], "total": 0}

        return result

    async def get_voyage_details(self, voyage_id: int) -> Dict[str, Any]:
        """
        Get detailed voyage information.

        Args:
            voyage_id: Voyage ID

        Returns:
            Detailed voyage data
        """
        logger.info(f"Fetching voyage details: {voyage_id}")
        return await self._request("GET", f"/voyages/{voyage_id}")

    # ========================================================================
    # Freight Rates
    # ========================================================================

    async def get_freight_rates(
        self,
        load_port: Optional[str] = None,
        discharge_port: Optional[str] = None,
        vessel_type: Optional[str] = None,
        cargo_type: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get current freight rates for routes.

        Args:
            load_port: Load port or area
            discharge_port: Discharge port or area
            vessel_type: Vessel type (VLCC, SUEZMAX, AFRAMAX, PANAMAX)
            cargo_type: Cargo type
            limit: Maximum results

        Returns:
            List of current freight rates
        """
        params = {"limit": limit}

        if load_port:
            params["loadPort"] = load_port
        if discharge_port:
            params["dischargePort"] = discharge_port
        if vessel_type:
            params["vesselType"] = vessel_type
        if cargo_type:
            params["cargoType"] = cargo_type

        logger.info(f"Fetching freight rates: {params}")
        result = await self._request("GET", "/freight-rates", params=params)

        if "error" in result and result.get("status") == 404:
            return {"freight_rates": [], "total": 0}

        return result

    async def get_historical_rates(
        self,
        load_port: str,
        discharge_port: str,
        vessel_type: str,
        days: int = 90,
    ) -> Dict[str, Any]:
        """
        Get historical freight rates.

        Args:
            load_port: Load port or area
            discharge_port: Discharge port or area
            vessel_type: Vessel type
            days: Number of days of history

        Returns:
            Historical rate data
        """
        params = {
            "loadPort": load_port,
            "dischargePort": discharge_port,
            "vesselType": vessel_type,
            "days": days,
        }

        logger.info(f"Fetching historical rates: {params}")
        return await self._request("GET", "/freight-rates/history", params=params)

    # ========================================================================
    # Port Operations
    # ========================================================================

    async def get_port_data(self, port_code: str) -> Dict[str, Any]:
        """
        Get port information and congestion data.

        Args:
            port_code: Port code or name

        Returns:
            Port details and congestion metrics
        """
        logger.info(f"Fetching port data: {port_code}")
        return await self._request("GET", f"/ports/{port_code}")

    async def get_port_congestion(self, port_code: str) -> Dict[str, Any]:
        """
        Get port congestion metrics.

        Args:
            port_code: Port code or name

        Returns:
            Congestion data
        """
        logger.info(f"Fetching port congestion: {port_code}")
        return await self._request("GET", f"/ports/{port_code}/congestion")


# Global client instance
_signalocean_client: Optional[SignalOceanClient] = None


async def get_signalocean_client() -> SignalOceanClient:
    """Get or create Signal Ocean client singleton"""
    global _signalocean_client
    if _signalocean_client is None:
        _signalocean_client = SignalOceanClient()
    return _signalocean_client


# ============================================================================
# Plugin Hooks
# ============================================================================


async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    """
    Enrich fixture with Signal Ocean market data.

    Hook: on_fixture_enrich
    """
    client = await get_signalocean_client()

    if not client.api_key:
        return {"error": "SIGNAL_OCEAN_API_KEY not configured"}

    enrichment = {}

    try:
        # Get vessel details if IMO available
        if fixture.imo_number:
            try:
                imo = int(fixture.imo_number)
                vessel_result = await client.get_vessel(imo)

                if "error" not in vessel_result:
                    enrichment["vessel"] = {
                        "imo": vessel_result.get("imo"),
                        "name": vessel_result.get("vesselName"),
                        "type": vessel_result.get("vesselType"),
                        "year_built": vessel_result.get("yearBuilt"),
                        "dwt": vessel_result.get("dwt"),
                        "flag": vessel_result.get("flag"),
                        "status": vessel_result.get("status"),
                        "destination": vessel_result.get("destination"),
                        "eta": vessel_result.get("eta"),
                    }
            except (ValueError, TypeError):
                pass

        # Get market voyages for the fixture's route
        voyages_result = await client.get_market_voyages(
            load_port=fixture.port_loading,
            discharge_port=fixture.port_discharge,
            cargo_type=fixture.cargo_type,
            limit=10,
        )

        if "voyages" in voyages_result:
            enrichment["market_voyages"] = voyages_result["voyages"]

        # Get freight rates for the route
        rates_result = await client.get_freight_rates(
            load_port=fixture.port_loading,
            discharge_port=fixture.port_discharge,
            limit=5,
        )

        if "freightRates" in rates_result or "rates" in rates_result:
            enrichment["freight_rates"] = rates_result.get(
                "freightRates", rates_result.get("rates", [])
            )

        # Update fixture enrichment data
        if hasattr(fixture, "enrichment_data") and fixture.enrichment_data:
            fixture.enrichment_data["signalocean"] = enrichment
        elif hasattr(fixture, "enrichment_data"):
            fixture.enrichment_data = {"signalocean": enrichment}

        return enrichment

    except Exception as e:
        logger.exception(f"Error enriching fixture with Signal Ocean: {e}")
        return {"error": str(e)}


# API endpoint helpers

async def get_vessel_details(imo: int) -> Dict[str, Any]:
    """Get vessel details from Signal Ocean."""
    client = await get_signalocean_client()
    return await client.get_vessel(imo)


async def get_market_voyages(
    load_port: Optional[str] = None,
    discharge_port: Optional[str] = None,
    cargo_type: Optional[str] = None,
    vessel_type: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Get market voyages from Signal Ocean."""
    client = await get_signalocean_client()
    return await client.get_market_voyages(
        load_port=load_port,
        discharge_port=discharge_port,
        cargo_type=cargo_type,
        vessel_type=vessel_type,
        limit=limit,
    )


async def get_freight_rates(
    load_port: Optional[str] = None,
    discharge_port: Optional[str] = None,
    vessel_type: Optional[str] = None,
    cargo_type: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Get freight rates from Signal Ocean."""
    client = await get_signalocean_client()
    return await client.get_freight_rates(
        load_port=load_port,
        discharge_port=discharge_port,
        vessel_type=vessel_type,
        cargo_type=cargo_type,
        limit=limit,
    )


# Plugin hooks registry
hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}


# Export models and client for external use
__all__ = [
    "SignalOceanVesselResponse",
    "SignalOceanVoyage",
    "SignalOceanFreightRate",
    "SignalOceanClient",
    "get_signalocean_client",
    "get_vessel_details",
    "get_market_voyages",
    "get_freight_rates",
    "hooks",
]
