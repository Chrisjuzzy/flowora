"""
Test agent management with your access token
"""
import requests
import json

# Base URL for API
BASE_URL = "http://localhost:8000"

# Your access token
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHJpbmciLCJyb2xlIjoidXNlciIsImV4cCI6MTc3MzE4Mjg4Nn0.2C8E90Ab4Lj9WWyLpQRrdCFvTRxAwRkSsfEwg0y_hh8"

def create_agent():
    """Create a new agent with role and skills"""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

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
            print("Agent created successfully!")
            print(f"ID: {agent['id']}")
            print(f"Name: {agent['name']}")
            print(f"Role: {agent['role']}")
            print(f"Skills: {agent['skills']}")
            print(f"Created at: {agent['created_at']}")
            return agent['id']
        else:
            print(f"Create failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Create error: {e}")
        return None

def list_agents():
    """List all agents"""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    try:
        response = requests.get(
            f"{BASE_URL}/agents",
            headers=headers
        )

        if response.status_code == 200:
            agents = response.json()
            print(f"Found {len(agents)} agents")
            print("
Agent List:")
            for agent in agents:
                print(f"
ID: {agent['id']}")
                print(f"Name: {agent['name']}")
                print(f"Role: {agent.get('role', 'N/A')}")
                print(f"Skills: {agent.get('skills', [])}")
                print(f"Owner: {agent.get('owner_id', 'System')}")
        else:
            print(f"List failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"List error: {e}")

def get_agent(agent_id):
    """Get a specific agent by ID"""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    try:
        response = requests.get(
            f"{BASE_URL}/agents/{agent_id}",
            headers=headers
        )

        if response.status_code == 200:
            agent = response.json()
            print(f"
Agent details:")
            print(f"ID: {agent['id']}")
            print(f"Name: {agent['name']}")
            print(f"Description: {agent['description']}")
            print(f"Role: {agent['role']}")
            print(f"Skills: {agent['skills']}")
            print(f"Category: {agent['category']}")
            print(f"Created: {agent['created_at']}")
            print(f"Updated: {agent['updated_at']}")
        else:
            print(f"Get failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Get error: {e}")

def update_agent(agent_id):
    """Update an existing agent"""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

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
            print(f"
Agent updated successfully!")
            print(f"Name: {agent['name']}")
            print(f"Role: {agent['role']}")
            print(f"Skills: {agent['skills']}")
            print(f"Updated at: {agent['updated_at']}")
        else:
            print(f"Update failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Update error: {e}")

def delete_agent(agent_id):
    """Delete an agent"""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    try:
        response = requests.delete(
            f"{BASE_URL}/agents/{agent_id}",
            headers=headers
        )

        if response.status_code == 200:
            result = response.json()
            print(f"
{result['message']}")
        else:
            print(f"Delete failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Delete error: {e}")

def main():
    """Run all tests in sequence"""
    print("=" * 60)
    print("Agent Management API Test")
    print("=" * 60)

    # Step 1: Create an agent
    print("
[Step 1] Create a new agent with role and skills")
    print("-" * 60)
    agent_id = create_agent()

    if not agent_id:
        print("
Cannot proceed without agent ID")
        return

    # Step 2: List all agents
    print("
[Step 2] List all agents")
    print("-" * 60)
    list_agents()

    # Step 3: Get specific agent
    print("
[Step 3] Get specific agent by ID")
    print("-" * 60)
    get_agent(agent_id)

    # Step 4: Update agent
    print("
[Step 4] Update agent")
    print("-" * 60)
    update_agent(agent_id)

    # Step 5: Verify update
    print("
[Step 5] Verify updated agent")
    print("-" * 60)
    get_agent(agent_id)

    # Step 6: Delete agent
    print("
[Step 6] Delete agent")
    print("-" * 60)
    delete_agent(agent_id)

    # Step 7: Verify deletion
    print("
[Step 7] Verify agent was deleted")
    print("-" * 60)
    get_agent(agent_id)  # Should fail with 404

    print("
" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
