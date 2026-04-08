"""
Cyber Compliance Sentinel - Scans for vulnerabilities and provides fixes
"""
import logging
import tempfile
import subprocess
import json
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
try:
    from ollama import Client
except Exception:
    Client = None
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_fixed, wait_exponential
from database_production import get_db

# Logger (assumes logging is configured in main.py)
logger = logging.getLogger(__name__)

# Router
router = APIRouter(
    prefix="/compliance",
    tags=["compliance"],
    responses={404: {"description": "Not found"}},
)

# Ollama client (optional dependency)
client = Client(host='http://127.0.0.1:11434') if Client else None


class ComplianceScanInput(BaseModel):
    target: str = Field(..., description="Target to scan (URL, IP, or file path)")
    scan_type: str = Field(default="quick", description="Type of scan: quick, full, custom")


class ComplianceScanOutput(BaseModel):
    vulnerabilities: List[Dict] = Field(default_factory=list)
    recommendations: List[Dict] = Field(default_factory=list)


@router.post("/scan", response_model=ComplianceScanOutput)
async def scan_compliance(input_data: ComplianceScanInput) -> ComplianceScanOutput:
    """Scan system for vulnerabilities using Ollama AI"""
    try:
        logger.info(f"Starting compliance scan for: {input_data.target}")

        if client is None:
            logger.warning("Ollama client not installed, returning mock data")
            return ComplianceScanOutput(
                vulnerabilities=[{
                    "id": "mock-1",
                    "severity": "info",
                    "category": "availability",
                    "title": "AI Client Unavailable",
                    "description": "Ollama Python client is not installed. Install it to enable full vulnerability scanning.",
                    "affected_component": "compliance-scanner"
                }],
                recommendations=[{
                    "action": "Install ollama Python client in the backend image",
                    "priority": "high"
                }]
            )
        
        # Check if Ollama is available
        try:
            import requests
            response = requests.get('http://127.0.0.1:11434/api/tags', timeout=2)
            if response.status_code != 200:
                raise Exception("Ollama not available")
        except:
            logger.warning("Ollama not available, returning mock data")
            return ComplianceScanOutput(
                vulnerabilities=[{
                    "id": "mock-1",
                    "severity": "info",
                    "category": "availability",
                    "title": "AI Service Unavailable",
                    "description": "Ollama AI service is not running. Please start Ollama to enable full vulnerability scanning.",
                    "affected_component": "compliance-scanner"
                }],
                recommendations=[{
                    "action": "Start Ollama service: ollama serve",
                    "priority": "high"
                }]
            )
        
        prompt = f"Scan {input_data.target} for security vulnerabilities. Scan type: {input_data.scan_type}. Return JSON with vulnerabilities and recommendations."
        
        logger.info(f"Calling Ollama for compliance scan")
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat,
                    model='qwen2.5-coder:7b',
                    messages=[{'role': 'user', 'content': prompt}]
                ),
                timeout=8
            )
            logger.info(f"Ollama response received")
            
            content = response.get('message', {}).get('content', '')
            
            # Parse the response (in production, you would validate the JSON structure)
            return ComplianceScanOutput(
                vulnerabilities=[{"target": input_data.target, "details": content}],
                recommendations=[{"action": "Review and patch identified vulnerabilities"}]
            )
        except Exception as e:
            logger.warning(f"Ollama scan failed, returning fallback: {e}", exc_info=True)
            return ComplianceScanOutput(
                vulnerabilities=[{
                    "id": "ai-fallback",
                    "severity": "info",
                    "category": "analysis",
                    "title": "AI analysis unavailable",
                    "description": f"AI analysis failed: {str(e)}",
                    "affected_component": "compliance-scanner"
                }],
                recommendations=[{
                    "action": "Retry scan when AI service is available",
                    "priority": "medium"
                }]
            )
        
    except Exception as e:
        logger.error(f"Compliance scan failed: {e}", exc_info=True)
        return ComplianceScanOutput(
            vulnerabilities=[{
                "id": "scan-error",
                "severity": "info",
                "category": "execution",
                "title": "Compliance scan failed",
                "description": str(e),
                "affected_component": "compliance-scanner"
            }],
            recommendations=[{
                "action": "Retry the scan or verify AI service availability",
                "priority": "medium"
            }]
        )



