import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.core.auth import get_current_user
from src.api.core.db import get_db
from src.api.models import AnalyticsEvent, Membership, User, Workspace
from src.api.schemas import AnalyticsIngestRequest, AnalyticsIngestResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _require_workspace_access(db: Session, user_id: uuid.UUID, workspace_id: uuid.UUID) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    membership = db.execute(
        select(Membership).where(Membership.user_id == user_id, Membership.organization_id == ws.organization_id)
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")

    return ws


# PUBLIC_INTERFACE
@router.post(
    "/ingest",
    response_model=AnalyticsIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest analytics events",
    description="Bulk ingests analytics events into Postgres for a workspace (requires workspace access).",
    operation_id="analytics_ingest",
)
def ingest_events(
    payload: AnalyticsIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsIngestResponse:
    """Ingest analytics events into database."""
    _require_workspace_access(db, current_user.id, payload.workspace_id)

    now = dt.datetime.now(dt.UTC)
    events = [
        AnalyticsEvent(
            workspace_id=payload.workspace_id,
            user_id=current_user.id,
            name=e.name,
            ts=e.ts or now,
            properties=e.properties,
        )
        for e in payload.events
    ]
    if not events:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No events provided")

    db.add_all(events)
    db.commit()

    return AnalyticsIngestResponse(ingested=len(events))
