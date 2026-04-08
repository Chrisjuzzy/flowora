
"""
Tests for Cyber Compliance Sentinel
"""
import pytest
from fastapi.testclient import TestClient


def test_compliance_scan_success(client):
    """Test successful compliance scan"""
    system_info = {
        "system_type": "web",
        "tech_stack": ["python", "fastapi"],
        "target": "example.com",
        "scan_type": "quick"
    }

    response = client.post("/compliance/scan", json=system_info)

    assert response.status_code == 200
    data = response.json()
    assert "scan_id" in data
    assert "vulnerabilities" in data
    assert "fixes" in data
    assert "summary" in data
    assert "scan_time" in data


def test_compliance_scan_invalid_target(client):
    """Test compliance scan with invalid target"""
    system_info = {
        "system_type": "web",
        "tech_stack": ["python"],
        "target": "invalid_target_format",
        "scan_type": "quick"
    }

    response = client.post("/compliance/scan", json=system_info)

    # Should handle invalid target gracefully
    assert response.status_code in [200, 400]


def test_compliance_scan_validation_error(client):
    """Test compliance scan with invalid input"""
    # Missing required fields
    system_info = {
        "system_type": "web"
        # Missing target and scan_type
    }

    response = client.post("/compliance/scan", json=system_info)

    assert response.status_code == 422  # Validation error


def test_compliance_scan_custom_options(client):
    """Test compliance scan with custom options"""
    system_info = {
        "system_type": "api",
        "tech_stack": ["python", "fastapi"],
        "target": "api.example.com",
        "scan_type": "custom",
        "custom_options": {
            "ports": [80, 443, 8080],
            "timeout": 60
        }
    }

    response = client.post("/compliance/scan", json=system_info)

    assert response.status_code == 200
    data = response.json()
    assert "scan_id" in data


def test_compliance_scan_full_scan(client):
    """Test full compliance scan"""
    system_info = {
        "system_type": "web",
        "tech_stack": ["python", "fastapi", "postgresql"],
        "target": "example.com",
        "scan_type": "full"
    }

    response = client.post("/compliance/scan", json=system_info)

    assert response.status_code == 200
    data = response.json()
    assert "scan_id" in data
    assert "vulnerabilities" in data


def test_compliance_scan_report_structure(client):
    """Test that compliance scan report has correct structure"""
    system_info = {
        "system_type": "web",
        "tech_stack": ["python"],
        "target": "example.com",
        "scan_type": "quick"
    }

    response = client.post("/compliance/scan", json=system_info)

    assert response.status_code == 200
    data = response.json()

    # Check summary structure
    assert "total_vulnerabilities" in data["summary"]
    assert "critical" in data["summary"]
    assert "high" in data["summary"]
    assert "medium" in data["summary"]
    assert "low" in data["summary"]

    # Check vulnerability structure if any
    if data["vulnerabilities"]:
        vuln = data["vulnerabilities"][0]
        assert "id" in vuln
        assert "severity" in vuln
        assert "title" in vuln
        assert "description" in vuln
