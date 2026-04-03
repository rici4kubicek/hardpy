#!/usr/bin/env python3
"""Test script to verify session token validation is working correctly."""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin"

def test_authentication():
    """Test that session token validation is working."""
    
    print("=" * 60)
    print("Testing Session Token Validation Security Fix")
    print("=" * 60)
    
    # Test 1: Unauthenticated request should fail
    print("\n[Test 1] Request without token should return 401")
    response = requests.get(f"{BASE_URL}/api/start")
    print(f"Status: {response.status_code}")
    print(f"Expected: 401")
    if response.status_code == 401:
        print("✓ PASS: Unauthenticated request rejected")
    else:
        print("✗ FAIL: Should have returned 401")
        return False
    
    # Test 2: Login to get token
    print("\n[Test 2] Login to get session token")
    login_data = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(f"{BASE_URL}/api/login", json=login_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        token = response.json().get("session_token")
        user = response.json().get("user")
        print(f"✓ PASS: Login successful")
        print(f"  User: {user}")
        print(f"  Token: {token[:20]}...")
    else:
        print("✗ FAIL: Login failed")
        print(f"Response: {response.text}")
        return False
    
    # Test 3: Request with valid token should succeed
    print("\n[Test 3] Request with valid Bearer token should succeed")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/start", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Expected: 200")
    if response.status_code == 200:
        print("✓ PASS: Authenticated request accepted")
    else:
        print("✗ FAIL: Should have accepted valid token")
        print(f"Response: {response.text}")
        return False
    
    # Test 4: Request with invalid token should fail
    print("\n[Test 4] Request with invalid token should return 401")
    headers = {"Authorization": "Bearer invalid_token_12345"}
    response = requests.get(f"{BASE_URL}/api/start", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Expected: 401")
    if response.status_code == 401:
        print("✓ PASS: Invalid token rejected")
    else:
        print("✗ FAIL: Should have rejected invalid token")
        return False
    
    # Test 5: Request with x-session-token header should also work
    print("\n[Test 5] Request with x-session-token header should succeed")
    headers = {"x-session-token": token}
    response = requests.get(f"{BASE_URL}/api/status", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ PASS: x-session-token header works")
    else:
        print("Note: This endpoint may not require auth, trying authenticated endpoint")
        response = requests.get(f"{BASE_URL}/api/start", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ PASS: x-session-token header works with authenticated endpoint")
        else:
            print("✗ FAIL: x-session-token header should work")
            return False
    
    # Test 6: Logout should invalidate token
    print("\n[Test 6] Logout should invalidate session token")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/api/logout", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ PASS: Logout successful")
    else:
        print("Note: Logout may not require strict auth")
        print(f"Response: {response.text}")
    
    # Test 7: Request with old token after logout should fail
    print("\n[Test 7] Request with token after logout should return 401")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/start", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Expected: 401")
    if response.status_code == 401:
        print("✓ PASS: Token invalidated after logout")
    else:
        print("✗ FAIL: Token should be invalidated after logout")
        print(f"Response: {response.text}")
        return False
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_authentication()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print("Make sure the server is running on http://localhost:8000")
        sys.exit(1)

