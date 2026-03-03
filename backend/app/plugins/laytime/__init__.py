from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json


class LaytimeEngine:
    """Built-in laytime/demurrage calculation engine"""
    
    def __init__(self):
        self.weather_api_key = None
    
    async def calculate_laytime(
        self,
        fixture_data: Dict[str, Any],
        nor_times: List[datetime],
        loading_rate: float,
        discharge_rate: float,
        weather_delays: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Calculate laytime based on NOR, rates, and delays"""
        
        total_cargo = fixture_data.get("cargo_quantity", 0)
        loading_time = total_cargo / loading_rate if loading_rate > 0 else 0
        discharge_time = total_cargo / discharge_rate if discharge_rate > 0 else 0
        
        total_laytime_hours = loading_time + discharge_time
        
        weather_delay_hours = 0
        if weather_delays:
            for delay in weather_delays:
                weather_delay_hours += delay.get("hours", 0)
        
        running_time = max(0, total_laytime_hours - weather_delay_hours)
        
        first_nor = min(nor_times) if nor_times else datetime.utcnow()
        estimated_completion = first_nor + timedelta(hours=running_time + weather_delay_hours)
        
        return {
            "total_laytime_hours": round(running_time, 2),
            "loading_hours": round(loading_time, 2),
            "discharge_hours": round(discharge_time, 2),
            "weather_delay_hours": round(weather_delay_hours, 2),
            "estimated_completion": estimated_completion.isoformat(),
            "turntime_hours": round(total_laytime_hours, 2),
        }
    
    async def calculate_demurrage(
        self,
        fixture_data: Dict[str, Any],
        actual_time_hours: float,
        laytime_hours: float,
        daily_rate: float = None,
        despatch_rate: float = None,
    ) -> Dict[str, Any]:
        """Calculate demurrage/despatch"""
        
        if daily_rate is None:
            daily_rate = fixture_data.get("demurrage_rate", 15000)
        if despatch_rate is None:
            despatch_rate = fixture_data.get("despatch_rate", 7500)
        
        excess_time = max(0, actual_time_hours - laytime_hours)
        demurrage_days = excess_time / 24
        demurrage_amount = demurrage_days * daily_rate
        
        saved_time = max(0, laytime_hours - actual_time_hours)
        despatch_days = saved_time / 24
        despatch_amount = despatch_days * despatch_rate
        
        return {
            "demurrage_days": round(demurrage_days, 2),
            "demurrage_amount": round(demurrage_amount, 2),
            "despatch_days": round(despatch_days, 2),
            "despatch_amount": round(despatch_amount, 2),
            "net_position": round(demurrage_amount - despatch_amount, 2),
            "excess_hours": round(excess_time, 2),
            "saved_hours": round(saved_time, 2),
        }
    
    async def parse_sof(self, sof_text: str) -> Dict[str, Any]:
        """Parse Statement of Facts from text"""
        
        events = []
        lines = sof_text.strip().split("\n")
        
        for line in lines:
            line = line.strip().lower()
            if "nor" in line or "notice of readiness" in line:
                events.append({"type": "NOR", "raw": line})
            elif "arrival" in line or "arr" in line:
                events.append({"type": "ARRIVAL", "raw": line})
            elif "commence" in line or "start" in line:
                events.append({"type": "COMMENCE", "raw": line})
            elif "complete" in line or "finish" in line:
                events.append({"type": "COMPLETE", "raw": line})
        
        return {
            "events": events,
            "event_count": len(events),
        }
    
    async def predict_demurrage_ml(self, fixture_data: Dict[str, Any]) -> Dict[str, Any]:
        """ML-based demurrage prediction (stub)"""
        
        base_prediction = {
            "predicted_demurrage_days": 1.5,
            "confidence": "medium",
            "model_version": "ml_v1",
            "factors": {
                "port_congestion": "moderate",
                "weather_risk": "low",
                "historical_performance": "average",
            },
        }
        
        return base_prediction


laytime_engine = LaytimeEngine()


async def on_laytime_calculate(fixture) -> Dict[str, Any]:
    """Hook to calculate laytime for fixture"""
    fixture_data = {
        "cargo_quantity": fixture.cargo_quantity,
        "cargo_type": fixture.cargo_type,
        "port_loading": fixture.port_loading,
        "port_discharge": fixture.port_discharge,
    }
    
    laytime = await laytime_engine.calculate_laytime(
        fixture_data,
        nor_times=[],
        loading_rate=10000,
        discharge_rate=10000,
    )
    
    if fixture.enrichment_data is None:
        fixture.enrichment_data = {}
    fixture.enrichment_data["laytime"] = laytime
    
    return laytime


hooks = {
    "on_laytime_calculate": on_laytime_calculate,
}
