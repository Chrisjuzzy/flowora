# Architecture
Flowora - Where AI Agents Flow Together.

Flowora is composed of a FastAPI backend, a Next.js frontend, and distributed worker services for async tasks.

## High-Level Architecture
```mermaid
graph LR
  UI[Next.js Frontend] --> API[FastAPI]
  API --> DB[(PostgreSQL + pgvector)]
  API --> Redis[(Redis)]
  API --> MinIO[(MinIO)]
  API --> Workers[Celery Workers]
  Workers --> Providers[LLM Providers]
  API --> Metrics[Prometheus / Grafana]
```

## Key Services
- Agent Runtime Engine
- Tool Registry and execution handlers
- Marketplace and billing
- Vector memory and retrieval
- Founder Mode orchestration

## Data Stores
- PostgreSQL for core data
- pgvector for semantic memory
- Redis for caching and rate limiting
- MinIO for object storage
