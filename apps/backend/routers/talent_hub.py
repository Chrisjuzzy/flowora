"""
AI Talent Marketplace Hub - Matches SMBs with virtual agents
"""
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from database_production import get_db
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
try:
    import ollama
except Exception:  # Optional dependency
    ollama = None
from security import oauth2_scheme, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/talent",
    tags=["talent"],
    responses={404: {"description": "Not found"}},
)


class TalentMatchInput(BaseModel):
    business_needs: str = Field(..., description="Business needs for agent matching")
    industry: Optional[str] = Field(None, description="Industry sector")
    role_type: Optional[str] = Field(None, description="Type of role needed")
    skills_required: Optional[List[str]] = Field(None, description="Required skills")
    experience_level: Optional[str] = Field(None, description="Required experience level")
    budget_range: Optional[str] = Field(None, description="Budget range for the role")
    work_hours: Optional[str] = Field(None, description="Preferred work hours")
    timezone: Optional[str] = Field(None, description="Timezone preference")
    special_requirements: Optional[str] = Field(None, description="Any special requirements")


class TalentMatchOutput(BaseModel):
    matches: List[Dict] = Field(default_factory=list)


class BusinessNeed(BaseModel):
    """Business requirements for talent matching"""
    business_needs: str = Field(..., description="Description of business needs")
    industry: Optional[str] = None
    role_type: Optional[str] = None
    skills_required: Optional[List[str]] = None
    experience_level: Optional[str] = None
    budget_range: Optional[str] = None
    work_hours: Optional[str] = None
    timezone: Optional[str] = None
    special_requirements: Optional[str] = None


class AgentProfile(BaseModel):
    """Extended agent profile with talent matching fields"""
    id: int
    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_published: bool = False
    tags: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = "1.0.0"
    owner_id: Optional[int] = None
    rating: float = 0.0  # Agent rating for filtering

    # Talent matching specific fields (extracted from config)
    role_type: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    hourly_rate: Optional[str] = None
    availability: Optional[str] = None
    timezone: Optional[str] = None


class MatchResult(BaseModel):
    """Result of matching a business need with an agent"""
    agent: AgentProfile
    match_score: float
    match_reasons: List[str]


class MatchResponse(BaseModel):
    """Response containing all match results"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    business_needs: BusinessNeed
    matches: List[MatchResult]
    total_matches: int
    generated_at: datetime


def get_all_agent_profiles(db: Session) -> List[AgentProfile]:
    """Get all available agent profiles from the database"""
    from models.agent import Agent as AgentModel
    agents = db.query(AgentModel).filter(AgentModel.is_published == True).all()

    # Convert database models to Pydantic schemas with proper config handling
    profiles = []
    for agent in agents:
        try:
            # Handle config field - ensure it's a dict, not a string
            config_data = agent.config
            if isinstance(config_data, str):
                import json
                config_data = json.loads(config_data)

            # Extract talent matching fields from config, tags, or category
            # Parse tags into list if they exist - handle both commas and hyphens
            skills_list = []
            if agent.tags:
                # First try to split by comma
                if ',' in agent.tags:
                    skills_list = [tag.strip() for tag in agent.tags.split(',')]
                # If no comma, split by hyphen
                elif '-' in agent.tags:
                    skills_list = [tag.strip() for tag in agent.tags.split('-')]
                # Otherwise, use the whole tag as a single skill
                else:
                    skills_list = [agent.tags.strip()]

            # Determine role type from category or description
            role_type_value = None
            if config_data and 'role_type' in config_data:
                role_type_value = config_data['role_type']
            elif agent.category:
                role_type_value = agent.category

            profile = AgentProfile(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                config=config_data,
                is_published=agent.is_published,
                tags=agent.tags,
                category=agent.category,
                version=agent.version,
                owner_id=agent.owner_id,
                # Talent matching fields - extract from multiple sources
                role_type=role_type_value,
                skills=skills_list,
                experience_level=config_data.get('experience_level') if config_data else "Intermediate",
                hourly_rate=config_data.get('hourly_rate') if config_data else "30-50 CHF",
                availability=config_data.get('availability') if config_data else "Part-time",
                timezone=config_data.get('timezone') if config_data else "CET"
            )
            profiles.append(profile)
        except Exception as e:
            logger.error(f"Error processing agent {agent.id}: {e}", exc_info=True)
            continue

    return profiles

        
        
        
        
        


async def analyze_match_with_ollama(
    business_needs: "BusinessNeed",
    agent_profile: "AgentProfile"
) -> Dict[str, Any]:
    """
    Use Ollama to analyze match quality between business needs and agent profile

    Args:
        business_needs: Business requirements
        agent_profile: Agent profile to match against

    Returns:
        Dictionary with match_score and match_reasons
    """
    try:
        if ollama is None:
            raise HTTPException(
                status_code=503,
                detail="Ollama client is not installed on the backend image"
            )
        # Create prompt for Ollama with more structured format
        prompt = f"""You are an AI talent matching expert. Analyze the compatibility between business needs and an agent profile.

