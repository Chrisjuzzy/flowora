#!/usr/bin/env python3
"""
Comprehensive Health and Functionality Scan for All Modules
Tests all endpoints for connectivity, functionality, status codes, and performance
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import sys

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on different port
TIMEOUT = 30  # seconds
RESULTS = {}

# Test credentials (adjust as needed)
TEST_USER = {
    "email": "test@example.com",
    "password": "testpass123"
}

# Module endpoints to test
MODULES = {
    "auth": {
        "endpoints": [
            {"path": "/auth/register", "method": "POST", "data": TEST_USER},
            {"path": "/auth/login", "method": "POST", "data": TEST_USER},
            {"path": "/auth/me", "method": "GET", "auth_required": True}
        ]
    },
    "agents": {
        "endpoints": [
            {"path": "/agents", "method": "GET", "auth_required": True},
            {"path": "/agents", "method": "POST", "auth_required": True, "data": {"name": "Test Agent", "description": "Test"}}
        ]
    },
    "executions": {
        "endpoints": [
            {"path": "/executions", "method": "GET", "auth_required": True}
        ]
    },
    "workflows": {
        "endpoints": [
            {"path": "/workflows", "method": "GET", "auth_required": True}
        ]
    },
    "marketplace": {
        "endpoints": [
            {"path": "/marketplace/agents", "method": "GET"},
            {"path": "/marketplace/templates", "method": "GET"}
        ]
    },
    "schedules": {
        "endpoints": [
            {"path": "/schedules", "method": "GET", "auth_required": True}
        ]
    },
    "intelligence": {
        "endpoints": [
            {"path": "/intelligence/insights", "method": "GET", "auth_required": True}
        ]
    },
    "workspaces": {
        "endpoints": [
            {"path": "/workspaces", "method": "GET", "auth_required": True}
        ]
    },
    "billing": {
        "endpoints": [
            {"path": "/billing/subscription", "method": "GET", "auth_required": True},
            {"path": "/billing/usage", "method": "GET", "auth_required": True}
        ]
    },
    "innovation": {
        "endpoints": [
            {"path": "/innovation/goals", "method": "GET", "auth_required": True}
        ]
    },
    "deployment": {
        "endpoints": [
            {"path": "/deployment/metrics", "method": "GET"},
            {"path": "/deployment/templates", "method": "GET"}
        ]
    },
    "admin": {
        "endpoints": [
            {"path": "/admin/users", "method": "GET", "auth_required": True, "admin_required": True}
        ]
    },
    "growth": {
        "endpoints": [
            {"path": "/growth/showcase/trending", "method": "GET"},
            {"path": "/growth/insights", "method": "GET", "auth_required": True}
        ]
    },
    "wallet": {
        "endpoints": [
            {"path": "/wallet/balance", "method": "GET", "auth_required": True}
        ]
    },
    "talent": {
        "endpoints": [
            {"path": "/talent/opportunities", "method": "GET", "auth_required": True}
        ]
    },
    "compliance": {
        "endpoints": [
            {"path": "/compliance/scan", "method": "POST", "data": {"target": "test", "scan_type": "quick"}}
        ]
    },
    "code-auditor": {
        "endpoints": [
            {"path": "/code/audit", "method": "POST", "data": {
                "source_type": "snippet",
                "content": "print('hello')",
                "language": "python"
            }}
        ]
    },
    "wellness": {
        "endpoints": [
            {"path": "/wellness/analyze", "method": "POST", "data": {
                "repo_path": "/tmp/test",
                "developer_email": "test@example.com"
            }}
        ]
    },
    "infra-optimizer": {
        "endpoints": [
            {"path": "/infra/analyze", "method": "GET"}
        ]
    },
    "ethics-guardian": {
        "endpoints": [
            {"path": "/ethics/scan", "method": "POST", "data": {"content": "test"}}
        ]
    }
}

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_result(status: str, message: str):
    """Print a formatted result"""
    symbols = {
        "PASS": "✅",
        "FAIL": "❌",
        "WARN": "⚠️",
        "INFO": "ℹ️"
    }
    print(f"{symbols.get(status, '•')} {message}")

def test_endpoint(module_name: str, endpoint: Dict, auth_token: str = None) -> Dict[str, Any]:
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint['path']}"
    method = endpoint['method']
    headers = {}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'

    try:
        start_time = time.time()

        if method == "GET":
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
        elif method == "POST":
            response = requests.post(
                url, 
                headers=headers, 
                json=endpoint.get('data', {}),
                timeout=TIMEOUT
            )
        elif method == "PUT":
            response = requests.put(
                url,
                headers=headers,
                json=endpoint.get('data', {}),
                timeout=TIMEOUT
            )
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=TIMEOUT)
        else:
            return {
                "status": "FAIL",
                "error": f"Unsupported method: {method}",
                "response_time": 0
            }

        response_time = time.time() - start_time

        result = {
            "status": "PASS" if response.status_code == 200 else "FAIL",
            "status_code": response.status_code,
            "response_time": response_time,
            "url": url,
            "method": method
        }

        if response.status_code != 200:
            result["error"] = f"Expected 200, got {response.status_code}"
            try:
                result["error_details"] = response.json()
            except:
                result["error_details"] = response.text

        return result

    except requests.exceptions.Timeout:
        return {
            "status": "FAIL",
            "error": "Request timed out",
            "response_time": TIMEOUT,
            "url": url
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "FAIL",
            "error": "Connection refused - server may not be running",
            "response_time": 0,
            "url": url
        }
    except Exception as e:
        return {
            "status": "FAIL",
            "error": str(e),
            "response_time": 0,
            "url": url
        }

def get_auth_token() -> str:
    """Get authentication token"""
    try:
        # First register user if not exists (ignore error if already exists)
        try:
            register_response = requests.post(
                f"{BASE_URL}/auth/register",
                json=TEST_USER,
                timeout=TIMEOUT
            )
        except:
            pass  # User might already exist, that's fine

        # Try to login
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json=TEST_USER,
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token") or data.get("token")
            if token:
                print(f"✅ Authentication successful")
                return token
            else:
                print(f"⚠️ No token in response: {data}")
        else:
            print(f"⚠️ Login failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ Authentication error: {str(e)}")
    return None

def scan_module(module_name: str, module_config: Dict, auth_token: str = None) -> Dict[str, Any]:
    """Scan a single module"""
    print(f"\nScanning module: {module_name}")
    print(f"{'-'*60}")

    results = {
        "module": module_name,
        "endpoints": [],
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "avg_response_time": 0
    }

    for endpoint in module_config.get("endpoints", []):
        # Skip admin endpoints if not admin
        if endpoint.get("admin_required") and not auth_token:
            print_result("WARN", f"Skipping admin endpoint: {endpoint['path']}")
            continue

        result = test_endpoint(module_name, endpoint, auth_token)
        results["endpoints"].append(result)
        results["total_tests"] += 1

        if result["status"] == "PASS":
            results["passed"] += 1
            print_result("PASS", f"{endpoint['method']} {endpoint['path']} - {result['response_time']:.3f}s")
        else:
            results["failed"] += 1
            print_result("FAIL", f"{endpoint['method']} {endpoint['path']} - {result.get('error', 'Unknown error')}")

    # Calculate average response time
    if results["endpoints"]:
        response_times = [e.get("response_time", 0) for e in results["endpoints"]]
        results["avg_response_time"] = sum(response_times) / len(response_times)

    return results

def generate_report(all_results: Dict[str, Any]):
    """Generate comprehensive report"""
    print_header("COMPREHENSIVE SCAN REPORT")

    # Summary
    total_tests = sum(r["total_tests"] for r in all_results.values())
    total_passed = sum(r["passed"] for r in all_results.values())
    total_failed = sum(r["failed"] for r in all_results.values())

    print(f"Total Modules Tested: {len(all_results)}")
    print(f"Total Endpoints Tested: {total_tests}")
    print(f"Passed: {total_passed} ({(total_passed/total_tests*100):.1f}%)")
    print(f"Failed: {total_failed} ({(total_failed/total_tests*100):.1f}%)")

    # Module by module results
    print_header("MODULE RESULTS")

    for module_name, results in all_results.items():
        print(f"\n{module_name.upper()}")
        print(f"{'-'*60}")
        print(f"Tests: {results['total_tests']} | Passed: {results['passed']} | Failed: {results['failed']}")
        print(f"Avg Response Time: {results['avg_response_time']:.3f}s")

        if results["failed"] > 0:
            print("\nFailed Endpoints:")
            for endpoint in results["endpoints"]:
                if endpoint["status"] == "FAIL":
                    print(f"  - {endpoint['method']} {endpoint['url']}")
                    print(f"    Error: {endpoint.get('error', 'Unknown')}")

    # Performance issues
    print_header("PERFORMANCE ANALYSIS")

    slow_modules = [
        (name, res["avg_response_time"])
        for name, res in all_results.items()
        if res["avg_response_time"] > 1.0  # More than 1 second
    ]

    if slow_modules:
        print("Slow Modules (>1s avg response time):")
        for module_name, avg_time in sorted(slow_modules, key=lambda x: x[1], reverse=True):
            print(f"  - {module_name}: {avg_time:.3f}s")
    else:
        print("✓ All modules performing well (<1s avg response time)")

    # Failed modules
    print_header("CRITICAL ISSUES")

    failed_modules = [
        name for name, res in all_results.items()
        if res["failed"] > 0
    ]

    if failed_modules:
        print("Modules with Failures:")
        for module_name in failed_modules:
            print(f"  - {module_name}")
    else:
        print("✓ All modules passed successfully")

    # Recommendations
    print_header("RECOMMENDATIONS")

    if total_failed > 0:
        print("\n1. Address Failed Endpoints:")
        for module_name in failed_modules:
            print(f"   - Review {module_name} module for errors")
            print(f"   - Check server logs for detailed error messages")

    if slow_modules:
        print("\n2. Optimize Performance:")
        for module_name, _ in slow_modules:
            print(f"   - Consider caching for {module_name}")
            print(f"   - Review database queries in {module_name}")

    print("\n3. General Recommendations:")
    print("   - Implement rate limiting for public endpoints")
    print("   - Add monitoring and alerting for response times")
    print("   - Consider implementing health check endpoints")
    print("   - Add comprehensive logging for debugging")

    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"scan_report_{timestamp}.json"

    with open(report_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nDetailed results saved to: {report_file}")

def main():
    """Main execution function"""
    print_header("STARTING COMPREHENSIVE SYSTEM SCAN")
    print(f"Target: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Get authentication token
    print("\nAttempting authentication...")
    auth_token = get_auth_token()

    if auth_token:
        print_result("PASS", "Authentication successful")
    else:
        print_result("WARN", "Authentication failed - some endpoints may fail")

    # Scan all modules
    all_results = {}

    for module_name, module_config in MODULES.items():
        results = scan_module(module_name, module_config, auth_token)
        all_results[module_name] = results

    # Generate report
    generate_report(all_results)

    print_header("SCAN COMPLETE")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        sys.exit(1)
