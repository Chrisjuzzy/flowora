import logging
from datetime import datetime, timedelta
import json
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
try:
    import ollama
except Exception:
    ollama = None
try:
    from git import Repo, InvalidGitRepositoryError, NoSuchPathError
except Exception:
    Repo = None
    InvalidGitRepositoryError = Exception
    NoSuchPathError = Exception
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wellness",
    tags=["wellness"],
    responses={404: {"description": "Not found"}},
)

class WellnessAnalyzeInput(BaseModel):
    """Input for wellness analysis."""
    repo_path: str = Field(..., description="Local path to Git repo")
    developer_email: str = Field(..., description="Git commit author email")

class WellnessAnalyzeOutput(BaseModel):
    """Output with wellness analysis and plan."""
    burnout_risk: str = Field(..., description="Low/Medium/High")
    insights: List[str] = Field(default_factory=list, description="Key observations")
    recommendations: List[str] = Field(default_factory=list, description="Actionable suggestions")

@router.post("/analyze", response_model=WellnessAnalyzeOutput)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))  # retry on transient errors
async def analyze_wellness(input_data: WellnessAnalyzeInput):
    """
    Analyzes Git commit history for burnout risk using GitPython + Ollama.
    Returns risk level, insights, and recommendations.
    """
    try:
        logger.info(f"Analyzing repo {input_data.repo_path} for {input_data.developer_email}")

        if Repo is None:
            return WellnessAnalyzeOutput(
                burnout_risk="Unknown",
                insights=["GitPython or git executable not available - cannot analyze commit history"],
                recommendations=["Install git in the backend image or disable wellness analysis"]
            )

        # Check if Ollama is available
        try:
            import requests
            response = requests.get('http://127.0.0.1:11434/api/tags', timeout=2)
            if response.status_code != 200:
                raise Exception("Ollama not available")
        except:
            logger.warning("Ollama not available, returning mock data")
            return WellnessAnalyzeOutput(
                burnout_risk="Unknown",
                insights=["AI service unavailable - cannot analyze commit history"],
                recommendations=["Start Ollama service: ollama serve", "Ensure Git repository path is valid"]
            )

        # 1. Load repo & get recent commits (last 30 days)
        try:
            repo = Repo(input_data.repo_path)
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            logger.warning(f"Invalid repo path: {input_data.repo_path} ({e})")
            raise HTTPException(status_code=400, detail="Invalid repo_path. Provide a valid Git repository path.")
        since = datetime.now() - timedelta(days=30)
        commits = list(repo.iter_commits(since=since.timestamp(), author=input_data.developer_email))

        if not commits:
            return WellnessAnalyzeOutput(
                burnout_risk="Low",
                insights=["No commits found in last 30 days for this email."],
                recommendations=["Start committing regularly or verify email."]
            )

        commit_summary = f"Found {len(commits)} commits in last 30 days.\n"
        commit_summary += f"First: {commits[-1].committed_datetime} - Last: {commits[0].committed_datetime}\n"
        commit_summary += "Recent messages: " + ", ".join(c.message.strip().split('\n')[0] for c in commits[:5])

        # 2. Ollama analysis
        prompt = (
            "You are a developer wellness coach. Analyze this commit history for burnout signs "
            "(high frequency, late-night commits, repetitive work). Return ONLY JSON with: "
            "'burnout_risk' ('Low', 'Medium', 'High'), 'insights' (list of strings), "
            "'recommendations' (list of actionable suggestions).\n\n"
            f"Commit summary:\n{commit_summary}"
        )

        logger.info(f"Calling Ollama for wellness analysis")
        client = ollama.Client(host='http://127.0.0.1:11434')
        response = client.chat(
            model="qwen2.5-coder:7b",
            messages=[{"role": "user", "content": prompt}]
        )
        logger.info(f"Ollama response received")
        content = response.get("message", {}).get("content", "")

        # Parse JSON response (with fallback)
        try:
            if content.startswith("```json"):
                content = content.strip("```json\n").strip("```")
            data = json.loads(content)
            return WellnessAnalyzeOutput(
                burnout_risk=data.get("burnout_risk", "Unknown"),
                insights=data.get("insights", []),
                recommendations=data.get("recommendations", [])
            )
        except json.JSONDecodeError:
            logger.warning("Ollama returned invalid JSON.")
            return WellnessAnalyzeOutput(
                burnout_risk="Unknown",
                insights=["Could not parse AI response"],
                recommendations=[content]
            )

    except Exception as e:
        logger.error(f"Wellness analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Wellness analysis failed: {str(e)}")
