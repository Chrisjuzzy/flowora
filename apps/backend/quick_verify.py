"""
Quick Startup Verification
Checks if the FastAPI app can be imported without errors
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Starting system verification...\n")

try:
    print("1. Testing configuration...")
    from config import settings
    print(f"   ✓ Config loaded - APP: {settings.APP_NAME}, DB: {settings.DATABASE_URL}")
except Exception as e:
    print(f"   ✗ Config failed: {e}")
    sys.exit(1)

try:
    print("2. Testing database...")
    from database import engine, SessionLocal, Base
    print("   ✓ Database module loaded")
except Exception as e:
    print(f"   ✗ Database failed: {e}")
    sys.exit(1)

try:
    print("3. Testing models...")
    import models
    print("   ✓ Models imported")
except Exception as e:
    print(f"   ✗ Models failed: {e}")
    sys.exit(1)

try:
    print("4. Testing schemas...")
    import schemas
    print("   ✓ Schemas imported")
except Exception as e:
    print(f"   ✗ Schemas failed: {e}")
    sys.exit(1)

try:
    print("5. Testing security...")
    import security
    print("   ✓ Security module loaded")
except Exception as e:
    print(f"   ✗ Security failed: {e}")
    sys.exit(1)

try:
    print("6. Testing middleware...")
    from middleware.rate_limit import RateLimitMiddleware
    print("   ✓ Middleware loaded")
except Exception as e:
    print(f"   ✗ Middleware failed: {e}")
    sys.exit(1)

try:
    print("7. Testing routers...")
    from routers import auth, agents, talent_hub
    print("   ✓ Core routers loaded")
except Exception as e:
    print(f"   ✗ Routers failed: {e}")
    sys.exit(1)

try:
    print("8. Testing agent registry...")
    from services.agent_registry import AgentRegistry
    agents = AgentRegistry.list_agents()
    print(f"   ✓ Agent registry loaded - {len(agents)} agents registered")
except Exception as e:
    print(f"   ✗ Agent registry failed: {e}")
    sys.exit(1)

try:
    print("9. Testing marketplace agents...")
    from services.marketplace_agents import MARKETPLACE_AGENTS
    print(f"   ✓ Marketplace agents loaded - {len(MARKETPLACE_AGENTS)} agents")
except Exception as e:
    print(f"   ✗ Marketplace agents failed: {e}")
    sys.exit(1)

try:
    print("10. Testing FastAPI app...")
    from main import app
    print("   ✓ FastAPI app created successfully")
except Exception as e:
    print(f"   ✗ FastAPI app failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("✓ All components verified successfully!")
print("="*50)
print("\nYou can now start the server with:")
print("uvicorn main:app --reload --port 8000")
