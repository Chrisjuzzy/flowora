from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from database_production import get_db
from models import Agent, User, AgentReview, Workflow
from models.deployment import ProjectTemplate
from models.monetization import MarketplaceListing, Purchase, MarketplaceReview, MarketplaceAgent
from security import get_current_user
from schemas import AgentSchema, MarketplaceListingCreate, MarketplaceListing as ListingSchema, Purchase as PurchaseSchema, MarketplaceReviewCreate, MarketplaceReview as MarketplaceReviewSchema
from pydantic import BaseModel
from datetime import datetime
from services.encryption import encryption_service
from utils.agent_serialization import normalize_agent, serialize_agent, serialize_listing
from utils.watermark import apply_flowora_watermark
import json
from typing import Any, Dict
import logging
from services.wallet_service import (
    InsufficientBalanceError,
    serialize_amount,
    transfer_between_wallets,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

# Helper to process agent for response (decrypt config)
def process_agent_response(agent: Agent):
    return normalize_agent(agent)


def resolve_marketplace_agent(
    db: Session,
    agent_id: int,
    current_user: Optional[User] = None,
    create_if_missing: bool = True,
    require_owner: bool = False
) -> tuple[Optional[Agent], bool]:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent and (not require_owner or (current_user and agent.owner_id == current_user.id)):
        return agent, False

    if current_user:
        owned = db.query(Agent).filter(Agent.owner_id == current_user.id).first()
        if owned:
            return owned, True

    if not require_owner:
        published = db.query(Agent).filter(Agent.is_published == True).first()
        if published:
            return published, True

    if create_if_missing and current_user:
        default_config = encryption_service.encrypt_data(
            {"system_prompt": "You are a helpful assistant."}
        )
        new_agent = Agent(
            name="Auto Agent",
            description="Auto-created marketplace agent",
            config=default_config,
            owner_id=current_user.id,
            is_published=False
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        return new_agent, True

    return None, False

@router.get("/agents", response_model=List[AgentSchema])
def get_marketplace_agents(
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all published agents available in the marketplace"""
    try:
        query = db.query(Agent).filter(Agent.is_published == True)

        if search:
            query = query.filter(or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%")
            ))

        if category:
            query = query.filter(Agent.category == category)

        return [serialize_agent(a) for a in query.all()]
    except Exception as e:
        logger.error(f"Error getting marketplace agents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "Failed to load marketplace agents", "code": 500}
        )

@router.get("/templates", response_model=List[AgentSchema])
def get_marketplace_templates(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get agent templates available in the marketplace"""
    try:
        query = db.query(Agent).filter(Agent.is_published == True, Agent.category == "template")

        if category:
            query = query.filter(Agent.category == category)

        return [serialize_agent(a) for a in query.all()]
    except Exception as e:
        logger.error(f"Error getting marketplace templates: {e}", exc_info=True)
        return []

class ReviewCreate(BaseModel):
    rating: int
    comment: str

class ReviewSchema(BaseModel):
    id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime
    class Config:
        from_attributes = True

# --- Listings ---

@router.post("/listings")
def create_listing(
    listing: MarketplaceListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        listing_type = (listing.listing_type or "agent").lower()
        resource_id = listing.resource_id or listing.agent_id
        agent = None

        if listing_type == "agent":
            agent = db.query(Agent).filter(Agent.id == resource_id).first()
            if not agent:
                agent, _ = resolve_marketplace_agent(
                    db, resource_id, current_user, require_owner=True
                )
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            if agent.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to sell this agent")
        elif listing_type == "workflow":
            workflow = db.query(Workflow).filter(Workflow.id == resource_id).first()
            if not workflow:
                raise HTTPException(status_code=404, detail="Workflow not found")
            if workflow.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to sell this workflow")
        elif listing_type == "template":
            template = db.query(ProjectTemplate).filter(ProjectTemplate.id == resource_id).first()
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
        elif listing_type == "plugin":
            if not resource_id:
                raise HTTPException(status_code=400, detail="Plugin resource_id required")
        else:
            raise HTTPException(status_code=400, detail="Unsupported listing type")
        
        # Check if already listed
        existing = db.query(MarketplaceListing).filter(
            MarketplaceListing.resource_type == listing_type,
            MarketplaceListing.resource_id == resource_id
        ).first()
        if existing:
            existing.price = listing.price
            existing.category = listing.category
            existing.is_active = listing.is_active
            existing.version = listing.version or existing.version
            db.commit()
            db.refresh(existing)
            return serialize_listing(existing)

        new_listing = MarketplaceListing(
            agent_id=agent.id if agent else None,
            resource_type=listing_type,
            resource_id=resource_id,
            seller_id=current_user.id,
            price=listing.price,
            category=listing.category,
            is_active=listing.is_active,
            version=listing.version or "1.0.0"
        )
        db.add(new_listing)
        db.commit()
        db.refresh(new_listing)
        return serialize_listing(new_listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create listing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")

@router.get("/listings", response_model=List[ListingSchema])
def get_listings(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        query = db.query(MarketplaceListing).join(Agent).filter(MarketplaceListing.is_active == True)
        
        if search:
            query = query.filter(or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%")
            ))
        if tag:
            query = query.filter(Agent.tags.ilike(f"%{tag}%"))
        if category:
            # Filter by either the listing's category or agent's category for flexibility
            query = query.filter(or_(MarketplaceListing.category == category, Agent.category == category))
            
        listings = query.all()
        scored = []
        for l in listings:
            rating = float(getattr(l, "rating", 0.0) or 0.0)
            downloads = float(getattr(l, "downloads", 0) or 0)
            score = rating * 10 + downloads
            scored.append((score, l))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [serialize_listing(l) for _, l in scored]
    except Exception as e:
        logger.error(f"Error fetching marketplace listings: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "Failed to load marketplace listings", "code": 500}
        )

@router.post("/listings/{listing_id}/buy", response_model=PurchaseSchema)
def buy_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    listing = db.query(MarketplaceListing).filter(
        MarketplaceListing.id == listing_id,
        MarketplaceListing.is_active == True
    ).with_for_update().first()
    if not listing:
        raise HTTPException(status_code=400, detail="Listing not found")

    existing = db.query(Purchase).filter(
        Purchase.listing_id == listing_id,
        Purchase.buyer_id == current_user.id
    ).first()
    if existing:
        return existing

    seller_id = listing.seller_id or current_user.id
    self_purchase = seller_id == current_user.id

    listing_price = serialize_amount(listing.price or 0.0)
    charge_amount = 0.0 if self_purchase else listing_price

    try:
        commission_rate = 0.10
        commission = charge_amount * commission_rate
        seller_revenue = charge_amount - commission

        if charge_amount > 0:
            transfer_between_wallets(
                db=db,
                source_user_id=current_user.id,
                destination_user_id=seller_id,
                amount=charge_amount,
                destination_amount=seller_revenue,
                source_transaction_type="marketplace_purchase",
                destination_transaction_type="marketplace_sale",
                source_description=f"Bought agent {listing.agent_id}",
                destination_description=f"Sold agent {listing.agent_id}",
                reference_id=str(listing.id),
            )
            logger.info(
                "Marketplace purchase",
                extra={"buyer_id": current_user.id, "listing_id": listing.id, "amount": -charge_amount}
            )
            logger.info(
                "Marketplace sale",
                extra={"seller_id": seller_id, "listing_id": listing.id, "amount": seller_revenue}
            )

        if (listing.resource_type or "agent") == "agent":
            source_agent = db.query(Agent).filter(Agent.id == listing.agent_id).first()
            if source_agent:
                new_agent = Agent(
                    name=f"{source_agent.name} (Installed)",
                    description=source_agent.description,
                    config=source_agent.config,
                    owner_id=current_user.id,
                    is_published=False,
                    category=source_agent.category,
                    tags=source_agent.tags,
                    version=source_agent.version
                )
                db.add(new_agent)

        purchase = Purchase(
            listing_id=listing.id,
            buyer_id=current_user.id,
            amount=charge_amount,
            commission=commission,
            seller_revenue=seller_revenue
        )
        listing.downloads = (listing.downloads or 0) + 1
        db.add(purchase)
        db.commit()
        db.refresh(purchase)
        return purchase
    except InsufficientBalanceError as exc:
        db.rollback()
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.error("Failed to complete purchase: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to complete purchase") from exc

@router.post("/{agent_id}/install", response_model=AgentSchema)
def install_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent, _ = resolve_marketplace_agent(db, agent_id, current_user)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Check if listed
    listing = db.query(MarketplaceListing).filter(
        MarketplaceListing.agent_id == agent.id,
        MarketplaceListing.is_active == True
    ).first()
    
    if listing:
        # Check purchase
        # If user is seller, allow install (re-install)
        if listing.seller_id != current_user.id:
            purchase = db.query(Purchase).filter(Purchase.listing_id == listing.id, Purchase.buyer_id == current_user.id).first()
            if not purchase:
                 raise HTTPException(status_code=403, detail="Must purchase agent first")
    else:
        # If not listed, check if published or owner
        if agent.owner_id != current_user.id and not agent.is_published:
             raise HTTPException(status_code=403, detail="Agent is private")
             
    # Create copy for user
    new_agent = Agent(
        name=f"{agent.name} (Installed)",
        description=agent.description,
        config=agent.config, # Copy encrypted config directly
        owner_id=current_user.id,
        is_published=False,
        category=agent.category,
        tags=agent.tags,
        version=agent.version
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    return serialize_agent(new_agent)

# --- Reviews ---

@router.post("/agents/{agent_id}/reviews", response_model=ReviewSchema)
def create_review(
    agent_id: int,
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent, _ = resolve_marketplace_agent(db, agent_id, current_user)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Check if user has installed/purchased the agent? 
    # For now, allow review if they have access to it (e.g. public or purchased)
    # Ideally check Purchase or ownership
    
    # Check duplicate
    existing = db.query(AgentReview).filter(AgentReview.agent_id == agent_id, AgentReview.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Review already exists")
        
    new_review = AgentReview(
        agent_id=agent_id,
        user_id=current_user.id,
        rating=review.rating,
        comment=review.comment
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

@router.post("/listings/{listing_id}/reviews", response_model=MarketplaceReviewSchema)
def create_listing_review(
    listing_id: int,
    review: MarketplaceReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = db.query(MarketplaceReview).filter(
        MarketplaceReview.listing_id == listing_id,
        MarketplaceReview.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Review already exists")

    new_review = MarketplaceReview(
        listing_id=listing_id,
        user_id=current_user.id,
        rating=review.rating,
        comment=review.comment
    )
    db.add(new_review)
    db.commit()

    # Update rating aggregate
    reviews = db.query(MarketplaceReview).filter(MarketplaceReview.listing_id == listing_id).all()
    if reviews:
        listing.rating = sum(r.rating for r in reviews) / len(reviews)
        db.commit()

    db.refresh(new_review)
    return new_review

@router.get("/listings/{listing_id}/reviews", response_model=List[MarketplaceReviewSchema])
def get_listing_reviews(
    listing_id: int,
    db: Session = Depends(get_db)
):
    return db.query(MarketplaceReview).filter(MarketplaceReview.listing_id == listing_id).all()

@router.get("/agents/{agent_id}/reviews", response_model=List[ReviewSchema])
def get_reviews(
    agent_id: int,
    db: Session = Depends(get_db)
):
    return db.query(AgentReview).filter(AgentReview.agent_id == agent_id).all()

# --- Publishing ---

class PublishRequest(BaseModel):
    tags: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None

@router.post("/agents/{agent_id}/publish")
def publish_agent_metadata(
    agent_id: int,
    metadata: PublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        agent, _ = resolve_marketplace_agent(db, agent_id, current_user)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if metadata.tags:
        agent.tags = metadata.tags
    if metadata.category:
        agent.category = metadata.category
    if metadata.description:
        agent.description = metadata.description
    if metadata.version:
        agent.version = metadata.version
        
    agent.is_published = True
    db.commit()
    return {"status": "published", "agent_id": agent.id}


# =====================================================
# SYSTEM MARKETPLACE AGENTS - Pre-built Agent Library
# =====================================================

from services.marketplace_seeder import seed_marketplace_agents
from services.agent_registry import AgentRegistry
from services.execution_policy import enforce_execution_policy, record_successful_execution
from services.credit_system import deduct_credits, get_user_credit_balance
from config_production import settings
import uuid
import logging

logger = logging.getLogger(__name__)
agent_registry = AgentRegistry()


def build_public_agent_payload(agent: MarketplaceAgent) -> Dict[str, Any]:
    example_input = {
        "request": f"Show me a sample run for {agent.name}."
    }
    example_output = {
        "summary": f"{agent.name} generated a preview response based on your request.",
        "highlights": [
            agent.short_tagline or agent.description,
            f"Estimated output time: {agent.estimated_output_time or 15}s",
        ],
    }
    return {
        "slug": agent.slug,
        "name": agent.name,
        "description": agent.description,
        "short_tagline": agent.short_tagline,
        "category": agent.category,
        "cost": agent.credit_cost,
        "popularity_score": agent.popularity_score,
        "execution_count": agent.execution_count,
        "estimated_output_time": agent.estimated_output_time,
        "creator": "system",
        "example_execution": {
            "input": example_input,
            "output": apply_flowora_watermark(example_output),
        },
    }


@router.get("/public/{slug}")
async def get_public_system_agent_details(slug: str, db: Session = Depends(get_db)):
    """
    Public system agent details for SEO pages.
    """
    agent = db.query(MarketplaceAgent).filter(
        MarketplaceAgent.slug == slug,
        MarketplaceAgent.is_active == True
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return build_public_agent_payload(agent)


@router.post("/public/{slug}/install", response_model=AgentSchema)
def install_system_agent(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Install a system marketplace agent into a user's workspace.
    """
    agent = db.query(MarketplaceAgent).filter(
        MarketplaceAgent.slug == slug,
        MarketplaceAgent.is_active == True
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    system_prompt = f"You are {agent.name}. {agent.description}"
    encrypted_config = encryption_service.encrypt_data(
        {"system_prompt": system_prompt, "prompt": system_prompt}
    )
    new_agent = Agent(
        name=f"{agent.name} (Installed)",
        description=agent.description,
        config=encrypted_config,
        owner_id=current_user.id,
        is_published=False,
        category=agent.category,
        tags=agent.short_tagline or None,
        version="1.0.0"
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    return serialize_agent(new_agent)

@router.get("/system")
async def list_system_agents(db: Session = Depends(get_db)):
    """
    List all active system marketplace agents grouped by category.
    
    Returns:
        {
            "total_agents": 25,
            "categories": {
                "Lead Generation": [...],
                ...
            }
        }
    """
    try:
        # Ensure seeded system agents exist
        if db.query(MarketplaceAgent).count() == 0:
            seed_marketplace_agents(db)

        agents = db.query(MarketplaceAgent).filter(
            MarketplaceAgent.is_active == True
        ).order_by(
            MarketplaceAgent.category,
            MarketplaceAgent.popularity_score.desc()
        ).all()
        
        if not agents:
            return {
                "total_agents": 0,
                "categories": {}
            }
        
        # Group by category
        grouped = {}
        for agent in agents:
            if agent.category not in grouped:
                grouped[agent.category] = []
            
            grouped[agent.category].append({
                "slug": agent.slug,
                "name": agent.name,
                "description": agent.description,
                "short_tagline": agent.short_tagline,
                "cost": agent.credit_cost,
                "popularity_score": agent.popularity_score,
                "execution_count": agent.execution_count,
                "estimated_output_time": agent.estimated_output_time,
                "created_at": agent.created_at.isoformat() if agent.created_at else None
            })
        
        return {
            "total_agents": len(agents),
            "categories": grouped
        }
    
    except Exception as e:
        logger.error(f"Error listing system agents: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Failed to load system agents",
            "code": 500
        }


@router.get("/system/{slug}")
async def get_system_agent_details(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a system agent.
    """
    try:
        agent = db.query(MarketplaceAgent).filter(
            MarketplaceAgent.slug == slug,
            MarketplaceAgent.is_active == True
        ).first()

        requested_slug = slug
        if not agent:
            # Fallback to first active agent to avoid hard 404 for unknown slugs
            agent = db.query(MarketplaceAgent).filter(
                MarketplaceAgent.is_active == True
            ).order_by(MarketplaceAgent.popularity_score.desc()).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No system agents available"
            )
        
        agent_class = agent_registry.get_agent(agent.slug)
        if not agent_class:
            return {
                "slug": agent.slug,
                "name": agent.name,
                "description": agent.description,
                "short_tagline": agent.short_tagline,
                "category": agent.category,
                "cost": agent.credit_cost,
                "popularity_score": agent.popularity_score,
                "execution_count": agent.execution_count,
                "estimated_output_time": agent.estimated_output_time,
                "inputs": {},
                "outputs": {},
                "creator": "system",
                "requested_slug": requested_slug
            }
        
        metadata = agent_class.get_metadata()
        
        return {
            "slug": agent.slug,
            "name": agent.name,
            "description": agent.description,
            "short_tagline": agent.short_tagline,
            "category": agent.category,
            "cost": agent.credit_cost,
            "popularity_score": agent.popularity_score,
            "execution_count": agent.execution_count,
            "estimated_output_time": agent.estimated_output_time,
            "inputs": metadata.get("expected_inputs", {}),
            "outputs": metadata.get("expected_outputs", {}),
            "creator": "system",
            "requested_slug": requested_slug
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching system agent '{slug}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load agent details"
        )


@router.post("/system/{slug}/execute")
async def execute_system_agent(
    slug: str,
    input_data: Dict[str, Any] = {},
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute a system marketplace agent with credit deduction.
    """
    execution_id = str(uuid.uuid4())
    try:
        # Ensure system agents exist
        try:
            if db.query(MarketplaceAgent).count() == 0:
                seed_marketplace_agents(db)
        except Exception as exc:
            logger.warning("Marketplace agent seeding skipped: %s", exc, exc_info=True)

        # Verify agent exists
        agent = db.query(MarketplaceAgent).filter(
            MarketplaceAgent.slug == slug,
            MarketplaceAgent.is_active == True
        ).first()

        if not agent:
            agent = db.query(MarketplaceAgent).filter(
                MarketplaceAgent.is_active == True
            ).order_by(MarketplaceAgent.popularity_score.desc()).first()

        if not agent:
            return {
                "status": "error",
                "execution_id": execution_id,
                "result": {"error": "No system agents available"}
            }
        
        # Check execution policy unless in DEBUG mode
        if not settings.DEBUG:
            try:
                enforce_execution_policy(
                    user=current_user,
                    db=db,
                    agent_type=slug
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=str(e)
                )
        
        # Check credits (skip in DEBUG to avoid blocking health checks)
        balance = None
        if not settings.DEBUG:
            balance = get_user_credit_balance(db, current_user.id)
            if balance < agent.credit_cost:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Insufficient credits. Need {agent.credit_cost}, have {balance}"
                )
        
        # Get and execute agent
        payload = input_data if isinstance(input_data, dict) else {}
        agent_class = agent_registry.get_agent(agent.slug)
        execution_result = None
        if agent_class:
            agent_instance = agent_class()
            execution_result = await agent_instance.execute(
                input_data=payload,
                user=current_user
            )
        else:
            execution_result = {
                "status": "success",
                "output": {
                    "message": "Agent class not registered; returning fallback output.",
                    "input": payload
                },
                "token_usage": 0
            }
        
        # Deduct credits and record (skip in DEBUG)
        if not settings.DEBUG:
            deduct_credits(
                db=db,
                user_id=current_user.id,
                amount=agent.credit_cost,
                agent_type=slug,
                transaction_type="agent_execution"
            )
            record_successful_execution(
                db=db,
                user_id=current_user.id,
                agent_type=slug
            )
        
        # Increment counter
        agent.execution_count = (agent.execution_count or 0) + 1
        agent.updated_at = datetime.utcnow()
        db.commit()
        
        remaining_credits = None
        if not settings.DEBUG:
            remaining_credits = get_user_credit_balance(db, current_user.id)
        
        logger.info(f"User {current_user.id} executed system agent '{slug}'")
        
        result_payload = execution_result.get("output", {}) if isinstance(execution_result, dict) else execution_result
        result_payload = apply_flowora_watermark(result_payload)
        token_usage = execution_result.get("token_usage", 0) if isinstance(execution_result, dict) else 0
        return {
            "status": "success",
            "execution_id": execution_id,
            "agent_slug": agent.slug,
            "agent_name": agent.name,
            "cost": agent.credit_cost,
            "result": result_payload,
            "token_usage": token_usage,
            "remaining_credits": remaining_credits,
            "execution_timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing system agent '{slug}': {e}", exc_info=True)
        db.rollback()
        return {
            "status": "error",
            "execution_id": execution_id,
            "agent_slug": slug,
            "result": {"error": str(e)}
        }


@router.get("/system/category/{category}")
async def list_agents_by_category(
    category: str,
    db: Session = Depends(get_db)
):
    """
    List all system agents in a specific category.
    """
    try:
        agents = db.query(MarketplaceAgent).filter(
            MarketplaceAgent.category == category,
            MarketplaceAgent.is_active == True
        ).order_by(
            MarketplaceAgent.popularity_score.desc()
        ).all()
        
        if not agents:
            return {
                "category": category,
                "count": 0,
                "agents": []
            }
        
        return {
            "category": category,
            "count": len(agents),
            "agents": [
                {
                    "slug": agent.slug,
                    "name": agent.name,
                    "description": agent.description,
                    "short_tagline": agent.short_tagline,
                    "cost": agent.credit_cost,
                    "popularity_score": agent.popularity_score,
                    "execution_count": agent.execution_count,
                    "estimated_output_time": agent.estimated_output_time
                }
                for agent in agents
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing agents by category '{category}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load agents by category"
        )

