"""
Fix for marketplace agents registration
"""
from services.agent_registry import AgentRegistry
import logging

logger = logging.getLogger(__name__)

def register_marketplace_agents():
    """Register marketplace agents - call this after app initialization"""
    try:
        from services.marketplace_agents import MARKETPLACE_AGENTS

        for agent_class in MARKETPLACE_AGENTS:
            try:
                AgentRegistry.register(agent_class)
                logger.debug(f"Registered marketplace agent: {agent_class.SLUG}")
            except Exception as e:
                logger.warning(f"Failed to register marketplace agent {agent_class.__name__}: {e}")

        logger.info(f"✅ Registered {len(MARKETPLACE_AGENTS)} marketplace agents")
    except ImportError as e:
        logger.warning(f"Marketplace agents module not available: {e}")
    except Exception as e:
        logger.warning(f"Failed to load marketplace agents: {e}")
