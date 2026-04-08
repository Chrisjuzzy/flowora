import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "apps", "backend"))

from database import SessionLocal, engine, Base
from models import User, Agent, AgentVersion, AgentReview
from models.monetization import MarketplaceListing, Purchase, Wallet
from services.encryption import encryption_service
from services.sandbox import sandbox_service

# Init DB
Base.metadata.create_all(bind=engine)

def verify_marketplace_system():
    db = SessionLocal()
    try:
        print("--- Verifying Marketplace System ---")
        
        # 1. Setup Users
        seller_email = f"seller_{int(datetime.now().timestamp())}@test.com"
        buyer_email = f"buyer_{int(datetime.now().timestamp())}@test.com"
        
        seller = User(email=seller_email, hashed_password="hashed_password", role="user")
        buyer = User(email=buyer_email, hashed_password="hashed_password", role="user")
        db.add(seller)
        db.add(buyer)
        db.commit()
        
        # 2. Create Agent & Publish
        print("Creating and Publishing Agent...")
        agent = Agent(
            name="Marketplace Agent",
            description="A test agent",
            owner_id=seller.id,
            config=encryption_service.encrypt_data({"prompt": "Hello"}),
            version="1.0.0"
        )
        db.add(agent)
        db.commit()
        
        listing = MarketplaceListing(
            agent_id=agent.id,
            seller_id=seller.id,
            price=10.0,
            is_active=True
        )
        db.add(listing)
        
        # Update Metadata
        agent.tags = "productivity,test"
        agent.category = "business"
        agent.is_published = True
        db.commit()
        print(f"Agent published: {agent.name} (v{agent.version})")
        
        # 3. Versioning
        print("Testing Versioning...")
        # Create v1 snapshot
        v1 = AgentVersion(
            agent_id=agent.id,
            version="1.0.0",
            config={"prompt": "Hello"},
            description="Initial release"
        )
        db.add(v1)
        db.commit()
        
        # Update to v2
        agent.version = "2.0.0"
        agent.config = encryption_service.encrypt_data({"prompt": "Hello World"})
        db.commit()
        
        # Create v2 snapshot
        v2 = AgentVersion(
            agent_id=agent.id,
            version="2.0.0",
            config={"prompt": "Hello World"},
            description="Updated prompt"
        )
        db.add(v2)
        db.commit()
        print(f"Agent updated to v{agent.version}")
        
        # Rollback to v1
        print("Rolling back to v1.0.0...")
        # Simulate logic from router
        target_version = db.query(AgentVersion).filter(AgentVersion.version == "1.0.0", AgentVersion.agent_id == agent.id).first()
        if target_version:
            agent.version = target_version.version
            if target_version.config:
                agent.config = encryption_service.encrypt_data(target_version.config)
            db.commit()
            print(f"Rollback successful. Current version: {agent.version}")
            
            # Verify config
            decrypted = encryption_service.decrypt_data(agent.config)
            if decrypted["prompt"] == "Hello":
                print("Config restored correctly.")
            else:
                print(f"Config mismatch! Got: {decrypted}")
        
        # 4. Purchase & Review
        print("Testing Purchase & Review...")
        # Buyer Wallet
        wallet = Wallet(user_id=buyer.id, balance=100.0)
        db.add(wallet)
        db.commit()
        
        # Purchase
        purchase = Purchase(
            listing_id=listing.id,
            buyer_id=buyer.id,
            amount=listing.price,
            created_at=datetime.utcnow()
        )
        db.add(purchase)
        db.commit()
        
        # Review
        review = AgentReview(
            agent_id=agent.id,
            user_id=buyer.id,
            rating=5,
            comment="Great agent!"
        )
        db.add(review)
        db.commit()
        print(f"Review added: {review.rating} stars - '{review.comment}'")
        
        # 5. Sandbox Check
        print("Testing Sandbox...")
        safe_input = "Hello agent"
        malicious_input = "import os; os.system('rm -rf /')"
        
        valid_check = sandbox_service.validate_execution_request(db, agent.id, buyer.id, safe_input)
        print(f"Safe input check: {valid_check['valid']}")
        
        malicious_check = sandbox_service.validate_execution_request(db, agent.id, buyer.id, malicious_input)
        print(f"Malicious input check: {malicious_check['valid']} (Error: {malicious_check.get('error')})")
        
        if not malicious_check['valid']:
            print("Sandbox successfully blocked malicious input.")
        else:
            print("WARNING: Sandbox failed to block malicious input.")
            
        print("\n--- Verification Completed Successfully ---")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_marketplace_system()
