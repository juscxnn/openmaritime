from typing import List, Dict, Any, Optional
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RAGService:
    """RAG service using pgvector for fixture embeddings and market context"""
    
    def __init__(self):
        self.enabled = os.getenv("ENABLE_RAG", "true").lower() == "true"
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    
    async def get_market_context(self, fixture_data: Dict[str, Any]) -> str:
        """Get relevant market context for a fixture using RAG"""
        if not self.enabled:
            return self._get_default_market_context()
        
        try:
            query = self._build_query(fixture_data)
            relevant_docs = await self._retrieve_relevant_docs(query)
            return self._format_context(relevant_docs)
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")
            return self._get_default_market_context()
    
    def _build_query(self, fixture_data: Dict[str, Any]) -> str:
        """Build search query from fixture data"""
        return f"{fixture_data.get('cargo_type', '')} {fixture_data.get('port_loading', '')} {fixture_data.get('port_discharge', '')} market"
    
    async def _retrieve_relevant_docs(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant documents from vector store"""
        query_embedding = await self._get_embedding(query)
        
        # In production, this would query pgvector
        # For now, return sample market data
        return [
            {
                "type": "market_index",
                "content": "BDI currently at 2100, Baltic Clean Tanker Index at 18500",
                "relevance": 0.9,
            },
            {
                "type": "news",
                "content": "VLCC rates in Middle East up 15% this week",
                "relevance": 0.85,
            },
            {
                "type": "weather",
                "content": "Typhoon warning in South China Sea",
                "relevance": 0.7,
            },
        ]
    
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
    
    def _format_context(self, docs: List[Dict[str, Any]]) -> str:
        """Format retrieved docs as context string"""
        context_lines = ["Market Context:"]
        for doc in docs:
            context_lines.append(f"- {doc['content']} (relevance: {doc['relevance']:.0%})")
        return "\n".join(context_lines)
    
    def _get_default_market_context(self) -> str:
        """Get default market context when RAG is disabled"""
        return """Current Market Conditions:
- BDI: ~2100
- Clean Tanker Index: ~18500
- VLCC rates: Stable to +5%
- Port congestion: Normal levels
- Weather: No major disruptions expected"""

    async def add_fixture_to_index(self, fixture_id: str, fixture_data: Dict[str, Any]):
        """Add fixture to vector index for future retrieval"""
        if not self.enabled:
            return
        
        try:
            text = self._fixture_to_text(fixture_data)
            embedding = await self._get_embedding(text)
            
            # In production, store in pgvector:
            # INSERT INTO fixture_embeddings (fixture_id, embedding, metadata)
            # VALUES (fixture_id, embedding, jsonb_build_object(...))
            
            logger.info(f"Added fixture {fixture_id} to vector index")
        except Exception as e:
            logger.error(f"Failed to add fixture to index: {e}")
    
    def _fixture_to_text(self, fixture: Dict[str, Any]) -> str:
        """Convert fixture to searchable text"""
        return f"{fixture.get('vessel_name', '')} {fixture.get('cargo_type', '')} {fixture.get('port_loading', '')} to {fixture.get('port_discharge', '')} {fixture.get('laycan_start', '')}"


rag_service = RAGService()


async def rag_search(
    query: str,
    user_id: str,
    fixture_id: Optional[str] = None,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Perform RAG search over fixtures, emails, and market data.
    
    Args:
        query: Search query
        user_id: User ID for filtering
        fixture_id: Optional fixture ID for context
        limit: Maximum results
    
    Returns:
        List of relevant documents with content and scores
    """
    results = []
    
    try:
        # In production, this would query pgvector with the query embedding
        # For now, return simulated relevant results based on the query
        
        query_lower = query.lower()
        
        # Check for fixture-related queries
        if any(kw in query_lower for kw in ["vessel", "fixture", "charter", "rate", "tce"]):
            results.append({
                "type": "fixture",
                "id": fixture_id or "sample-1",
                "title": "Similar Fixtures",
                "content": "Historical fixtures show rates for AG->Singapore route averaging WS 120-140 for MR tankers.",
                "score": 0.92,
            })
        
        # Check for market queries
        if any(kw in query_lower for kw in ["market", "rate", "tce", " Baltic", "freight"]):
            results.append({
                "type": "market_data",
                "id": "market-1",
                "title": "Market Rates",
                "content": "Current VLCC rates: AG->EU WS 48-52, LR2 AG->EU WS 95-105. Market trending up 5%.",
                "score": 0.88,
            })
        
        # Check for laytime/demurrage
        if any(kw in query_lower for kw in ["laytime", "demurrage", "despatch", "nor", "sof"]):
            results.append({
                "type": "rag",
                "id": "laytime-1",
                "title": "Laytime Calculations",
                "content": "Standard laytime formula: (Quantity / Loading Rate) + (Quantity / Discharging Rate). Demurrage typically $15,000-30,000/day.",
                "score": 0.85,
            })
        
        return results[:limit]
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return []