class FixRecommendation(BaseModel):
    """Recommended fix for a vulnerability"""
    vulnerability_id: str
    priority: str
    description: str
    steps: List[str]
    code_example: Optional[str] = None
    references: List[str] = []


class SystemInfo(BaseModel):
    """System information for compliance scan"""
    system_type: str = Field(..., description="Type of system: web, api, mobile, desktop")
    hostname: str = Field(..., description="System hostname or URL")
    ip_address: Optional[str] = Field(None, description="IP address if applicable")
    environment: str = Field(default="production", description="Environment: development, staging, production")
    description: Optional[str] = Field(None, description="System description")
    target: str = Field(..., description="Target to scan (URL, IP, or file path)")
    scan_type: str = Field(default="quick", description="Type of scan: quick, full, custom")
    tech_stack: List[str] = Field(default_factory=list, description="Technology stack used in the system")


class Vulnerability(BaseModel):
    """Detected vulnerability"""
    id: str
    severity: str  # critical, high, medium, low
    category: str  # injection, misconfig, xss, etc.
    title: str
    description: str
    affected_component: str
    cvss_score: Optional[float] = None
    references: List[str] = []
    evidence: Optional[str] = None  # Evidence or code snippet showing the vulnerability


class ComplianceReport(BaseModel):
    """Compliance scan report"""
    scan_id: str
    system_info: SystemInfo
    vulnerabilities: List[Vulnerability]
    fixes: List[FixRecommendation]
    summary: Dict[str, Any]
    scan_time: datetime
    scan_duration: float


# --- Scan Functions ---

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def run_nmap_scan(target: str, scan_type: str = "quick") -> List[Dict[str, Any]]:
    """
    Run Nmap scan on target

    Args:
        target: Target to scan (URL, IP)
        scan_type: Type of scan (quick, full)

    Returns:
        List of detected vulnerabilities
    """
    try:
        # Build nmap command based on scan type
        if scan_type == "quick":
            cmd = ["nmap", "-sV", "-sC", "-oX", "-", target]
        elif scan_type == "full":
            cmd = ["nmap", "-p-", "-sV", "-sC", "-A", "-oX", "-", target]
        else:
            cmd = ["nmap", "-sV", "-oX", "-", target]

        # Run nmap
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"Nmap scan failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)

        # Parse XML output
        import xml.etree.ElementTree as ET
        root = ET.fromstring(result.stdout)

        vulnerabilities = []

        # Parse ports and services
        for port in root.findall(".//port"):
            port_id = port.get("portid")
            protocol = port.get("protocol")

            service = port.find("service")
            if service is not None:
                service_name = service.get("name", "unknown")
                service_version = service.get("version", "")

                # Check for common vulnerabilities
                vuln = check_common_vulnerabilities(service_name, service_version)
                if vuln:
                    vulnerabilities.append(vuln)

        return vulnerabilities

    except subprocess.TimeoutExpired:
        logger.error(f"Nmap scan timed out for target: {target}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Scan timed out"
        )
    except Exception as e:
        logger.error(f"Error running Nmap scan: {e}")
        raise


