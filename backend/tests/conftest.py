"""
Pytest configuration and fixtures for OpenMaritime backend tests.

Provides:
- Test database session (SQLite in-memory)
- Mock fixtures for external services (Ollama, APIs)
- Sample fixture data for testing
- Async test utilities
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import JSON, String, Float, Integer, Boolean, DateTime, Text, Column
from sqlalchemy.orm import declarative_base

# Set test environment variables before imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["LLAMA_MODEL"] = "llama3.1:70b"
os.environ["USE_LOCAL_LLAMA"] = "false"
os.environ["ENABLE_RAG"] = "false"
os.environ["RIGHTSHIP_API_KEY"] = "test_rightship_key"
os.environ["MARINETRAFFIC_API_KEY"] = "test_marinetraffic_key"

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a separate test base
TestBase = declarative_base()


# =============================================================================
# Test-Safe Fixture Model (SQLite compatible)
# =============================================================================

class Fixture(TestBase):
    """Test fixture model - simplified for SQLite compatibility."""
    __tablename__ = "fixtures"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False, index=True)
    
    # Vessel info
    vessel_name = Column(String(100), nullable=False)
    imo_number = Column(String(7), index=True)
    
    # Cargo info
    cargo_type = Column(String(100), nullable=False)
    cargo_quantity = Column(Float, default=0.0)
    cargo_unit = Column(String(10), default="MT")
    
    # Laycan
    laycan_start = Column(DateTime, nullable=False)
    laycan_end = Column(DateTime, nullable=False)
    
    # Rate
    rate = Column(Float)
    rate_currency = Column(String(3), default="USD")
    rate_unit = Column(String(5), default="/mt")
    
    # Ports
    port_loading = Column(String(100), nullable=False)
    port_discharge = Column(String(100), nullable=False)
    
    # Charterer/Broker
    charterer = Column(String(100))
    broker = Column(String(100))
    
    # Source tracking
    source_email_id = Column(String(255))
    source_subject = Column(String(500))
    
    # Status
    status = Column(String(20), default="new")
    
    # Wake AI fields
    wake_score = Column(Float)
    tce_estimate = Column(Float)
    market_diff = Column(Float)
    
    # JSON data - use JSON for SQLite
    raw_data = Column(JSON)
    enrichment_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class User(TestBase):
    """Test user model - simplified for SQLite."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    tenant_id = Column(String(36), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EmailSync(TestBase):
    """Test email sync model - simplified for SQLite."""
    __tablename__ = "email_syncs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False, index=True)
    
    provider = Column(String(20))
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    last_sync_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PluginConfig(TestBase):
    """Test plugin config model - simplified for SQLite."""
    __tablename__ = "plugin_configs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False, index=True)
    
    plugin_name = Column(String(100), index=True)
    config = Column(JSON)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# Test Database Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine (SQLite in-memory)."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session_maker(test_engine):
    """Create a test session maker."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture(scope="function")
async def db_session(test_session_maker) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with auto-cleanup."""
    async with test_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def session_with_data(test_session_maker) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with sample data."""
    async with test_session_maker() as session:
        # Create sample fixtures
        fixtures = create_sample_fixtures(str(uuid4()), str(uuid4()))
        for f in fixtures:
            session.add(f)
        
        await session.commit()
        
        yield session


# =============================================================================
# Sample Data Fixtures
# =============================================================================

def create_sample_fixtures(
    user_id: str,
    tenant_id: str,
    count: int = 5,
) -> list[Fixture]:
    """Create sample fixtures for testing."""
    fixtures = []
    
    sample_data = [
        {
            "vessel_name": "Pacific Voyager",
            "imo_number": "1234567",
            "cargo_type": "Crude Oil",
            "cargo_quantity": 280000,
            "rate": 52.5,
            "port_loading": "Ras Tanura",
            "port_discharge": "Ningbo",
            "charterer": "Shell",
            "broker": "Barry Rogliano Salles",
            "status": "new",
            "wake_score": 75.0,
        },
        {
            "vessel_name": "Atlantic Glory",
            "imo_number": "2345678",
            "cargo_type": "Product",
            "cargo_quantity": 80000,
            "rate": 35.0,
            "port_loading": "Rotterdam",
            "port_discharge": "New York",
            "charterer": "Trafigura",
            "broker": "Gibson",
            "status": "approved",
            "wake_score": 85.0,
        },
        {
            "vessel_name": "Nordic Star",
            "imo_number": "3456789",
            "cargo_type": "LNG",
            "cargo_quantity": 170000,
            "rate": 28.0,
            "port_loading": "Sabine Pass",
            "port_discharge": "Tokyo",
            "charterer": "Cheniere",
            "broker": "Poten",
            "status": "rejected",
            "wake_score": 45.0,
        },
        {
            "vessel_name": "Mediterranean Spirit",
            "imo_number": "4567890",
            "cargo_type": "Chemicals",
            "cargo_quantity": 45000,
            "rate": 42.0,
            "port_loading": "Antwerp",
            "port_discharge": "Mumbai",
            "charterer": "BASF",
            "broker": "Clarksons",
            "status": "new",
            "wake_score": 60.0,
        },
        {
            "vessel_name": "Asian Enterprise",
            "imo_number": "5678901",
            "cargo_type": "Coal",
            "cargo_quantity": 150000,
            "rate": 18.5,
            "port_loading": "Newcastle",
            "port_discharge": "Busan",
            "charterer": "Sempra",
            "broker": "Braemar",
            "status": "new",
            "wake_score": 55.0,
        },
    ]
    
    for i in range(min(count, len(sample_data))):
        data = sample_data[i]
        now = datetime.utcnow()
        
        fixture = Fixture(
            id=str(uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            vessel_name=data["vessel_name"],
            imo_number=data["imo_number"],
            cargo_type=data["cargo_type"],
            cargo_quantity=data["cargo_quantity"],
            cargo_unit="MT",
            laycan_start=now + timedelta(days=5 + i),
            laycan_end=now + timedelta(days=10 + i),
            rate=data["rate"],
            rate_currency="USD",
            rate_unit="/mt",
            port_loading=data["port_loading"],
            port_discharge=data["port_discharge"],
            charterer=data["charterer"],
            broker=data["broker"],
            status=data["status"],
            wake_score=data["wake_score"],
            tce_estimate=25000 + (i * 1000),
            market_diff=5.0 + (i * 2),
        )
        fixtures.append(fixture)
    
    return fixtures


@pytest.fixture
def sample_fixture_data() -> dict:
    """Sample fixture data for testing."""
    now = datetime.utcnow()
    return {
        "vessel_name": "Test Vessel",
        "imo_number": "9876543",
        "cargo_type": "Crude Oil",
        "cargo_quantity": 300000,
        "cargo_unit": "MT",
        "laycan_start": (now + timedelta(days=7)).isoformat(),
        "laycan_end": (now + timedelta(days=12)).isoformat(),
        "rate": 55.0,
        "rate_currency": "USD",
        "rate_unit": "/mt",
        "port_loading": "Kuwait",
        "port_discharge": "Singapore",
        "charterer": "Test Charterer",
        "broker": "Test Broker",
    }


@pytest.fixture
def sample_email_text() -> str:
    """Sample email text for fixture extraction testing."""
    return """
