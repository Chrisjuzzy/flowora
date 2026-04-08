import os
import requests
from typing import Optional

def call_llm(prompt: str, system_prompt: Optional[str] = None, model: str = "mistral-small"):
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise ValueError("Missing AI_API_KEY environment variable")

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
