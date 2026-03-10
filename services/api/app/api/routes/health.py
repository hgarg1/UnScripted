from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from services.api.app.db.session import get_db_session
from services.api.app.services.metrics import render_metrics

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics")
def metrics(session: Session = Depends(get_db_session)) -> Response:
    return Response(content=render_metrics(session), media_type="text/plain; version=0.0.4")
