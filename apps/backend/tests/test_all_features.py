
"""
Comprehensive integration tests for all Flowora features
"""
import pytest
from fastapi.testclient import TestClient


def test_all_features_health_check(client):
    """Test that all feature routers are accessible"""
    # Test health check
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_all_features_endpoints_exist(client):
    """Test that all feature endpoints are registered"""
    endpoints = [
        "/talent/match",
        "/talent/agents",
        "/compliance/scan",
        "/code/audit",
        "/wellness/analyze",
        "/infra/optimize",
        "/ethics/audit"
    ]

    for endpoint in endpoints:
        # Check that endpoint exists (might return 405 for wrong method, or 422 for validation)
        response = client.post(endpoint, json={})
        assert response.status_code in [200, 422, 405]


def test_all_features_integration(client):
    """Test integration between different features"""
    # Test Talent Hub
    talent_response = client.post("/talent/match", json={
        "industry": "technology",
        "role_type": "code_reviewer",
        "skills_required": ["python", "security"]
    })
    assert talent_response.status_code == 200
    talent_data = talent_response.json()
    assert "matches" in talent_data

    # Test Compliance
    compliance_response = client.post("/compliance/scan", json={
        "system_type": "web",
        "tech_stack": ["python", "fastapi"],
        "target": "example.com",
        "scan_type": "quick"
    })
    assert compliance_response.status_code == 200
    compliance_data = compliance_response.json()
    assert "scan_id" in compliance_data

    # Test Code Auditor
    code_response = client.post("/code/audit", json={
        "source_type": "snippet",
        "content": "def test(): return True",
        "language": "python",
        "audit_type": "quick"
    })
    assert code_response.status_code == 200
    code_data = code_response.json()
    assert "audit_id" in code_data

    # Test Wellness
    wellness_response = client.post("/wellness/analyze", json={
        "git_data": {
            "total_commits": 100,
            "days_analyzed": 30,
            "weekend_ratio": 0.2,
            "late_night_ratio": 0.1
        }
    })
    assert wellness_response.status_code == 200
    wellness_data = wellness_response.json()
    assert "analysis_id" in wellness_data

    # Test Infra Optimizer
    infra_response = client.post("/infra/optimize", json={
        "model_name": "test-model",
        "model_type": "LLM",
        "parameters": "7B",
        "framework": "PyTorch",
        "current_hardware": {
            "cpu_cores": 8,
            "memory_gb": 16
        },
        "performance_requirements": {
            "inference_time_ms": 100
        }
    })
    assert infra_response.status_code == 200
    infra_data = infra_response.json()
    assert "plan_id" in infra_data

    # Test Ethics Guardian
    ethics_response = client.post("/ethics/audit", json={
        "system_name": "Test System",
        "system_type": "chatbot",
        "purpose": "Test purpose",
        "target_users": ["test_users"],
        "data_sources": ["test_data"],
        "model_details": {
            "architecture": "transformer"
        }
    })
    assert ethics_response.status_code == 200
    ethics_data = ethics_response.json()
    assert "audit_id" in ethics_data


def test_all_features_error_handling(client):
    """Test that all features handle errors gracefully"""
    # Test Talent Hub with invalid data
    response = client.post("/talent/match", json={})
    assert response.status_code in [422, 400]

    # Test Compliance with invalid data
    response = client.post("/compliance/scan", json={})
    assert response.status_code in [422, 400]

    # Test Code Auditor with invalid data
    response = client.post("/code/audit", json={})
    assert response.status_code in [422, 400]

    # Test Wellness with invalid data
    response = client.post("/wellness/analyze", json={})
    assert response.status_code in [422, 400]

    # Test Infra Optimizer with invalid data
    response = client.post("/infra/optimize", json={})
    assert response.status_code in [422, 400]

    # Test Ethics Guardian with invalid data
    response = client.post("/ethics/audit", json={})
    assert response.status_code in [422, 400]


def test_all_features_response_structure(client):
    """Test that all features return consistent response structures"""
    # Test Talent Hub response structure
    response = client.post("/talent/match", json={
        "industry": "tech",
        "role_type": "developer",
        "skills_required": ["python"]
    })
    if response.status_code == 200:
        data = response.json()
        assert "business_needs" in data
        assert "matches" in data
        assert "total_matches" in data
        assert "generated_at" in data

    # Test Compliance response structure
    response = client.post("/compliance/scan", json={
        "system_type": "web",
        "tech_stack": ["python"],
        "target": "example.com",
        "scan_type": "quick"
    })
    if response.status_code == 200:
        data = response.json()
        assert "scan_id" in data
        assert "vulnerabilities" in data
        assert "fixes" in data
        assert "summary" in data
        assert "scan_time" in data

    # Test Code Auditor response structure
    response = client.post("/code/audit", json={
        "source_type": "snippet",
        "content": "def test(): pass",
        "language": "python",
        "audit_type": "quick"
    })
    if response.status_code == 200:
        data = response.json()
        assert "audit_id" in data
        assert "issues" in data
        assert "fixes" in data
        assert "summary" in data
        assert "audit_time" in data

    # Test Wellness response structure
    response = client.post("/wellness/analyze", json={
        "git_data": {"total_commits": 50, "days_analyzed": 30}
    })
    if response.status_code == 200:
        data = response.json()
        assert "analysis_id" in data
        assert "issues" in data
        assert "recommendations" in data
        assert "summary" in data
        assert "generated_at" in data

    # Test Infra Optimizer response structure
    response = client.post("/infra/optimize", json={
        "model_name": "test",
        "model_type": "LLM",
        "parameters": "7B",
        "framework": "PyTorch",
        "current_hardware": {"cpu_cores": 8, "memory_gb": 16},
        "performance_requirements": {"inference_time_ms": 100}
    })
    if response.status_code == 200:
        data = response.json()
        assert "plan_id" in data
        assert "current_assessment" in data
        assert "suggestions" in data
        assert "summary" in data
        assert "generated_at" in data

    # Test Ethics Guardian response structure
    response = client.post("/ethics/audit", json={
        "system_name": "test",
        "system_type": "chatbot",
        "purpose": "test",
        "target_users": ["users"],
        "data_sources": ["data"],
        "model_details": {"architecture": "transformer"}
    })
    if response.status_code == 200:
        data = response.json()
        assert "audit_id" in data
        assert "concerns" in data
        assert "recommendations" in data
        assert "summary" in data
        assert "audit_time" in data
