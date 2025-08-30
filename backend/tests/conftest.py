"""
Test configuration and fixtures for FinVault backend tests.
"""
import os

# Set test environment BEFORE any imports
os.environ["ENVIRONMENT"] = "test"

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-testing-only")
os.environ.setdefault("POSTGRES_URI", "postgresql+asyncpg://test:test@localhost:5432/test_db")
# Don't set MONGODB_URI or REDIS_URI to ensure they are None in tests
# os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/test_db")
# os.environ.setdefault("REDIS_URI", "redis://localhost:6379/1")

from app.database import AsyncSessionLocal, mongo_db, redis_client, get_db
from app.main import app
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import Base  # Import Base from the user model


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine using SQLite."""
    from sqlalchemy import create_engine
    from app.models.user import Base
    
    # Use SQLite for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Create tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Create a test database session."""
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def async_client(test_db_session):
    """Create an async test client for FastAPI."""
    import asyncio
    from httpx import AsyncClient
    
    # Create an async wrapper for the sync session
    class AsyncSessionWrapper:
        def __init__(self, sync_session):
            self.sync_session = sync_session
        
        async def execute(self, *args, **kwargs):
            return self.sync_session.execute(*args, **kwargs)
        
        async def commit(self):
            self.sync_session.commit()
        
        async def rollback(self):
            self.sync_session.rollback()
        
        async def close(self):
            self.sync_session.close()
        
        async def refresh(self, *args, **kwargs):
            return self.sync_session.refresh(*args, **kwargs)
        
        def add(self, *args, **kwargs):
            self.sync_session.add(*args, **kwargs)
        
        def __getattr__(self, name):
            return getattr(self.sync_session, name)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Override the get_db dependency to use test database session
    async def override_get_db():
        yield AsyncSessionWrapper(test_db_session)
    
    app.dependency_overrides[get_db] = override_get_db
    
    client = AsyncClient(app=app, base_url="http://testserver")
    
    yield client
    
    # Clean up
    loop.run_until_complete(client.aclose())
    loop.close()


@pytest.fixture(scope="function")
def sync_client() -> TestClient:
    """Create a synchronous test client for FastAPI."""
    return TestClient(app)


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "is_verified": True,
        "role": "user"
    }


@pytest.fixture
def sample_transaction_data() -> Dict[str, Any]:
    """Sample transaction data for testing."""
    return {
        "user_id": 1,
        "amount": 10.0,  # Small amount to avoid large_amount rule
        "target_account": "ACC123456",
        "device_info": "chrome-windows-123",  # Match the behavior profile
        "location": "New York, US",  # Match the behavior profile
        "intent": "Purchase"
    }


@pytest.fixture
def sample_behavior_profile() -> Dict[str, Any]:
    """Sample behavior profile for testing."""
    return {
        "user_id": 1,
        "device_fingerprint": "chrome-windows-123",
        "location": "New York, US",
        "typing_pattern": {
            "wpm": 60,
            "error_rate": 0.02
        },
        "known_networks": ["192.168.1.0/24"]
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_client.setex.return_value = True
    mock_client.ping.return_value = True
    return mock_client


@pytest.fixture
def mock_mongo():
    """Mock MongoDB client."""
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    
    # Set up return values for common operations
    mock_collection.find_one.return_value = None
    mock_collection.insert_one.return_value = AsyncMock(inserted_id="test_id")
    mock_collection.update_one.return_value = AsyncMock(modified_count=1)
    mock_collection.delete_one.return_value = AsyncMock(deleted_count=1)
    mock_collection.delete_many.return_value = AsyncMock(deleted_count=1)
    
    # Mock cursor for find operations
    mock_cursor = AsyncMock()
    mock_cursor.to_list.return_value = []
    mock_collection.find.return_value = mock_cursor

    # Set up all collections used by the services
    collections = [
        'behavior_profiles', 'ip_addresses', 'devices', 'device_ip_events',
        'known_network_counters', 'geo_events', 'risk_feedback', 'stepup_logs',
        'magic_links', 'users', 'webauthn_credentials', 'trusted_devices'
    ]
    
    for collection_name in collections:
        setattr(mock_db, collection_name, mock_collection)

    return mock_db


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch, mock_redis, mock_mongo):
    """Mock external services for all tests."""
    # Ensure MongoDB and Redis URIs are None to prevent real connections
    monkeypatch.setattr("app.database.MONGODB_URI", None)
    monkeypatch.setattr("app.database.REDIS_URI", None)
    
    # Mock the database clients
    monkeypatch.setattr("app.database.mongo_db", mock_mongo)
    monkeypatch.setattr("app.database.redis_client", mock_redis)
    
    # Also patch the telemetry service imports
    monkeypatch.setattr("app.services.telemetry_service.mongo_db", mock_mongo)
    monkeypatch.setattr("app.services.telemetry_service.redis_client", mock_redis)
    
    # Patch the auth module imports specifically
    monkeypatch.setattr("app.api.auth.mongo_db", mock_mongo)
    monkeypatch.setattr("app.api.auth.redis_client", mock_redis)


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    with patch("app.services.email_service.send_magic_link_email") as mock_send:
        mock_send.return_value = True
        yield mock_send


@pytest.fixture
def mock_sms_service():
    """Mock SMS service."""
    with patch("app.services.sms_service.send_magic_link_sms") as mock_send:
        mock_send.return_value = True
        yield mock_send
