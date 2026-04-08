"""
Test script for Agent Management API
Tests: Create, List, Get, Update, Delete operations
"""
import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000"

# First, let's login to get an auth token
def login():
    """Login to get authentication token"""
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }

    # Try to login
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✅ Login successful")
            return token
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def create_agent(token):
    """Create a new agent with role and skills"""
    headers = {"Authorization": f"Bearer {token}"}

    agent_data = {
        "name": "Marketing Specialist",
        "description": "An AI agent specialized in marketing campaigns and social media management",
        "role": "Marketing",
        "skills": ["social media", "content creation", "campaign management", "analytics"],
        "category": "Marketing",
        "is_published": True,
        "tags": "marketing,social-media,content",
        "config": {
            "system_prompt": "You are a marketing specialist...",
            "temperature": 0.7
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/agents/create",
            json=agent_data,
            headers=headers
        )

        if response.status_code == 200:
            agent = response.json()
            print(f"✅ Agent created successfully!")
            print(f"   ID: {agent['id']}")
            print(f"   Name: {agent['name']}")
            print(f"   Role: {agent['role']}")
            print(f"   Skills: {agent['skills']}")
            print(f"   Created at: {agent['created_at']}")
            return agent['id']
        else:
            print(f"❌ Create failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Create error: {e}")
        return None

def list_agents(token):
    """List all agents"""
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{BASE_URL}/agents",
            headers=headers
        )

        if response.status_code == 200:
            agents = response.json()
            print(f"✅ Found {len(agents)} agents")
            print("\n--- Agent List ---")
            for agent in agents:
                print(f"\nID: {agent['id']}")
                print(f"Name: {agent['name']}")
                print(f"Role: {agent.get('role', 'N/A')}")
                print(f"Skills: {agent.get('skills', [])}")
                print(f"Owner: {agent.get('owner_id', 'System')}")
        else:
            print(f"❌ List failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ List error: {e}")

def get_agent(token, agent_id):
    """Get a specific agent by ID"""
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{BASE_URL}/agents/{agent_id}",
            headers=headers
        )

        if response.status_code == 200:
            agent = response.json()
            print(f"\n✅ Agent details retrieved:")
            print(f"   ID: {agent['id']}")
            print(f"   Name: {agent['name']}")
            print(f"   Description: {agent['description']}")
            print(f"   Role: {agent['role']}")
            print(f"   Skills: {agent['skills']}")
            print(f"   Category: {agent['category']}")
            print(f"   Created: {agent['created_at']}")
            print(f"   Updated: {agent['updated_at']}")
        else:
            print(f"❌ Get failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Get error: {e}")

def update_agent(token, agent_id):
    """Update an existing agent"""
    headers = {"Authorization": f"Bearer {token}"}

    update_data = {
        "name": "Marketing Specialist (Updated)",
        "description": "Updated description for marketing agent",
        "role": "Marketing",
        "skills": ["social media", "content creation", "campaign management", "analytics", "SEO"],
        "is_published": False
    }

    try:
        response = requests.patch(
            f"{BASE_URL}/agents/{agent_id}",
            json=update_data,
            headers=headers
        )

        if response.status_code == 200:
            agent = response.json()
            print(f"\n✅ Agent updated successfully!")
            print(f"   Name: {agent['name']}")
            print(f"   Role: {agent['role']}")
            print(f"   Skills: {agent['skills']}")
            print(f"   Updated at: {agent['updated_at']}")
        else:
            print(f"❌ Update failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Update error: {e}")

def delete_agent(token, agent_id):
    """Delete an agent"""
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.delete(
            f"{BASE_URL}/agents/{agent_id}",
            headers=headers
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ {result['message']}")
        else:
            print(f"❌ Delete failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Delete error: {e}")

def main():
    """Run all tests in sequence"""
    print("=" * 60)
    print("Agent Management API Test Suite")
    print("=" * 60)

    # Step 1: Login
    print("\n[Step 1] Login to get authentication token")
    print("-" * 60)
    token = login()

    if not token:
        print("\n❌ Cannot proceed without authentication token")
        return

    # Step 2: Create an agent
    print("\n[Step 2] Create a new agent with role and skills")
    print("-" * 60)
    agent_id = create_agent(token)

    if not agent_id:
        print("\n❌ Cannot proceed without agent ID")
        return

    # Step 3: List all agents
    print("\n[Step 3] List all agents")
    print("-" * 60)
    list_agents(token)

    # Step 4: Get specific agent
    print("\n[Step 4] Get specific agent by ID")
    print("-" * 60)
    get_agent(token, agent_id)

    # Step 5: Update agent
    print("\n[Step 5] Update the agent")
    print("-" * 60)
    update_agent(token, agent_id)

    # Step 6: Verify update
    print("\n[Step 6] Verify updated agent")
    print("-" * 60)
    get_agent(token, agent_id)

    # Step 7: Delete agent
    print("\n[Step 7] Delete the agent")
    print("-" * 60)
    delete_agent(token, agent_id)

    # Step 8: Verify deletion
    print("\n[Step 8] Verify agent was deleted")
    print("-" * 60)
    get_agent(token, agent_id)  # Should fail with 404

    print("\n" + "=" * 60)
    print("Test suite completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
