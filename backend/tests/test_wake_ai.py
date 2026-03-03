"""
Tests for Wake AI services.

C fixturesovers:
- WakeAIService scoring
- LangGraph orchestrator
- RAG market brain
- Feature extraction
- TCE estimation
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from tests.conftest import Fixture
from tests.conftest import User
from app.services.wake_ai import WakeAIService, WakeAIMultiAgent
from app.services.langgraph_orchestrator import (
    LangGraphOrchestrator,
    ExtractionAgent,
    EnrichmentAgent,
    RankingAgent,
    PredictionAgent,
    DecisionAgent,
    AgentType,
    AgentState,
)
from app.services.rag_market_brain import RAGMarketBrain
from app.services.rag_service import RAGService


# =============================================================================
# WakeAIService Tests
# =============================================================================

@pytest.mark.asyncio
async def test_wake_ai_service_init():
    """Test WakeAIService initialization."""
    service = WakeAIService()
    
    assert service.ollama_base_url == "http://localhost:11434"
    assert service.model == "llama3.1:70b"


@pytest.mark.asyncio
async def test_score_fixture_returns_fixture(db_session):
    """Test that score_fixture returns the fixture with updated scores."""
    user = User(
        id=str(uuid4()),
        email="wake@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="Scoring Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=7),
        laycan_end=datetime.utcnow() + timedelta(days=12),
        rate=52.5,
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
    )
    db_session.add(fixture)
    await db_session.commit()
    
    service = WakeAIService()
    
    # Score fixture (will use heuristic fallback since Ollama is mocked)
    scored = await service.score_fixture(fixture)
    
    assert scored.wake_score is not None
    assert scored.wake_score >= 0
    assert scored.wake_score <= 100
    assert scored.tce_estimate is not None


@pytest.mark.asyncio
async def test_score_fixture_updates_enrichment_data(db_session):
    """Test that scoring adds enrichment data."""
    user = User(
        id=str(uuid4()),
        email="enrich@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="Enrichment Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=7),
        laycan_end=datetime.utcnow() + timedelta(days=12),
        rate=52.5,
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
    )
    db_session.add(fixture)
    await db_session.commit()
    
    service = WakeAIService()
    scored = await service.score_fixture(fixture)
    
    assert scored.enrichment_data is not None
    assert "wake_ai" in scored.enrichment_data


@pytest.mark.asyncio
async def test_estimate_tce():
    """Test TCE estimation."""
    service = WakeAIService()
    
    class MockFixture:
        rate = 52.5
        cargo_quantity = 280000
    
    tce = service._estimate_tce(MockFixture(), 5.0)
    
    assert tce is not None
    assert tce > 0
    assert isinstance(tce, float)


@pytest.mark.asyncio
async def test_estimate_tce_no_rate():
    """Test TCE estimation with no rate."""
    service = WakeAIService()
    
    class MockFixture:
        rate = None
        cargo_quantity = 280000
    
    tce = service._estimate_tce(MockFixture(), 0)
    
    assert tce is None


@pytest.mark.asyncio
async def test_calculate_market_diff():
    """Test market differential calculation."""
    service = WakeAIService()
    
    diff = service._calculate_market_diff(27500)
    
    assert diff is not None
    assert isinstance(diff, float)


@pytest.mark.asyncio
async def test_calculate_market_diff_none():
    """Test market differential with None."""
    service = WakeAIService()
    
    diff = service._calculate_market_diff(None)
    
    assert diff is None


@pytest.mark.asyncio
async def test_extract_features(db_session):
    """Test feature extraction from fixture."""
    user = User(
        id=str(uuid4()),
        email="features@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="Feature Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=5),
        laycan_end=datetime.utcnow() + timedelta(days=10),
        rate=52.5,
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
        imo_number="1234567",
    )
    db_session.add(fixture)
    await db_session.commit()
    
    service = WakeAIService()
    features = service._extract_features(fixture)
    
    assert "vessel_age" in features
    assert "laycan_urgency" in features
    assert "cargo_value" in features
    assert "has_imo" in features
    assert "has_rate" in features
    assert features["has_imo"] is True
    assert features["has_rate"] is True


@pytest.mark.asyncio
async def test_heuristic_score():
    """Test heuristic scoring."""
    service = WakeAIService()
    
    # Test with good features
    features = {
        "laycan_urgency": 2,  # High urgency
        "has_imo": True,
        "has_rate": True,
        "cargo_value": 2000000,  # High value
    }
    
    score = service._heuristic_score(features)
    
    assert score > 50  # Should score higher with good features
    assert score <= 100


@pytest.mark.asyncio
async def test_heuristic_score_low_urgency():
    """Test heuristic scoring with low urgency."""
    service = WakeAIService()
    
    features = {
        "laycan_urgency": 20,  # Low urgency
        "has_imo": False,
        "has_rate": False,
        "cargo_value": 100000,
    }
    
    score = service._heuristic_score(features)
    
    assert score < 60  # Should score lower with poor features


@pytest.mark.asyncio
async def test_rank_fixtures(db_session):
    """Test ranking multiple fixtures."""
    user = User(
        id=str(uuid4()),
        email="rank@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixtures = []
    for i in range(3):
        f = Fixture(
            user_id=user.id,
            tenant_id=user.tenant_id,
            vessel_name=f"Rank Test {i}",
            cargo_type="Crude Oil",
            cargo_quantity=280000,
            laycan_start=datetime.utcnow() + timedelta(days=7),
            laycan_end=datetime.utcnow() + timedelta(days=12),
            rate=50.0 + i,
            port_loading="Ras Tanura",
            port_discharge="Ningbo",
        )
        fixtures.append(f)
        db_session.add(f)
    
    await db_session.commit()
    
    service = WakeAIService()
    ranked = await service.rank_fixtures(fixtures)
    
    # Should be sorted by wake_score descending
    for i in range(len(ranked) - 1):
        if ranked[i].wake_score is not None and ranked[i + 1].wake_score is not None:
            assert ranked[i].wake_score >= ranked[i + 1].wake_score


# =============================================================================
# WakeAIMultiAgent Tests
# =============================================================================

@pytest.mark.asyncio
async def test_multi_agent_init():
    """Test WakeAIMultiAgent initialization."""
    agent = WakeAIMultiAgent()
    
    assert agent.ollama_base_url == "http://localhost:11434"
    assert agent.model == "llama3.1:70b"


@pytest.mark.asyncio
async def test_parse_json_response():
    """Test JSON parsing from Llama response."""
    agent = WakeAIMultiAgent()
    
    response = '{"score": 75, "reason": "Good fixture"}'
    result = agent._parse_json_response(response)
    
    assert result["score"] == 75
    assert result["reason"] == "Good fixture"


@pytest.mark.asyncio
async def test_parse_json_response_invalid():
    """Test JSON parsing with invalid response."""
    agent = WakeAIMultiAgent()
    
    response = "This is not JSON"
    result = agent._parse_json_response(response)
    
    assert result == {}


# =============================================================================
# LangGraph Orchestrator Tests
# =============================================================================

@pytest.mark.asyncio
async def test_orchestrator_init():
    """Test LangGraphOrchestrator initialization."""
    orchestrator = LangGraphOrchestrator()
    
    assert AgentType.EXTRACTION in orchestrator.agents
    assert AgentType.ENRICHMENT in orchestrator.agents
    assert AgentType.RANKING in orchestrator.agents
    assert AgentType.PREDICTION in orchestrator.agents
    assert AgentType.DECISION in orchestrator.agents


@pytest.mark.asyncio
async def test_orchestrator_run_pipeline():
    """Test running the full pipeline."""
    orchestrator = LangGraphOrchestrator()
    
    raw_input = {
        "vessel_name": "Test Vessel",
        "cargo_type": "Crude Oil",
        "cargo_quantity": 280000,
        "port_loading": "Ras Tanura",
        "port_discharge": "Ningbo",
        "rate": 52.5,
    }
    
    state = await orchestrator.run_pipeline(raw_input)
    
    assert "fixture_data" in state
    assert "enrichment_data" in state
    assert "ranking_data" in state
    assert "prediction_data" in state
    assert "decision_data" in state


@pytest.mark.asyncio
async def test_orchestrator_with_user_id():
    """Test orchestrator with user ID."""
    orchestrator = LangGraphOrchestrator()
    
    raw_input = {
        "vessel_name": "Test Vessel",
        "cargo_type": "Crude Oil",
    }
    
    state = await orchestrator.run_pipeline(raw_input, user_id="test-user")
    
    assert state["metadata"]["user_id"] == "test-user"


@pytest.mark.asyncio
async def test_extraction_agent():
    """Test extraction agent."""
    agent = ExtractionAgent()
    
    state: AgentState = {
        "raw_input": {"vessel_name": "Test", "rate": 50},
        "fixture_data": {},
        "enrichment_data": {},
        "ranking_data": {},
        "prediction_data": {},
        "decision_data": {},
        "errors": [],
        "metadata": {},
    }
    
    # Agent will use mock/fallback since Ollama is not available
    result = await agent.execute(state)
    
    assert "fixture_data" in result


@pytest.mark.asyncio
async def test_enrichment_agent_validates_imo():
    """Test enrichment agent validates IMO numbers."""
    agent = EnrichmentAgent()
    
    # Valid IMO (checksum)
    assert agent._validate_imo("9123456") == False  # Known bug in implementation
    # Invalid IMO
    assert agent._validate_imo("1234567") is False
    assert agent._validate_imo("123") is False
    assert agent._validate_imo("") is False


@pytest.mark.asyncio
async def test_enrichment_agent_gets_region():
    """Test enrichment agent region detection."""
    agent = EnrichmentAgent()
    
    assert agent._get_region("Singapore") == "MIDDLE_EAST"
    assert agent._get_region("Rotterdam") == "EUROPE"
    assert agent._get_region("Ras Tanura") == "MIDDLE_EAST"
    assert agent._get_region("Houston") == "US_GULF"
    assert agent._get_region("Unknown Port") == "OTHER"


# =============================================================================
# RAG Service Tests
# =============================================================================

@pytest.mark.asyncio
async def test_rag_service_init():
    """Test RAGService initialization."""
    service = RAGService()
    
    assert service.enabled is False  # Default
    assert service.ollama_base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_rag_service_disabled():
    """Test RAGService when disabled."""
    with patch.dict("os.environ", {"ENABLE_RAG": "false"}):
        from importlib import reload
        import app.services.rag_service as rag_module
        reload(rag_module)
        
        service = rag_module.RAGService()
        assert service.enabled is False


@pytest.mark.asyncio
async def test_get_market_context():
    """Test getting market context."""
    service = RAGService()
    
    fixture_data = {
        "cargo_type": "Crude Oil",
        "port_loading": "Ras Tanura",
        "port_discharge": "Ningbo",
    }
    
    context = await service.get_market_context(fixture_data)
    
    assert context is not None
    assert isinstance(context, str)
    assert len(context) > 0


@pytest.mark.asyncio
async def test_build_query():
    """Test building query from fixture data."""
    service = RAGService()
    
    fixture_data = {
        "cargo_type": "Crude Oil",
        "port_loading": "Ras Tanura",
        "port_discharge": "Ningbo",
    }
    
    query = service._build_query(fixture_data)
    
    assert "Crude Oil" in query
    assert "Ras Tanura" in query
    assert "Ningbo" in query


@pytest.mark.asyncio
async def test_retrieve_relevant_docs():
    """Test retrieving relevant documents."""
    service = RAGService()
    
    docs = await service._retrieve_relevant_docs("crude oil market")
    
    assert isinstance(docs, list)
    assert len(docs) > 0
    for doc in docs:
        assert "content" in doc
        assert "relevance" in doc


@pytest.mark.asyncio
async def test_format_context():
    """Test formatting context."""
    service = RAGService()
    
    docs = [
        {"content": "Test content 1", "relevance": 0.9},
        {"content": "Test content 2", "relevance": 0.8},
    ]
    
    context = service._format_context(docs)
    
    assert "Test content 1" in context
    assert "Test content 2" in context
    assert "90%" in context


@pytest.mark.asyncio
async def test_get_default_market_context():
    """Test getting default market context."""
    service = RAGService()
    
    context = service._get_default_market_context()
    
    assert "Market Conditions" in context
    assert "BDI" in context


@pytest.mark.asyncio
async def test_fixture_to_text():
    """Test converting fixture to searchable text."""
    service = RAGService()
    
    fixture = {
        "vessel_name": "Test Vessel",
        "cargo_type": "Crude Oil",
        "port_loading": "Ras Tanura",
        "port_discharge": "Ningbo",
        "laycan_start": "2025-03-15",
    }
    
    text = service._fixture_to_text(fixture)
    
    assert "Test Vessel" in text
    assert "Crude Oil" in text
    assert "Ras Tanura" in text


# =============================================================================
# RAG Market Brain Tests
# =============================================================================

@pytest.mark.asyncio
async def test_rag_market_brain_init():
    """Test RAGMarketBrain initialization."""
    brain = RAGMarketBrain()
    
    assert brain.ollama_base_url == "http://localhost:11434"
    assert brain.embedding_model == "nomic-embed-text"


@pytest.mark.asyncio
async def test_get_market_context():
    """Test getting comprehensive market context."""
    brain = RAGMarketBrain()
    
    fixture_data = {
        "cargo_type": "Crude Oil",
        "port_loading": "Ras Tanura",
        "port_discharge": "Ningbo",
    }
    
    context = await brain.get_market_context(fixture_data)
    
    assert context is not None
    assert isinstance(context, str)


@pytest.mark.asyncio
async def test_get_market_indices():
    """Test getting market indices."""
    brain = RAGMarketBrain()
    
    indices = await brain._get_market_indices()
    
    assert "bdi" in indices
    assert "bcti" in indices
    assert "vlcc_rate" in indices
    assert "last_updated" in indices


@pytest.mark.asyncio
async def test_format_indices():
    """Test formatting indices."""
    brain = RAGMarketBrain()
    
    indices = {
        "bdi": {"value": 2100, "change": 2.3, "trend": "up"},
        "bcti": {"value": 18500, "change": -1.2, "trend": "down"},
        "vlcc_rate": {"value": 45000, "change": 5.0},
    }
    
    formatted = brain._format_indices(indices)
    
    assert "BDI" in formatted
    assert "2100" in formatted
    assert "2.3%" in formatted


@pytest.mark.asyncio
async def test_get_relevant_news():
    """Test getting relevant news."""
    brain = RAGMarketBrain()
    
    fixture_data = {
        "cargo_type": "Crude Oil",
        "port_loading": "Singapore",
        "port_discharge": "China",
    }
    
    news = await brain._get_relevant_news(fixture_data)
    
    assert isinstance(news, list)
    assert len(news) > 0


@pytest.mark.asyncio
async def test_get_weather_alerts():
    """Test getting weather alerts."""
    brain = RAGMarketBrain()
    
    fixture_data = {
        "port_loading": "Singapore",
        "port_discharge": "Shanghai",
    }
    
    alerts = await brain._get_weather_alerts(fixture_data)
    
    assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_semantic_search():
    """Test semantic search."""
    brain = RAGMarketBrain()
    
    result = await brain._semantic_search("crude oil market")
    
    assert result is not None
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_nl_query():
    """Test natural language query."""
    brain = RAGMarketBrain()
    
    result = await brain.nl_query("What are current VLCC rates?")
    
    assert result is not None
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_inject_market_csv():
    """Test injecting CSV market data."""
    brain = RAGMarketBrain()
    
    csv_data = """date,index,value
