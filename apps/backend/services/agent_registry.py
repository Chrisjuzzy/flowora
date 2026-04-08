"""
=====================================
AGENT REGISTRY SYSTEM
=====================================

Dynamic agent registration and execution framework.
Enables pluggable agents without hardcoding logic in routes.

Each agent must:
1. Inherit from BaseAgent
2. Implement execute() method
3. Define inputs and outputs
4. Specify execution cost (in credits)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
import logging

logger = logging.getLogger(__name__)


class AgentInput(BaseModel):
    """Schema for agent-specific inputs."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pass


class AgentOutput(BaseModel):
    """Schema for agent-specific outputs."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pass


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    All agents must inherit from this and implement execute().
    """
    
    # Agent metadata (override in subclasses)
    AGENT_TYPE: str = "base"
    DISPLAY_NAME: str = "Base Agent"
    SLUG: str = "base-agent"  # URL-friendly identifier
    DESCRIPTION: str = "Base agent class"
    SHORT_TAGLINE: str = "Base agent"
    CATEGORY: str = "general"
    EXECUTION_COST: int = 1  # Cost in credits per execution
    ESTIMATED_OUTPUT_TIME: int = 5  # Seconds
    VERSION: str = "1.0.0"
    
    def __init__(self):
        """Initialize agent."""
        pass
    
    @abstractmethod
    async def execute(self, input_data: dict, user: 'User' = None) -> dict:
        """
        Execute the agent with given inputs.
        
        Must be implemented by subclasses.
        
        Args:
            input_data: Dict with agent-specific input parameters
            user: Optional user object for context
            
        Returns:
            Dict with execution results including:
            - status: "success" or "error"
            - output: Main result data
            - token_usage: Tokens consumed (for tracking)
            
        Raises:
            ValueError: If required inputs missing or invalid
            Exception: If execution fails
        """
        pass
    
    def get_metadata(self) -> dict:
        """Return agent metadata."""
        return {
            "agent_type": self.AGENT_TYPE,
            "display_name": self.DISPLAY_NAME,
            "slug": self.SLUG,
            "description": self.DESCRIPTION,
            "short_tagline": self.SHORT_TAGLINE,
            "category": self.CATEGORY,
            "execution_cost": self.EXECUTION_COST,
            "estimated_output_time": self.ESTIMATED_OUTPUT_TIME,
            "version": self.VERSION,
        }


# =====================================
# SYSTEM AGENTS (Phase 1-2)
# =====================================

class LeadGeneratorAgent(BaseAgent):
    """
    Lead Generation Agent
    
    Generates qualified leads based on business criteria.
    """
    
    AGENT_TYPE = "lead_generator"
    DISPLAY_NAME = "Lead Generator"
    DESCRIPTION = "Generate qualified leads for your target market"
    EXECUTION_COST = 1.0
    CATEGORY = "sales"
    VERSION = "2.0.0"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Generate leads.
        
        Args:
            business_type: Type of business (e.g., "SaaS", "E-commerce")
            target_market: Target market description
            criteria: Lead qualification criteria
            
        Returns:
            List of qualified leads with contact info and fit score
        """
        business_type = kwargs.get("business_type", "")
        target_market = kwargs.get("target_market", "")
        criteria = kwargs.get("criteria", "")
        
        if not business_type or not target_market:
            raise ValueError("business_type and target_market are required")
        
        # Placeholder implementation - replace with actual LLM call
        leads = [
            {
                "company": "Example Corp",
                "contact": "john@example.com",
                "fit_score": 0.95,
                "reason": "Matches all criteria"
            }
        ]
        
        return {
            "status": "success",
            "lead_count": len(leads),
            "leads": leads,
            "generation_time_ms": 1250
        }


class SocialMediaContentAgent(BaseAgent):
    """
    Social Media Content Agent
    
    Generates content calendar and captions for social platforms.
    """
    
    AGENT_TYPE = "social_content"
    DISPLAY_NAME = "Social Media Content Planner"
    DESCRIPTION = "Generate 7-day content calendar with captions and hashtags"
    EXECUTION_COST = 1.0
    CATEGORY = "marketing"
    VERSION = "1.0.0"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Generate social media content.
        
        Args:
            business_type: Type of business
            tone: Content tone (professional, casual, humorous, etc.)
            platform: Target platform (Instagram, LinkedIn, Facebook)
            
        Returns:
            7-day content calendar with captions and hashtags
        """
        business_type = kwargs.get("business_type", "")
        tone = kwargs.get("tone", "professional")
        platform = kwargs.get("platform", "Instagram")
        
        if not business_type:
            raise ValueError("business_type is required")
        
        # Placeholder implementation
        content_calendar = [
            {
                "day": "Monday",
                "caption": f"Check out our latest {business_type} insights!",
                "hashtags": ["#business", "#marketing", f"#{business_type.lower()}"],
                "post_type": "image",
                "optimal_time": "09:00 AM"
            }
        ]
        
        return {
            "status": "success",
            "platform": platform,
            "tone": tone,
            "day_count": len(content_calendar),
            "content_calendar": content_calendar,
            "generation_time_ms": 1800
        }


