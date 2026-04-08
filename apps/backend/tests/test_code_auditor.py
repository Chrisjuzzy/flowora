
"""
Tests for AI Code Auditor Pro
"""
import pytest
from fastapi.testclient import TestClient


def test_code_audit_with_snippet(client):
    """Test code audit with code snippet"""
    code_input = {
        "source_type": "snippet",
        "content": "def insecure_function(user_input):\n    sql = \"SELECT * FROM users WHERE name = \'" + user_input + "\'\"\n    return execute_query(sql)",
        "language": "python",
        "audit_type": "security"
    }

    response = client.post("/code/audit", json=code_input)

    assert response.status_code == 200
    data = response.json()
    assert "audit_id" in data
    assert "issues" in data
    assert "fixes" in data
    assert "summary" in data
    assert "audit_time" in data


def test_code_audit_with_repo(client):
    """Test code audit with repository URL"""
    code_input = {
        "source_type": "repo_url",
        "content": "https://github.com/example/python-project",
        "language": "python",
        "audit_type": "full"
    }

    response = client.post("/code/audit", json=code_input)

    assert response.status_code in [200, 400, 408]


def test_code_audit_validation_error(client):
    """Test code audit with invalid input"""
    code_input = {
        "source_type": "snippet"
    }

    response = client.post("/code/audit", json=code_input)

    assert response.status_code == 422


def test_code_audit_quick_scan(client):
    """Test quick code audit"""
    code_input = {
        "source_type": "snippet",
        "content": "def calculate(x, y):\n    return x + y",
        "language": "python",
        "audit_type": "quick"
    }

    response = client.post("/code/audit", json=code_input)

    assert response.status_code == 200
    data = response.json()
    assert "audit_id" in data
    assert "issues" in data


def test_code_audit_report_structure(client):
    """Test that code audit report has correct structure"""
    code_input = {
        "source_type": "snippet",
        "content": "def process_data(data):\n    result = []\n    for item in data:\n        result.append(item)\n    return result",
        "language": "python",
        "audit_type": "full"
    }

    response = client.post("/code/audit", json=code_input)

    assert response.status_code == 200
    data = response.json()

    assert "total_issues" in data["summary"]
    assert "critical" in data["summary"]
    assert "high" in data["summary"]
    assert "medium" in data["summary"]
    assert "low" in data["summary"]

    if data["issues"]:
        issue = data["issues"][0]
        assert "id" in issue
        assert "severity" in issue
        assert "category" in issue
        assert "title" in issue
        assert "description" in issue


def test_code_audit_multiple_languages(client):
    """Test code audit with different languages"""
    languages = ["python", "javascript", "java"]

    for lang in languages:
        code_input = {
            "source_type": "snippet",
            "content": "// Sample code",
            "language": lang,
            "audit_type": "quick"
        }

        response = client.post("/code/audit", json=code_input)

        assert response.status_code == 200
        data = response.json()
        assert "audit_id" in data


def test_code_audit_fix_recommendations(client):
    """Test that code audit provides fix recommendations"""
    code_input = {
        "source_type": "snippet",
        "content": "def insecure_query(user_id):\n    query = f\"SELECT * FROM users WHERE id = {user_id}\"\n    return execute(query)",
        "language": "python",
        "audit_type": "security"
    }

    response = client.post("/code/audit", json=code_input)

    assert response.status_code == 200
    data = response.json()

    if data["issues"]:
        assert len(data["fixes"]) > 0
        fix = data["fixes"][0]
        assert "issue_id" in fix
        assert "description" in fix
        assert "explanation" in fix
