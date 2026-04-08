"""
Seed test agents for talent matching functionality
"""
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models.agent import Agent
import json

def seed_talent_agents():
    """Add test agents with talent matching profiles"""
    db = SessionLocal()

    try:
        # Check if agents already exist
        existing_agents = db.query(Agent).filter(Agent.name.in_([
            "social_media_pro",
            "coffee_shop_marketer",
            "content_creator_expert",
            "instagram_specialist",
            "social_media_manager_pro",
            "content_strategist"
        ])).all()

        if existing_agents:
            print(f"Found {len(existing_agents)} existing test agents. Skipping seed.")
            return

        # Test Agent 1: Social Media Pro
        agent1 = Agent(
            name="social_media_pro",
            description="Specialist in creative social media content for small businesses like coffee shops",
            config=json.dumps({
                "role_type": "Marketing",
                "skills": ["Instagram", "content creation", "social media management", "TikTok", "Facebook"],
                "experience_level": "Intermediate",
                "hourly_rate": "30-50 CHF",
                "availability": "Part-time",
                "timezone": "CET"
            }),
            is_published=True,
            tags="social media, marketing, content",
            category="Marketing",
            version="1.0.0",
            owner_id=1
        )

        # Test Agent 2: Coffee Shop Marketer
        agent2 = Agent(
            name="coffee_shop_marketer",
            description="Expert in coffee shop branding and daily social media engagement",
            config=json.dumps({
                "role_type": "Marketing",
                "skills": ["Instagram", "content creation", "social media", "visual posts", "daily posting"],
                "experience_level": "Advanced",
                "hourly_rate": "40-60 CHF",
                "availability": "Full-time",
                "timezone": "CET"
            }),
            is_published=True,
            tags="coffee shop, marketing, social media",
            category="Marketing",
            version="1.0.0",
            owner_id=1
        )

        # Test Agent 3: Content Creator Expert
        agent3 = Agent(
            name="content_creator_expert",
            description="Professional content creator specializing in visual storytelling for food and beverage businesses",
            config=json.dumps({
                "role_type": "Marketing",
                "skills": ["Instagram", "content creation", "visual storytelling", "photography", "video editing"],
                "experience_level": "Advanced",
                "hourly_rate": "50-70 CHF",
                "availability": "Full-time",
                "timezone": "CET"
            }),
            is_published=True,
            tags="content creation, visual, photography",
            category="Marketing",
            version="1.0.0",
            owner_id=1
        )

        # Test Agent 4: Instagram Specialist
        agent4 = Agent(
            name="instagram_specialist",
            description="Instagram growth specialist focused on engagement and follower acquisition for small businesses",
            config=json.dumps({
                "role_type": "Marketing",
                "skills": ["Instagram", "social media growth", "engagement", "hashtags", "Instagram Stories", "Reels"],
                "experience_level": "Intermediate",
                "hourly_rate": "35-55 CHF",
                "availability": "Part-time",
                "timezone": "CET"
            }),
            is_published=True,
            tags="instagram, growth, engagement",
            category="Marketing",
            version="1.0.0",
            owner_id=1
        )

        # Test Agent 5: Social Media Manager Pro
        agent5 = Agent(
            name="social_media_manager_pro",
            description="Full-service social media manager with experience managing multiple platforms for retail businesses",
            config=json.dumps({
                "role_type": "Marketing",
                "skills": ["social media management", "Instagram", "Facebook", "TikTok", "LinkedIn", "content scheduling"],
                "experience_level": "Senior",
                "hourly_rate": "60-80 CHF",
                "availability": "Full-time",
                "timezone": "CET"
            }),
            is_published=True,
            tags="social media, management, multi-platform",
            category="Marketing",
            version="1.0.0",
            owner_id=1
        )

        # Test Agent 6: Content Strategist
        agent6 = Agent(
            name="content_strategist",
            description="Strategic content planner specializing in developing comprehensive social media content calendars",
            config=json.dumps({
                "role_type": "Marketing",
                "skills": ["content strategy", "content calendar", "social media planning", "brand voice", "campaign planning"],
                "experience_level": "Advanced",
                "hourly_rate": "55-75 CHF",
                "availability": "Full-time",
                "timezone": "CET"
            }),
            is_published=True,
            tags="content strategy, planning, calendar",
            category="Marketing",
            version="1.0.0",
            owner_id=1
        )

        # Add all agents to database
        db.add(agent1)
        db.add(agent2)
        db.add(agent3)
        db.add(agent4)
        db.add(agent5)
        db.add(agent6)

        db.commit()
        print("✅ Successfully added 6 test agents to the database!")
        print("
Agents added:")
        print(f"1. {agent1.name} - {agent1.description}")
        print(f"2. {agent2.name} - {agent2.description}")
        print(f"3. {agent3.name} - {agent3.description}")
        print(f"4. {agent4.name} - {agent4.description}")
        print(f"5. {agent5.name} - {agent5.description}")
        print(f"6. {agent6.name} - {agent6.description}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding agents: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_talent_agents()
