
import requests
import json

BASE_URL = "http://localhost:8000"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHJpbmciLCJyb2xlIjoidXNlciIsImV4cCI6MTc3MzE4Mjg4Nn0.2C8E90Ab4Lj9WWyLpQRrdCFvTRxAwRkSsfEwg0y_hh8"

def create_agent():
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    agent_data = {
        "name": "Marketing Specialist",
        "description": "An AI agent specialized in marketing campaigns",
        "role": "Marketing",
        "skills": ["social media", "content creation", "analytics"],
        "category": "Marketing",
        "is_published": True,
        "tags": "marketing,social-media",
        "config": {"system_prompt": "You are a marketing specialist...", "temperature": 0.7}
    }

    response = requests.post(f"{BASE_URL}/agents/create", json=agent_data, headers=headers)
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

def list_agents():
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(f"{BASE_URL}/agents", headers=headers)
    if response.status_code == 200:
        agents = response.json()
        print(f"
Found {len(agents)} agents")
        for agent in agents:
            print(f"
ID: {agent['id']}")
            print(f"Name: {agent['name']}")
            print(f"Role: {agent.get('role', 'N/A')}")
            print(f"Skills: {agent.get('skills', [])}")
            print(f"Owner: {agent.get('owner_id', 'System')}")
    else:
        print(f"List failed: {response.status_code}")

def get_agent(agent_id):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(f"{BASE_URL}/agents/{agent_id}", headers=headers)
    if response.status_code == 200:
        agent = response.json()
        print(f"
Agent details:")
        print(f"ID: {agent['id']}")
        print(f"Name: {agent['name']}")
        print(f"Description: {agent['description']}")
        print(f"Role: {agent['role']}")
        print(f"Skills: {agent['skills']}")
        print(f"Created: {agent['created_at']}")
        print(f"Updated: {agent['updated_at']}")
    else:
        print(f"Get failed: {response.status_code}")

def update_agent(agent_id):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    update_data = {
        "name": "Marketing Specialist (Updated)",
        "description": "Updated description",
        "role": "Marketing",
        "skills": ["social media", "content creation", "analytics", "SEO"],
        "is_published": False
    }
    response = requests.patch(f"{BASE_URL}/agents/{agent_id}", json=update_data, headers=headers)
    if response.status_code == 200:
        agent = response.json()
        print(f"
Agent updated successfully!")
        print(f"Name: {agent['name']}")
        print(f"Skills: {agent['skills']}")
        print(f"Updated at: {agent['updated_at']}")
    else:
        print(f"Update failed: {response.status_code}")

def delete_agent(agent_id):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.delete(f"{BASE_URL}/agents/{agent_id}", headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"
{result['message']}")
    else:
        print(f"Delete failed: {response.status_code}")

def main():
    print("=" * 60)
    print("Agent Management API Test")
    print("=" * 60)

    print("
[Step 1] Create agent")
    print("-" * 60)
    agent_id = create_agent()

    if not agent_id:
        return

    print("
[Step 2] List agents")
    print("-" * 60)
    list_agents()

    print("
[Step 3] Get agent")
    print("-" * 60)
    get_agent(agent_id)

    print("
[Step 4] Update agent")
    print("-" * 60)
    update_agent(agent_id)

    print("
[Step 5] Verify update")
    print("-" * 60)
    get_agent(agent_id)

    print("
[Step 6] Delete agent")
    print("-" * 60)
    delete_agent(agent_id)

    print("
[Step 7] Verify deletion")
    print("-" * 60)
    get_agent(agent_id)

    print("
" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
