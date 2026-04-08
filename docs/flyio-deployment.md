# Fly.io Deployment Blueprint
Flowora - Where AI Agents Flow Together.

This is the recommended first public deployment target for Flowora.

Fly config files:
- `infra/fly/flowora-api.toml`
- `infra/fly/flowora-web.toml`
- `infra/fly/flowora-worker.toml`
- `infra/fly/flowora-beat.toml`

## Why Fly.io First
- Docker-native deployment model
- Better fit for multi-service systems than simpler single-web-app platforms
- Easier path to split API, workers, and frontend cleanly
- Closer to the production topology Flowora already uses locally

## Recommended Production Topology
Deploy Flowora as four Fly apps plus managed data services:

1. `flowora-api`
- FastAPI backend
- Internal port: `8000`

2. `flowora-worker`
- Celery worker
- No public port

3. `flowora-beat`
- Celery beat scheduler
- No public port

4. `flowora-web`
- Next.js frontend
- Internal port: `3000`

Managed services:
- Fly Postgres or external managed Postgres
- Upstash Redis / Fly Redis / other managed Redis
- Managed LLM provider: OpenAI recommended for first public launch

Optional:
- Self-hosted object storage only if needed
- Self-hosted Ollama only if you have a GPU-backed deployment plan

## Environment Strategy
Use `.env.prod` as the source of truth, then copy values into Fly secrets.

Recommended cloud AI configuration:
```env
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_MODEL=gpt-4.1-mini
ALLOW_LLM_MOCK_FALLBACK=false
REQUEST_TIMEOUT_SECONDS=120
TIMEOUT_BUFFER_SECONDS=10
OLLAMA_TIMEOUT_SECONDS=110
```

## App Mapping

### `flowora-api`
Build context:
- `apps/backend`

Start command:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Must set secrets:
- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `FRONTEND_URL`
- `ALLOWED_ORIGINS`
- `DEFAULT_AI_PROVIDER`
- `DEFAULT_AI_MODEL`
- `OPENAI_API_KEY` or provider equivalent
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET`
- `MINIO_SECURE`

Health check:
- `GET /health`

### `flowora-worker`
Build context:
- `apps/backend`

Start command:
```bash
celery -A celery_app.celery_app worker --loglevel=INFO --queues=celery,agent_executions,workflows,optimization,scheduled,swarm,compliance,ethics,simulation
```

Use the same core secrets as `flowora-api`.

Recommended initial size:
- `shared-cpu-1x`
- `1024MB`

### `flowora-beat`
Build context:
- `apps/backend`

Start command:
```bash
celery -A celery_app.celery_app beat --loglevel=INFO
```

Use the same database and Redis secrets as `flowora-api`.

Recommended initial size:
- `shared-cpu-1x`
- `512MB`

### `flowora-web`
Build context:
- `apps/frontend`

Start command:
```bash
npm run start -- -H 0.0.0.0 -p 3000
```

Must set:
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SITE_URL`
- `NEXT_PUBLIC_DEMO_AGENT_ID`

Recommended initial size:
- `shared-cpu-1x`
- `1024MB`

## Secrets Setup
Apply secrets per app using Fly secrets.

### Shared backend secrets
Use the same secret set for:
- `flowora-api`
- `flowora-worker`
- `flowora-beat`

Example:
```bash
fly secrets set \
  SECRET_KEY="..." \
  DATABASE_URL="..." \
  REDIS_URL="..." \
  CELERY_BROKER_URL="..." \
  CELERY_RESULT_BACKEND="..." \
  FRONTEND_URL="https://app.flowora.ai" \
  ALLOWED_ORIGINS="https://app.flowora.ai,https://flowora.ai" \
  DEFAULT_AI_PROVIDER="openai" \
  DEFAULT_AI_MODEL="gpt-4.1-mini" \
  OPENAI_API_KEY="..." \
  MINIO_ENDPOINT="..." \
  MINIO_ACCESS_KEY="..." \
  MINIO_SECRET_KEY="..." \
  MINIO_BUCKET="flowora" \
  MINIO_SECURE="true" \
  EMAIL_VERIFICATION_REQUIRED="true" \
  AUTO_VERIFY_EMAIL="false" \
  ALLOW_LLM_MOCK_FALLBACK="false" \
  --app flowora-api
```

Repeat the same secret set for:
```bash
fly secrets set ... --app flowora-worker
fly secrets set ... --app flowora-beat
```

### Frontend secrets / public env
```bash
fly secrets set \
  NEXT_PUBLIC_API_URL="https://api.flowora.ai" \
  NEXT_PUBLIC_SITE_URL="https://flowora.ai" \
  NEXT_PUBLIC_DEMO_AGENT_ID="1" \
  --app flowora-web
```

