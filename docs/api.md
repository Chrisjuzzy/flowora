# API Reference
Flowora - Where AI Agents Flow Together.

FastAPI includes interactive documentation at `/docs`.

## Core Endpoints
- `POST /auth/login`
- `GET /agents/`
- `POST /agents/{agent_id}/run`
- `GET /workflows/`
- `POST /workflows/{workflow_id}/run`
- `GET /marketplace/listings`
- `POST /marketplace/listings/{listing_id}/buy`

## Public Sharing
- `GET /agents/public/{agent_id}`
- `POST /agents/public/{agent_id}/run`
- `POST /agents/{agent_id}/clone`
- `POST /marketplace/{agent_id}/install`
- `GET /marketplace/public/{slug}`
- `POST /marketplace/public/{slug}/install`
- `GET /share/{run_id}`
- `GET /workflows/public/{workflow_id}`
- `POST /workflows/{workflow_id}/clone`
- `POST /workflows/{workflow_id}/install`

## Analytics
- `GET /analytics/summary`
- `GET /analytics/agents/{agent_id}/prompt-performance`
- `GET /analytics/founder-runs`
- `GET /growth/metrics`

## Founder Mode
- `POST /founder/run`
