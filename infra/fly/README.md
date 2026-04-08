# Flowora Fly.io Configs

Canonical Fly.io app configs for Flowora:

- `infra/fly/flowora-api.toml`
- `infra/fly/flowora-web.toml`
- `infra/fly/flowora-worker.toml`
- `infra/fly/flowora-beat.toml`

Recommended deployment order:
1. API
2. Web
3. Worker
4. Beat

Use `docs/flyio-deployment.md` for the full rollout procedure and smoke test plan.
