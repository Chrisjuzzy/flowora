
"""
Tests for Ethical AI Guardian
"""
import pytest
from fastapi.testclient import TestClient


def test_ethics_audit_success(client):
    """Test successful ethical audit"""
    ai_config = {
        "system_name": "Customer Service Bot",
        "system_type": "chatbot",
        "purpose": "Handle customer inquiries",
        "target_users": ["general_public"],
        "data_sources": ["customer_feedback", "product_manual"],
        "model_details": {
            "architecture": "transformer",
            "parameters": "7B",
            "training_data": "internal_dataset"
        },
        "safeguards": ["content_filtering", "rate_limiting"]
    }

    response = client.post("/ethics/audit", json=ai_config)

    assert response.status_code == 200
    data = response.json()
    assert "audit_id" in data
    assert "concerns" in data
    assert "recommendations" in data
    assert "summary" in data
    assert "audit_time" in data


def test_ethics_audit_minimal_config(client):
    """Test ethical audit with minimal config"""
    ai_config = {
        "system_name": "Simple Bot",
        "system_type": "chatbot",
        "purpose": "Basic assistance",
        "target_users": ["internal_staff"],
        "data_sources": ["internal_docs"],
        "model_details": {
            "architecture": "transformer"
        }
    }

    response = client.post("/ethics/audit", json=ai_config)

    assert response.status_code == 200
    data = response.json()
    assert "audit_id" in data


def test_ethics_audit_validation_error(client):
    """Test ethical audit with invalid input"""
    ai_config = {
        "system_name": "Test Bot"
        # Missing required fields
    }

    response = client.post("/ethics/audit", json=ai_config)

    assert response.status_code == 422  # Validation error


def test_ethics_audit_concerns_detection(client):
    """Test that ethical audit detects concerns"""
    ai_config = {
        "system_name": "Test System",
        "system_type": "recommendation",
        "purpose": "Product recommendations",
        "target_users": ["online_shoppers"],
        "data_sources": ["user_behavior"],  # Limited data sources
        "model_details": {
            "architecture": "neural_network"
        }
        # No safeguards - should trigger concerns
    }

    response = client.post("/ethics/audit", json=ai_config)

    assert response.status_code == 200
    data = response.json()

    # Should detect concerns due to limited data sources and no safeguards
    assert len(data["concerns"]) > 0


def test_ethics_audit_concerns_structure(client):
    """Test that ethical concerns have correct structure"""
    ai_config = {
        "system_name": "Test System",
        "system_type": "chatbot",
        "purpose": "Test purpose",
        "target_users": ["test_users"],
        "data_sources": ["test_data"],
        "model_details": {
            "architecture": "transformer"
        }
    }

    response = client.post("/ethics/audit", json=ai_config)

    assert response.status_code == 200
    data = response.json()

    # Check concern structure
    if data["concerns"]:
        concern = data["concerns"][0]
        assert "id" in concern
        assert "category" in concern
        assert "severity" in concern
        assert "title" in concern
        assert "description" in concern
        assert "impact" in concern
        assert "affected_stakeholders" in concern


def test_ethics_audit_recommendations_structure(client):
    """Test that ethical recommendations have correct structure"""
    ai_config = {
        "system_name": "Test System",
        "system_type": "chatbot",
        "purpose": "Test purpose",
        "target_users": ["test_users"],
        "data_sources": ["test_data"],
        "model_details": {
            "architecture": "transformer"
        }
    }

    response = client.post("/ethics/audit", json=ai_config)

    assert response.status_code == 200
    data = response.json()

    # Check recommendation structure
    if data["recommendations"]:
        rec = data["recommendations"][0]
        assert "concern_id" in rec
        assert "priority" in rec
        assert "title" in rec
        assert "description" in rec
        assert "implementation_steps" in rec
        assert "expected_outcome" in rec
        assert isinstance(rec["implementation_steps"], list)


def test_ethics_audit_summary_structure(client):
    """Test that ethical audit summary has correct structure"""
    ai_config = {
        "system_name": "Test System",
        "system_type": "chatbot",
        "purpose": "Test purpose",
        "target_users": ["test_users"],
        "data_sources": ["test_data"],
        "model_details": {
            "architecture": "transformer"
        }
    }

    response = client.post("/ethics/audit", json=ai_config)

    assert response.status_code == 200
    data = response.json()

    # Check summary structure
    assert "total_concerns" in data["summary"]
    assert "critical_concerns" in data["summary"]
    assert "high_concerns" in data["summary"]
    assert "overall_risk_level" in data["summary"]


def test_ethics_audit_bias_detection(client):
    """Test that ethical audit detects bias issues"""
    ai_config = {
        "system_name": "Hiring Assistant",
        "system_type": "recommendation",
        "purpose": "Candidate screening",
        "target_users": ["recruiters"],  # Narrow target users
        "data_sources": ["historical_hiring_data"],  # Single data source
        "model_details": {
            "architecture": "neural_network"
        }
        # No bias safeguards
    }

    response = client.post("/ethics/audit", json=ai_config)

    assert response.status_code == 200
    data = response.json()

    # Should detect bias concerns
    bias_concerns = [c for c in data["concerns"] if c["category"] == "bias"]
    assert len(bias_concerns) > 0
