"""
Comprehensive System Test Script
Tests all major components of the FastAPI backend
"""
import sys
import os
import json
import requests
from datetime import datetime

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

BASE_URL = "http://localhost:8000"

def print_test(test_name, passed, message=""):
    """Print test result with color"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {test_name}")
    if message:
        print(f"  {message}")

def test_health_check():
    """Test basic health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        passed = response.status_code == 200
        data = response.json()
        print_test("Health Check", passed, f"Status: {data.get('status', 'N/A')}")
        return passed
    except Exception as e:
        print_test("Health Check", False, str(e))
        return False

def test_swagger_docs():
    """Test Swagger documentation is accessible"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        passed = response.status_code == 200
        print_test("Swagger Documentation", passed)
        return passed
    except Exception as e:
        print_test("Swagger Documentation", False, str(e))
        return False

def test_openapi_schema():
    """Test OpenAPI schema is available"""
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        passed = response.status_code == 200
        data = response.json()
        routes = len(data.get('paths', {}))
        print_test("OpenAPI Schema", passed, f"Routes found: {routes}")
        return passed
    except Exception as e:
        print_test("OpenAPI Schema", False, str(e))
        return False

def test_cors():
    """Test CORS headers are present"""
    try:
        response = requests.options(f"{BASE_URL}/health", timeout=5)
        headers = response.headers
        cors_headers = ['access-control-allow-origin', 'access-control-allow-methods']
        has_cors = all(h in headers for h in cors_headers)
        print_test("CORS Middleware", has_cors)
        return has_cors
    except Exception as e:
        print_test("CORS Middleware", False, str(e))
        return False

def test_rate_limiting():
    """Test rate limiting is working"""
    try:
        # Make multiple requests quickly
        responses = []
        for _ in range(35):  # Slightly above limit of 30
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            responses.append(response.status_code)

        # Check if any request was rate limited
        rate_limited = 429 in responses
        print_test("Rate Limiting", rate_limited, f"Rate limited after {len(responses)} requests")
        return rate_limited
    except Exception as e:
        print_test("Rate Limiting", False, str(e))
        return False

def test_talent_match():
    """Test talent matching endpoint"""
    try:
        payload = {
            "business_needs": "Need help with social media posts for my coffee shop",
            "industry": "Food & Beverage",
            "role_type": "Marketing",
            "skills_required": ["Instagram", "content creation", "social media"],
            "experience_level": "Intermediate",
            "budget_range": "30-50 CHF",
            "availability": "Part-time",
            "timezone": "CET"
        }
        response = requests.post(f"{BASE_URL}/talent/match", json=payload, timeout=30)
        passed = response.status_code == 200
        if passed:
            data = response.json()
            matches = len(data.get('matches', []))
            print_test("Talent Matching", passed, f"Found {matches} matches")
        else:
            print_test("Talent Matching", False, f"Status: {response.status_code}")
        return passed
    except Exception as e:
        print_test("Talent Matching", False, str(e))
        return False

def test_agents_list():
    """Test agents listing endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/talent/agents", timeout=10)
        passed = response.status_code == 200
        if passed:
            agents = response.json()
            count = len(agents)
            print_test("Agents List", passed, f"Found {count} agents")
        else:
            print_test("Agents List", False, f"Status: {response.status_code}")
        return passed
    except Exception as e:
        print_test("Agents List", False, str(e))
        return False

def test_database_connection():
    """Test database is accessible"""
    try:
        from database import SessionLocal, engine
        from models.agent import Agent

        # Test database connection
        db = SessionLocal()
        try:
            # Try to query agents
            agents = db.query(Agent).filter(Agent.is_published == True).all()
            count = len(agents)
            print_test("Database Connection", True, f"Found {count} published agents")
            return True
        finally:
            db.close()
    except Exception as e:
        print_test("Database Connection", False, str(e))
        return False

def test_environment_variables():
    """Test environment variables are loaded"""
    try:
        from config import settings

        tests = []
        tests.append(("APP_NAME", bool(settings.APP_NAME)))
        tests.append(("DATABASE_URL", bool(settings.DATABASE_URL)))
        tests.append(("SECRET_KEY", bool(settings.SECRET_KEY)))
        tests.append(("CORS Origins", bool(settings.ALLOWED_ORIGINS)))

        all_passed = all(passed for _, passed in tests)
        details = ", ".join([f"{name}: {'✓' if passed else '✗'}" for name, passed in tests])
        print_test("Environment Variables", all_passed, details)
        return all_passed
    except Exception as e:
        print_test("Environment Variables", False, str(e))
        return False

def main():
    """Run all tests"""
    print(f"\n{'='*60}")
    print(f"FastAPI Backend System Test")
    print(f"{'='*60}\n")

    print(f"{YELLOW}Testing Core Components...{RESET}\n")

    results = {
        "Health Check": test_health_check(),
        "Swagger Documentation": test_swagger_docs(),
        "OpenAPI Schema": test_openapi_schema(),
        "Environment Variables": test_environment_variables(),
        "Database Connection": test_database_connection(),
        "CORS Middleware": test_cors(),
        "Rate Limiting": test_rate_limiting(),
        "Talent Matching": test_talent_match(),
        "Agents List": test_agents_list(),
    }

    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{GREEN}✓{RESET}" if result else f"{RED}✗{RESET}"
        print(f"{status} {test_name}")

    print(f"\n{YELLOW}Results: {passed}/{total} tests passed{RESET}\n")

    if passed == total:
        print(f"{GREEN}All tests passed! System is working correctly.{RESET}")
        return 0
    else:
        print(f"{RED}Some tests failed. Please review the errors above.{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
