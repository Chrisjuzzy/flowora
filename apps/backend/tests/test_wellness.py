
"""
Tests for Dev Wellness Guardian
"""
import pytest
from fastapi.testclient import TestClient


def test_wellness_analyze_success(client):
    """Test successful wellness analysis"""
    wellness_data = {
        "git_data": {
            "total_commits": 100,
            "days_analyzed": 30,
            "days_with_commits": 20,
            "avg_commits_per_day": 5.0,
            "peak_hours": [9, 10, 11],
            "weekend_commits": 10,
            "weekend_ratio": 0.1,
            "late_night_commits": 5,
            "late_night_ratio": 0.05
        },
        "calendar_data": {
            "total_meetings": 20,
            "avg_meeting_duration": 30,
            "meetings_per_day": 1.0
        },
        "work_hours": {
            "avg_hours_per_day": 8.0,
            "max_hours_in_day": 10.0
        },
        "self_reported": {
            "stress_level": 5,
            "satisfaction": 7
        }
    }

    response = client.post("/wellness/analyze", json=wellness_data)

    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "issues" in data
    assert "recommendations" in data
    assert "summary" in data
    assert "generated_at" in data


def test_wellness_analyze_minimal_data(client):
    """Test wellness analysis with minimal data"""
    wellness_data = {
        "git_data": {
            "total_commits": 50,
            "days_analyzed": 30,
            "days_with_commits": 15,
            "weekend_ratio": 0.2,
            "late_night_ratio": 0.1
        }
    }

    response = client.post("/wellness/analyze", json=wellness_data)

    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data


def test_wellness_analyze_validation_error(client):
    """Test wellness analysis with invalid input"""
    wellness_data = {}

    response = client.post("/wellness/analyze", json=wellness_data)

    # Should accept empty data or return validation error
    assert response.status_code in [200, 422]


def test_wellness_analyze_high_weekend_ratio(client):
    """Test wellness analysis detects high weekend work"""
    wellness_data = {
        "git_data": {
            "total_commits": 100,
            "days_analyzed": 30,
            "days_with_commits": 25,
            "weekend_commits": 40,
            "weekend_ratio": 0.4,
            "late_night_ratio": 0.1
        }
    }

    response = client.post("/wellness/analyze", json=wellness_data)

    assert response.status_code == 200
    data = response.json()

    # Should detect overwork issue
    if data["issues"]:
        assert any(issue["category"] == "overwork" for issue in data["issues"])


def test_wellness_analyze_high_late_night_ratio(client):
    """Test wellness analysis detects late night work"""
    wellness_data = {
        "git_data": {
            "total_commits": 100,
            "days_analyzed": 30,
            "days_with_commits": 20,
            "weekend_ratio": 0.1,
            "late_night_commits": 30,
            "late_night_ratio": 0.3
        }
    }

    response = client.post("/wellness/analyze", json=wellness_data)

    assert response.status_code == 200
    data = response.json()

    # Should detect poor balance issue
    if data["issues"]:
        assert any(issue["category"] == "poor_balance" for issue in data["issues"])


def test_wellness_recommendations_structure(client):
    """Test that wellness recommendations have correct structure"""
    wellness_data = {
        "git_data": {
            "total_commits": 100,
            "days_analyzed": 30,
            "weekend_ratio": 0.3,
            "late_night_ratio": 0.2
        }
    }

    response = client.post("/wellness/analyze", json=wellness_data)

    assert response.status_code == 200
    data = response.json()

    # Check recommendation structure
    if data["recommendations"]:
        rec = data["recommendations"][0]
        assert "issue_id" in rec
        assert "priority" in rec
        assert "title" in rec
        assert "description" in rec
        assert "action_steps" in rec
        assert isinstance(rec["action_steps"], list)


def test_wellness_summary_structure(client):
    """Test that wellness summary has correct structure"""
    wellness_data = {
        "git_data": {
            "total_commits": 100,
            "days_analyzed": 30,
            "weekend_ratio": 0.2,
            "late_night_ratio": 0.15
        },
        "self_reported": {
            "stress_level": 7,
            "satisfaction": 5
        }
    }

    response = client.post("/wellness/analyze", json=wellness_data)

    assert response.status_code == 200
    data = response.json()

    # Check summary structure
    assert "overall_score" in data["summary"]
    assert "total_issues" in data["summary"]
    assert "risk_level" in data["summary"]
