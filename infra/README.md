# Infrastructure Setup Guide

This guide describes how to run the Flowora platform locally with Docker, and how to deploy it to Kubernetes for production.

**Prerequisites**
- Docker Desktop (or Docker Engine)
- kubectl
- A Kubernetes cluster (EKS/GKE/AKS or self-managed)
- Container registry credentials (GHCR/ECR/GCR)

**Local Distributed Stack (Docker)**
1. Copy environment defaults and update secrets:
   - `apps/backend/.env.example` -> `apps/backend/.env`
2. Start the distributed stack:
   - `docker compose -f infra/docker-compose.distributed.yml up -d`
3. Verify health:
   - API: `http://localhost:8000/health`
   - Grafana: `http://localhost:3001`
   - Prometheus: `http://localhost:9090`

**Kubernetes Deployment**
1. Build and push container images:
   - `apps/backend` image
   - `apps/frontend` image (optional)
2. Update image references in `infra/k8s/api-deployment.yaml` and `infra/k8s/worker-deployment.yaml`.
3. Update secrets in `infra/k8s/secret.yaml`.
4. Apply manifests:
   - `kubectl apply -k infra/k8s`
5. Confirm rollout:
   - `kubectl rollout status deployment/flowora-api -n flowora`
   - `kubectl rollout status deployment/flowora-worker -n flowora`

**Scaling**
- Use `infra/k8s/hpa.yaml` to scale API and workers based on CPU.
- Adjust queue workers by changing worker deployment replicas.

**Observability**
- OpenTelemetry collector receives traces and exports to Prometheus.
- Grafana dashboards should be configured with Prometheus as a data source.

**Security**
- JWT + RBAC enforced by backend.
- Rate limiting middleware enabled in FastAPI.
- Keep secrets in K8s secrets or external vaults.
