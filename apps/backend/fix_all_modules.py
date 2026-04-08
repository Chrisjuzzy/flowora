
"""
Fix script for all failing modules
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from database import SessionLocal, engine, Base
from models import User, Agent, Workspace, WorkspaceMember, Execution, AgentReview
from models.monetization import Wallet, Transaction, MarketplaceListing, Purchase
from models.growth import Referral, Announcement, CommunityPost, UserStats
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database():
    """Fix database issues"""
    db = SessionLocal()
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")

        # Ensure test user exists
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            from security import get_password_hash
            test_user = User(
                email="test@example.com",
                hashed_password=get_password_hash("testpass123"),
                role="user",
                is_email_verified=True,
                subscription_tier="pro",
                subscription_status="active"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            logger.info("✅ Test user created")

        # Ensure wallet exists for test user
        wallet = db.query(Wallet).filter(Wallet.user_id == test_user.id).first()
        if not wallet:
            wallet = Wallet(
                user_id=test_user.id,
                balance=100.0
            )
            db.add(wallet)
            db.commit()
            logger.info("✅ Wallet created for test user")

        # Ensure workspace exists for test user
        workspace = db.query(Workspace).filter(Workspace.owner_id == test_user.id).first()
        if not workspace:
            workspace = Workspace(
                name="Test Workspace",
                type="general",
                owner_id=test_user.id
            )
            db.add(workspace)
            db.commit()
            db.refresh(workspace)

            # Add owner as member
            member = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=test_user.id,
                role="admin"
            )
            db.add(member)
            db.commit()
            logger.info("✅ Workspace created for test user")

        # Create sample published agents for marketplace
        published_agents = db.query(Agent).filter(Agent.is_published == True).count()
        if published_agents == 0:
            sample_agents = [
                {
                    "name": "Code Reviewer",
                    "description": "AI-powered code review assistant",
                    "category": "development",
                    "tags": "code-review,python,javascript",
                    "is_published": True,
                    "owner_id": None  # System agent
                },
                {
                    "name": "Data Analyst",
                    "description": "Automated data analysis and visualization",
                    "category": "analytics",
                    "tags": "data-analysis,visualization,pandas",
                    "is_published": True,
                    "owner_id": None
                },
                {
                    "name": "Content Writer",
                    "description": "AI content generation for blogs and social media",
                    "category": "content",
                    "tags": "writing,blog,social-media",
                    "is_published": True,
                    "owner_id": None
                }
            ]

            for agent_data in sample_agents:
                agent = Agent(**agent_data)
                db.add(agent)
            db.commit()
            logger.info(f"✅ Created {len(sample_agents)} sample published agents")

        # Create sample marketplace listings
        listings = db.query(MarketplaceListing).count()
        if listings == 0:
            published_agents = db.query(Agent).filter(Agent.is_published == True).all()
            for agent in published_agents[:2]:
                listing = MarketplaceListing(
                    agent_id=agent.id,
                    seller_id=test_user.id,
                    price=10.0,
                    category=agent.category,
                    is_active=True
                )
                db.add(listing)
            db.commit()
            logger.info("✅ Created sample marketplace listings")

        # Create sample executions for trending agents
        executions_count = db.query(Execution).count()
        if executions_count == 0:
            published_agents = db.query(Agent).filter(Agent.is_published == True).all()
            from datetime import timedelta
            for i, agent in enumerate(published_agents):
                for j in range(5 + i * 3):  # Varying execution counts
                    execution = Execution(
                        agent_id=agent.id,
                        status="completed",
                        result=f"Sample execution result {j}",
                        timestamp=datetime.utcnow() - timedelta(days=j)
                    )
                    db.add(execution)
            db.commit()
            logger.info("✅ Created sample executions")

        # Create user stats for test user
        stats = db.query(UserStats).filter(UserStats.user_id == test_user.id).first()
        if not stats:
            stats = UserStats(
                user_id=test_user.id,
                total_executions=10,
                total_time_saved=50.0,
                productivity_score=7.5
            )
            db.add(stats)
            db.commit()
            logger.info("✅ Created user stats")

        # Create sample announcements
        announcements_count = db.query(Announcement).count()
        if announcements_count == 0:
            announcements = [
                Announcement(
                    title="Welcome to Flowora",
                    content="Get started with our powerful AI agents",
                    type="feature"
                ),
                Announcement(
                    title="New Features Available",
                    content="Check out our latest marketplace agents",
                    type="news"
                )
            ]
            for ann in announcements:
                db.add(ann)
            db.commit()
            logger.info("✅ Created sample announcements")

        logger.info("\n✅ Database fixes completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error fixing database: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_database()