def check_common_vulnerabilities(service_name: str, service_version: str) -> Optional[Dict[str, Any]]:
    """
    Check for common vulnerabilities in services

    Args:
        service_name: Name of the service
        service_version: Version of the service

    Returns:
        Vulnerability dict if found, None otherwise
    """
    # Define known vulnerable services/versions
    known_vulns = {
        "ssh": {
            "1.0": {"severity": "critical", "title": "SSH Protocol 1.0", "description": "SSH protocol 1.0 has known vulnerabilities"},
            "1.5": {"severity": "high", "title": "SSH Protocol 1.5", "description": "SSH protocol 1.5 has known vulnerabilities"}
        },
        "http": {
            "1.0": {"severity": "high", "title": "HTTP/1.0", "description": "HTTP/1.0 is deprecated and insecure"},
            "apache": {
                "2.2.22": {"severity": "high", "title": "Apache 2.2.22", "description": "Multiple vulnerabilities in Apache 2.2.22"}
            }
        }
    }

    # Check if service/version is in known vulnerabilities
    if service_name.lower() in known_vulns:
        service_vulns = known_vulns[service_name.lower()]

        # Direct version match
        if service_version in service_vulns:
            vuln_info = service_vulns[service_version]
            return {
                "id": f"{service_name}-{service_version}",
                "severity": vuln_info["severity"],
                "title": vuln_info["title"],
                "description": vuln_info["description"],
                "affected_component": f"{service_name} {service_version}"
            }

        # Check nested versions
        for version, vuln_info in service_vulns.items():
            if isinstance(vuln_info, dict) and version in service_version:
                return {
                    "id": f"{service_name}-{version}",
                    "severity": vuln_info["severity"],
                    "title": vuln_info["title"],
                    "description": vuln_info["description"],
                    "affected_component": f"{service_name} {service_version}"
                }

    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def run_bandit_scan(file_path: str) -> List[Dict[str, Any]]:
    """
    Run Bandit security scan on Python code

    Args:
        file_path: Path to Python file or directory to scan

    Returns:
        List of detected vulnerabilities
    """
    try:
        # Build bandit command
        cmd = ["bandit", "-r", "-f", "json", file_path]

        # Run bandit
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Parse JSON output
        try:
            bandit_output = json.loads(result.stdout)

            vulnerabilities = []

            for issue in bandit_output.get("results", []):
                vuln = {
                    "id": f"bandit-{issue['test_id']}",
                    "severity": map_severity(issue["issue_severity"]),
                    "title": issue["test_name"],
                    "description": issue["issue_text"],
                    "affected_component": f"{issue['filename']}:{issue['line_number']}",
                    "evidence": issue.get("code", "")
                }
                vulnerabilities.append(vuln)

            return vulnerabilities

        except json.JSONDecodeError:
            logger.error(f"Failed to parse Bandit output: {result.stdout}")
            return []

    except subprocess.TimeoutExpired:
        logger.error(f"Bandit scan timed out for: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Scan timed out"
        )
    except FileNotFoundError:
        logger.warning(f"Bandit not installed, skipping code scan")
        return []
    except Exception as e:
        logger.error(f"Error running Bandit scan: {e}")
        raise


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


