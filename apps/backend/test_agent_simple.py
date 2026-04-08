"""
Simple test script for Agent Management API (without authentication)
Tests basic CRUD operations using Swagger UI
"""
import requests
import json

# Base URL for API
BASE_URL = "http://localhost:8000"

def test_endpoints():
    """Test all agent endpoints"""
    print("=" * 60)
    print("Agent Management API Test")
    print("=" * 60)

    print("
✅ Available Endpoints:")
    print("-" * 60)
    endpoints = [
        ("POST", "/agents/create", "Create a new agent"),
        ("GET", "/agents", "List all agents"),
        ("GET", "/agents/{agent_id}", "Get specific agent"),
        ("PUT", "/agents/{agent_id}", "Update agent (full)"),
        ("PATCH", "/agents/{agent_id}", "Update agent (partial)"),
        ("DELETE", "/agents/{agent_id}", "Delete agent"),
    ]

    for method, endpoint, description in endpoints:
        print(f"{method:6} {endpoint:25} - {description}")

    print("
" + "=" * 60)
    print("Test endpoints in Swagger UI at:")
    print("http://localhost:8000/docs")
    print("=" * 60)

    print("
📝 Example Request Body for Creating Agent:")
    print("-" * 60)
    example_body = {
        "name": "Marketing Specialist",
        "description": "An AI agent specialized in marketing campaigns",
        "role": "Marketing",
        "skills": ["social media", "content creation", "analytics"],
        "category": "Marketing",
        "is_published": True,
        "tags": "marketing,social-media",
        "config": {
            "system_prompt": "You are a marketing specialist...",
            "temperature": 0.7
        }
    }
    print(json.dumps(example_body, indent=2))

if __name__ == "__main__":
    test_endpoints()
