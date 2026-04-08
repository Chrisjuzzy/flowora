from sqlalchemy.orm import Session
from models import Goal, Simulation, DigitalTwinProfile, Opportunity, EthicalLog, GoalStatus
from services.ai_provider import AIProviderFactory
import json
import asyncio

class GoalService:
    @staticmethod
    async def create_goal(db: Session, user_id: int, title: str, description: str):
        # 1. Create main goal
        goal = Goal(user_id=user_id, title=title, description=description, status=GoalStatus.PENDING)
        db.add(goal)
        db.commit()
        db.refresh(goal)
        
        # 2. Use AI to breakdown goal into subtasks
        try:
            provider = AIProviderFactory.get_provider()
            prompt = f"Break down this goal into 3-5 high-level sequential subtasks: '{title} - {description}'. Return ONLY a JSON list of strings."
            response = await provider.generate(prompt)
            
            # Simple parsing attempt (expecting JSON list)
            try:
                # Clean markdown code blocks if present
                clean_response = response.replace("```json", "").replace("```", "").strip()
                tasks = json.loads(clean_response)
                
                if isinstance(tasks, list):
                    for task_title in tasks:
                        subgoal = Goal(
                            user_id=user_id,
                            title=task_title,
                            parent_id=goal.id,
                            status=GoalStatus.PENDING
                        )
                        db.add(subgoal)
                    db.commit()
            except json.JSONDecodeError:
                print(f"Failed to parse goal breakdown: {response}")
                
        except Exception as e:
            print(f"Error auto-generating subtasks: {e}")
            
        return goal

class SimulationService:
    @staticmethod
    async def run_simulation(db: Session, agent_id: int, scenario: str):
        # Run a "dry run" with the agent
        provider = AIProviderFactory.get_provider()
        
        prompt = f"""
        [SIMULATION MODE]
        Scenario: {scenario}
        
        Predict the outcome of this scenario if you were to handle it. 
        Analyze potential risks and success probability (0-100).
        Format:
        Outcome: <description>
        Score: <number>
        """
        
        response = await provider.generate(prompt)
        
        # Parse score
        score = 50 # Default
        if "Score:" in response:
            try:
                score_line = [l for l in response.split('\n') if "Score:" in l][0]
                score = int(score_line.split(":")[1].strip())
            except:
                pass
                
        sim = Simulation(
            agent_id=agent_id,
            scenario=scenario,
            predicted_outcome=response,
            score=score
        )
        db.add(sim)
        db.commit()
        return sim

class DigitalTwinService:
    @staticmethod
    async def update_profile(db: Session, user_id: int, interaction_data: dict):
        profile = db.query(DigitalTwinProfile).filter(DigitalTwinProfile.user_id == user_id).first()
        if not profile:
            profile = DigitalTwinProfile(user_id=user_id)
            db.add(profile)
            
        # Update preferences/behavior (Mock learning)
        current_prefs = dict(profile.preferences) if profile.preferences else {}
        current_prefs.update(interaction_data)
        profile.preferences = current_prefs
        
        db.commit()
        return profile

    @staticmethod
    async def predict_needs(db: Session, user_id: int):
        profile = db.query(DigitalTwinProfile).filter(DigitalTwinProfile.user_id == user_id).first()
        if not profile:
            return []
            
        provider = AIProviderFactory.get_provider()
        prompt = f"""
        Based on user behavior: {json.dumps(profile.behavior_model)}
        And preferences: {json.dumps(profile.preferences)}
        
        Predict 3 future needs or tasks the user might have in the next 24 hours.
        Return as JSON list of strings.
        """
        try:
            response = await provider.generate(prompt)
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            needs = json.loads(clean_resp)
            
            # Store
            profile.predicted_needs = needs
            db.commit()
            return needs
        except Exception:
            return []

    @staticmethod
    async def automate_tasks(db: Session, user_id: int):
        profile = db.query(DigitalTwinProfile).filter(DigitalTwinProfile.user_id == user_id).first()
        if not profile or not profile.proactive_enabled:
            return []
            
        needs = profile.predicted_needs or []
        automated = []
        
        for need in needs:
            # Mock automation logic
            if "schedule" in need.lower() or "email" in need.lower():
                automated.append(f"Automated: {need}")
        
        if automated:
            current_log = list(profile.automated_tasks) if profile.automated_tasks else []
            current_log.extend(automated)
            profile.automated_tasks = current_log
            db.commit()
            
        return automated

    @staticmethod
    async def suggest_optimization(db: Session, user_id: int):
        profile = db.query(DigitalTwinProfile).filter(DigitalTwinProfile.user_id == user_id).first()
        if not profile:
            return "No digital twin profile found."
            
        provider = AIProviderFactory.get_provider()
        prompt = f"Based on user preferences {json.dumps(profile.preferences)}, suggest one proactive optimization for their workflow."
        return await provider.generate(prompt)

class DiscoveryService:
    @staticmethod
    async def scan_opportunities(db: Session):
        # Mock scanning external sources or using AI to hallucinate trends based on current date
        provider = AIProviderFactory.get_provider()
        prompt = "Generate 3 innovative business automation ideas or market trends relevant to AI agents. Return as JSON list of objects {title, description, type, confidence}."
        
        try:
            response = await provider.generate(prompt)
            clean_response = response.replace("```json", "").replace("```", "").strip()
            opportunities = json.loads(clean_response)
            
            created_opps = []
            for opp in opportunities:
                new_opp = Opportunity(
                    title=opp.get("title"),
                    description=opp.get("description"),
                    type=opp.get("type", "business_idea"),
                    confidence_score=opp.get("confidence", 0.8),
                    source="AI Market Scan"
                )
                db.add(new_opp)
                created_opps.append(new_opp)
            
            db.commit()
            return created_opps
        except Exception as e:
            print(f"Error scanning opportunities: {e}")
            return []
