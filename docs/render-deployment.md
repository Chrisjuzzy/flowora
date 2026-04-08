# Render Deployment

This guide deploys Flowora's backend to Render in a safe boot mode first.
It keeps the deployment simple and reliable before you add managed Postgres,
Redis, and a real AI provider.

Recommended first step:
- deploy only the backend API
- verify `/health`
- verify `/api/health`
- then connect the frontend from Vercel later

## Blueprint

Use the root `render.yaml` file in this repository. It defines:

- `flowora-api`
- Python runtime
- `apps/backend` as the root directory
- a safe starter environment

## Safe Boot

The Render blueprint uses:

- `DATABASE_URL=sqlite:///./test.db`
- `USE_PGVECTOR=false`
- `REDIS_URL=redis://localhost:6379/0`
- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/0`
- `DEFAULT_AI_PROVIDER=mock`
- `ALLOW_LLM_MOCK_FALLBACK=true`
- `ENABLE_ASYNC_EXECUTION=false`
- `EMAIL_VERIFICATION_REQUIRED=false`
- `AUTO_VERIFY_EMAIL=true`

This keeps the API booting without external dependencies while you validate
the live service.

## Deploy Steps

1. Create a Render account and connect your GitHub repo.
2. Import the repo as a new blueprint or web service.
3. Point Render at the root `render.yaml`.
4. Deploy the `flowora-api` service.
5. Wait for the health check to pass.
6. Open:
   - `/health`
   - `/api/health`
   - `/docs`

## Expected Health

You should see a healthy response similar to:

```json
{
  "status": "healthy"
}
```

or a richer health payload that still reports the app as healthy.

## After The Backend Is Green

Once the backend is stable:

1. Deploy the frontend on Vercel.
2. Set `NEXT_PUBLIC_API_URL` to the Render backend URL.
3. Move from safe boot mode to production mode:
   - managed Postgres
   - managed Redis
   - real AI provider
   - SMTP

## Production Mode Later

For production, replace the safe boot values in Render with:

- managed Postgres `DATABASE_URL`
- managed Redis URLs
- `DEFAULT_AI_PROVIDER=openai` or another managed provider
- `ALLOW_LLM_MOCK_FALLBACK=false`
- `ENABLE_ASYNC_EXECUTION=true`

Keep the safe boot config around as a fallback profile.
