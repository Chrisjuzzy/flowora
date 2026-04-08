"""
Ethical AI Guardian - Audits AI configurations for ethical concerns
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from database_production import get_db
import logging
from datetime import datetime
import json
from tenacity import retry, stop_after_attempt, wait_exponential
try:
    import ollama
except Exception:
    ollama = None

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ethics",
    tags=["ethics-guardian"],
    responses={404: {"description": "Not found"}},
)


# --- Pydantic Models ---

class AIConfig(BaseModel):
    """AI system configuration"""
    system_name: str = Field(..., description="Name of the AI system")
    system_type: str = Field(..., description="Type of AI system (chatbot, recommendation, etc.)")
    purpose: str = Field(..., description="Intended purpose of the AI system")
    target_users: List[str] = Field(..., description="Target user groups")
    data_sources: List[str] = Field(..., description="Data sources used for training")
    model_details: Dict[str, Any] = Field(..., description="Model details (architecture, parameters, etc.)")
    deployment_context: Optional[Dict[str, Any]] = Field(None, description="Deployment context and constraints")
    safeguards: Optional[List[str]] = Field(None, description="Existing safeguards and mitigations")


class EthicalConcern(BaseModel):
    """Detected ethical concern"""
    id: str
    category: str  # bias, privacy, transparency, accountability, safety, fairness
    severity: str  # critical, high, medium, low
    title: str
    description: str
    impact: str
    affected_stakeholders: List[str]
    evidence: Optional[str] = None


class EthicalRecommendation(BaseModel):
    """Recommendation for addressing ethical concerns"""
    concern_id: str
    priority: str
    title: str
    description: str
    implementation_steps: List[str]
    expected_outcome: str
    references: List[str] = []


class EthicalReport(BaseModel):
    """Ethical audit report"""
    audit_id: str
    ai_config: AIConfig
    concerns: List[EthicalConcern]
    recommendations: List[EthicalRecommendation]
    summary: Dict[str, Any]
    audit_time: datetime


# --- Audit Functions ---

async def check_for_bias(
    ai_config: AIConfig
) -> List[EthicalConcern]:
    """
    Check AI configuration for potential bias issues

    Args:
        ai_config: AI system configuration

    Returns:
        List of bias-related concerns
    """
    concerns = []

    # Check for diverse data sources
    if len(ai_config.data_sources) < 3:
        concerns.append(EthicalConcern(
            id="bias-limited-data",
            category="bias",
            severity="medium",
            title="Limited Data Source Diversity",
            description=f"AI system uses only {len(ai_config.data_sources)} data source(s), which may lead to biased outcomes",
            impact="Model may not generalize well to diverse populations or contexts",
            affected_stakeholders=["end_users", "minority_groups"],
            evidence=f"Data sources: {', '.join(ai_config.data_sources)}"
        ))

    # Check for diverse target users
    if len(ai_config.target_users) < 2:
        concerns.append(EthicalConcern(
            id="bias-limited-users",
            category="bias",
            severity="medium",
            title="Limited Target User Diversity",
            description="AI system is designed for a narrow range of users, which may lead to exclusion",
            impact="System may not work well for users outside the primary target group",
            affected_stakeholders=["excluded_users"],
            evidence=f"Target users: {', '.join(ai_config.target_users)}"
        ))

    # Check for bias mitigation strategies
    safeguards = ai_config.safeguards or []
    bias_safeguards = [s for s in safeguards if 'bias' in s.lower()]
    if not bias_safeguards:
        concerns.append(EthicalConcern(
            id="bias-no-mitigation",
            category="bias",
            severity="high",
            title="No Explicit Bias Mitigation",
            description="AI configuration does not include explicit bias mitigation strategies",
            impact="Model may perpetuate or amplify existing biases in the data",
            affected_stakeholders=["end_users", "minority_groups", "society"],
            evidence="No bias-related safeguards found in configuration"
        ))

    return concerns


async def check_for_privacy(
    ai_config: AIConfig
) -> List[EthicalConcern]:
    """
    Check AI configuration for privacy issues

    Args:
        ai_config: AI system configuration

    Returns:
        List of privacy-related concerns
    """
    concerns = []

    # Check for privacy safeguards
    safeguards = ai_config.safeguards or []
    privacy_safeguards = [s for s in safeguards if 'privacy' in s.lower() or 'anonym' in s.lower()]
    if not privacy_safeguards:
        concerns.append(EthicalConcern(
            id="privacy-no-safeguards",
            category="privacy",
            severity="high",
            title="No Explicit Privacy Safeguards",
            description="AI configuration does not include explicit privacy protection measures",
            impact="User data may be at risk of exposure or misuse",
            affected_stakeholders=["end_users"],
            evidence="No privacy-related safeguards found in configuration"
        ))

    # Check for data source transparency
    if not ai_config.data_sources:
        concerns.append(EthicalConcern(
            id="privacy-opaque-sources",
            category="privacy",
            severity="medium",
            title="Opaque Data Sources",
            description="AI configuration does not specify data sources used for training",
            impact="Cannot assess privacy implications of data usage",
            affected_stakeholders=["end_users", "regulators"],
            evidence="No data sources specified in configuration"
        ))

    return concerns


async def check_for_transparency(
    ai_config: AIConfig
) -> List[EthicalConcern]:
    """
    Check AI configuration for transparency issues

    Args:
        ai_config: AI system configuration

    Returns:
        List of transparency-related concerns
    """
    concerns = []

    # Check for model explainability
    safeguards = ai_config.safeguards or []
    explainability_safeguards = [s for s in safeguards if 'explain' in s.lower() or 'interpret' in s.lower()]
    if not explainability_safeguards:
        concerns.append(EthicalConcern(
            id="transparency-no-explainability",
            category="transparency",
            severity="medium",
            title="No Explainability Mechanisms",
            description="AI configuration does not include explainability or interpretability features",
            impact="Users and developers cannot understand how decisions are made",
            affected_stakeholders=["end_users", "developers", "regulators"],
            evidence="No explainability-related safeguards found in configuration"
        ))

    # Check for documentation
    if not ai_config.model_details:
        concerns.append(EthicalConcern(
            id="transparency-limited-docs",
            category="transparency",
            severity="low",
            title="Limited Model Documentation",
            description="AI configuration provides limited model details",
            impact="Difficult to assess system capabilities and limitations",
            affected_stakeholders=["developers", "auditors"],
            evidence="Model details not specified in configuration"
        ))

    return concerns


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def analyze_ethics_with_ollama(
    ai_config: AIConfig,
    category: str
) -> List[EthicalConcern]:
    """
    Use Ollama to analyze AI configuration for ethical concerns in a specific category

    Args:
        ai_config: AI system configuration
        category: Category to analyze (bias, privacy, transparency, accountability, safety, fairness)

    Returns:
        List of ethical concerns
    """
    try:
        if ollama is None:
            return []
        # Create prompt for Ollama
        prompt = f"""
        Analyze this AI system configuration for {category} concerns:

        System Name: {ai_config.system_name}
        System Type: {ai_config.system_type}
        Purpose: {ai_config.purpose}
        Target Users: {', '.join(ai_config.target_users)}
        Data Sources: {', '.join(ai_config.data_sources)}

        Model Details:
        {json.dumps(ai_config.model_details, indent=2)}

        Deployment Context:
        {json.dumps(ai_config.deployment_context or {}, indent=2)}

        Existing Safeguards:
        {', '.join(ai_config.safeguards or [])}

        Return a JSON object with:
        {{
            "concerns": [
                {{
                    "id": "<unique identifier>",
                    "category": "{category}",
                    "severity": "<critical/high/medium/low>",
                    "title": "<short title>",
                    "description": "<detailed description>",
                    "impact": "<potential impact>",
                    "affected_stakeholders": ["<stakeholder 1>", "<stakeholder 2>", ...],
                    "evidence": "<evidence from configuration>"
                }}
            ]
        }}
        """

        # Call Ollama
        response = ollama.generate(
            model='qwen2.5-coder:7b',
            prompt=prompt,
            format='json'
        )

        # Parse response
        result = json.loads(response['response'])

        # Validate response structure
        if 'concerns' not in result:
            logger.error(f"Invalid response from Ollama: {result}")
            raise ValueError("Invalid response format from Ollama")

        # Create EthicalConcern objects
        concerns = []
        for concern_data in result['concerns']:
            concern = EthicalConcern(**concern_data)
            concerns.append(concern)

        return concerns

    except Exception as e:
        logger.error(f"Error analyzing {category} with Ollama: {e}")
        raise


async def generate_ethical_recommendations(
    concerns: List[EthicalConcern],
    ai_config: AIConfig
) -> List[EthicalRecommendation]:
    """
    Generate recommendations for addressing ethical concerns

    Args:
        concerns: List of ethical concerns
        ai_config: AI system configuration

    Returns:
        List of ethical recommendations
    """
    if ollama is None:
        return [
            EthicalRecommendation(
                concern_id=concern.id,
                priority=concern.severity,
                title=f"Address {concern.title}",
                description=f"Implement measures to address: {concern.description}",
                implementation_steps=[
                    "Review the ethical concern",
                    "Consult with stakeholders",
                    "Implement appropriate safeguards",
                    "Monitor effectiveness"
                ],
                expected_outcome="Reduced ethical risk",
                references=[]
            )
            for concern in concerns[:5]
        ]

    recommendations = []

    for concern in concerns[:5]:  # Limit to top 5 for performance
        try:
            # Create prompt for Ollama
            prompt = f"""
            Generate a recommendation to address this ethical concern:

            Concern:
            - ID: {concern.id}
            - Category: {concern.category}
            - Severity: {concern.severity}
            - Title: {concern.title}
            - Description: {concern.description}
            - Impact: {concern.impact}
            - Affected Stakeholders: {', '.join(concern.affected_stakeholders)}
            - Evidence: {concern.evidence or 'None'}

            AI System:
            - Name: {ai_config.system_name}
            - Type: {ai_config.system_type}
            - Purpose: {ai_config.purpose}
            - Target Users: {', '.join(ai_config.target_users)}

            Return a JSON object with:
            {{
                "priority": "<critical/high/medium/low>",
                "title": "<short title>",
                "description": "<clear description of the recommendation>",
                "implementation_steps": ["<step 1>", "<step 2>", ...],
                "expected_outcome": "<what this will achieve>",
                "references": ["<reference 1>", "<reference 2>", ...]
            }}
            """

            # Call Ollama
            response = ollama.generate(
                model='qwen2.5-coder:7b',
                prompt=prompt,
                format='json'
            )

            # Parse response
            rec_data = json.loads(response['response'])

            # Create recommendation
            recommendation = EthicalRecommendation(
                concern_id=concern.id,
                priority=rec_data.get('priority', 'medium'),
                title=rec_data.get('title', f"Address {concern.title}"),
                description=rec_data.get('description', ''),
                implementation_steps=rec_data.get('implementation_steps', []),
                expected_outcome=rec_data.get('expected_outcome', ''),
                references=rec_data.get('references', [])
            )

            recommendations.append(recommendation)

        except Exception as e:
            logger.error(f"Error generating recommendation for {concern.id}: {e}")
            # Add basic recommendation as fallback
            recommendations.append(EthicalRecommendation(
                concern_id=concern.id,
                priority=concern.severity,
                title=f"Address {concern.title}",
                description=f"Implement measures to address: {concern.description}",
                implementation_steps=[
                    "Review the ethical concern",
                    "Consult with stakeholders",
                    "Implement appropriate safeguards",
                    "Monitor effectiveness"
                ],
                expected_outcome="Reduced ethical risk",
                references=[]
            ))

    return recommendations


def calculate_overall_risk(concerns: List[EthicalConcern]) -> str:
    """
    Calculate overall risk level from list of concerns

    Args:
        concerns: List of ethical concerns

    Returns:
        Overall risk level (critical, high, medium, low)
    """
    if not concerns:
        return "low"

    # Count concerns by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for concern in concerns:
        severity_counts[concern.severity] = severity_counts.get(concern.severity, 0) + 1

    # Determine overall risk
    if severity_counts["critical"] > 0:
        return "critical"
    elif severity_counts["high"] >= 2:
        return "high"
    elif severity_counts["high"] >= 1 or severity_counts["medium"] >= 3:
        return "medium"
    else:
        return "low"


# --- API Endpoints ---

class EthicsScanRequest(BaseModel):
    """Request for ethics scan"""
    content: str = Field(..., description="AI system content to scan for ethical concerns")
    system_type: str = Field(default="chatbot", description="Type of AI system")

@router.post("/scan", response_model=EthicalReport, status_code=status.HTTP_200_OK)
async def scan_ethics(
    request: EthicsScanRequest,
    db: Session = Depends(get_db)
):
    """
    Quick scan of AI content for ethical concerns

    Performs a simplified ethical audit on provided content
    """
    try:
        # Generate unique scan ID
        scan_id = f"ethics-scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Create minimal AI config from content
        ai_config = AIConfig(
            system_name="Quick Scan",
            system_type=request.system_type,
            purpose="Quick ethical assessment",
            target_users=["general"],
            data_sources=[request.content],
            model_details={"type": "unknown"},
            safeguards=[]
        )

        # Collect concerns
        all_concerns = []

        # Check for bias
        bias_concerns = await check_for_bias(ai_config)
        all_concerns.extend(bias_concerns)

        # Check for privacy
        privacy_concerns = await check_for_privacy(ai_config)
        all_concerns.extend(privacy_concerns)

        # Check for transparency
        transparency_concerns = await check_for_transparency(ai_config)
        all_concerns.extend(transparency_concerns)

        # Generate recommendations
        recommendations = await generate_ethical_recommendations(all_concerns, ai_config)

        # Sort concerns by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_concerns.sort(key=lambda x: severity_order.get(x.severity, 4))

        # Create summary
        summary = {
            "total_concerns": len(all_concerns),
            "critical_concerns": sum(1 for c in all_concerns if c.severity == "critical"),
            "high_concerns": sum(1 for c in all_concerns if c.severity == "high"),
            "medium_concerns": sum(1 for c in all_concerns if c.severity == "medium"),
            "low_concerns": sum(1 for c in all_concerns if c.severity == "low"),
            "categories": list(set(c.category for c in all_concerns)),
            "overall_risk_level": calculate_overall_risk(all_concerns)
        }

        # Return report
        return EthicalReport(
            audit_id=scan_id,
            ai_config=ai_config,
            concerns=all_concerns,
            recommendations=recommendations,
            summary=summary,
            audit_time=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error in ethics scan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ethics scan failed: {str(e)}"
        )

@router.post("/audit", response_model=EthicalReport, status_code=status.HTTP_200_OK)
async def audit_ethics(
    ai_config: AIConfig,
    db: Session = Depends(get_db)
):
    """
    Audit AI configuration for ethical concerns

    Analyzes AI system configuration and returns ethical concerns
    with recommendations for addressing them
    """
    try:
        # Generate unique audit ID
        audit_id = f"ethics-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Collect all concerns
        all_concerns = []

        # Check for bias
        bias_concerns = await check_for_bias(ai_config)
        all_concerns.extend(bias_concerns)

        # Check for privacy
        privacy_concerns = await check_for_privacy(ai_config)
        all_concerns.extend(privacy_concerns)

        # Check for transparency
        transparency_concerns = await check_for_transparency(ai_config)
        all_concerns.extend(transparency_concerns)

        # Use AI to analyze additional categories
        try:
            accountability_concerns = await analyze_ethics_with_ollama(ai_config, "accountability")
            all_concerns.extend(accountability_concerns)
        except Exception as e:
            logger.warning(f"AI analysis for accountability failed: {e}")

        try:
            safety_concerns = await analyze_ethics_with_ollama(ai_config, "safety")
            all_concerns.extend(safety_concerns)
        except Exception as e:
            logger.warning(f"AI analysis for safety failed: {e}")

        try:
            fairness_concerns = await analyze_ethics_with_ollama(ai_config, "fairness")
            all_concerns.extend(fairness_concerns)
        except Exception as e:
            logger.warning(f"AI analysis for fairness failed: {e}")

        # Generate recommendations
        recommendations = await generate_ethical_recommendations(all_concerns, ai_config)

        # Sort concerns by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_concerns.sort(key=lambda x: severity_order.get(x.severity, 4))

        # Create summary
        summary = {
            "total_concerns": len(all_concerns),
            "critical_concerns": sum(1 for c in all_concerns if c.severity == "critical"),
            "high_concerns": sum(1 for c in all_concerns if c.severity == "high"),
            "medium_concerns": sum(1 for c in all_concerns if c.severity == "medium"),
            "low_concerns": sum(1 for c in all_concerns if c.severity == "low"),
            "categories": list(set(c.category for c in all_concerns)),
            "overall_risk_level": calculate_overall_risk(all_concerns)
        }

        # Log successful audit
        logger.info(
            f"Ethical audit completed for {ai_config.system_name}: "
            f"{len(all_concerns)} concerns found, "
            f"risk level: {summary['overall_risk_level']}"
        )

        # Return report
        return EthicalReport(
            audit_id=audit_id,
            ai_config=ai_config,
            concerns=all_concerns,
            recommendations=recommendations,
            summary=summary,
            audit_time=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ethical audit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during ethical audit"
        )


def calculate_overall_risk(concerns: List[EthicalConcern]) -> str:
    """
    Calculate overall risk level based on concerns

    Args:
        concerns: List of ethical concerns

    Returns:
        Risk level (critical, high, medium, low)
    """
    if not concerns:
        return "low"

    # Count concerns by severity
    critical_count = sum(1 for c in concerns if c.severity == "critical")
    high_count = sum(1 for c in concerns if c.severity == "high")
    medium_count = sum(1 for c in concerns if c.severity == "medium")

    # Determine overall risk
    if critical_count > 0:
        return "critical"
    elif high_count >= 3:
        return "critical"
    elif high_count > 0:
        return "high"
    elif medium_count >= 5:
        return "high"
    elif medium_count > 0:
        return "medium"
    else:
        return "low"
        return "low"
