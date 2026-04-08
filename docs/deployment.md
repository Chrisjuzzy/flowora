# Deployment
Flowora is ready for cloud deployment. This guide covers production Docker Compose, Render, and Fly.io.

Recommended first public deployment target:
- Fly.io

Detailed Fly.io rollout guide:
- `docs/flyio-deployment.md`

**Deployment Architecture**
- Frontend: Next.js (port 3000)
- Backend API: FastAPI (port 8000)
- Workers: Celery worker and beat
- Database: Managed Postgres (recommended)
- Cache/Queue: Managed Redis (recommended)
- Object storage: S3-compatible (MinIO or cloud object storage)
- Optional local AI: Ollama (local dev only)

**Production Docker Compose**
Use `docker-compose.prod.yml` as the canonical production compose file for a VM or bare-metal deployment.

1. Copy `.env.prod.example` to `.env.prod` and set real values.
2. Build and start:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
3. Route traffic:
- `http://<your-domain>` -> Next.js frontend
- `http://<your-domain>/api` -> FastAPI backend
4. Optional profiles:
- `--profile local` for bundled Postgres, Redis, and MinIO
- `--profile local-ai` for bundled Ollama
- `--profile observability` for Prometheus and Grafana
5. Health checks:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl -H "Host: flowora.ai" http://localhost/api/health
```

**Production Environment Variables**
Set these in your cloud provider or `.env.prod`.

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `FRONTEND_URL`
- `ALLOWED_ORIGINS`
- `DEFAULT_AI_PROVIDER`
- `DEFAULT_AI_MODEL`
- `OLLAMA_BASE_URL` (local only)
- `OLLAMA_TIMEOUT_SECONDS`
- `REQUEST_TIMEOUT_SECONDS`
- `TIMEOUT_BUFFER_SECONDS`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET`
- `MINIO_SECURE`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SITE_URL`
- `NEXT_PUBLIC_DEMO_AGENT_ID`
- `TRAEFIK_DOMAIN`
- `GRAFANA_ADMIN_PASSWORD`

**Render Deployment**
Recommended layout is four services plus managed Postgres and Redis.

1. Create a Render Postgres instance and copy its connection URL into `DATABASE_URL`.
2. Create a Render Redis instance and set `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.
3. Create a Web Service for the backend.
4. Set the backend start command:
```
uvicorn main:app --host 0.0.0.0 --port 8000
```
5. Create a Background Worker for Celery:
```
celery -A celery_app.celery_app worker --loglevel=INFO --queues=celery,agent_executions,workflows,optimization,scheduled,swarm,compliance,ethics,simulation
```
6. Create a second Background Worker for Celery Beat:
```
celery -A celery_app.celery_app beat --loglevel=INFO
```
7. Create a Web Service for the frontend.
8. Set frontend build command:
```
npm install && npm run build
```
9. Set frontend start command:
```
npm run start -- -p 3000
```
10. Set `NEXT_PUBLIC_API_URL` to the backend public URL and `NEXT_PUBLIC_SITE_URL` to the frontend public URL.
11. Use a managed LLM provider in cloud by setting `DEFAULT_AI_PROVIDER=openai` (or Anthropic/Gemini) and keep `ALLOW_LLM_MOCK_FALLBACK=false`.

**Fly.io Deployment**
Recommended layout is separate apps for API, worker, beat, and frontend.

1. Create a Fly Postgres cluster and set `DATABASE_URL`.
2. Create a Fly Redis instance and set `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.
3. Launch the API app in `apps/backend`.
4. Set API internal port to `8000` in `fly.toml`.
5. Launch a worker app in `apps/backend` with process command:
```
celery -A celery_app.celery_app worker --loglevel=INFO --queues=celery,agent_executions,workflows,optimization,scheduled,swarm,compliance,ethics,simulation
```
6. Launch a beat app in `apps/backend` with process command:
```
celery -A celery_app.celery_app beat --loglevel=INFO
```
7. Launch the frontend app in `apps/frontend`.
8. Set frontend internal port to `3000`.
9. Set `NEXT_PUBLIC_API_URL` to the API app URL and `NEXT_PUBLIC_SITE_URL` to the frontend URL.
10. Use a managed LLM provider unless the Fly deployment has dedicated Ollama/GPU support.

**Ports**
- Backend: `8000`
- Frontend: `3000`
- Public reverse proxy: `80` and `443`

**Ollama Notes**
- Ollama is optional and recommended only for local or GPU-enabled environments.
- For cloud deployments, set `DEFAULT_AI_PROVIDER=openai` (or another managed provider) and omit Ollama.
