"""
Simple JWT Authentication Test Script
Tests user registration, login, and protected endpoints
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_register():
    """Test user registration"""
    print("\n" + "="*60)
    print("TEST 1: User Registration")
    print("="*60)

    url = f"{BASE_URL}/auth/register"
    data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }

    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_login():
    """Test user login"""
    print("\n" + "="*60)
    print("TEST 2: User Login")
    print("="*60)

    url = f"{BASE_URL}/auth/login"
    data = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }

    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Access Token: {result.get('access_token', 'N/A')[:50]}...")
            print(f"Token Type: {result.get('token_type', 'N/A')}")
            print(f"Role: {result.get('role', 'N/A')}")
            return result.get('access_token')
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_protected_endpoint(access_token):
    """Test protected endpoint with JWT token"""
    print("\n" + "="*60)
    print("TEST 3: Protected Endpoint (GET /talent/opportunities)")
    print("="*60)

    url = f"{BASE_URL}/talent/opportunities"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Successfully accessed protected endpoint!")
            result = response.json()
            print(f"Found {len(result)} opportunities")
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_protected_endpoint_without_token():
    """Test protected endpoint without JWT token"""
    print("\n" + "="*60)
    print("TEST 4: Protected Endpoint Without Token")
    print("="*60)

    url = f"{BASE_URL}/talent/opportunities"

    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly rejected unauthorized request!")
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 401
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("JWT AUTHENTICATION TEST SUITE")
    print("="*60)
    print(f"Base URL: {BASE_URL}")

    # Test 1: Register
    register_success = test_register()

    # Test 2: Login
    access_token = test_login()

    # Test 3: Access protected endpoint with token
    if access_token:
        protected_success = test_protected_endpoint(access_token)
    else:
        protected_success = False
        print("\n❌ Skipping protected endpoint test - no access token obtained")

    # Test 4: Access protected endpoint without token
    unauthorized_success = test_protected_endpoint_without_token()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"1. Registration: {'✅ PASS' if register_success else '❌ FAIL'}")
    print(f"2. Login: {'✅ PASS' if access_token else '❌ FAIL'}")
    print(f"3. Protected Endpoint (with token): {'✅ PASS' if protected_success else '❌ FAIL'}")
    print(f"4. Protected Endpoint (without token): {'✅ PASS' if unauthorized_success else '❌ FAIL'}")

    all_passed = register_success and access_token and protected_success and unauthorized_success
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

if __name__ == "__main__":
    main()
