#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

kubectl apply -k "${ROOT_DIR}/infra/k8s"
kubectl rollout status deployment/flowora-api -n flowora
kubectl rollout status deployment/flowora-worker -n flowora
kubectl rollout status deployment/flowora-beat -n flowora
