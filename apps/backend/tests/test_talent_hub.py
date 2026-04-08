
"""
Tests for AI Talent Marketplace Hub
"""
import pytest
from fastapi.testclient import TestClient
from routers.talent_hub import BusinessNeed, AgentProfile


def test_match_talent_success(client):
    """Test successful talent matching"""
    business_needs = {
        "industry": "technology",
        "role_type": "code_reviewer",
        "skills_required": ["python", "code_quality"],
        "experience_level": "senior",
        "budget_range": "30-50",
        "work_hours": "full-time",
        "timezone": "UTC"
    }

    response = client.post("/talent/match", json=business_needs)

    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert "total_matches" in data
    assert data["total_matches"] > 0
    assert len(data["matches"]) > 0

    # Check first match structure
    first_match = data["matches"][0]
    assert "agent" in first_match
    assert "match_score" in first_match
    assert "match_reasons" in first_match
    assert 0 <= first_match["match_score"] <= 1


def test_match_talent_no_results(client):
    """Test talent matching with no results"""
    business_needs = {
        "industry": "unknown_industry",
        "role_type": "nonexistent_role",
        "skills_required": ["nonexistent_skill"]
    }

    response = client.post("/talent/match", json=business_needs)

    # Should still return 200 but with no matches
    assert response.status_code == 200
    data = response.json()
    assert data["total_matches"] == 0
    assert len(data["matches"]) == 0


def test_list_agents(client):
    """Test listing available agents"""
    response = client.get("/talent/agents")

    assert response.status_code == 200
    agents = response.json()
    assert len(agents) > 0

    # Check agent structure
    agent = agents[0]
    assert "id" in agent
    assert "name" in agent
    assert "role_type" in agent
    assert "skills" in agent
    assert "rating" in agent


def test_list_agents_with_filters(client):
    """Test listing agents with filters"""
    response = client.get("/talent/agents?role_type=code_reviewer&min_rating=4.5")

    assert response.status_code == 200
    agents = response.json()

    # Verify filters applied
    for agent in agents:
        assert "code_reviewer" in agent["role_type"].lower()
        assert agent["rating"] >= 4.5


def test_match_talent_validation_error(client):
    """Test talent matching with invalid input"""
    # Missing required field
    business_needs = {
        "industry": "technology"
        # Missing role_type and skills_required
    }

    response = client.post("/talent/match", json=business_needs)

    assert response.status_code == 422  # Validation error


def test_list_agents_invalid_filter(client):
    """Test listing agents with invalid filter values"""
    response = client.get("/talent/agents?min_rating=invalid")

    # Should return 422 for invalid query parameter
    assert response.status_code == 422
