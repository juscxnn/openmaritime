"""
Tests for Fixture CRUD operations, ranking, filtering, and pagination.

C fixturesovers:
- Creating fixtures
- Reading fixtures (list and single)
- Updating fixtures
- Deleting fixtures
- Fixture ranking
- Filtering by status
- Pagination
- Sorting
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from tests.conftest import User
from tests.conftest import Fixture


# =============================================================================
# Create Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_fixture(db_session, sample_fixture_data):
    """Test creating a new fixture."""
    # Create a test user first
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create fixture
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name=sample_fixture_data["vessel_name"],
        imo_number=sample_fixture_data["imo_number"],
        cargo_type=sample_fixture_data["cargo_type"],
        cargo_quantity=sample_fixture_data["cargo_quantity"],
        cargo_unit=sample_fixture_data["cargo_unit"],
        laycan_start=datetime.fromisoformat(sample_fixture_data["laycan_start"]),
        laycan_end=datetime.fromisoformat(sample_fixture_data["laycan_end"]),
        rate=sample_fixture_data["rate"],
        rate_currency=sample_fixture_data["rate_currency"],
        rate_unit=sample_fixture_data["rate_unit"],
        port_loading=sample_fixture_data["port_loading"],
        port_discharge=sample_fixture_data["port_discharge"],
        charterer=sample_fixture_data["charterer"],
        broker=sample_fixture_data["broker"],
    )
    
    db_session.add(fixture)
    await db_session.commit()
    await db_session.refresh(fixture)
    
    # Verify
    assert fixture.id is not None
    assert fixture.vessel_name == "Test Vessel"
    assert fixture.imo_number == "9876543"
    assert fixture.cargo_type == "Crude Oil"
    assert fixture.cargo_quantity == 300000
    assert fixture.rate == 55.0
    assert fixture.port_loading == "Kuwait"
    assert fixture.port_discharge == "Singapore"
    assert fixture.status == "new"
    assert fixture.wake_score is None  # Not scored yet


@pytest.mark.asyncio
async def test_create_fixture_minimal_data(db_session):
    """Test creating fixture with minimal required data."""
    user = User(
        id=str(uuid4()),
        email="minimal@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="Minimal Vessel",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=7),
        laycan_end=datetime.utcnow() + timedelta(days=12),
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
    )
    
    db_session.add(fixture)
    await db_session.commit()
    await db_session.refresh(fixture)
    
    assert fixture.id is not None
    assert fixture.vessel_name == "Minimal Vessel"
    assert fixture.rate is None  # Optional
    assert fixture.imo_number is None  # Optional


# =============================================================================
# Read Tests
# =============================================================================

@pytest.mark.asyncio
async def test_list_fixtures_empty(db_session):
    """Test listing fixtures when none exist."""
    result = await db_session.execute(select(Fixture))
    fixtures = result.scalars().all()
    
    assert len(fixtures) == 0


@pytest.mark.asyncio
async def test_list_fixtures_with_data(session_with_data):
    """Test listing fixtures with sample data."""
    result = await session_with_data.execute(select(Fixture))
    fixtures = result.scalars().all()
    
    assert len(fixtures) == 5
    # Verify all fixtures have required fields
    for f in fixtures:
        assert f.vessel_name is not None
        assert f.cargo_type is not None
        assert f.port_loading is not None


@pytest.mark.asyncio
async def test_get_fixture_by_id(session_with_data):
    """Test getting a fixture by ID."""
    # Get first fixture
    result = await session_with_data.execute(select(Fixture).limit(1))
    fixture = result.scalar_one()
    
    # Fetch by ID
    result = await session_with_data.execute(
        select(Fixture).where(Fixture.id == fixture.id)
    )
    fetched = result.scalar_one()
    
    assert fetched.id == fixture.id
    assert fetched.vessel_name == fixture.vessel_name


@pytest.mark.asyncio
async def test_get_fixture_not_found(db_session):
    """Test getting non-existent fixture raises error."""
    fake_id = uuid4()
    result = await db_session.execute(
        select(Fixture).where(Fixture.id == fake_id)
    )
    fixture = result.scalar_one_or_none()
    
    assert fixture is None


# =============================================================================
# Update Tests
# =============================================================================

@pytest.mark.asyncio
async def test_update_fixture_basic(session_with_data):
    """Test updating basic fixture fields."""
    result = await session_with_data.execute(select(Fixture).limit(1))
    fixture = result.scalar_one()
    
    original_name = fixture.vessel_name
    fixture.vessel_name = "Updated Vessel Name"
    fixture.status = "approved"
    
    await session_with_data.commit()
    await session_with_data.refresh(fixture)
    
    assert fixture.vessel_name == "Updated Vessel Name"
    assert fixture.status == "approved"
    assert fixture.vessel_name != original_name


@pytest.mark.asyncio
async def test_update_fixture_wake_score(session_with_data):
    """Test updating fixture wake score."""
    result = await session_with_data.execute(select(Fixture).limit(1))
    fixture = result.scalar_one()
    
    fixture.wake_score = 92.5
    fixture.tce_estimate = 35000
    fixture.market_diff = 12.5
    
    await session_with_data.commit()
    await session_with_data.refresh(fixture)
    
    assert fixture.wake_score == 92.5
    assert fixture.tce_estimate == 35000
    assert fixture.market_diff == 12.5


@pytest.mark.asyncio
async def test_update_fixture_enrichment_data(session_with_data):
    """Test updating fixture enrichment data."""
    result = await session_with_data.execute(select(Fixture).limit(1))
    fixture = result.scalar_one()
    
    enrichment = {
        "rightship": {"safety_score": "A", "ghg_rating": "B"},
        "marinetraffic": {"lat": 1.26, "lon": 103.82},
    }
    fixture.enrichment_data = enrichment
    
    await session_with_data.commit()
    await session_with_data.refresh(fixture)
    
    assert fixture.enrichment_data["rightship"]["safety_score"] == "A"
    assert fixture.enrichment_data["marinetraffic"]["lat"] == 1.26


# =============================================================================
# Delete Tests
# =============================================================================

@pytest.mark.asyncio
async def test_delete_fixture(session_with_data):
    """Test deleting a fixture."""
    result = await session_with_data.execute(select(Fixture).limit(1))
    fixture = result.scalar_one()
    fixture_id = fixture.id
    
    await session_with_data.delete(fixture)
    await session_with_data.commit()
    
    # Verify deleted
    result = await session_with_data.execute(
        select(Fixture).where(Fixture.id == fixture_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_all_fixtures(session_with_data):
    """Test deleting all fixtures for a user."""
    result = await session_with_data.execute(select(Fixture))
    fixtures = result.scalars().all()
    
    for f in fixtures:
        await session_with_data.delete(f)
    
    await session_with_data.commit()
    
    result = await session_with_data.execute(select(Fixture))
    remaining = result.scalars().all()
    
    assert len(remaining) == 0


# =============================================================================
# Filtering Tests
# =============================================================================

@pytest.mark.asyncio
async def test_filter_by_status(session_with_data):
    """Test filtering fixtures by status."""
    # Get fixtures with status 'new'
    result = await session_with_data.execute(
        select(Fixture).where(Fixture.status == "new")
    )
    new_fixtures = result.scalars().all()
    
    for f in new_fixtures:
        assert f.status == "new"
    
    # Get fixtures with status 'approved'
    result = await session_with_data.execute(
        select(Fixture).where(Fixture.status == "approved")
    )
    approved_fixtures = result.scalars().all()
    
    for f in approved_fixtures:
        assert f.status == "approved"


@pytest.mark.asyncio
async def test_filter_by_cargo_type(session_with_data):
    """Test filtering fixtures by cargo type."""
    result = await session_with_data.execute(
        select(Fixture).where(Fixture.cargo_type == "Crude Oil")
    )
    crude_fixtures = result.scalars().all()
    
    for f in crude_fixtures:
        assert f.cargo_type == "Crude Oil"


@pytest.mark.asyncio
async def test_filter_by_port(session_with_data):
    """Test filtering fixtures by port."""
    result = await session_with_data.execute(
        select(Fixture).where(Fixture.port_loading == "Ras Tanura")
    )
    ras_tanura_fixtures = result.scalars().all()
    
    for f in ras_tanura_fixtures:
        assert f.port_loading == "Ras Tanura"


@pytest.mark.asyncio
async def test_filter_by_imo(session_with_data):
    """Test filtering fixtures by IMO number."""
    result = await session_with_data.execute(
        select(Fixture).where(Fixture.imo_number == "1234567")
    )
    fixtures = result.scalars().all()
    
    assert len(fixtures) == 1
    assert fixtures[0].imo_number == "1234567"


# =============================================================================
# Pagination Tests
# =============================================================================

@pytest.mark.asyncio
async def test_pagination_limit(session_with_data):
    """Test pagination with limit."""
    result = await session_with_data.execute(
        select(Fixture).limit(2)
    )
    fixtures = result.scalars().all()
    
    assert len(fixtures) == 2


@pytest.mark.asyncio
async def test_pagination_offset(session_with_data):
    """Test pagination with offset."""
    # Get first 2
    result = await session_with_data.execute(
        select(Fixture).limit(2)
    )
    first_page = result.scalars().all()
    
    # Get next 2
    result = await session_with_data.execute(
        select(Fixture).limit(2).offset(2)
    )
    second_page = result.scalars().all()
    
    # Verify no overlap
    first_ids = {f.id for f in first_page}
    second_ids = {f.id for f in second_page}
    
    assert len(first_ids.intersection(second_ids)) == 0


@pytest.mark.asyncio
async def test_pagination_out_of_bounds(session_with_data):
    """Test pagination with offset beyond data."""
    result = await session_with_data.execute(
        select(Fixture).limit(10).offset(100)
    )
    fixtures = result.scalars().all()
    
    assert len(fixtures) == 0


# =============================================================================
# Sorting Tests
# =============================================================================

@pytest.mark.asyncio
async def test_sort_by_wake_score_desc(session_with_data):
    """Test sorting fixtures by wake score descending."""
    result = await session_with_data.execute(
        select(Fixture).order_by(Fixture.wake_score.desc())
    )
    fixtures = result.scalars().all()
    
    scores = [f.wake_score for f in fixtures if f.wake_score is not None]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_sort_by_wake_score_asc(session_with_data):
    """Test sorting fixtures by wake score ascending."""
    result = await session_with_data.execute(
        select(Fixture).order_by(Fixture.wake_score.asc())
    )
    fixtures = result.scalars().all()
    
    scores = [f.wake_score for f in fixtures if f.wake_score is not None]
    assert scores == sorted(scores)


@pytest.mark.asyncio
async def test_sort_by_created_at_desc(session_with_data):
    """Test sorting fixtures by creation date descending."""
    result = await session_with_data.execute(
        select(Fixture).order_by(Fixture.created_at.desc())
    )
    fixtures = result.scalars().all()
    
    dates = [f.created_at for f in fixtures]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_sort_by_rate(session_with_data):
    """Test sorting fixtures by rate."""
    result = await session_with_data.execute(
        select(Fixture).order_by(Fixture.rate.desc())
    )
    fixtures = result.scalars().all()
    
    rates = [f.rate for f in fixtures if f.rate is not None]
    assert rates == sorted(rates, reverse=True)


# =============================================================================
# Ranking Tests
# =============================================================================

@pytest.mark.asyncio
async def test_fixtures_have_wake_scores(session_with_data):
    """Test that fixtures have wake scores."""
    result = await session_with_data.execute(select(Fixture))
    fixtures = result.scalars().all()
    
    # Check that at least some have wake scores
    scored = [f for f in fixtures if f.wake_score is not None]
    assert len(scored) > 0


@pytest.mark.asyncio
async def test_ranking_by_wake_score(session_with_data):
    """Test ranking fixtures by wake score."""
    result = await session_with_data.execute(
        select(Fixture).order_by(Fixture.wake_score.desc())
    )
    fixtures = result.scalars().all()
    
    # Verify sorted correctly
    for i in range(len(fixtures) - 1):
        if fixtures[i].wake_score is not None and fixtures[i + 1].wake_score is not None:
            assert fixtures[i].wake_score >= fixtures[i + 1].wake_score


@pytest.mark.asyncio
async def test_fixtures_have_tce_estimates(session_with_data):
    """Test that fixtures have TCE estimates."""
    result = await session_with_data.execute(select(Fixture))
    fixtures = result.scalars().all()
    
    with_tce = [f for f in fixtures if f.tce_estimate is not None]
    assert len(with_tce) > 0


@pytest.mark.asyncio
async def test_fixtures_have_market_diff(session_with_data):
    """Test that fixtures have market differential."""
    result = await session_with_data.execute(select(Fixture))
    fixtures = result.scalars().all()
    
    with_diff = [f for f in fixtures if f.market_diff is not None]
    assert len(with_diff) > 0


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_fixture_with_null_rate(db_session):
    """Test fixture without rate."""
    user = User(
        id=str(uuid4()),
        email="nullrate@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="No Rate Vessel",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=datetime.utcnow() + timedelta(days=7),
        laycan_end=datetime.utcnow() + timedelta(days=12),
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
        rate=None,
    )
    
    db_session.add(fixture)
    await db_session.commit()
    
    assert fixture.rate is None
    assert fixture.wake_score is None  # Can't score without rate


@pytest.mark.asyncio
async def test_fixture_laycan_order(db_session):
    """Test that laycan end is after start."""
    user = User(
        id=str(uuid4()),
        email="laycan@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    now = datetime.utcnow()
    fixture = Fixture(
        user_id=user.id,
        tenant_id=user.tenant_id,
        vessel_name="Laycan Test",
        cargo_type="Crude Oil",
        cargo_quantity=280000,
        laycan_start=now + timedelta(days=7),
        laycan_end=now + timedelta(days=12),
        port_loading="Ras Tanura",
        port_discharge="Ningbo",
    )
    
    assert fixture.laycan_start < fixture.laycan_end
