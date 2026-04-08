"""
=====================================
MARKETPLACE AGENTS SEEDER
=====================================

Auto-seeds marketplace with 25 production agents on startup.

This script is called automatically when the application starts.
It ensures the marketplace is always populated with agents.
"""

from sqlalchemy.orm import Session
from models.monetization import MarketplaceAgent
from services.marketplace_agents import get_agents_for_seeding
import logging
import random

logger = logging.getLogger(__name__)


def seed_marketplace_agents(db: Session) -> int:
    """
    Seed marketplace with production agents.
    
    Only seeds if marketplace table is empty.
    Prevents duplicates on restart.
    
    Args:
        db: Database session
        
    Returns:
        Number of agents seeded
    """
    # Check if marketplace already seeded
    existing_count = db.query(MarketplaceAgent).count()
    
    if existing_count > 0:
        logger.info(f"Marketplace already seeded with {existing_count} agents. Skipping seed.")
        return 0
    
    # Get agent definitions
    agents_data = get_agents_for_seeding()
    
    logger.info(f"Seeding marketplace with {len(agents_data)} production agents...")
    
    seeded = 0
    
    for agent_data in agents_data:
        try:
            # Randomize popularity score for realism
            agent_data["popularity_score"] = random.randint(35, 95)
            
            # Create agent
            agent = MarketplaceAgent(**agent_data)
            db.add(agent)
            seeded += 1
            
            logger.debug(f"Added: {agent_data['slug']}")
        
        except Exception as e:
            logger.error(f"Failed to seed {agent_data.get('slug', 'unknown')}: {e}")
            db.rollback()
            continue
    
    try:
        db.commit()
        logger.info(f"✅ Successfully seeded {seeded} marketplace agents")
        
        # Log by category
        for category in [
            "Lead Generation",
            "Marketing",
            "Sales",
            "Ecommerce",
            "Productivity",
            "Content"
        ]:
            count = db.query(MarketplaceAgent).filter(
                MarketplaceAgent.category == category
            ).count()
            if count > 0:
                logger.info(f"  • {category}: {count} agents")
        
        return seeded
    
    except Exception as e:
        logger.error(f"Failed to commit seeding: {e}")
        db.rollback()
        return 0


def verify_marketplace_seeding(db: Session) -> bool:
    """
    Verify marketplace is properly seeded.
    
    Args:
        db: Database session
        
    Returns:
        True if marketplace has agents, False otherwise
    """
    count = db.query(MarketplaceAgent).count()
    active_count = db.query(MarketplaceAgent).filter(
        MarketplaceAgent.is_active == True
    ).count()
    
    if count == 0:
        logger.warning("❌ Marketplace is empty! No agents seeded.")
        return False
    
    logger.info(f"✅ Marketplace verified: {count} total agents ({active_count} active)")
    
    # Verify category distribution
    categories = db.query(MarketplaceAgent.category).distinct().all()
    category_list = ', '.join([c[0] for c in categories])
    logger.info(f"   Categories: {len(categories)} ({category_list})")
    
    return True
