import requests
import json

# Test the talent matching endpoint
body = {
    "business_needs": "Need help with social media posts for my coffee shop",
    "industry": "Food & Beverage",
    "role_type": "Marketing",
    "skills_required": ["Instagram", "content creation", "social media"],
    "experience_level": "Intermediate",
    "budget_range": "30-50 CHF",
    "availability": "Part-time",
    "timezone": "CET"
}

response = requests.post("http://localhost:8000/talent/match", json=body)
print(f"Status Code: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")
