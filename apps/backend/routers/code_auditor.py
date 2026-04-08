"""
AI Code Auditor Pro - Audits code and provides fixes
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from database_production import get_db
import logging
from datetime import datetime
import subprocess
import json
import os
import tempfile
import shutil
from tenacity import retry, stop_after_attempt, wait_exponential
try:
    import ollama
except Exception:
    ollama = None
import asyncio
try:
    import git
except Exception:
    git = None

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/code",
    tags=["code-auditor"],
    responses={404: {"description": "Not found"}},
)


# --- Pydantic Models ---

class CodeInput(BaseModel):
    """Input for code audit"""
    source_type: str = Field(..., description="Type of source: 'repo_url' or 'snippet'")
    content: str = Field(..., description="Repository URL or code snippet")
    language: Optional[str] = Field(None, description="Programming language")
    audit_type: str = Field("full", description="Type of audit: 'quick', 'full', 'security'")


class CodeIssue(BaseModel):
    """Detected code issue"""
    id: str
    severity: str  # critical, high, medium, low, info
    category: str  # security, performance, style, best_practices, bugs
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None


class CodeFix(BaseModel):
    """Recommended fix for a code issue"""
    issue_id: str
    description: str
    code_before: Optional[str] = None
    code_after: Optional[str] = None
    explanation: str
    references: List[str] = []


class AuditReport(BaseModel):
    """Code audit report"""
    audit_id: str
    code_input: CodeInput
    issues: List[CodeIssue]
    fixes: List[CodeFix]
    summary: Dict[str, Any]
    audit_time: datetime
    audit_duration: float


# --- Audit Functions ---

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def clone_repository(repo_url: str) -> str:
    """
    Clone a Git repository to a temporary directory

    Args:
        repo_url: URL of the repository to clone

    Returns:
        Path to the cloned repository
    """
    try:
        if git is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitPython or git executable not available in this environment"
            )
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="code_audit_")

        # Clone repository
        git.Repo.clone_from(repo_url, temp_dir)

        logger.info(f"Successfully cloned repository from {repo_url}")
        return temp_dir

    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        # Clean up temp directory if it was created
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to clone repository: {str(e)}"
        )


def find_code_files(directory: str, language: Optional[str] = None) -> List[str]:
    """
    Find code files in a directory

    Args:
        directory: Directory to search
        language: Optional language filter (e.g., 'python', 'javascript')

    Returns:
        List of file paths
    """
    code_files = []

    # Map language to file extensions
    language_extensions = {
        'python': ['.py'],
        'javascript': ['.js', '.jsx'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'c': ['.c'],
        'cpp': ['.cpp', '.cc', '.cxx'],
        'csharp': ['.cs'],
        'go': ['.go'],
        'rust': ['.rs'],
        'php': ['.php'],
        'ruby': ['.rb'],
        'swift': ['.swift'],
        'kotlin': ['.kt', '.kts'],
    }

    # Get extensions to search for
    if language and language.lower() in language_extensions:
        extensions = language_extensions[language.lower()]
    else:
        # Search for all code files
        extensions = []
        for exts in language_extensions.values():
            extensions.extend(exts)

    # Walk through directory
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common non-code directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and 
                   d not in ['node_modules', 'venv', 'env', '__pycache__', 
                            'dist', 'build', 'target']]

        for file in files:
            # Check if file has a code extension
            for ext in extensions:
                if file.endswith(ext):
                    code_files.append(os.path.join(root, file))
                    break

    return code_files


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def run_bandit_scan(file_path: str) -> List[Dict[str, Any]]:
    """
    Run Bandit security scan on Python code

    Args:
        file_path: Path to Python file to scan

    Returns:
        List of detected issues
    """
    try:
        # Build bandit command
        cmd = ["bandit", "-f", "json", file_path]

        # Run bandit
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout per file
        )

        # Parse JSON output
        try:
            bandit_output = json.loads(result.stdout)

            issues = []

            for issue in bandit_output.get("results", []):
                issue_data = {
                    "id": f"bandit-{issue['test_id']}",
                    "severity": map_severity(issue["issue_severity"]),
                    "category": "security",
                    "title": issue["test_name"],
                    "description": issue["issue_text"],
                    "file_path": issue['filename'],
                    "line_number": issue['line_number'],
                    "code_snippet": issue.get("code", "")
                }
                issues.append(issue_data)

            return issues

        except json.JSONDecodeError:
            logger.error(f"Failed to parse Bandit output: {result.stdout}")
            return []

    except subprocess.TimeoutExpired:
        logger.error(f"Bandit scan timed out for: {file_path}")
        return []
    except FileNotFoundError:
        logger.warning(f"Bandit not installed, skipping security scan for {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error running Bandit scan: {e}")
        return []


def map_severity(bandit_severity: str) -> str:
    """
    Map Bandit severity to standard severity levels

    Args:
        bandit_severity: Bandit severity level (LOW, MEDIUM, HIGH)

    Returns:
        Standardized severity level (low, medium, high, critical)
    """
    severity_map = {
        "LOW": "low",
        "MEDIUM": "medium",
        "HIGH": "high"
    }
    return severity_map.get(bandit_severity.upper(), "info")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def analyze_code_with_ollama(
    code_snippet: str,
    language: str,
    audit_type: str = "full"
) -> Dict[str, Any]:
    """
    Use Ollama to analyze code for issues

    Args:
        code_snippet: Code to analyze
        language: Programming language
        audit_type: Type of audit (quick, full, security)

    Returns:
        Dictionary with detected issues
    """
    try:
        if ollama is None:
            return {
                'issues': [{
                    'id': 'ollama-missing',
                    'severity': 'info',
                    'category': 'availability',
                    'title': 'Ollama client unavailable',
                    'description': 'Ollama Python client is not installed.',
                    'suggestion': 'Install ollama in the backend image or enable the Ollama service.'
                }]
            }
        # Create prompt for Ollama
        audit_focus = {
            'quick': 'basic syntax and obvious bugs',
            'full': 'security, performance, style, best practices, and bugs',
            'security': 'security vulnerabilities and potential exploits'
        }

        prompt = f"""
        Analyze this {language} code for {audit_focus.get(audit_type, 'issues')}:

        ```{language}
        {code_snippet}
        ```

        Return a JSON object with:
        {{
            "issues": [
                {{
                    "id": "<unique identifier>",
                    "severity": "<critical/high/medium/low/info>",
                    "category": "<security/performance/style/best_practices/bugs>",
                    "title": "<short title>",
                    "description": "<detailed description>",
                    "line_number": <line number if applicable>,
                    "code_snippet": "<relevant code snippet>",
                    "suggestion": "<suggested fix>"
                }}
            ]
        }}
        """

        # Call Ollama
        logger.info(f"Calling Ollama for code analysis")
        client = ollama.Client(host='http://127.0.0.1:11434')
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat,
                model='qwen2.5-coder:7b',
                messages=[{'role': 'user', 'content': prompt}]
            ),
            timeout=8
        )
        logger.info(f"Ollama response received")

        # Parse response
        response_text = response['message']['content'].strip()
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning(f"Non-JSON response from Ollama: {response_text}")
            return {
                'issues': [{
                    'id': 'parse-error',
                    'severity': 'info',
                    'category': 'parsing',
                    'title': 'Could not parse AI response',
                    'description': response_text[:200],
                    'suggestion': 'Try again or review code manually'
                }]
            }

        # Validate response structure
        if 'issues' not in result:
            logger.error(f"Invalid response structure from Ollama: {result}")
            return {
                'issues': [{
                    'id': 'invalid-response',
                    'severity': 'info',
                    'category': 'parsing',
                    'title': 'Invalid AI response format',
                    'description': response_text[:200],
                    'suggestion': 'Try again or review code manually'
                }]
            }

        return result

    except Exception as e:
        logger.error(f"Error analyzing code with Ollama: {e}", exc_info=True)
        return {
            'issues': [{
                'id': 'analysis-error',
                'severity': 'info',
                'category': 'availability',
                'title': 'AI analysis unavailable',
                'description': str(e),
                'suggestion': 'Verify the configured Ollama model and try again'
            }]
        }


async def generate_code_fixes(
    issues: List[CodeIssue],
    language: str
) -> List[CodeFix]:
    """
    Generate code fixes using Ollama

    Args:
        issues: List of code issues
        language: Programming language

    Returns:
        List of code fixes
    """
    if ollama is None:
        return [
            CodeFix(
                issue_id=issue.id,
                description=f"Fix {issue.title}",
                code_before=issue.code_snippet,
                code_after=issue.suggestion or "# Fix implementation needed",
                explanation=issue.description,
                references=[]
            )
            for issue in issues[:10]
        ]

    fixes = []

    for issue in issues[:10]:  # Limit to top 10 for performance
        try:
            # Create prompt for Ollama
            prompt = f"""
            Generate a fix for this {language} code issue:

            Issue:
            - ID: {issue.id}
            - Severity: {issue.severity}
            - Category: {issue.category}
            - Title: {issue.title}
            - Description: {issue.description}
            - Line Number: {issue.line_number or 'N/A'}
            - Code Snippet:
            ```{language}
            {issue.code_snippet or 'N/A'}
            ```

            Return a JSON object with:
            {{
                "description": "<clear description of the fix>",
                "code_before": "<original code>",
                "code_after": "<fixed code>",
                "explanation": "<why this fix works>",
                "references": ["<reference 1>", "<reference 2>", ...]
            }}
            """

            # Call Ollama
            client = ollama.Client(host='http://127.0.0.1:11434')
            response = client.generate(
                model='qwen2.5-coder:7b',
                prompt=prompt,
                format='json'
            )

            # Parse response
            fix_data = json.loads(response.get('response', '{}'))

            # Create fix
            code_fix = CodeFix(
                issue_id=issue.id,
                description=fix_data.get('description', ''),
                code_before=fix_data.get('code_before'),
                code_after=fix_data.get('code_after'),
                explanation=fix_data.get('explanation', ''),
                references=fix_data.get('references', [])
            )

            fixes.append(code_fix)

        except Exception as e:
            logger.error(f"Error generating fix for {issue.id}: {e}")
            # Add basic fix as fallback
            fixes.append(CodeFix(
                issue_id=issue.id,
                description=f"Fix {issue.title}",
                code_before=issue.code_snippet,
                code_after=issue.suggestion or "# Fix implementation needed",
                explanation=issue.description,
                references=[]
            ))

    return fixes


# --- API Endpoints ---

@router.post("/audit", response_model=AuditReport, status_code=status.HTTP_200_OK)
async def audit_code(
    code_input: CodeInput,
    db: Session = Depends(get_db)
):
    """
    Audit code from a repository URL or code snippet

    Analyzes code for security vulnerabilities, performance issues,
    style violations, and bugs. Returns a detailed report with fixes.
    """
    import uuid
    audit_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    try:
        # Check if Ollama is available
        try:
            import requests
            response = requests.get('http://127.0.0.1:11434/api/tags', timeout=2)
            if response.status_code != 200:
                raise Exception("Ollama not available")
        except:
            logger.warning("Ollama not available, returning mock data")
            return AuditReport(
                audit_id=audit_id,
                code_input=code_input,
                issues=[{
                    "id": "mock-1",
                    "severity": "info",
                    "category": "availability",
                    "title": "AI Service Unavailable",
                    "description": "Ollama AI service is not running. Please start Ollama to enable full code auditing.",
                    "file_path": None,
                    "line_number": None,
                    "code_snippet": None,
                    "suggestion": "Start Ollama service: ollama serve"
                }],
                fixes=[],
                summary={
                    "total_issues": 1,
                    "by_severity": {"info": 1},
                    "by_category": {"availability": 1}
                },
                audit_time=datetime.utcnow(),
                audit_duration=0.1
            )

        all_issues = []

        if code_input.source_type == "repo_url":
            # Clone repository
            repo_path = await clone_repository(code_input.content)

            try:
                # Find code files
                language = code_input.language or detect_language_from_repo(repo_path)
                code_files = find_code_files(repo_path, language)

                if not code_files:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No code files found in repository"
                    )

                # Run security scans for Python files
                if language == "python":
                    for file_path in code_files[:10]:  # Limit to 10 files for performance
                        bandit_issues = await run_bandit_scan(file_path)
                        for issue in bandit_issues:
                            all_issues.append(CodeIssue(**issue))

                # Analyze code with AI for top files
                for file_path in code_files[:5]:  # Limit to 5 files for AI analysis
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code_content = f.read()

                        # Limit code size for AI analysis
                        if len(code_content) > 10000:  # ~300 lines
                            code_content = code_content[:10000]

                        ai_result = await analyze_code_with_ollama(
                            code_content,
                            language,
                            code_input.audit_type
                        )

                        for issue_data in ai_result.get('issues', []):
                            issue_data['file_path'] = file_path
                            all_issues.append(CodeIssue(**issue_data))

                    except Exception as e:
                        logger.error(f"Error analyzing file {file_path}: {e}")
                        continue

            finally:
                # Clean up cloned repository
                if os.path.exists(repo_path):
                    shutil.rmtree(repo_path)

        elif code_input.source_type == "snippet":
            # Analyze code snippet
            language = code_input.language or detect_language_from_snippet(code_input.content)
            if code_input.audit_type == "quick":
                # Quick audits skip AI to avoid long-running analysis
                all_issues = []
            else:
                # Analyze with AI
                try:
                    ai_result = await analyze_code_with_ollama(
                        code_input.content,
                        language,
                        code_input.audit_type
                    )

                    for issue_data in ai_result.get('issues', []):
                        all_issues.append(CodeIssue(**issue_data))
                except Exception as e:
                    logger.warning(f"AI analysis failed, returning fallback: {e}", exc_info=True)
                    all_issues.append(CodeIssue(
                        id="ai-fallback",
                        severity="info",
                        category="analysis",
                        title="AI analysis unavailable",
                        description=str(e)
                    ))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid source_type. Use 'repo_url' or 'snippet'"
            )

        # Sort issues by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
        all_issues.sort(key=lambda x: severity_order.get(x.severity, 5))

        # Generate fixes for top issues
        fixes = await generate_code_fixes(all_issues[:20], language)

        # Calculate audit duration
        audit_duration = (datetime.utcnow() - start_time).total_seconds()

        # Create summary
        summary = {
            "total_issues": len(all_issues),
            "critical_issues": sum(1 for i in all_issues if i.severity == "critical"),
            "high_issues": sum(1 for i in all_issues if i.severity == "high"),
            "medium_issues": sum(1 for i in all_issues if i.severity == "medium"),
            "low_issues": sum(1 for i in all_issues if i.severity == "low"),
            "info_issues": sum(1 for i in all_issues if i.severity == "info"),
            "categories": {}
        }

        # Count issues by category
        for issue in all_issues:
            category = issue.category
            if category not in summary["categories"]:
                summary["categories"][category] = 0
            summary["categories"][category] += 1

        # Log successful audit
        logger.info(
            f"Completed code audit {audit_id}: "
            f"{len(all_issues)} issues found in {audit_duration:.2f}s"
        )

        # Return response
        return AuditReport(
            audit_id=audit_id,
            code_input=code_input,
            issues=all_issues,
            fixes=fixes,
            summary=summary,
            audit_time=start_time,
            audit_duration=audit_duration
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in code audit: {e}", exc_info=True)
        fallback_issue = CodeIssue(
            id="audit-error",
            severity="info",
            category="execution",
            title="Audit failed",
            description=str(e),
            suggestion="Retry the audit or verify AI service availability"
        )
        return AuditReport(
            audit_id=audit_id,
            code_input=code_input,
            issues=[fallback_issue],
            fixes=[],
            summary={
                "total_issues": 1,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
                "info_issues": 1,
                "categories": {"execution": 1}
            },
            audit_time=start_time,
            audit_duration=(datetime.utcnow() - start_time).total_seconds()
        )


def detect_language_from_repo(repo_path: str) -> str:
    """
    Detect primary programming language from repository

    Args:
        repo_path: Path to repository

    Returns:
        Detected language (default: 'python')
    """
    # Simple heuristic based on file extensions
    language_counts = {}

    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                language_counts['python'] = language_counts.get('python', 0) + 1
            elif file.endswith('.js') or file.endswith('.jsx'):
                language_counts['javascript'] = language_counts.get('javascript', 0) + 1
            elif file.endswith('.ts') or file.endswith('.tsx'):
                language_counts['typescript'] = language_counts.get('typescript', 0) + 1
            elif file.endswith('.java'):
                language_counts['java'] = language_counts.get('java', 0) + 1
            elif file.endswith('.go'):
                language_counts['go'] = language_counts.get('go', 0) + 1

    # Return most common language
    if language_counts:
        return max(language_counts.items(), key=lambda x: x[1])[0]

    return 'python'  # Default


def detect_language_from_snippet(code: str) -> str:
    """
    Detect programming language from code snippet

    Args:
        code: Code snippet

    Returns:
        Detected language (default: 'python')
    """
    # Simple heuristic based on code patterns
    if 'def ' in code or 'import ' in code or 'from ' in code:
        return 'python'
    elif 'function ' in code or 'const ' in code or 'let ' in code:
        return 'javascript'
    elif 'interface ' in code or 'type ' in code or ': ' in code:
        return 'typescript'
    elif 'public class ' in code or 'private ' in code:
        return 'java'

    return 'python'  # Default if no language detected
