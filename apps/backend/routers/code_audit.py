import logging
import json
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
try:
    import ollama
except Exception:
    ollama = None
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/code",
    tags=["code"],
    responses={404: {"description": "Not found"}},
)

class CodeAuditInput(BaseModel):
    """Input for code audit endpoint."""
    code_snippet: Optional[str] = Field(None, description="Direct code to audit")
    repo_url: Optional[str] = Field(None, description="Git repo URL to audit")

class CodeAuditOutput(BaseModel):
    """Output from code audit."""
    issues: List[Dict] = Field(default_factory=list, description="List of issues found")
    fixes: List[str] = Field(default_factory=list, description="Suggested fixes")

@router.post("/audit", response_model=CodeAuditOutput)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))  # retry on transient Ollama errors
async def audit_code(input_data: CodeAuditInput):
    """
    Audits code snippet or repo for bugs, security issues, and tech debt using Ollama.
    Returns structured JSON with issues and fixes.
    """
    if not input_data.code_snippet and not input_data.repo_url:
        raise HTTPException(status_code=400, detail="Provide either code_snippet or repo_url")

    target = input_data.code_snippet or input_data.repo_url
    prompt = (
        "You are a code auditor. Analyze this code/repo for bugs, security vulnerabilities, "
        "and technical debt. Return ONLY a JSON object with two keys: "
        "'issues' (list of dicts with 'type', 'line', 'description') and "
        "'fixes' (list of strings with suggested code changes).\\n\\n"
        f"Code/Repo to audit:\\n{target}"
    )

    if ollama is None:
        return CodeAuditOutput(
            issues=[{"type": "availability", "description": "Ollama client is not installed"}],
            fixes=["Install the Ollama Python client or enable the Ollama service."]
        )

    try:
        logger.info(f"Starting code audit for input length {len(target)}")
        response = ollama.chat(
            model="qwen2.5-coder:7b",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.get("message", {}).get("content", "")

        # Clean up possible markdown
        if content.startswith("```json"):
            content = content.strip("```json\\n").strip("```")

        data = json.loads(content)

        return CodeAuditOutput(
            issues=data.get("issues", []),
            fixes=data.get("fixes", [])
        )

    except json.JSONDecodeError:
        logger.warning("Ollama returned invalid JSON. Using raw content.")
        return CodeAuditOutput(
            issues=[{"type": "parse_error", "description": "Could not parse AI response"}],
            fixes=[content]
        )
    except Exception as e:
        logger.error(f"Code audit failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Audit failed - check logs")
