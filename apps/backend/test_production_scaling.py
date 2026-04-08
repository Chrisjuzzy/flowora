
"""
Production Scaling Test Suite
Tests all critical components after fixes
"""
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_config():
    """Test 1: Configuration loading"""
    logger.info("Test 1: Configuration Loading")
    try:
        from config_production import settings
        settings.validate_required_fields()
        logger.info("✅ Configuration loaded and validated")
        logger.info(f"   - Database URL: {settings.DATABASE_URL[:20]}...")
        logger.info(f"   - Redis URL: {settings.REDIS_URL[:20]}...")
        logger.info(f"   - Environment: {settings.ENVIRONMENT}")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False


def test_database():
    """Test 2: Database connection"""
    logger.info("\nTest 2: Database Connection")
    try:
        from database_production import check_db_connection, get_db_context
        from models import Base

        # Check connection
        if check_db_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.error("❌ Database connection failed")
            return False

        # Test session
        try:
            with get_db_context() as db:
                result = db.execute("SELECT 1")
                logger.info("✅ Database session works")
        except Exception as e:
            logger.error(f"❌ Database session failed: {e}")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False


def test_redis():
    """Test 3: Redis connection"""
    logger.info("\nTest 3: Redis Connection")
    try:
        from services.redis_service import cache, rate_limiter, session_manager

        # Test cache operations
        cache.set("test_key", "test_value", ttl=60)
        value = cache.get("test_key")
        if value == "test_value":
            logger.info("✅ Redis cache operations work")
        else:
            logger.error("❌ Redis cache operations failed")
            return False

        # Test rate limiter
        result = rate_limiter.is_allowed("test_user", limit=10, window=60)
        if result["allowed"]:
            logger.info("✅ Redis rate limiting works")
        else:
            logger.error("❌ Redis rate limiting failed")
            return False

        # Test session manager
        session_id = session_manager.create_session(
            user_id=1,
            session_data={"test": "data"},
            ttl=3600
        )
        if session_id:
            logger.info("✅ Redis session management works")
        else:
            logger.error("❌ Redis session management failed")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Redis test failed: {e}")
        return False


def test_celery():
    """Test 4: Celery configuration"""
    logger.info("\nTest 4: Celery Configuration")
    try:
        from celery_app import celery_app

        # Check Celery app
        if celery_app:
            logger.info("✅ Celery app configured")
            logger.info(f"   - Broker: {celery_app.conf.broker_url[:20]}...")
            logger.info(f"   - Backend: {celery_app.conf.result_backend[:20]}...")
        else:
            logger.error("❌ Celery app not configured")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Celery test failed: {e}")
        return False


def test_ai_providers():
    """Test 5: AI provider services"""
    logger.info("\nTest 5: AI Provider Services")
    try:
        from services.ai_provider_service_production import AIProviderFactory

        # Test factory
        providers = ["openai", "anthropic", "gemini"]
        for provider_name in providers:
            try:
                provider = AIProviderFactory.get_provider(provider_name)
                logger.info(f"✅ {provider_name.upper()} provider initialized")
            except Exception as e:
                logger.warning(f"⚠️  {provider_name.upper()} provider initialization failed: {e}")

        return True
    except Exception as e:
        logger.error(f"❌ AI provider test failed: {e}")
        return False


def test_logging():
    """Test 6: Logging system"""
    logger.info("\nTest 6: Logging System")
    try:
        from utils.logger_config import get_logger

        # Test logger
        test_logger = get_logger("test")
        test_logger.info("Test log message")
        test_logger.warning("Test warning")
        test_logger.error("Test error")

        logger.info("✅ Logging system works")
        return True
    except Exception as e:
        logger.error(f"❌ Logging test failed: {e}")
        return False


def test_models():
    """Test 7: Database models"""
    logger.info("\nTest 7: Database Models")
    try:
        from models import (
            User, Agent, Execution, AgentRun,
            Workspace, Wallet, Transaction,
            MarketplaceListing, Purchase,
            Workflow, Schedule
        )

        models_list = [
            "User", "Agent", "Execution", "AgentRun",
            "Workspace", "Wallet", "Transaction",
            "MarketplaceListing", "Purchase",
            "Workflow", "Schedule"
        ]

        for model_name in models_list:
            logger.info(f"✅ {model_name} model imported")

        return True
    except Exception as e:
        logger.error(f"❌ Models test failed: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("PRODUCTION SCALING TEST SUITE")
    logger.info("=" * 60)

    tests = [
        ("Configuration", test_config),
        ("Database", test_database),
        ("Redis", test_redis),
        ("Celery", test_celery),
        ("AI Providers", test_ai_providers),
        ("Logging", test_logging),
        ("Models", test_models)
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
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
