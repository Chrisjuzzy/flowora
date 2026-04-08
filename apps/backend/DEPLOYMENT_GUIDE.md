"""
================================
PRODUCTION DEPLOYMENT GUIDE
================================

This is your Flowora SaaS platform, hardened and ready for production deployment.

================================
COMPLETED PHASES
================================

✅ PHASE 1: Production Configuration
   - Created core/config.py with BaseSettings
   - All secrets use environment variables
   - Created .env.example with all required variables
   - No hardcoded secrets in codebase

✅ PHASE 2: JWT Auth Hardening
   - Uses JOSE JWT library
   - SECRET_KEY from environment
   - Token expiration enforced (60 minutes default)
   - Invalid tokens rejected with 401

✅ PHASE 3: Rate Limiting
   - Middleware-based rate limiting
   - Auth routes: 10 req/min
   - API routes: 30 req/min
   - Execution routes: 5 req/min

✅ PHASE 4: CORS Security
   - Whitelist only FRONTEND_URL from config
   - No wildcard CORS
   - Production-safe: localhost removed in production

✅ PHASE 5: Logging
   - Structured logging with Python logging module
   - Log level from config (INFO default)
   - No print statements (all logging)
   - Logs to stdout + optional file

✅ PHASE 6: Global Error Handler
   - Consistent error response format:
     {"success": false, "error": "message", "code": 403}
   - Validation errors: 422
   - Server errors: 500
   - Controlled error messages (no stack traces to client)

✅ PHASE 7: Dockerization
   - Multi-stage Dockerfile (builder + runtime)
   - Docker Compose for local + production setup
   - Health check included
   - Environment-based configuration

✅ PHASE 8: Database Migrations
   - All migrations applied (3 total)
   - Email verification fields added
   - Monetization fields added
   - Schema verified production-ready

✅ PHASE 9: Production Safety
   - Passwords: bcrypt hashing
   - Reset tokens: hashed with bcrypt before storage
   - Verification codes: 6-digit, 15 min expiry
   - Execution enforcement: before agent runs
   - Usage tracking: post-execution only
   - Email verification: required before execution

✅ PHASE 10: Project Structure
   Clean organization:
   backend/
   ├── config.py (configuration)
   ├── main.py (FastAPI app)
   ├── security.py (JWT + auth)
   ├── database.py (DB connection)
   ├── models.py (SQLAlchemy models)
   ├── schemas.py (Pydantic schemas)
   ├── .env.example (env template)
   ├── Dockerfile (containerization)
   ├── alembic/ (migrations)
   ├── routers/ (API routes)
   ├── services/ (business logic)
   ├── middleware/ (HTTP middleware)
   └── models/, utils/... (organized modules)

✅ PHASE 11: Summary Output
   ✓ Folder structure clean
   ✓ No duplicate files
   ✓ Environment variables documented
   ✓ Docker ready
   ✓ Deployment-ready

================================
BEFORE DEPLOYMENT
================================

1. Environment Variables

   Copy .env.example to .env
   
   CRITICAL VARIABLES:
   - SECRET_KEY: Generate with:
     python -c "import secrets; print(secrets.token_urlsafe(32))"
   - FRONTEND_URL: Your frontend domain
   - SMTP_HOST/USER/PASSWORD: Email provider credentials

2. Database

   Run migrations:
   alembic upgrade head

   Verify schema:
   python verify_schema.py

3. SMTP Configuration

   If using Gmail:
   - Enable 2FA on Gmail account
   - Generate app password (not account password)
   - Set SMTP_HOST=smtp.gmail.com, SMTP_PORT=587

4. Deploy Strategy

   Option A: Docker Compose (Recommended for MVP)
   docker-compose up -d

   Option B: Traditional Deployment
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8000

================================
LOCAL DEVELOPMENT
================================

1. Setup

   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt

2. Environment

   Copy .env.example to .env
   Update with local values:
   - DATABASE_URL=sqlite:///./app.db
   - SECRET_KEY=(any random string for dev)
   - DEBUG=true

3. Migrations

   alembic upgrade head

4. Run

   uvicorn main:app --reload

5. Access

   API: http://localhost:8000
   Docs: http://localhost:8000/docs
   ReDoc: http://localhost:8000/redoc

================================
DOCKER DEPLOYMENT (PRODUCTION)
================================

1. Build Images

   docker-compose build

2. Configure Environment

   Create .env file with production values:

   # Copy from root directory
   cp apps/backend/.env.example .env

   Edit .env with production values:
   SECRET_KEY=<generate-new>
   FRONTEND_URL=https://yourdomain.com
   DEBUG=false
   SMTP_HOST=your-smtp-server
   SMTP_USER=your-email
   SMTP_PASSWORD=your-password

3. Run Services

   docker-compose up -d

4. Verify

   docker-compose logs -f backend
   curl http://localhost:8000/health

5. Shutdown

   docker-compose down

================================
NEW ENDPOINTS
================================

AUTHENTICATION:
- POST /auth/register           → Create account + send verification code
- POST /auth/verify-email       → Verify with 6-digit code
- POST /auth/resend-verification-code → Get new code
- POST /auth/forgot-password    → Send reset link
- POST /auth/reset-password     → Reset password with token
- GET  /auth/me                 → User dashboard with usage stats
- POST /auth/login              → Get JWT tokens
- POST /auth/token              → Get access token

HEALTH CHECK:
- GET  /health                  → Detailed health status
- GET  /                         → Quick health check

================================
AGENT EXECUTION FLOW
================================

User requests agent run:

1. enforce_execution_policy(user, db)
   ├─ Check: email_verified == True (403 if false)
   ├─ Check: subscription_status == "active" (403 if false)
   ├─ Check: executions_this_month < limit (429 if exceeded)
   └─ Check: wallet.balance >= 1.0 credit (402 if false)

2. execute_agent() or execute_workflow()
   └─ Run the agent

3. record_successful_execution(user, db, tokens)
   ├─ Increment executions_this_month
   ├─ Increment tokens_used_this_month
   └─ Commit to database

================================
MONETIZATION READY
================================

✅ 3 Seeded Agents:
   1. Lead Generator (Free: 10/month, Pro: 200/month)
   2. Social Media Planner (Free: 4/month, Pro: unlimited)
   3. Offer Optimizer (Free: 2/month, Pro: 20/month)

✅ Usage Tracking:
   - executions_this_month (counter per user)
   - tokens_used_this_month (LLM token tracking)

✅ Subscription Tiers:
   - free: 50 execution/month base limit
   - pro: 1000 executions/month
   - enterprise: unlimited

✅ Next: Integrate Stripe for payments

================================
MONITORING & LOGS
================================

Production logs available at:
- app stdout (docker logs)
- Optional log file (set LOG_FILE in .env)

Monitor:
- Authentication attempts (success/failure)
- Agent executions (blocked/allowed)
- Email delivery (verification/reset)
- Rate limit hits
- Server errors

=====================================
SECURITY CHECKLIST (PRE-DEPLOYMENT)
=====================================

□ SECRET_KEY is random (32+ bytes)
□ DEBUG=false in production
□ FRONTEND_URL updated to production domain
□ SMTP credentials configured
□ Database backed up before deployment
□ CORS origins whitelisted correctly
□ Rate limits tuned for load
□ Logging configured
□ Health check endpoint accessible
□ Error responses don't leak stack traces
□ Password hashing verified (bcrypt)
□ Email verification required before execution
□ Usage only increments after success

=====================================
TROUBLESHOOTING
=====================================

Issue: "Could not validate credentials"
→ Check SECRET_KEY in .env matches token generation
→ Check token hasn't expired (60 minutes default)

Issue: "Email not verified"
→ User must complete email verification first
→ Check SMTP is configured to send emails
→ Send verification code with /auth/resend-verification-code

Issue: "Limit reached"
→ User hit monthly execution limit
→ Check user's tier (free/pro/enterprise)
→ Admin can reset with database update

Issue: "Insufficient credits"
→ User's wallet balance is below cost
→ User must purchase or upgrade

Issue: Docker build fails
→ Clear cache: docker system prune
→ Check requirements.txt syntax
→ Verify base image is available

=====================================
SUPPORT & NEXT STEPS
=====================================

1. Stripe Integration
   - Users purchase credits
   - Subscription management
   - Invoice generation

2. Analytics Dashboard
   - User engagement tracking
   - Revenue metrics
   - Agent popularity

3. Frontend Implementation
   - User login/signup
   - Agent marketplace
   - Execution dashboard
   - Billing management

4. Scaling
   - Move to PostgreSQL
   - Add Redis for caching
   - Load balancing
   - CDN for assets

================================
DEPLOYMENT IS READY ✅
================================

This system is production-hardened and ready for:
✓ Real user signups
✓ Email verification
✓ Secure JWT authentication
✓ Agent execution with limits
✓ Usage tracking and monetization
✓ Error handling and logging
✓ Docker containerization
✓ Scalable architecture

Start your deployment with:
  docker-compose up -d

Monitor with:
  docker-compose logs -f

Good luck with your SaaS! 🚀
"""

if __name__ == "__main__":
    print(__doc__)
