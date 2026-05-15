import datetime as dt
from typing import Literal, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.core.auth import get_current_user
from src.api.core.db import get_db
from src.api.models import AnalyticsEvent, Membership, User, Workspace
from src.api.schemas import (
    DashboardKpiResponse,
    DashboardSummaryResponse,
    DashboardTimeseriesPoint,
    DashboardTimeseriesResponse,
    DashboardTopEvent,
    DashboardTopEventsResponse,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _parse_range(
    start: Optional[dt.datetime],
    end: Optional[dt.datetime],
) -> tuple[dt.datetime, dt.datetime]:
    now = dt.datetime.now(dt.UTC)
    end_dt = end or now
    start_dt = start or (end_dt - dt.timedelta(days=7))
    if start_dt > end_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start must be <= end")
    return start_dt, end_dt


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


def _bucket_expr(granularity: Literal["hour", "day"]):
    # date_trunc is Postgres-specific, which is fine for this container.
    return func.date_trunc(granularity, AnalyticsEvent.ts)


# PUBLIC_INTERFACE
@router.get(
    "/kpis",
    response_model=DashboardKpiResponse,
    summary="Dashboard KPIs",
    description="Returns KPIs (total events, unique users, top event) for a workspace and time range.",
    operation_id="dashboard_kpis",
)
def get_kpis(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    start: Optional[dt.datetime] = Query(default=None, description="Range start (ISO8601)"),
    end: Optional[dt.datetime] = Query(default=None, description="Range end (ISO8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardKpiResponse:
    """Compute KPI metrics for the dashboard."""
    _require_workspace_access(db, current_user.id, workspace_id)
    start_dt, end_dt = _parse_range(start, end)

    total_events = db.execute(
        select(func.count()).select_from(AnalyticsEvent).where(
            AnalyticsEvent.workspace_id == workspace_id,
            AnalyticsEvent.ts >= start_dt,
            AnalyticsEvent.ts <= end_dt,
        )
    ).scalar_one()

    unique_users = db.execute(
        select(func.count(func.distinct(AnalyticsEvent.user_id))).select_from(AnalyticsEvent).where(
            AnalyticsEvent.workspace_id == workspace_id,
            AnalyticsEvent.ts >= start_dt,
            AnalyticsEvent.ts <= end_dt,
            AnalyticsEvent.user_id.is_not(None),
        )
    ).scalar_one()

    top = db.execute(
        select(AnalyticsEvent.name, func.count().label("c"))
        .where(
            AnalyticsEvent.workspace_id == workspace_id,
            AnalyticsEvent.ts >= start_dt,
            AnalyticsEvent.ts <= end_dt,
        )
        .group_by(AnalyticsEvent.name)
        .order_by(func.count().desc())
        .limit(1)
    ).first()

    if top is None:
        return DashboardKpiResponse(total_events=int(total_events), unique_users=int(unique_users), top_event_name=None, top_event_count=0)

    return DashboardKpiResponse(
        total_events=int(total_events),
        unique_users=int(unique_users),
        top_event_name=top[0],
        top_event_count=int(top[1]),
    )


# PUBLIC_INTERFACE
@router.get(
    "/timeseries",
    response_model=DashboardTimeseriesResponse,
    summary="Dashboard timeseries",
    description="Returns event count timeseries for a workspace and time range.",
    operation_id="dashboard_timeseries",
)
def get_timeseries(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    granularity: Literal["hour", "day"] = Query(default="day", description="Timeseries granularity"),
    start: Optional[dt.datetime] = Query(default=None, description="Range start (ISO8601)"),
    end: Optional[dt.datetime] = Query(default=None, description="Range end (ISO8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardTimeseriesResponse:
    """Compute timeseries for the dashboard."""
    _require_workspace_access(db, current_user.id, workspace_id)
    start_dt, end_dt = _parse_range(start, end)

    bucket = _bucket_expr(granularity)
    rows = (
        db.execute(
            select(bucket.label("b"), func.count().label("c"))
            .where(
                AnalyticsEvent.workspace_id == workspace_id,
                AnalyticsEvent.ts >= start_dt,
                AnalyticsEvent.ts <= end_dt,
            )
            .group_by("b")
            .order_by("b")
        )
        .all()
    )

    points = [DashboardTimeseriesPoint(bucket=r[0], count=int(r[1])) for r in rows]
    return DashboardTimeseriesResponse(points=points)


# PUBLIC_INTERFACE
@router.get(
    "/top-events",
    response_model=DashboardTopEventsResponse,
    summary="Top events",
    description="Returns top N event names for a workspace and time range.",
    operation_id="dashboard_top_events",
)
def get_top_events(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    limit: int = Query(default=10, ge=1, le=50, description="Max number of events"),
    start: Optional[dt.datetime] = Query(default=None, description="Range start (ISO8601)"),
    end: Optional[dt.datetime] = Query(default=None, description="Range end (ISO8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardTopEventsResponse:
    """Compute top events for the dashboard."""
    _require_workspace_access(db, current_user.id, workspace_id)
    start_dt, end_dt = _parse_range(start, end)

    rows = (
        db.execute(
            select(AnalyticsEvent.name, func.count().label("c"))
            .where(
                AnalyticsEvent.workspace_id == workspace_id,
                AnalyticsEvent.ts >= start_dt,
                AnalyticsEvent.ts <= end_dt,
            )
            .group_by(AnalyticsEvent.name)
            .order_by(func.count().desc())
            .limit(limit)
        )
        .all()
    )

    items = [DashboardTopEvent(name=r[0], count=int(r[1])) for r in rows]
    return DashboardTopEventsResponse(items=items)


# PUBLIC_INTERFACE
@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard summary",
    description="Convenience endpoint returning KPIs + timeseries + top events in one call.",
    operation_id="dashboard_summary",
)
def get_summary(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    granularity: Literal["hour", "day"] = Query(default="day", description="Timeseries granularity"),
    limit: int = Query(default=10, ge=1, le=50, description="Top events limit"),
    start: Optional[dt.datetime] = Query(default=None, description="Range start (ISO8601)"),
    end: Optional[dt.datetime] = Query(default=None, description="Range end (ISO8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummaryResponse:
    """Aggregate and return all dashboard data needed by the frontend."""
    kpis = get_kpis(workspace_id=workspace_id, start=start, end=end, db=db, current_user=current_user)
    timeseries = get_timeseries(
        workspace_id=workspace_id,
        granularity=granularity,
        start=start,
        end=end,
        db=db,
        current_user=current_user,
    )
    top_events = get_top_events(
        workspace_id=workspace_id, limit=limit, start=start, end=end, db=db, current_user=current_user
    )
    return DashboardSummaryResponse(kpis=kpis, timeseries=timeseries, top_events=top_events)