class OfferOptimizerAgent(BaseAgent):
    """
    Offer Optimization Agent
    
    Optimizes product positioning, pricing, and sales angles.
    """
    
    AGENT_TYPE = "offer_optimizer"
    DISPLAY_NAME = "Offer Optimizer"
    DESCRIPTION = "Optimize pricing, positioning, and value stack"
    EXECUTION_COST = 2.0  # Costs 2 credits (more complex)
    CATEGORY = "sales"
    VERSION = "1.0.0"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Optimize offer.
        
        Args:
            product_description: Description of product
            target_audience: Target audience description
            current_price: Current pricing (for reference)
            
        Returns:
            Optimized positioning, pricing tiers, and sales angles
        """
        product_description = kwargs.get("product_description", "")
        target_audience = kwargs.get("target_audience", "")
        current_price = kwargs.get("current_price", 0)
        
        if not product_description or not target_audience:
            raise ValueError("product_description and target_audience are required")
        
        # Placeholder implementation
        optimization = {
            "improved_positioning": "Premium solution for enterprise teams",
            "value_stack": [
                "Save 20 hours/month",
                "Increase ROI by 35%",
                "Enterprise-grade security"
            ],
            "pricing_tiers": [
                {"name": "Starter", "price": current_price or 99, "seats": "5"},
                {"name": "Pro", "price": (current_price or 99) * 2, "seats": "50"},
                {"name": "Enterprise", "price": "Custom", "seats": "Unlimited"}
            ],
            "sales_angles": [
                "ROI-focused messaging",
                "Pain-point elimination",
                "Competitive differentiation"
            ]
        }
        
        return {
            "status": "success",
            "optimization": optimization,
            "confidence_score": 0.87,
            "generation_time_ms": 2200
        }


# =====================================
# AGENT REGISTRY
# =====================================

class AgentRegistry:
    """
    Central registry for all available agents.
    
    Enables dynamic agent lookup and instantiation without hardcoding.
    """
    
    _agents: Dict[str, type] = {}
    
    @classmethod
    def register(cls, agent_class: type) -> None:
        """
        Register an agent class.
        
        Args:
            agent_class: Agent class inheriting from BaseAgent
        """
        agent_type = agent_class.AGENT_TYPE
        cls._agents[agent_type] = agent_class
        logger.info(f"Registered agent: {agent_type}")
    
    @classmethod
    def get_agent(cls, agent_type: str) -> Optional[BaseAgent]:
        """
        Get agent instance by type or slug.
        
        Supports both:
        1. AGENT_TYPE lookup (e.g., "lead_generator")
        2. SLUG lookup (e.g., "local-business-lead-finder")
        
        Args:
            agent_type: Type identifier or slug
            
        Returns:
            Agent instance or None if not found
        """
        # Try direct lookup first (by AGENT_TYPE)
        agent_class = cls._agents.get(agent_type)
        if agent_class:
            return agent_class()
        
        # Try SLUG-based lookup (convert slug with hyphens to underscores)
        agent_type_converted = agent_type.replace('-', '_')
        agent_class = cls._agents.get(agent_type_converted)
        if agent_class:
            return agent_class()
        
        # Try reverse: convert underscores to hyphens if it's in AGENT_TYPE format
        agent_type_converted = agent_type.replace('_', '-')
        # Search by SLUG in all registered agents
        for agent_class_item in cls._agents.values():
            if hasattr(agent_class_item, 'SLUG') and agent_class_item.SLUG == agent_type_converted:
                return agent_class_item()
        
        logger.warning(f"Agent not found: {agent_type}")
        return None
    
    @classmethod
    def list_agents(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all registered agents with metadata.
        
        Returns:
            Dict mapping agent_type to metadata
        """
        result = {}
        for agent_type, agent_class in cls._agents.items():
            instance = agent_class()
            result[agent_type] = instance.get_metadata()
        return result
    
    @classmethod
    def get_execution_cost(cls, agent_type: str) -> float:
        """
        Get execution cost for agent.
        
        Args:
            agent_type: Type identifier
            
        Returns:
            Cost in credits (default 1.0 if not found)
        """
        agent_class = cls._agents.get(agent_type)
        if agent_class:
            return agent_class.EXECUTION_COST
        return 1.0


# =====================================
# REGISTER SYSTEM AGENTS
# =====================================

AgentRegistry.register(LeadGeneratorAgent)
AgentRegistry.register(SocialMediaContentAgent)
AgentRegistry.register(OfferOptimizerAgent)

# =====================================
# REGISTER MARKETPLACE AGENTS
# =====================================

# Dynamically register all marketplace agents
try:
    from services.marketplace_agents import MARKETPLACE_AGENTS
    
    for agent_class in MARKETPLACE_AGENTS:
        try:
            AgentRegistry.register(agent_class)
            logger.debug(f"Registered marketplace agent: {agent_class.SLUG}")
        except Exception as e:
            logger.warning(f"Failed to register marketplace agent {agent_class.__name__}: {e}")
    
    logger.info(f"✅ Registered {len(MARKETPLACE_AGENTS)} marketplace agents")
except ImportError:
    logger.warning("Marketplace agents module not available")
except Exception as e:
    logger.warning(f"Failed to load marketplace agents: {e}")


# =====================================
# AGENT EXECUTION HELPER
# =====================================

async def execute_agent_by_type(
    agent_type: str,
    agent_inputs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute agent by type with given inputs.
    
    Args:
        agent_type: Type identifier (e.g., "lead_generator")
        agent_inputs: Dict of input parameters
        
    Returns:
        Execution result
        
    Raises:
        ValueError: If agent not found or execution fails
    """
    agent = AgentRegistry.get_agent(agent_type)
    
    if not agent:
        raise ValueError(f"Agent not found: {agent_type}")
    
    result = await agent.execute(**agent_inputs)
    return result