## Step-by-Step Deploy Order
1. Create Postgres
2. Create Redis
3. Create `flowora-api`
4. Add API secrets
5. Deploy API and verify `/health`
6. Create `flowora-worker`
7. Add shared secrets and deploy worker
8. Create `flowora-beat`
9. Add shared secrets and deploy beat
10. Create `flowora-web`
11. Set `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_SITE_URL`
12. Attach domains and TLS
13. Run smoke tests against the public URLs

## Dry Run Deployment Order
Do not deploy everything at once.

### 1. Deploy backend only
```bash
fly launch --no-deploy --copy-config --name flowora-api --config infra/fly/flowora-api.toml
fly deploy --config infra/fly/flowora-api.toml
```

Verify:
```bash
curl https://flowora-api.fly.dev/health
curl https://flowora-api.fly.dev/api/health
```

### 2. Deploy frontend second
```bash
fly launch --no-deploy --copy-config --name flowora-web --config infra/fly/flowora-web.toml
fly deploy --config infra/fly/flowora-web.toml
```

Verify:
```bash
curl -I https://flowora-web.fly.dev/
```

### 3. Deploy worker and beat last
```bash
fly launch --no-deploy --copy-config --name flowora-worker --config infra/fly/flowora-worker.toml
fly deploy --config infra/fly/flowora-worker.toml

fly launch --no-deploy --copy-config --name flowora-beat --config infra/fly/flowora-beat.toml
fly deploy --config infra/fly/flowora-beat.toml
```

This order keeps debugging focused:
- API first
- then frontend
- then async jobs

## Smoke Test Checklist
- `https://<api-domain>/health`
- `https://<api-domain>/docs`
- `https://<web-domain>/`
- register
- verify email
- login
- create agent
- run agent
- create workflow
- run workflow

## First Live Smoke Test
Do this before inviting any real users:

1. Register
2. Verify email
3. Login
4. Create agent
5. Run agent
6. Create workflow
7. Run workflow

Watch during the test:
- `fly logs --app flowora-api`
- `fly logs --app flowora-worker`
- `fly logs --app flowora-beat`

Confirm:
- no crashes
- no restart loops
- healthy `/health`
- correct overload behavior (`429` / `504`)

Do not skip this step.

## Common Misconfigurations

### 1. Wrong public API URL
Symptom:
- frontend loads but API calls fail

Fix:
- set `NEXT_PUBLIC_API_URL` to the actual public backend URL

### 2. CORS mismatch
Symptom:
- browser shows blocked API requests

Fix:
- set `ALLOWED_ORIGINS` to the exact frontend domain(s)

### 3. Local Ollama left enabled in cloud
Symptom:
- inference fails or hangs

Fix:
- use `DEFAULT_AI_PROVIDER=openai` for first public deploy

### 4. Multiple backend workers on small instance
Symptom:
- memory spikes and unstable inference behavior

Fix:
- keep `uvicorn ... --workers 1`

### 5. Missing Redis split DBs
Symptom:
- Celery and cache behavior interfere

Fix:
- keep separate DB indexes:
  - `REDIS_URL` -> `/0`
  - `CELERY_BROKER_URL` -> `/1`
  - `CELERY_RESULT_BACKEND` -> `/2`

### 6. Dev/test endpoints left enabled
Symptom:
- unexpected internal-only routes exposed publicly

Fix:
- run a final public route review after deploy
- keep `DEBUG=false`
- verify no development-only toggles are enabled

## Final Hardening After First Deploy
1. Confirm rate limiting is active
2. Confirm email verification works end-to-end
3. Confirm custom domain and HTTPS are live
4. Review public routes for debug/test exposure
5. Watch logs and metrics for the first live runs

## Scaling Recommendations

### Initial public launch
- `flowora-api`: 1 machine, `shared-cpu-1x`, `1024MB`
- `flowora-web`: 1 machine, `shared-cpu-1x`, `1024MB`
- `flowora-worker`: 1 machine, `shared-cpu-1x`, `1024MB`
- `flowora-beat`: 1 machine, `shared-cpu-1x`, `512MB`

### After real traffic begins
- scale `flowora-worker` first
- scale `flowora-api` second
- keep `flowora-beat` single-instance
- move inference to managed LLM capacity before scaling app replicas aggressively

## Recommendation
For first public launch:
- Use Fly.io
- Use managed Postgres
- Use managed Redis
- Use OpenAI as the production inference provider
- Keep Ollama for local development only
