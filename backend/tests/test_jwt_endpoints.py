#!/usr/bin/env python3
"""
Simple test script for JWT authentication endpoints
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_jwt_endpoints():
    """Test JWT login, refresh, and logout endpoints"""

    base_url = "http://localhost:8000"

    print("Testing JWT Authentication Endpoints")
    print("=" * 50)

    async with httpx.AsyncClient(base_url=base_url) as client:
        # Test 1: JWT Login with valid credentials
        print("\n1. Testing JWT Login (valid credentials)")
        login_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }

        try:
            response = await client.post("/api/auth/jwt/login", json=login_data)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("✅ Login successful!")
                print(f"Token Type: {data.get('token_type')}")
                print(f"Expires In: {data.get('expires_in')} seconds")
                print(f"Access Token: {data.get('access_token')[:50]}...")
                print(f"Refresh Token: {data.get('refresh_token')[:50]}...")

                access_token = data.get('access_token')
                refresh_token = data.get('refresh_token')
            else:
                print(f"❌ Login failed: {response.text}")
                return

        except Exception as e:
            print(f"❌ Login error: {e}")
            return

        # Test 2: JWT Refresh Token
        print("\n2. Testing JWT Refresh Token")
        refresh_data = {
            "refresh_token": refresh_token
        }

        try:
            response = await client.post("/api/auth/jwt/refresh", json=refresh_data)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("✅ Token refresh successful!")
                print(f"New Access Token: {data.get('access_token')[:50]}...")
                new_access_token = data.get('access_token')
            else:
                print(f"❌ Token refresh failed: {response.text}")

        except Exception as e:
            print(f"❌ Refresh error: {e}")

        # Test 3: JWT Logout
        print("\n3. Testing JWT Logout")
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = await client.post("/api/auth/jwt/logout", headers=headers)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("✅ Logout successful!")
                print(f"Message: {data.get('message')}")
            else:
                print(f"❌ Logout failed: {response.text}")

        except Exception as e:
            print(f"❌ Logout error: {e}")

        # Test 4: JWT Login with invalid credentials
        print("\n4. Testing JWT Login (invalid credentials)")
        invalid_login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }

        try:
            response = await client.post("/api/auth/jwt/login", json=invalid_login_data)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 401:
                print("✅ Invalid credentials properly rejected!")
            else:
                print(f"❌ Unexpected response: {response.text}")

        except Exception as e:
            print(f"❌ Invalid login test error: {e}")

        # Test 5: JWT Refresh with invalid token
        print("\n5. Testing JWT Refresh (invalid token)")
        invalid_refresh_data = {
            "refresh_token": "invalid_refresh_token"
        }

        try:
            response = await client.post("/api/auth/jwt/refresh", json=invalid_refresh_data)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 401:
                print("✅ Invalid refresh token properly rejected!")
            else:
                print(f"❌ Unexpected response: {response.text}")

        except Exception as e:
            print(f"❌ Invalid refresh test error: {e}")

        # Test 6: JWT Logout without token
        print("\n6. Testing JWT Logout (no token)")
        try:
            response = await client.post("/api/auth/jwt/logout")
            print(f"Status Code: {response.status_code}")

            if response.status_code == 401:
                print("✅ Unauthorized logout properly rejected!")
            else:
                print(f"❌ Unexpected response: {response.text}")

        except Exception as e:
            print(f"❌ No token logout test error: {e}")

    print("\n" + "=" * 50)
    print("JWT Endpoint Testing Complete!")

if __name__ == "__main__":
    # Note: Make sure the FastAPI server is running on localhost:8000
    print("Make sure to start the FastAPI server first:")
    print("cd backend && python -m uvicorn app.main:app --reload")
    print()

    asyncio.run(test_jwt_endpoints())