From: broker@example.com
Subject: Fixture - MT Everest / 130k Products / USG to Japan

Hi,

Please find below fixture details:

Vessel: MT EVEREST
IMO: 9123456
Cargo: 130,000 MT Naphtha
Laycan: 15-18 March 2025
Rate: USD 42.50/MT
Load: US Gulf
Discharge: Japan (Yokohama/Chiba)
Charterer: ENOC

Best regards,
Broker
"""


@pytest.fixture
def sample_market_context() -> str:
    """Sample market context for RAG testing."""
    return """Current Market Conditions:
- BDI: 2150 (+2.3%)
- BCTI: 18200 (-1.2%)
- VLCC Rate (WS): 45 (up 5%)
- Suezmax Rate (WS): 38 (up 2%)
- Aframax Rate (WS): 28 (-1.5%)

News:
- OPEC+ extends production cuts
- Singapore port congestion building
- Chinese oil demand recovery

Weather:
- Typhoon warning South China Sea
"""


# =============================================================================
# Mock Fixtures for External Services
# =============================================================================

@pytest_asyncio.fixture
async def mock_ollama_response():
    """Mock Ollama API response."""
    async def mock_response(*args, **kwargs):
        class MockResponse:
            status = 200
            async def json(self):
                return {"response": '{"score": 78, "reason": "Good fixture with competitive rate", "urgency": "medium"}'}
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        return MockResponse()
    return mock_response


@pytest_asyncio.fixture
async def mock_rag_response():
    """Mock RAG response."""
    return [
        {"type": "market_index", "content": "BDI currently at 2150, up 2.3%", "relevance": 0.92},
        {"type": "news", "content": "VLCC rates in Middle East up 15%", "relevance": 0.88},
        {"type": "weather", "content": "No major weather alerts", "relevance": 0.75},
    ]


@pytest_asyncio.fixture
async def mock_rightship_response():
    """Mock RightShip API response."""
    return {
        "safety_score": "A",
        "ghg_rating": "B",
        "inspection_status": "Valid",
        "last_inspection_date": "2024-12-15",
    }


@pytest_asyncio.fixture
async def mock_marinetraffic_response():
    """Mock MarineTraffic API response."""
    return [
        {
            "LAT": 1.2644,
            "LON": 103.8208,
            "SPEED": 12.5,
            "HEADING": 270,
            "DESTINATION": "SINGAPORE",
            "ETA": "2025-03-05 0800",
            "LAST_UPDATE": "2025-03-03T06:30:00",
        }
    ]


# =============================================================================
# HTTP Client Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def async_client(test_session_maker):
    """Create an async HTTP client for API testing."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    
    # Override the database dependency
    async def override_get_db():
        async with test_session_maker() as session:
            yield session
    
    from app.main import async_session_maker
    app.dependency_overrides[async_session_maker] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client_with_data(test_session_maker):
    """Create an async HTTP client with sample data."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    
    # Override the database dependency with pre-loaded data
    async def override_get_db():
        async with test_session_maker() as session:
            # Create sample fixtures
            fixtures = create_sample_fixtures(str(uuid4()), str(uuid4()))
            for f in fixtures:
                session.add(f)
            
            await session.commit()
            
            yield session
    
    from app.main import async_session_maker
    app.dependency_overrides[async_session_maker] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    """Set anyio backend for async tests."""
    return "asyncio"