Business Requirements:
- Description: {business_needs.business_needs or 'Not specified'}
- Industry: {business_needs.industry or 'Not specified'}
- Role Type: {business_needs.role_type or 'Not specified'}
- Required Skills: {', '.join(business_needs.skills_required) if business_needs.skills_required else 'Not specified'}
- Experience Level: {business_needs.experience_level or 'Not specified'}
- Budget Range: {business_needs.budget_range or 'Not specified'}
- Work Hours: {business_needs.work_hours or 'Not specified'}
- Timezone: {business_needs.timezone or 'Not specified'}
- Special Requirements: {business_needs.special_requirements or 'None'}

Agent Profile:
- Name: {agent_profile.name}
- Category: {agent_profile.category or 'Not specified'}
- Role Type: {agent_profile.role_type or 'Not specified'}
- Skills: {', '.join(agent_profile.skills) if agent_profile.skills else 'Not specified'}
- Experience Level: {agent_profile.experience_level or 'Not specified'}
- Hourly Rate: {agent_profile.hourly_rate or 'Not specified'}
- Availability: {agent_profile.availability or 'Not specified'}
- Timezone: {agent_profile.timezone or 'Not specified'}
- Description: {agent_profile.description or 'Not specified'}

Evaluate the match based on:
1. Role type compatibility (exact match = 0.3, partial match = 0.15)
2. Skills overlap (each matched skill = 0.1, max 0.4)
3. Experience level alignment (exact match = 0.15)
4. Budget fit (within range = 0.1)
5. Timezone compatibility (same timezone = 0.05)
6. Availability match (matches preference = 0.05)

Scoring Guidelines:
- 0.9-1.0: Excellent match - all major criteria met
- 0.7-0.9: Good match - most criteria met with minor gaps
- 0.5-0.7: Moderate match - some criteria met, may need clarification
- 0.3-0.5: Weak match - few criteria met, significant gaps
- 0.0-0.3: Poor match - not suitable for this role

