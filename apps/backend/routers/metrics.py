from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from utils.metrics import snapshot
from utils.prometheus_metrics import update_snapshot_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics():
    update_snapshot_metrics(snapshot())
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