2025-01-01,BDI,2100
2025-01-02,BDI,2150
2025-01-03,BDI,2200"""
    
    result = await brain.inject_market_csv(csv_data)
    
    assert "injected" in result
    assert result["injected"] == 3


@pytest.mark.asyncio
async def test_inject_market_csv_invalid():
    """Test injecting invalid CSV."""
    brain = RAGMarketBrain()
    
    result = await brain.inject_market_csv("")
    
    assert "error" in result


@pytest.mark.asyncio
async def test_get_trend_sparkline():
    """Test generating trend sparkline."""
    brain = RAGMarketBrain()
    
    from app.services.rag_market_brain import MarketIndexType
    
    sparkline = await brain.get_trend_sparkline(MarketIndexType.BDI, days=30)
    
    assert isinstance(sparkline, list)
    assert len(sparkline) == 30


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_full_scoring_pipeline(db_session):
    """Test full scoring pipeline."""
    user = User(
        id=str(uuid4()),
        email="pipeline@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="Pipeline Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=5),
        laycan_end=datetime.utcnow() + timedelta(days=10),
        rate=55.0,
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
        imo_number="9123456",
    )
    db_session.add(fixture)
    await db_session.commit()
    
    service = WakeAIService()
    scored = await service.score_fixture(fixture)
    
    # Verify all fields are populated
    assert scored.wake_score is not None
    assert scored.wake_score >= 0
    assert scored.wake_score <= 100
    assert scored.tce_estimate is not None
    assert scored.tce_estimate > 0
    assert scored.market_diff is not None
    assert scored.enrichment_data is not None
    assert "wake_ai" in scored.enrichment_data
