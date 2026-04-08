"""
=====================================
REVENUE PLATFORM ARCHITECTURE
=====================================

Complete system architecture for Flowora SaaS platform v2.0
Designed for scalable revenue generation.

Last Updated: March 1, 2026
Status: Production Ready
"""

# =====================================
# ARCHITECTURE OVERVIEW
# =====================================

ARCHITECTURE = """

┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                              │
│                      (React + TypeScript)                               │
│  ┌──────────────┬─────────────────────┬──────────────────────────────┐  │
│  │ Agent        │ Workflow            │ User Dashboard               │  │
│  │ Marketplace  │ Builder             │ • Profile                    │  │
│  │              │                     │ • Credits/Billing            │  │
│  │              │                     │ • Revenue Reports            │  │
│  └──────────────┴─────────────────────┴──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                     HTTP/REST API (Port 8000)
                                    │
        ┌───────────────────────────┴───────────────────────────────┐
        │                                                             │
┌───────▼──────────────────────────────────────────────────────────┐│
│                     FASTAPI APPLICATION                           ││
│                  (Python + SQLAlchemy ORM)                        ││
│                                                                   ││
│  ┌── AUTHENTICATION LAYER ────────────────────────────────────┐  ││
│  │ • JWT Token Management (HS256)                            │  ││
│  │ • Email Verification (6-digit codes, 15 min)             │  ││
│  │ • Password Reset (secure tokens, 30 min)                 │  ││
│  │ • Role-Based Access Control (admin, user)                │  ││
│  └────────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  ┌── EXECUTION ENFORCEMENT LAYER (UNIFIED GATE) ──────────────┐  ││
│  │ enforce_execution_policy():                                │  ││
│  │   ✓ Email verified?                                       │  ││
│  │   ✓ Subscription status = active?                         │  ││
│  │   ✓ Monthly execution limit not exceeded?                 │  ││
│  │   ✓ Credits available? (Credit System)                    │  ││
│  │                                                             │  ││
│  │ record_successful_execution():                            │  ││
│  │   • Increment execution counter                           │  ││
│  │   • Increment token counter                               │  ││
│  │   • Deduct credits (CreditTransaction)                    │  ││
│  └────────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  ┌── AGENT FRAMEWORK LAYER ──────────────────────────────────┐  ││
│  │ AgentRegistry (Dynamic agent resolution)                  │  ││
│  │                                                             │  ││
│  │ BaseAgent (Abstract class):                               │  ││
│  │   • LeadGeneratorAgent (1 credit/execution)               │  ││
│  │   • SocialMediaContentAgent (1 credit/execution)          │  ││
│  │   • OfferOptimizerAgent (2 credits/execution)             │  ││
│  │                                                             │  ││
│  │ Execution Flow:                                            │  ││
│  │   1. execute_agent_by_type() → AgentRegistry              │  ││
│  │   2. Get agent instance                                   │  ││
│  │   3. Call agent.execute(**inputs)                         │  ││
│  │   4. Return results + token_usage                         │  ││
│  └────────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  ┌── CREDIT SYSTEM LAYER ────────────────────────────────────┐  ││
│  │ Allocations:                                              │  ││
│  │   • Free: 20 credits/month                                │  ││
│  │   • Pro: 500 credits/month                                │  ││
│  │   • Enterprise: Unlimited                                 │  ││
│  │                                                             │  ││
│  │ Processing:                                               │  ││
│  │   • get_available_credits_this_month()                    │  ││
│  │   • deduct_credits() → CreditTransaction                  │  ││
│  │   • grant_credits() → Credits granted/purchased           │  ││
│  │   • monthly_reset() → Scheduled job                       │  ││
│  │   • refund_credits() → For failed executions              │  ││
│  └────────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  ┌── REVENUE TRACKING LAYER ─────────────────────────────────┐  ││
│  │ User Reports:                  Admin Controls:             │  ││
│  │  • POST /revenue/report        • GET /stats/revenue-      │  ││
│  │  • GET /revenue/summary          reports                  │  ││
│  │  • GET /revenue/leaderboard   • POST /stats/verify-       │  ││
│  │  • DELETE /revenue/reports/ID   revenue/{id}              │  ││
│  │                                 • Verify reports          │  ││
│  │ Tracks:                          • Monitor revenue        │  ││
│  │  • Reported revenue             • Public leaderboard      │  ││
│  │  • Source agent                                            │  ││
│  │  • Verification status                                     │  ││
│  └────────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  ┌── ADMIN ANALYTICS LAYER ──────────────────────────────────┐  ││
│  │ Platform Metrics:              User Management:            │  ││
│  │  • GET /stats/platform         • GET /stats/users         │  ││
│  │    - Users (total/active)       • GET /stats/top-agents   │  ││
│  │    - Executions                 • POST /admin/reset-      │  ││
│  │    - Credits used/granted         user-credits/{id}       │  ││
│  │    - Revenue (Est. MRR)                                    │  ││
│  │    - Agent usage by type                                   │  ││
│  │                                                             │  ││
│  │ Admin must verify revenue reports for credibility          │  ││
│  └────────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  ┌── API ROUTERS ────────────────────────────────────────────┐  ││
│  │ /auth/        → Authentication & verification             │  ││
│  │ /agents/      → Agent CRUD + execution                    │  ││
│  │ /workflows/   → Workflow management                       │  ││
│  │/revenue/      → Revenue reporting (user)                  │  ││
│  │ /stats/       → Admin analytics dashboard                 │  ││
│  │ /wallet/      → Wallet management (legacy)                │  ││
│  │ /marketplace/ → Agent marketplace                         │  ││
│  │ /admin/       → Admin controls                            │  ││
│  └────────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  ┌── MIDDLEWARE ─────────────────────────────────────────────┐  ││
│  │ • Rate Limiting (Auth 10/min, API 30/min, Exec 5/min)    │  ││
│  │ • CORS Security (Whitelist by FRONTEND_URL)              │  ││
│  │ • Structured Logging (no print statements)                │  ││
│  │ • Global Error Handler (consistent response format)       │  ││
│  │ • Request/Response logging for auditing                   │  ││
│  └────────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  ┌── CONFIGURATION ──────────────────────────────────────────┐  ││
│  │ • BaseSettings (Pydantic)     Loaded from .env:           │  ││
│  │ • DATABASE_URL                 SECRET_KEY                 │  ││
│  │ • FRONTEND_URL                 SMTP settings              │  ││
│  │ • DEBUG mode (false in prod)   AI provider settings       │  ││
│  │ • Logging level                Feature flags              │  ││
│  │ • Rate limit thresholds                                   │  ││
│  └────────────────────────────────────────────────────────────┘  ││
└───────────────────────────────────────────────────────────────────┘│
        │
        │ SQLAlchemy ORM
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│                    DATABASE LAYER                                 │
│              (SQLite Dev | PostgreSQL Prod)                       │
│                                                                   │
│  TABLES:                                                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ users (Core)                                              │ │
│  │ • id, email, hashed_password                              │ │
│  │ • subscription_tier, subscription_status                  │ │
│  │ • executions_this_month, tokens_used_this_month           │ │
│  │ • is_email_verified, email_verification_code (+ expiry)   │ │
│  │ • password_reset_token (hashed, + expiry)                 │ │
│  │ • created_at, is_active, role                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ agents (Execution Framework)                              │ │
│  │ • id, name, agent_type (NEW)                              │ │
│  │ • description, config (JSON)                              │ │
│  │ • owner_id, is_active                                     │ │
│  │ • created_at                                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ credit_transactions (NEW - Usage Tracking)                │ │
│  │ • id, user_id, amount (int, ±)                            │ │
│  │ • type (usage, purchase, refund, monthly_grant)           │ │
│  │ • description, agent_type, reference_id                   │ │
│  │ • created_at (indexed for month queries)                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ user_revenue_tracking (NEW - Revenue Reporting)           │ │
│  │ • id, user_id, reported_revenue (float)                   │ │
│  │ • source_agent, description                               │ │
│  │ • verified (bool, admin-set for credibility)              │ │
│  │ • created_at (indexed)                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ wallets (Legacy - Marketplace)                            │ │
│  │ • id, user_id, balance, currency, updated_at              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ transactions (Legacy - Wallet History)                    │ │
│  │ • id, wallet_id, amount, type                             │ │
│  │ • description, reference_id, created_at                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [Other tables: workflows, executions, marketplace_        │ │
│  │  listings, purchases, invoices, audit_logs, etc.]         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ALEMBIC MIGRATIONS:                                             │
│  • 670ef2d63cfb_initial_stage3                                   │
│  • 2026_02_27_add_monetization_fields                            │
│  • 2026_02_28_add_email_auth_fields                              │
│  • 2026_03_01_revenue_platform (NEW: agent_type,                │
│    credit_transactions, user_revenue_tracking)                   │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                              │
│                                                                   │
│  Email:                                                           │
│  • SMTP (Gmail, SendGrid, AWS SES)                               │
│  • Verification codes (6-digit, 15 min)                          │
│  • Password reset links (30 min)                                 │
│                                                                   │
│  AI Providers (Future):                                           │
│  • OpenAI (for agent execution)                                  │
│  • Anthropic (alternatives)                                      │
│                                                                   │
│  Payment (Future - Next Phase):                                   │
│  • Stripe (subscriptions + one-time payments)                    │
│  • Webhooks for subscription events                              │
│                                                                   │
│  Monitoring (Optional):                                           │
│  • Sentry (error tracking)                                       │
│  • LogRocket (session replay)                                    │
│  • DataDog (performance monitoring)                              │
└───────────────────────────────────────────────────────────────────┘


# =====================================
# DATA FLOW EXAMPLES
# =====================================

EXAMPLE 1: Agent Execution with Credit Deduction
──────────────────────────────────────────────────

User Request:
  POST /agents/119/run
  Input: { "business_type": "SaaS" }

1. authenticate() → Get current_user from JWT

2. enforce_execution_policy(user, db, agent_type="lead_generator")
   ├─ Check: is_email_verified == True ✓
   ├─ Check: subscription_status == "active" ✓
   ├─ Check: executions_this_month < limit ✓
   └─ Check: available_credits (Pro: 500) >= 1 ✓

3. execute_agent_by_type("lead_generator", {inputs})
   ├─ AgentRegistry.get_agent("lead_generator") → LeadGeneratorAgent()
   ├─ agent.execute(**inputs) → Results + token_usage
   └─ Return: { "leads": [...], "token_usage": 1250 }

4. record_successful_execution(user, db, tokens=1250, agent_type="lead_generator")
   ├─ Increment: user.executions_this_month (50 → 51)
   ├─ Increment: user.tokens_used_this_month (10000 → 11250)
   ├─ Deduct credits: CreditSystem.deduct_credits(1 credit for "lead_generator")
   │  └─ Create CreditTransaction (user_id, amount=-1, type="usage", agent="lead_generator")
   └─ Commit: db.commit()

5. Return response with cost, results, remaining credits


EXAMPLE 2: Revenue Reporting & Verification
─────────────────────────────────────────────

User Reports Revenue:
  POST /revenue/report
  Body: { "reported_revenue": 15000, "source_agent": "lead_generator" }

1. authenticate() → Get current_user

2. Validate:
   ├─ reported_revenue > 0 ✓
   ├─ reported_revenue < 10M (sanity check) ✓
   └─ Agent type is valid

3. Create UserRevenueTracking:
   ├─ user_id: current_user.id
   ├─ reported_revenue: 15000
   ├─ source_agent: "lead_generator"  
   ├─ verified: False (pending admin review)
   └─ created_at: now

4. db.add(transaction) + db.commit()

Admin Review:
  POST /stats/verify-revenue/42
  
1. check_admin_role(current_user) ✓

2. Query UserRevenueTracking(id=42)

3. Set verified=True, db.commit()

User Checks Status:
  GET /revenue/summary
  
  Returns:
    ├─ total_reported_revenue: 15000
    ├─ verified_revenue: 15000 (if approved)
    ├─ unverified_revenue: 0
    └─ by_agent: { "lead_generator": 15000 }


EXAMPLE 3: Admin Analytics Dashboard
─────────────────────────────────────

GET /stats/platform (admin only)

Returns:
{
  "users": {
    "total": 1250,
    "active": 950,
    "email_verified": 920,
    "by_tier": { "free": 750, "pro": 450, "enterprise": 50 }
  },
  "executions": {
    "total": 45320,
    "avg_per_user": 36.26,
    "total_tokens_processed": 1850000
  },
  "credits": {
    "total_used_month": 12450,
    "total_granted_month": 15000,
    "net_deficit": -2550
  },
  "revenue": {
    "estimated_mrr": 94650,  # (450 * 99) + (50 * 999)
    "user_reported_revenue": 385000,
    "verified_revenue": 320000,
    "unverified_revenue": 65000,
    "mrr_breakdown": { "pro": 44550, "enterprise": 49950 }
  },
  "agents": {
    "lead_generator": { "executions": 12400, "credits_used": 12400 },
    "social_content": { "executions": 18920, "credits_used": 18920 },
    "offer_optimizer": { "executions": 14000, "credits_used": 28000 }
  }
}


# =====================================
# ENFORCEMENT LAYER (UNIFIED)
# =====================================

SINGLE POINT OF CONTROL: services/execution_policy.py

Pro:
✓ No duplicate enforcement logic
✓ All agents use same policy
✓ Easy to audit and test
✓ Changes propagate to all agents instantly
✓ Clear error messages for users

Enforcement Happens at:
1. PRE-EXECUTION: enforce_execution_policy()
   └─ Email, subscription, limits, credits verified
   
2. POST-EXECUTION: record_successful_execution()
   └─ Usage incremented, credits deducted
   
3. FALLBACK: catch exceptions in route handlers
   └─ Rollback transactions, return error


# =====================================
# CREDIT SYSTEM
# =====================================

ALLOCATIONS (Tier-based, Monthly Reset):

free:       20 credits/month
pro:       500 credits/month  
enterprise: ∞ (unlimited)

AGENT COSTS (Per Execution):

lead_generator:       1 credit
social_content:       1 credit
offer_optimizer:      2 credits

TRACKING:

Every execution creates CreditTransaction:
├─ type="usage" → Deduct credits
├─ type="monthly_grant" → Monthly allocation
├─ type="purchase" → User bought credits  
├─ type="refund" → Failed execution refund

QUERIES:

get_used_credits_this_month(user)
  └─ SELECT SUM(Amount) FROM credit_transactions
     WHERE user_id=X AND type="usage" AND created_at >= month_start

get_available_credits_this_month(user)
  └─ allocation - used_this_month (0 minimum)

RESET:

Monthly job (scheduled):
  └─ For all active users: grant monthly_allocation credits


# =====================================
# AGENT REGISTRY SYSTEM
# =====================================

REGISTRATION:

class LeadGeneratorAgent(BaseAgent):
    AGENT_TYPE = "lead_generator"
    DISPLAY_NAME = "Lead Generator"
    EXECUTION_COST = 1
    
    async def execute(self, **kwargs):
        # Implementation
        pass

AgentRegistry.register(LeadGeneratorAgent)

USAGE:

1. Dynamic Resolution:
   agent = AgentRegistry.get_agent("lead_generator")
   
2. Execution (No Hardcoding):
   result = await execute_agent_by_type("lead_generator", inputs)
   
3. Metadata Listing:
   agents = AgentRegistry.list_agents()
   → { "lead_generator": {...}, "social_content": {...} }

BENEFITS:

✓ Agents pluggable without code changes
✓ New agents added via inheritance + register
✓ Types referenced everywhere (agents.py, policies, analytics)
✓ Costs defined in one place (EXECUTION_COST)


# =====================================
# DEPLOYMENT CHECKLIST
# =====================================

BEFORE PRODUCTION:

1. Database
   ├─ Run: alembic upgrade head
   ├─ Verify: all 4 migrations applied
   └─ Check: schema with PRAGMA table_info(users)

2. Environment
   ├─ Copy: .env.example → .env
   ├─ Generate: NEW SECRET_KEY (32+ bytes, random)
   ├─ Update: FRONTEND_URL to production domain
   ├─ Configure: SMTP for email verification
   └─ Set: DEBUG=false

3. Docker
   ├─ Build: docker-compose build
   ├─ Run: docker-compose up -d
   ├─ Test: curl http://localhost:8000/health
   └─ Verify: Backend logs show no errors

4. Initialization
   ├─ Create: Initial admin user (manual SQL or script)
   ├─ Seed: System agents (if not auto-migrated)
   ├─ Verify: GET /stats/platform returns data
   └─ Test: All endpoints accessible

5. Monitoring
   ├─ Logs: Check output for errors
   ├─ Database: Monitor connection pool
   ├─ Memory: Watch memory usage
   └─ Rate Limits: Verify rate limiting active

PRODUCTION FEATURES:

✓ JWT auth with token expiry
✓ Email verification required
✓ Credit-based execution limits
✓ Monthly allocations reset
✓ Revenue tracking with admin verification
✓ Audit logging
✓ Error handling & logging
✓ CORS security
✓ Rate limiting
✓ Database migrations
✓ Configuration via environment


# =====================================
# NEXT PHASE (NOT IN SCOPE)
# =====================================

1. Stripe Integration
   ├─ Payment processing
   ├─ Subscription management
   └─ Invoice generation
   
2. Frontend Implementation
   ├─ User signup/login
   ├─ Agent marketplace
   ├─ Execution dashboard
   └─ Billing management
   
3. Scheduled Jobs
   ├─ Monthly credit reset
   ├─ Revenue report verification workflow
   └─ Cleanup archived logs
   
4. Analytics Dashboard
   ├─ User growth charts
   ├─ Revenue trends
   └─ Agent popularity
   
5. Advanced Features
   ├─ API keys for external integrations
   ├─ Webhooks for execution events
   ├─ Custom agent creation UI
   └─ Workflow builder


# =====================================
# KEY DESIGN PRINCIPLES
# =====================================

1. UNIFIED ENFORCEMENT
   Single enforce_execution_policy() gate for all agents
   
2. NO BREAKING CHANGES
   Legacy wallet system preserved alongside new credit system
   
3. MODULAR AGENTS
   AgentRegistry enables dynamic agent addition
   
4. AUDITABLE CREDITS
   CreditTransaction model tracks every credit change
   
5. REVENUE TRACKING
   UserRevenueTracking enables case studies + social proof
   
6. ADMIN CONTROLS
   /stats endpoints provide full platform visibility
   
7. SCALABLE ARCHITECTURE
   Ready for PostgreSQL, load balancing, caching
   
8. SECURE BY DEFAULT
   No hardcoded secrets, CORS whitelisted, JWT expiry
"""

if __name__ == "__main__":
    print(ARCHITECTURE)
