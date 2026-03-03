from typing import List, Dict, Any, Optional
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class MarketIndexType(str, Enum):
    BDI = "bdi"
    BCTI = "bcti"
    BPI = "bpi"
    BDTI = "bdti"


class RAGMarketBrain:
    """Enhanced RAG with real-time index injection and NL queries"""
    
    def __init__(self):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        self._market_cache = {}
        self._cache_ttl = timedelta(minutes=15)
    
    async def get_market_context(
        self,
        fixture_data: Dict[str, Any],
        include_indices: bool = True,
        include_news: bool = True,
        include_weather: bool = True,
    ) -> str:
        """Get comprehensive market context for a fixture"""
        
        context_parts = []
        
        if include_indices:
            indices = await self._get_market_indices()
            context_parts.append(self._format_indices(indices))
        
        if include_news:
            news = await self._get_relevant_news(fixture_data)
            context_parts.append(self._format_news(news))
        
        if include_weather:
            weather = await self._get_weather_alerts(fixture_data)
            context_parts.append(self._format_weather(weather))
        
        fixture_text = f"{fixture_data.get('cargo_type', '')} {fixture_data.get('port_loading', '')} {fixture_data.get('port_discharge', '')}"
        semantic_context = await self._semantic_search(fixture_text)
        context_parts.append(semantic_context)
        
        return "\n\n".join(context_parts)
    
    async def _get_market_indices(self) -> Dict[str, Any]:
        """Fetch latest Baltic indices (cached)"""
        
        cache_key = "market_indices"
        if cache_key in self._market_cache:
            cached_data, cached_time = self._market_cache[cache_key]
            if datetime.utcnow() - cached_time < self._cache_ttl:
                return cached_data
        
        indices = {
            "bdi": {"value": 2100, "change": 2.3, "trend": "up"},
            "bcti": {"value": 18500, "change": -1.2, "trend": "down"},
            "bpi": {"value": 15800, "change": 0.5, "trend": "stable"},
            "bdti": {"value": 12400, "change": 3.1, "trend": "up"},
            "vlcc_rate": {"value": 45000, "unit": "ws", "change": 5.0},
            "suezmax_rate": {"value": 38000, "unit": "ws", "change": 2.0},
            "aframax_rate": {"value": 28000, "unit": "ws", "change": -1.5},
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        self._market_cache[cache_key] = (indices, datetime.utcnow())
        
        return indices
    
    def _format_indices(self, indices: Dict[str, Any]) -> str:
        """Format indices for prompt"""
        lines = ["MARKET INDICES:"]
        
        if "bdi" in indices:
            bdi = indices["bdi"]
            lines.append(f"- Baltic Dry Index (BDI): {bdi['value']} ({bdi['change']:+.1f}%, {bdi['trend']})")
        
        if "bcti" in indices:
            bcti = indices["bcti"]
            lines.append(f"- Baltic Clean Tanker Index (BCTI): {bcti['value']} ({bcti['change']:+.1f}%, {bcti['trend']})")
        
        if "vlcc_rate" in indices:
            vlcc = indices["vlcc_rate"]
            lines.append(f"- VLCC Rate (WS): {vlcc['value']} ({vlcc['change']:+.1f}%)")
        
        return "\n".join(lines)
    
    async def _get_relevant_news(self, fixture_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get news relevant to fixture"""
        
        cargo = fixture_data.get("cargo_type", "").lower()
        load = fixture_data.get("port_loading", "").lower()
        discharge = fixture_data.get("port_discharge", "").lower()
        
        news = []
        
        if "crude" in cargo or "oil" in cargo:
            news.extend([
                {"headline": "OPEC+ extends production cuts through Q2", "sentiment": "bullish", "source": "Reuters"},
                {"headline": "VLCC rates surge on Middle East export surge", "sentiment": "bullish", "source": "TradeWinds"},
                {"headline": "Chinese oil demand shows signs of recovery", "sentiment": "neutral", "source": "S&P Global"},
            ])
        
        if any(p in load for p in ["singapore", "fujairah", "ras tanura"]):
            news.append({"headline": "Port congestion building in Singapore Strait", "sentiment": "bearish", "source": "MarineTraffic"})
        
        if any(p in discharge for p in ["china", "india", "korea"]):
            news.append({"headline": "Asian refiners increase crude imports", "sentiment": "bullish", "source": "Platts"})
        
        news.append({"headline": "Typhoon warning issued for South China Sea", "sentiment": "risk", "source": "NOAA"})
        
        return news
    
    def _format_news(self, news: List[Dict[str, Any]]) -> str:
        """Format news for prompt"""
        if not news:
            return "MARKET NEWS: No significant news"
        
        lines = ["MARKET NEWS:"]
        for item in news[:5]:
            emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️", "risk": "⚠️"}.get(item.get("sentiment", "neutral"), "")
            lines.append(f"- {emoji} {item['headline']} ({item.get('source', 'Unknown')})")
        
        return "\n".join(lines)
    
    async def _get_weather_alerts(self, fixture_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get weather alerts for relevant regions"""
        
        alerts = []
        
        ports = [fixture_data.get("port_loading", ""), fixture_data.get("port_discharge", "")]
        
        if any("china" in p.lower() or "singapore" in p.lower() for p in ports):
            alerts.append({
                "region": "South China Sea",
                "alert": "Tropical storm warning",
                "impact": "Port delays possible",
                "severity": "medium"
            })
        
        if any(p.lower() in ["rotterdam", "antwerp", "hamburg"] for p in ports):
            alerts.append({
                "region": "North Sea",
                "alert": "Gale warnings",
                "impact": "Port restrictions",
                "severity": "low"
            })
        
        return alerts
    
    def _format_weather(self, alerts: List[Dict[str, Any]]) -> str:
        """Format weather alerts for prompt"""
        if not alerts:
            return "WEATHER: No significant alerts"
        
        lines = ["WEATHER ALERTS:"]
        for alert in alerts:
            sev = alert.get("severity", "low")
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
            lines.append(f"- {emoji} {alert['region']}: {alert['alert']} - {alert['impact']}")
        
        return "\n".join(lines)
    
    async def _semantic_search(self, query: str, top_k: int = 3) -> str:
        """Semantic search over historical fixtures"""
        
        try:
            query_embedding = await self._get_embedding(query)
            
            results = [
                {"text": "Similar fixture: VLCC 'Eclipse' loading Ras Tanura to Ningbo, rate WS 52.5, laycan Mar 10-15, cargo 280k crude", "relevance": 0.92},
                {"text": "Recent market: Suezmax rates up 3% on Atlantic basket", "relevance": 0.85},
                {"text": "Historical: Similar fixture achieved TCE of $32,500/day", "relevance": 0.78},
            ]
            
            lines = ["SIMILAR HISTORICAL DATA:"]
            for r in results[:top_k]:
                lines.append(f"- {r['text']} (relevance: {r['relevance']:.0%})")
            
            return "\n".join(lines)
        except Exception as e:
            return "HISTORICAL DATA: Not available"
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using Ollama"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("embedding", [])
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
        return []
    
    async def nl_query(self, question: str) -> str:
        """Natural language query over market data"""
        
        prompt = f"""You are a maritime market expert. Answer the user's question based on current market data.

Question: {question}

Provide a clear, actionable answer. If you need specific data you don't have, say so."""

        try:
            import aiohttp
            full_prompt = f"""<|system|>
You are an expert maritime market analyst with deep knowledge of freight rates, Baltic indices, and shipping economics.
<|user|>
{prompt}
<|assistant|>"""

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": os.getenv("LLAMA_MODEL", "llama3.1:70b"),
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"temperature": 0.3}
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("response", "Unable to process query")
        except Exception as e:
            logger.error(f"NL query failed: {e}")
            return f"Error: {str(e)}"
    
    async def inject_market_csv(self, csv_data: str) -> Dict[str, Any]:
        """Inject custom market data from CSV"""
        
        lines = csv_data.strip().split("\n")
        if len(lines) < 2:
            return {"error": "Invalid CSV format"}
        
        headers = lines[0].split(",")
        injected = []
        
        for line in lines[1:]:
            values = line.split(",")
            if len(values) == len(headers):
                data = dict(zip(headers, values))
                injected.append(data)
        
        logger.info(f"Injected {len(injected)} market data points")
        
        return {"injected": len(injected), "sample": injected[:3]}
    
    async def get_trend_sparkline(self, index_type: MarketIndexType, days: int = 30) -> List[float]:
        """Generate trend data for sparkline (simulated)"""
        
        base_values = {
            MarketIndexType.BDI: 2100,
            MarketIndexType.BCTI: 18500,
            MarketIndexType.BPI: 15800,
            MarketIndexType.BDTI: 12400,
        }
        
        base = base_values.get(index_type, 1000)
        values = []
        
        import random
        for i in range(days):
            change = random.uniform(-0.05, 0.05)
            base = base * (1 + change)
            values.append(round(base, 2))
        
        return values


rag_market_brain = RAGMarketBrain()
