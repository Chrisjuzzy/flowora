"""
System Verification Script
Verifies all critical components are working correctly
"""
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_test(test_name, passed, message=""):
    """Print test result with color"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {test_name}")
    if message:
        print(f"  {message}")

def test_config():
    """Test configuration loading"""
    try:
        from config import settings

        tests = []
        tests.append(("APP_NAME", bool(settings.APP_NAME), settings.APP_NAME))
        tests.append(("DATABASE_URL", bool(settings.DATABASE_URL), settings.DATABASE_URL))
        tests.append(("SECRET_KEY", bool(settings.SECRET_KEY), "Set" if settings.SECRET_KEY else "Not Set"))
        tests.append(("CORS Origins", bool(settings.ALLOWED_ORIGINS), settings.ALLOWED_ORIGINS))
        tests.append(("Rate Limit", bool(settings.RATE_LIMIT_API_PER_MINUTE), str(settings.RATE_LIMIT_API_PER_MINUTE) + "/min"))

        all_passed = all(passed for _, passed, _ in tests)
        details = ", ".join([f"{name}: {val}" for name, passed, val in tests])
        print_test("Configuration Loading", all_passed, details)
        return all_passed
    except Exception as e:
        print_test("Configuration Loading", False, str(e))
        return False

def test_database():
    """Test database connection and models"""
    try:
        from database import engine, SessionLocal
        from models import User, Agent, Execution, Workflow

        # Test connection
        db = SessionLocal()
        try:
            # Test basic query
            user_count = db.query(User).count()
            agent_count = db.query(Agent).count()

            print_test("Database Connection", True, f"Users: {user_count}, Agents: {agent_count}")
            return True
        finally:
            db.close()
    except Exception as e:
        print_test("Database Connection", False, str(e))
        return False

def test_models():
    """Test all models are importable"""
    try:
        from models import (
            User, RefreshToken, AuditLog,
            Agent, AgentVersion,
            Execution,
            Workflow,
            Schedule,
            UserAPIKey,
            AgentMemory, ReflectionLog, SharedKnowledge, SkillEvolution,
            AgentMessage, DelegatedTask, WorkspaceMemory, FailurePattern,
            Workspace, WorkspaceMember, Subscription, AgentReview,
            Goal, Simulation, DigitalTwinProfile, Opportunity, EthicalLog,
            GoalStatus, BoardAdvisor, EvolutionExperiment, IntelligenceGraphNode,
            Feedback, ProjectTemplate, MemoryShard,
            Referral, Announcement, CommunityPost, UserStats,
            Wallet, Transaction, Invoice, MarketplaceListing, Purchase, MarketplaceAgent
        )

        print_test("Models Import", True, "All models imported successfully")
        return True
    except Exception as e:
        print_test("Models Import", False, str(e))
        return False

def test_schemas():
    """Test all schemas are importable"""
    try:
        from schemas import (
            User, UserCreate, UserDashboard,
            VerifyEmailRequest, ForgotPasswordRequest, ResetPasswordRequest,
            Referral, AnnouncementCreate, Announcement,
            CommunityPostCreate, CommunityPost, UserStats,
            MarketplaceListingBase, MarketplaceListingCreate, MarketplaceListing,
            Purchase, Token, TokenData,
            WorkflowBase, WorkflowCreate, Workflow,
            AgentBase, AgentCreate, Agent, AgentSchema,
            ExecutionBase, ExecutionCreate, Execution
        )

        print_test("Schemas Import", True, "All schemas imported successfully")
        return True
    except Exception as e:
        print_test("Schemas Import", False, str(e))
        return False

def test_security():
    """Test security module"""
    try:
        from security import (
            verify_password, get_password_hash,
            create_access_token, create_refresh_token,
            get_current_user, get_current_active_user,
            RoleChecker
        )

        # Test password hashing
        test_password = "test123"
        hashed = get_password_hash(test_password)
        verified = verify_password(test_password, hashed)

        print_test("Security Module", verified, "Password hashing and verification working")
        return verified
    except Exception as e:
        print_test("Security Module", False, str(e))
        return False

def test_middleware():
    """Test middleware components"""
    try:
        from middleware.rate_limit import RateLimiter, RateLimitMiddleware

        # Test rate limiter
        limiter = RateLimiter(limit=10, window=60)
        allowed = limiter.is_allowed("test_key")

        print_test("Middleware", allowed, "Rate limiting middleware loaded")
        return allowed
    except Exception as e:
        print_test("Middleware", False, str(e))
        return False

def test_routers():
    """Test all routers are importable"""
    try:
        from routers import (
            auth, agents, execution, workflows, marketplace,
            schedules, intelligence, workspaces, billing, innovation,
            deployment, admin, growth, wallet, talent_hub, compliance,
            code_auditor, wellness, infra_optimizer, ethics_guardian
        )

        router_count = 19
        print_test("Routers Import", True, f"Loaded {router_count} routers")
        return True
    except Exception as e:
        print_test("Routers Import", False, str(e))
        return False

def test_agent_registry():
    """Test agent registry"""
    try:
        from services.agent_registry import AgentRegistry

        # Get list of agents
        agents = AgentRegistry.list_agents()
        agent_count = len(agents)

        print_test("Agent Registry", True, f"Registered {agent_count} agents")
        return True
    except Exception as e:
        print_test("Agent Registry", False, str(e))
        return False

def test_marketplace_agents():
    """Test marketplace agents"""
    try:
        from services.marketplace_agents import MARKETPLACE_AGENTS

        agent_count = len(MARKETPLACE_AGENTS)
        print_test("Marketplace Agents", True, f"Found {agent_count} marketplace agents")
        return True
    except Exception as e:
        print_test("Marketplace Agents", False, str(e))
        return False

def test_talent_hub():
    """Test talent hub functionality"""
    try:
        from routers.talent_hub import (
            BusinessNeed, AgentProfile, MatchResult, MatchResponse,
            get_all_agent_profiles, analyze_match_with_ollama, calculate_match_score
        )

        print_test("Talent Hub", True, "All talent hub components loaded")
        return True
    except Exception as e:
        print_test("Talent Hub", False, str(e))
        return False

def main():
    """Run all tests"""
    print(f"\n{'='*60}")
    print(f"FastAPI Backend System Verification")
    print(f"{'='*60}\n")

    print(f"{YELLOW}Testing Core Components...{RESET}\n")

    results = {
        "Configuration": test_config(),
        "Database": test_database(),
        "Models": test_models(),
        "Schemas": test_schemas(),
        "Security": test_security(),
        "Middleware": test_middleware(),
        "Routers": test_routers(),
        "Agent Registry": test_agent_registry(),
        "Marketplace Agents": test_marketplace_agents(),
        "Talent Hub": test_talent_hub(),
    }

    print(f"\n{'='*60}")
    print("Verification Summary")
    print(f"{'='*60}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{GREEN}✓{RESET}" if result else f"{RED}✗{RESET}"
        print(f"{status} {test_name}")

    print(f"\n{YELLOW}Results: {passed}/{total} tests passed{RESET}\n")

    if passed == total:
        print(f"{GREEN}All tests passed! System is ready for startup.{RESET}")
        return 0
    else:
        print(f"{RED}Some tests failed. Please review the errors above.{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