async def generate_fix_recommendations(
    vulnerabilities: List[Vulnerability],
    system_info: SystemInfo
) -> List[FixRecommendation]:
    """
    Generate fix recommendations using Ollama

    Args:
        vulnerabilities: List of detected vulnerabilities
        system_info: System information

    Returns:
        List of fix recommendations
    """
    if client is None:
        return [
            FixRecommendation(
                vulnerability_id=vuln.id,
                priority=vuln.severity,
                description=f"Fix {vuln.title}: {vuln.description}",
                steps=[f"Update or patch {vuln.affected_component}"],
                references=[]
            )
            for vuln in vulnerabilities[:5]
        ]

    recommendations = []

    for vuln in vulnerabilities[:5]:  # Limit to top 5 for performance
        try:
            # Create prompt for Ollama
            prompt = f"""
            Generate a fix recommendation for this vulnerability:

            Vulnerability:
            - ID: {vuln.id}
            - Severity: {vuln.severity}
            - Title: {vuln.title}
            - Description: {vuln.description}
            - Affected Component: {vuln.affected_component}
            - Evidence: {vuln.evidence or 'None'}

            System Info:
            - Type: {system_info.system_type}
            - Tech Stack: {', '.join(system_info.tech_stack)}

            Return a JSON object with:
            {{
                "priority": "<critical/high/medium/low>",
                "description": "<clear description of the fix>",
                "steps": [<step 1>, <step 2>, ...],
                "code_example": "<optional code example if applicable>",
                "references": ["<reference 1>", "<reference 2>", ...]
            }}
            """

            # Call Ollama
            response = client.generate(
                model='qwen2.5-coder:7b',
                prompt=prompt,
                format='json'
            )

            # Parse response
            fix_data = json.loads(response.get('response', '{}'))

            # Create recommendation
            recommendation = FixRecommendation(
                vulnerability_id=vuln.id,
                priority=fix_data.get('priority', 'medium'),
                description=fix_data.get('description', ''),
                steps=fix_data.get('steps', []),
                code_example=fix_data.get('code_example'),
                references=fix_data.get('references', [])
            )

            recommendations.append(recommendation)

        except Exception as e:
            logger.error(f"Error generating fix for {vuln.id}: {e}")
            # Add basic recommendation as fallback
            recommendations.append(FixRecommendation(
                vulnerability_id=vuln.id,
                priority=vuln.severity,
                description=f"Fix {vuln.title}: {vuln.description}",
                steps=[f"Update or patch {vuln.affected_component}"],
                references=[]
            ))

    return recommendations


# --- API Endpoints ---

@router.post("/scan/system")
async def scan_system(
    system_info: SystemInfo,
    db: Session = Depends(get_db)
):
    """
    Scan system for vulnerabilities

    Analyzes the specified system for security vulnerabilities and provides
    detailed report with fix recommendations.
    """
    scan_id = f"scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    start_time = datetime.utcnow()

    try:
        vulnerabilities = []

        # Run appropriate scan based on system type
        if system_info.system_type in ["web", "api"]:
            # Run Nmap scan for web/API systems
            try:
                nmap_vulns = await run_nmap_scan(
                    system_info.target,
                    system_info.scan_type
                )
                vulnerabilities.extend(nmap_vulns)
            except Exception as e:
                logger.error(f"Nmap scan failed: {e}")

        # Run Bandit scan if Python is in tech stack
        if "python" in [t.lower() for t in system_info.tech_stack]:
            try:
                bandit_vulns = await run_bandit_scan(system_info.target)
                vulnerabilities.extend(bandit_vulns)
            except Exception as e:
                logger.error(f"Bandit scan failed: {e}")

        # Generate fix recommendations
        fixes = await generate_fix_recommendations(vulnerabilities, system_info)

        # Calculate summary
        severity_counts = {}
        for vuln in vulnerabilities:
            severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1

        summary = {
            "total_vulnerabilities": len(vulnerabilities),
            "severity_breakdown": severity_counts,
            "system_type": system_info.system_type,
            "tech_stack": system_info.tech_stack
        }

        # Calculate scan duration
        scan_duration = (datetime.utcnow() - start_time).total_seconds()

        # Log successful scan
        logger.info(
            f"Completed compliance scan {scan_id}: "
            f"{len(vulnerabilities)} vulnerabilities found in {scan_duration:.2f}s"
        )

        # Return report
        return ComplianceReport(
            scan_id=scan_id,
            system_info=system_info,
            vulnerabilities=vulnerabilities,
            fixes=fixes,
            summary=summary,
            scan_time=start_time,
            scan_duration=scan_duration
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in compliance scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during the compliance scan"
        )


@router.get("/scans")
async def list_scans(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    List recent compliance scans

    Returns a list of recent scans with basic information
    """
    try:
        # In production, this would query the database
        # For now, return empty list
        return []

    except Exception as e:
        logger.error(f"Error listing scans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing scans"
        )
