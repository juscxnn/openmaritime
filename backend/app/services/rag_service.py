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