Return ONLY a valid JSON object (no markdown, no explanation):
{{
    "match_score": <float between 0.0 and 1.0>,
    "match_reasons": ["<specific reason 1>", "<specific reason 2>", "<specific reason 3>"]
}}"""

        logger.info(f"Calling Ollama chat - prompt start: {prompt[:100]}...")
        client = ollama.Client(host='http://127.0.0.1:11434')
        response = client.chat(
            model='qwen2.5:7b-instruct-q4_K_M',
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.3}
        )
        logger.info(f"Ollama response received: {response}")

        # Parse response
        import json
        response_text = response['message']['content'].strip()
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning(f"Non-JSON response from Ollama: {response_text}")
            return {
                'match_score': 0.5,
                'match_reasons': [f"AI response: {response_text[:200]}"]
            }

        # Validate response structure
        if 'match_score' not in result or 'match_reasons' not in result:
            logger.error(f"Invalid response structure from Ollama: {result}")
            return {
                'match_score': 0.5,
                'match_reasons': [f"Raw response: {response_text[:200]}"]
            }

        return result

    except Exception as e:
        logger.error(f"Error analyzing match with Ollama: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")


def calculate_match_score(
    business_needs: BusinessNeed,
    agent_profile: AgentProfile
) -> Dict[str, Any]:
    """
    Calculate match score between business needs and agent profile

    Uses rule-based scoring with keyword matching
    """
    # Calculate match score between business needs and agent profile
    # Uses rule-based scoring with keyword matching

    # Rule-based initial score
    score = 0.0
    reasons = []

    # Check role type match - normalize and check for partial matches
    if business_needs.role_type and agent_profile.role_type:
        # Normalize: lowercase and remove special characters
        norm_req = business_needs.role_type.lower().replace('-', ' ').replace('_', ' ')
        norm_agent = agent_profile.role_type.lower().replace('-', ' ').replace('_', ' ')

        if norm_req == norm_agent:
            score += 0.3
            reasons.append(f"Perfect role type match: {agent_profile.role_type}")
        elif norm_req in norm_agent or norm_agent in norm_req:
            score += 0.15
            reasons.append(f"Partial role type match: {agent_profile.role_type}")

    # Check skills match - normalize by removing hyphens and spaces
    if business_needs.skills_required and agent_profile.skills:
        # Normalize skills: remove hyphens and convert to lowercase
        normalized_required = [s.lower().replace('-', ' ').replace('_', ' ') for s in business_needs.skills_required]
        normalized_agent_skills = [s.lower().replace('-', ' ').replace('_', ' ') for s in agent_profile.skills]

        # Find partial matches (one skill contains another)
        matched_skills = []
        for req_skill in normalized_required:
            for agent_skill in normalized_agent_skills:
                if req_skill in agent_skill or agent_skill in req_skill:
                    matched_skills.append((req_skill, agent_skill))
                    break

        if matched_skills:
            skill_score = len(matched_skills) / len(business_needs.skills_required) * 0.4
            score += skill_score
            matched_names = [f"{req} ↔ {agent}" for req, agent in matched_skills]
            reasons.append(f"Skills match: {', '.join(matched_names)}")

    # Check experience level
    if business_needs.experience_level and agent_profile.experience_level:
        if business_needs.experience_level.lower() == agent_profile.experience_level.lower():
            score += 0.15
            reasons.append(f"Experience level match: {agent_profile.experience_level}")
        elif (business_needs.experience_level.lower() == 'mid' and 
              agent_profile.experience_level.lower() == 'senior'):
            score += 0.1
            reasons.append(f"Agent has higher experience level than required")

    # Normalize score to 0-1 range
    score = min(score, 1.0)

    # Check category/industry match - normalize and check for partial matches
    if business_needs.industry and agent_profile.category:
        # Normalize: lowercase and remove special characters
        norm_industry = business_needs.industry.lower().replace('-', ' ').replace('_', ' ')
        norm_category = agent_profile.category.lower().replace('-', ' ').replace('_', ' ')

        # Check for partial match (industry contains category or vice versa)
        if norm_industry in norm_category or norm_category in norm_industry:
            score += 0.1
            reasons.append(f"Industry match: {agent_profile.category}")

    # Check tags match
    if business_needs.skills_required and agent_profile.tags:
        tags_list = [tag.strip() for tag in agent_profile.tags.split(',')]
        matched_tags = set(business_needs.skills_required) & set(tags_list)
        if matched_tags:
            tag_score = len(matched_tags) / len(business_needs.skills_required) * 0.1
            score += tag_score
            reasons.append(f"Tags match: {', '.join(matched_tags)}")

    # Normalize score to 0-1 range
    score = min(score, 1.0)

    return {
        'match_score': score,
        'match_reasons': reasons
    }


# --- API Endpoints ---

@router.get("/opportunities", response_model=List[AgentProfile])
def get_talent_opportunities(
    category: Optional[str] = None,
    skills: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get available talent opportunities (published agents)

    Args:
        category: Filter by agent category
        skills: Filter by required skills (comma-separated)
    """
    profiles = get_all_agent_profiles(db)

    # Filter by category if specified
    if category:
        profiles = [p for p in profiles if p.category and p.category.lower() == category.lower()]

    # Filter by skills if specified
    if skills:
        required_skills = [s.strip().lower() for s in skills.split(',')]
        profiles = [
            p for p in profiles 
            if any(skill in p.skills for skill in required_skills)
        ]

    return profiles

@router.post("/match")
async def match_talent(
    business_needs: BusinessNeed,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Match business needs with available virtual agents

    Analyzes business requirements and returns ranked list of matching agents
    with scores and reasons for each match.
    """
    try:
        # Get all available agent profiles
        agent_profiles = get_all_agent_profiles(db)

        if not agent_profiles:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No agent profiles available"
            )

        # Calculate match scores for all agents
        match_results = []
        for agent in agent_profiles:
            try:
                match_data = calculate_match_score(business_needs, agent)
                match_result = MatchResult(
                    agent=agent,
                    match_score=match_data['match_score'],
                    match_reasons=match_data['match_reasons']
                )
                match_results.append(match_result)
            except Exception as e:
                logger.error(f"Error calculating match for agent {agent.id}: {e}")
                continue

        # Sort by match score (descending)
        match_results.sort(key=lambda x: x.match_score, reverse=True)

        # Log successful match
        logger.info(
            f"Generated {len(match_results)} matches for business needs: "
            f"{business_needs.industry or 'Not specified'} - {business_needs.role_type or 'Not specified'}"
        )

        # Return response
        return MatchResponse(
            business_needs=business_needs,
            matches=match_results,
            total_matches=len(match_results),
            generated_at=datetime.now(timezone.utc)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in talent matching: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in talent matching: {str(e)}"
        )


@router.get("/agents", response_model=List[AgentProfile])
async def list_agents(
    role_type: Optional[str] = None,
    min_rating: Optional[float] = None,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    List available virtual agents with optional filters

    Can filter by role type and minimum rating
    """
    try:
        # Get all agent profiles
        agents = get_all_agent_profiles(db)

        # Apply filters
        if role_type:
            agents = [a for a in agents if a.role_type and role_type.lower() in a.role_type.lower()]

        if min_rating:
            agents = [a for a in agents if a.rating >= min_rating]

        return agents

    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing agents"
        )
