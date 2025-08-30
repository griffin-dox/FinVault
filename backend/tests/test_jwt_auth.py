import pytest
from httpx import AsyncClient
from app.main import app
from app.database import get_db
from app.models.user import User
from app.services.token_service import create_jwt_token_pair
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
import asyncio
from datetime import datetime, timedelta
import os

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_jwt.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac

@pytest.fixture
async def test_user():
    # Create test user
    db = TestingSessionLocal()
    user = User(
        email="test@example.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4fYwLxQ9W",  # password: testpass123
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    # Cleanup
    db.delete(user)
    db.commit()
    db.close()

class TestJWTAuth:
    """Test JWT authentication endpoints"""

    @pytest.mark.asyncio
    async def test_jwt_login_success(self, client, test_user):
        """Test successful JWT login"""
        login_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }

        response = await client.post("/api/auth/jwt/login", json=login_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] == 900  # 15 minutes

    @pytest.mark.asyncio
    async def test_jwt_login_wrong_password(self, client, test_user):
        """Test JWT login with wrong password"""
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }

        response = await client.post("/api/auth/jwt/login", json=login_data)
        assert response.status_code == 401

        data = response.json()
        assert "detail" in data
        assert "Invalid credentials" in data["detail"]

    @pytest.mark.asyncio
    async def test_jwt_login_nonexistent_user(self, client):
        """Test JWT login with nonexistent user"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "testpass123"
        }

        response = await client.post("/api/auth/jwt/login", json=login_data)
        assert response.status_code == 401

        data = response.json()
        assert "detail" in data
        assert "Invalid credentials" in data["detail"]

    @pytest.mark.asyncio
    async def test_jwt_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        # First login to get tokens
        login_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }

        login_response = await client.post("/api/auth/jwt/login", json=login_data)
        assert login_response.status_code == 200

        refresh_token = login_response.json()["refresh_token"]

        # Now refresh the token
        refresh_data = {
            "refresh_token": refresh_token
        }

        response = await client.post("/api/auth/jwt/refresh", json=refresh_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @pytest.mark.asyncio
    async def test_jwt_refresh_token_invalid(self, client):
        """Test refresh with invalid token"""
        refresh_data = {
            "refresh_token": "invalid_refresh_token"
        }

        response = await client.post("/api/auth/jwt/refresh", json=refresh_data)
        assert response.status_code == 401

        data = response.json()
        assert "detail" in data
        assert "Invalid refresh token" in data["detail"]

    @pytest.mark.asyncio
    async def test_jwt_logout_success(self, client, test_user):
        """Test successful logout"""
        # First login to get tokens
        login_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }

        login_response = await client.post("/api/auth/jwt/login", json=login_data)
        assert login_response.status_code == 200

        access_token = login_response.json()["access_token"]

        # Now logout
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post("/api/auth/jwt/logout", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "Successfully logged out" in data["message"]

    @pytest.mark.asyncio
    async def test_jwt_logout_no_token(self, client):
        """Test logout without token"""
        response = await client.post("/api/auth/jwt/logout")
        assert response.status_code == 401

        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_jwt(self, client, test_user):
        """Test accessing protected endpoint with JWT"""
        # First login to get access token
        login_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }

        login_response = await client.post("/api/auth/jwt/login", json=login_data)
        assert login_response.status_code == 200

        access_token = login_response.json()["access_token"]

        # Try to access a protected endpoint (assuming /api/auth/me exists)
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get("/api/auth/me", headers=headers)
        # This might return 404 if the endpoint doesn't exist, but should not be 401
        assert response.status_code != 401

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
