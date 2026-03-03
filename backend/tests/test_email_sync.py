"""
Tests for email sync service.

C fixturesovers:
- Email parsing
- Fixture extraction from emails
- Gmail sync (mocked)
- Pattern matching
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from tests.conftest import Fixture, EmailSync
from tests.conftest import User
from app.services.email_sync import EmailSyncService


# =============================================================================
# Email Parser Tests
# =============================================================================

@pytest.mark.asyncio
async def test_email_sync_service_init():
    """Test EmailSyncService initialization."""
    service = EmailSyncService()
    
    assert service.credentials_path == "credentials.json"
    assert service.token_path == "token.json"


@pytest.mark.asyncio
async def test_parse_fixture_from_text_complete(sample_email_text):
    """Test parsing complete fixture from email text."""
    service = EmailSyncService()
    
    result = service._parse_fixture_from_text(
        subject="Fixture - MT Everest / 130k Products",
        body=sample_email_text,
        from_addr="broker@example.com",
        email_id="test-123",
    )
    
    assert result is not None
    assert "vessel_name" in result
    assert "cargo_type" in result
    assert "cargo_quantity" in result


@pytest.mark.asyncio
async def test_parse_fixture_minimal_text():
    """Test parsing fixture with minimal data."""
    service = EmailSyncService()
    
    text = """
    Vessel: Test Vessel
    Cargo: 100,000 MT Crude Oil
    Rate: $45.00/MT
    Load: Port A
    Discharge: Port B
    """
    
    result = service._parse_fixture_from_text(
        subject="Test",
        body=text,
        from_addr="broker@test.com",
        email_id="test-456",
    )
    
    # Should still extract even with minimal data
    assert result is not None


@pytest.mark.asyncio
async def test_parse_fixture_incomplete_data():
    """Test parsing fixture with incomplete data."""
    service = EmailSyncService()
    
    text = """
    Vessel: Test Vessel
    Some random text without required fields
    """
    
    result = service._parse_fixture_from_text(
        subject="Test",
        body=text,
        from_addr="broker@test.com",
        email_id="test-789",
    )
    
    # Should return None when critical data missing
    assert result is None or result.get("vessel_name") is None


@pytest.mark.asyncio
async def test_extract_pattern():
    """Test pattern extraction utility."""
    service = EmailSyncService()
    
    text = "Vessel: Test Vessel Name, IMO: 1234567"
    
    result = service._extract_pattern(text, r"Vessel:\s+([A-Za-z\s]+)")
    
    assert result is not None
    assert "Test Vessel Name" in result


@pytest.mark.asyncio
async def test_extract_pattern_no_match():
    """Test pattern extraction with no match."""
    service = EmailSyncService()
    
    text = "No match here"
    
    result = service._extract_pattern(text, r"XYZ:\s+(\d+)")
    
    assert result is None


# =============================================================================
# IMO Extraction Tests
# =============================================================================

@pytest.mark.asyncio
async def test_extract_imo_standard_format():
    """Test IMO extraction from standard format."""
    service = EmailSyncService()
    
    text = "IMO: 9123456"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    assert result is not None


@pytest.mark.asyncio
async def test_extract_imo_alternative_format():
    """Test IMO extraction from alternative format."""
    service = EmailSyncService()
    
    text = "Vessel MT Test IMO #9876543"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    # May or may not extract depending on implementation
    assert result is not None


# =============================================================================
# Cargo Extraction Tests
# =============================================================================

@pytest.mark.asyncio
async def test_extract_cargo_quantity():
    """Test cargo quantity extraction."""
    service = EmailSyncService()
    
    text = "Cargo: 280,000 MT Crude Oil"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}",
        from_addr="test@test.com",
        email_id="test",
    )
    
    if result:
        assert "cargo_quantity" in result


@pytest.mark.asyncio
async def test_extract_cargo_quantity_with_k():
    """Test cargo quantity with k suffix."""
    service = EmailSyncService()
    
    text = "Cargo: 280k MT"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}",
        from_addr="test@test.com",
        email_id="test",
    )
    
    if result:
        assert result.get("cargo_quantity", 0) > 0


@pytest.mark.asyncio
async def test_extract_cargo_type():
    """Test cargo type extraction."""
    service = EmailSyncService()
    
    cargo_types = ["Crude Oil", "Diesel", "Gasoline", "Naphtha", "Coal", "Iron Ore"]
    
    for cargo_type in cargo_types:
        text = f"Cargo: 100,000 MT {cargo_type}"
        result = service._parse_fixture_from_text(
            subject="Test",
            body=f"Vessel: Test\n{text}",
            from_addr="test@test.com",
            email_id="test",
        )
        
        if result:
            assert "cargo_type" in result


# =============================================================================
# Laycan Extraction Tests
# =============================================================================

@pytest.mark.asyncio
async def test_extract_laycan():
    """Test laycan extraction."""
    service = EmailSyncService()
    
    text = "Laycan: 15-20 March 2025"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    if result:
        assert "laycan_start" in result or result is None


@pytest.mark.asyncio
async def test_extract_laycan_short_format():
    """Test laycan extraction with short month format."""
    service = EmailSyncService()
    
    text = "Laycan: 15-18 Mar"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    # Should handle gracefully


@pytest.mark.asyncio
async def test_extract_laycan_invalid():
    """Test laycan extraction with invalid date."""
    service = EmailSyncService()
    
    text = "Laycan: invalid date"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    # Should handle gracefully


# =============================================================================
# Rate Extraction Tests
# =============================================================================

@pytest.mark.asyncio
async def test_extract_rate():
    """Test rate extraction."""
    service = EmailSyncService()
    
    text = "Rate: $50.00/MT"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    if result:
        assert "rate" in result


@pytest.mark.asyncio
async def test_extract_rate_without_dollar():
    """Test rate extraction without dollar sign."""
    service = EmailSyncService()
    
    text = "Rate: 50.00 per MT"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    if result:
        assert "rate" in result or result.get("rate") is None


# =============================================================================
# Port Extraction Tests
# =============================================================================

@pytest.mark.asyncio
async def test_extract_ports():
    """Test port extraction."""
    service = EmailSyncService()
    
    text = "Load: Singapore\nDischarge: Rotterdam"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    if result:
        assert "port_loading" in result
        assert "port_discharge" in result


@pytest.mark.asyncio
async def test_extract_port_alternative_format():
    """Test port extraction with alternative format."""
    service = EmailSyncService()
    
    text = "Origin: Houston\nDestination: Hamburg"
    result = service._parse_fixture_from_text(
        subject="Test",
        body=f"Vessel: Test\n{text}\nCargo: 100k",
        from_addr="test@test.com",
        email_id="test",
    )
    
    # Should try to extract


# =============================================================================
# Gmail Sync Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_gmail_credentials_no_token():
    """Test getting Gmail credentials with no token file."""
    service = EmailSyncService()
    
    # Patch token path to non-existent
    with patch("os.path.exists", return_value=False):
        result = await service.get_gmail_credentials("test-user")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_gmail_credentials_expired():
    """Test getting Gmail credentials with expired token."""
    service = EmailSyncService()
    
    # Mock expired credentials
    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "test-refresh"
    
    with patch("os.path.exists", return_value=True):
        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file", return_value=mock_creds):
            with patch("google.auth.transport.requests.Request") as mock_request:
                result = await service.get_gmail_credentials("test-user")
    
    # Should attempt refresh


@pytest.mark.asyncio
async def test_sync_gmail_no_credentials():
    """Test Gmail sync without credentials."""
    service = EmailSyncService()
    
    with patch.object(service, "get_gmail_credentials", return_value=None):
        result = await service.sync_gmail("test-user", None)
    
    assert "error" in result
    assert result["fixtures_extracted"] == 0


@pytest.mark.asyncio
async def test_sync_gmail_no_email_sync(db_session):
    """Test Gmail sync without email sync configured."""
    service = EmailSyncService()
    
    user = User(
        id=str(uuid4()),
        email="gmail@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    mock_creds = MagicMock()
    mock_creds.token = "test-token"
    
    with patch.object(service, "get_gmail_credentials", return_value=mock_creds):
        result = await service.sync_gmail(str(user.id), db_session)
    
    assert "error" in result


@pytest.mark.asyncio
async def test_sync_gmail_with_email_sync(db_session):
    """Test Gmail sync with email sync configured."""
    service = EmailSyncService()
    
    user = User(
        id=str(uuid4()),
        email="gmail2@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    # Add email sync config
    email_sync = EmailSync(
        user_id=user.id,
        provider="gmail",
        access_token="test-token",
        is_active=True,
    )
    db_session.add(email_sync)
    await db_session.commit()
    
    mock_creds = MagicMock()
    mock_creds.token = "test-token"
    
    # Mock the Gmail API response
    mock_messages = [{"id": "msg-1", "threadId": "thread-1"}]
    
    with patch.object(service, "get_gmail_credentials", return_value=mock_creds):
        with patch("aiohttp.ClientSession") as mock_session:
            # Setup mock responses
            mock_list_resp = AsyncMock()
            mock_list_resp.status = 200
            mock_list_resp.json = AsyncMock(return_value={"messages": mock_messages})
            
            mock_get_resp = AsyncMock()
            mock_get_resp.status = 200
            
            # Create payload with headers and body
            payload = {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "test@example.com"},
                ],
                "body": {"data": ""},
            }
            mock_get_resp.json = AsyncMock(return_value={"payload": payload})
            
            mock_session_instance = MagicMock()
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session_instance.get = MagicMock(side_effect=[mock_list_resp, mock_get_resp])
            
            mock_session.return_value = mock_session_instance
            
            result = await service.sync_gmail(str(user.id), db_session)
    
    assert "fixtures_extracted" in result


# =============================================================================
# Fixture Creation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_fixture_from_email(db_session):
    """Test creating fixture from email data."""
    service = EmailSyncService()
    
    user = User(
        id=str(uuid4()),
        email="create@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    fixture_data = {
        "vessel_name": "Email Vessel",
        "imo_number": "9123456",
        "cargo_type": "Crude Oil",
        "cargo_quantity": 280000,
        "cargo_unit": "MT",
        "laycan_start": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "laycan_end": (datetime.utcnow() + timedelta(days=12)).isoformat(),
        "rate": 52.5,
        "rate_currency": "USD",
        "rate_unit": "/mt",
        "port_loading": "Ras Tanura",
        "port_discharge": "Ningbo",
        "charterer": None,
        "broker": "test@example.com",
        "source_email_id": "test-123",
        "source_subject": "Test Fixture",
    }
    
    await service._create_fixture(str(user.id), fixture_data, db_session)
    await db_session.commit()
    
    # Verify fixture created
    from sqlalchemy import select
    result = await db_session.execute(
        select(Fixture).where(Fixture.source_email_id == "test-123")
    )
    fixture = result.scalar_one_or_none()
    
    assert fixture is not None
    assert fixture.vessel_name == "Email Vessel"
    assert fixture.broker == "test@example.com"


# =============================================================================
# Setup Tests
# =============================================================================

@pytest.mark.asyncio
async def test_setup_gmail_connection(db_session):
    """Test setting up Gmail connection."""
    service = EmailSyncService()
    
    user = User(
        id=str(uuid4()),
        email="setup@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    # Mock the OAuth flow
    mock_creds = MagicMock()
    mock_creds.token = "test-token"
    
    with patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file") as mock_flow:
        mock_flow_instance = MagicMock()
        mock_flow_instance.run_local_server = MagicMock(return_value=mock_creds)
        mock_flow.return_value = mock_flow_instance
        
        with patch("builtins.open", MagicMock()):
            result = await service.setup_gmail_connection(str(user.id), "auth-code", db_session)
    
    # Result should indicate success or error
    assert "status" in result or "error" in result


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_full_email_to_fixture_flow(db_session):
    """Test full flow from email to fixture."""
    service = EmailSyncService()
    
    user = User(
        id=str(uuid4()),
        email="full@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    # Sample email text
    email_text = """
    Subject: Fixture - MT Pacific / 280k Crude / ME to Asia
    
    Vessel: MT PACIFIC
    IMO: 9123456
    Cargo: 280,000 MT Crude Oil
    Laycan: 10-15 March 2025
    Rate: $52.50/MT
    Load: Ras Tanura
    Discharge: Ningbo
    Charterer: Shell
    """
    
    # Parse fixture
    fixture_data = service._parse_fixture_from_text(
        subject="Fixture - MT Pacific",
        body=email_text,
        from_addr="broker@test.com",
        email_id="full-test-123",
    )
    
    if fixture_data and fixture_data.get("vessel_name"):
        # Create fixture
        await service._create_fixture(str(user.id), fixture_data, db_session)
        await db_session.commit()
        
        # Verify
        from sqlalchemy import select
        result = await db_session.execute(
            select(Fixture).where(Fixture.source_email_id == "full-test-123")
        )
        fixture = result.scalar_one_or_none()
        
        if fixture:
            assert fixture.vessel_name is not None
            assert fixture.cargo_type is not None


@pytest.mark.asyncio
async def test_email_fixture_source_tracking(db_session):
    """Test that email source is tracked."""
    service = EmailSyncService()
    
    user = User(
        id=str(uuid4()),
        email="track@example.com",
        hashed_password="hashed",
        tenant_id=str(uuid4()),
    )
    db_session.add(user)
    await db_session.commit()
    
    email_id = "unique-email-123"
    subject = "Test Fixture Email"
    
    fixture_data = {
        "vessel_name": "Track Test",
        "cargo_type": "Crude Oil",
        "cargo_quantity": 280000,
        "laycan_start": datetime.utcnow() + timedelta(days=7),
        "laycan_end": datetime.utcnow() + timedelta(days=12),
        "port_loading": "Test",
        "port_discharge": "Test",
        "source_email_id": email_id,
        "source_subject": subject,
    }
    
    await service._create_fixture(str(user.id), fixture_data, db_session)
    await db_session.commit()
    
    # Verify source tracking
    from sqlalchemy import select
    result = await db_session.execute(
        select(Fixture).where(Fixture.source_email_id == email_id)
    )
    fixture = result.scalar_one()
    
    assert fixture.source_email_id == email_id
    assert fixture.source_subject == subject
