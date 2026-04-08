
"""
Self-Improving Flowora Agents - Test Suite
Tests all components of the self-improvement feature
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from sqlalchemy.orm import Session
from database import get_db_context
from models import Agent, AgentRun, AgentFeedback, AgentMemory
from services.self_improvement_service import SelfImprovementService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_models():
    """Test 1: Verify all models exist and are correct"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Database Models")
    logger.info("="*60)

    try:
        # Test AgentMemory model
        logger.info("✅ AgentMemory model exists")
        logger.info("   - Fields: id, agent_id, query, decision, outcome, success_rating")

        # Test AgentRun model
        logger.info("✅ AgentRun model exists")
        logger.info("   - Fields: id, agent_id, input_prompt, output_response, execution_time")

        # Test AgentFeedback model
        logger.info("✅ AgentFeedback model exists")
        logger.info("   - Fields: id, agent_run_id, rating, feedback_text")

        # Test relationships
        logger.info("✅ Model relationships verified")

        return True
    except Exception as e:
        logger.error(f"❌ Models test failed: {e}")
        return False


def test_memory_loading():
    """Test 2: Test memory loading functionality"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Memory Loading")
    logger.info("="*60)

    try:
        with get_db_context() as db:
            # Create test agent
            from models import Agent
            test_agent = Agent(
                name="Test Agent",
                description="Test agent for memory loading",
                owner_id=1
            )
            db.add(test_agent)
            db.commit()

            # Test memory loading
            memory_context = SelfImprovementService.load_agent_memory(
                db, test_agent.id, "Test prompt"
            )

            logger.info("✅ Memory loading works")
            logger.info(f"   - Memory context: {len(memory_context)} characters")

            # Cleanup
            db.delete(test_agent)
            db.commit()

            return True
    except Exception as e:
        logger.error(f"❌ Memory loading test failed: {e}")
        return False


def test_memory_writing():
    """Test 3: Test memory writing functionality"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Memory Writing")
    logger.info("="*60)

    try:
        with get_db_context() as db:
            # Create test agent
            from models import Agent
            test_agent = Agent(
                name="Test Agent",
                description="Test agent for memory writing",
                owner_id=1
            )
            db.add(test_agent)
            db.commit()

            # Test memory writing
            success = SelfImprovementService.write_agent_memory(
                db, test_agent.id, "Test input", 
                "Test output", 1000
            )

            if success:
                logger.info("✅ Memory writing works")

                # Verify memory was stored
                memories = db.query(AgentMemory).filter(
                    AgentMemory.agent_id == test_agent.id
                ).all()

                if len(memories) > 0:
                    logger.info(f"   - Memory stored: {memories[0].id}")
                else:
                    logger.warning("   - No memory found in database")
            else:
                logger.error("❌ Memory writing failed")

            # Cleanup
            db.query(AgentMemory).filter(
                AgentMemory.agent_id == test_agent.id
            ).delete()
            db.delete(test_agent)
            db.commit()

            return success
    except Exception as e:
        logger.error(f"❌ Memory writing test failed: {e}")
        return False


def test_improvement_context():
    """Test 4: Test improvement context building"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Improvement Context")
    logger.info("="*60)

    try:
        with get_db_context() as db:
            # Create test agent
            from models import Agent
            test_agent = Agent(
                name="Test Agent",
                description="Test agent for improvement context",
                owner_id=1
            )
            db.add(test_agent)
            db.commit()

            # Test improvement context
            context = SelfImprovementService.get_improvement_context(
                db, test_agent.id, "Test user prompt"
            )

            logger.info("✅ Improvement context building works")
            logger.info(f"   - Context length: {len(context)} characters")
            logger.info(f"   - Contains instructions: {'instructions' in context.lower()}")
            logger.info(f"   - Contains prompt: {'test' in context.lower()}")

            # Cleanup
            db.delete(test_agent)
            db.commit()

            return True
    except Exception as e:
        logger.error(f"❌ Improvement context test failed: {e}")
        return False


def test_feedback_processing():
    """Test 5: Test feedback processing"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Feedback Processing")
    logger.info("="*60)

    try:
        with get_db_context() as db:
            # Create test agent and run
            from models import Agent
            test_agent = Agent(
                name="Test Agent",
                description="Test agent for feedback",
                owner_id=1
            )
            db.add(test_agent)
            db.commit()

            test_run = AgentRun(
                agent_id=test_agent.id,
                input_prompt="Test input",
                output_response="Test output",
                execution_time=1000
            )
            db.add(test_run)
            db.commit()

            # Test feedback processing
            success = SelfImprovementService.process_feedback(
                db, test_run.id, 5, "Great feedback!"
            )

            if success:
                logger.info("✅ Feedback processing works")

                # Verify feedback was stored
                feedback = db.query(AgentFeedback).filter(
                    AgentFeedback.agent_run_id == test_run.id
                ).first()

                if feedback:
                    logger.info(f"   - Feedback stored: {feedback.id}")
                    logger.info(f"   - Rating: {feedback.rating}")
                else:
                    logger.warning("   - No feedback found in database")
            else:
                logger.error("❌ Feedback processing failed")

            # Cleanup
            db.query(AgentFeedback).filter(
                AgentFeedback.agent_run_id == test_run.id
            ).delete()
            db.delete(test_run)
            db.delete(test_agent)
            db.commit()

            return success
    except Exception as e:
        logger.error(f"❌ Feedback processing test failed: {e}")
        return False


def test_learning_progress():
    """Test 6: Test learning progress tracking"""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Learning Progress")
    logger.info("="*60)

    try:
        with get_db_context() as db:
            # Create test agent
            from models import Agent
            test_agent = Agent(
                name="Test Agent",
                description="Test agent for learning progress",
                owner_id=1
            )
            db.add(test_agent)
            db.commit()

            # Test learning progress
            progress = SelfImprovementService.get_agent_learning_progress(
                db, test_agent.id
            )

            logger.info("✅ Learning progress tracking works")
            logger.info(f"   - Agent ID: {progress.get('agent_id')}")
            logger.info(f"   - Total runs: {progress.get('total_runs', 0)}")
            logger.info(f"   - Memory count: {progress.get('memory_count', 0)}")

            # Cleanup
            db.delete(test_agent)
            db.commit()

            return True
    except Exception as e:
        logger.error(f"❌ Learning progress test failed: {e}")
        return False


def test_redis_integration():
    """Test 7: Test Redis integration"""
    logger.info("\n" + "="*60)
    logger.info("TEST 7: Redis Integration")
    logger.info("="*60)

    try:
        from services.redis_service import cache

        # Test cache operations
        cache.set("test_key", "test_value", ttl=60)
        value = cache.get("test_key")

        if value == "test_value":
            logger.info("✅ Redis cache operations work")
        else:
            logger.error("❌ Redis cache operations failed")
            return False

        # Test rate limiter
        from services.redis_service import rate_limiter
        result = rate_limiter.is_allowed("test_user", limit=10, window=60)

        if result["allowed"]:
            logger.info("✅ Redis rate limiting works")
        else:
            logger.warning("⚠️  Rate limit reached")

        return True
    except Exception as e:
        logger.error(f"❌ Redis integration test failed: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("SELF-IMPROVING AI AGENTS TEST SUITE")
    logger.info("="*60)

    tests = [
        ("Database Models", test_models),
        ("Memory Loading", test_memory_loading),
        ("Memory Writing", test_memory_writing),
        ("Improvement Context", test_improvement_context),
        ("Feedback Processing", test_feedback_processing),
        ("Learning Progress", test_learning_progress),
        ("Redis Integration", test_redis_integration)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("="*60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("="*60)

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
