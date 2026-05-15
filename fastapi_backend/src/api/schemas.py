import datetime as dt
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field, EmailStr


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field(default="bearer", description="Token type (bearer).")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., min_length=8, description="User password (min 8 chars).")
    name: Optional[str] = Field(default=None, description="Display name.")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., description="User password.")


class UserResponse(BaseModel):
    id: uuid.UUID = Field(..., description="User ID.")
    email: EmailStr = Field(..., description="Email.")
    name: Optional[str] = Field(default=None, description="Display name.")

    class Config:
        from_attributes = True


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Organization name.")


class OrganizationResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Organization ID.")
    name: str = Field(..., description="Organization name.")

    class Config:
        from_attributes = True


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Workspace name.")


class WorkspaceResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Workspace ID.")
    organization_id: uuid.UUID = Field(..., description="Owning organization ID.")
    name: str = Field(..., description="Workspace name.")

    class Config:
        from_attributes = True


class AnalyticsIngestEvent(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Event name.")
    ts: Optional[dt.datetime] = Field(
        default=None,
        description="Event timestamp (ISO8601). If omitted, server time will be used.",
    )
    properties: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary JSON properties.")


class AnalyticsIngestRequest(BaseModel):
    workspace_id: uuid.UUID = Field(..., description="Target workspace ID.")
    events: List[AnalyticsIngestEvent] = Field(..., min_length=1, description="List of events to ingest.")


class AnalyticsIngestResponse(BaseModel):
    ingested: int = Field(..., description="Number of ingested events.")


class DashboardKpiResponse(BaseModel):
    total_events: int = Field(..., description="Total events in range.")
    unique_users: int = Field(..., description="Distinct users seen in range.")
    top_event_name: Optional[str] = Field(default=None, description="Most frequent event name in range.")
    top_event_count: int = Field(default=0, description="Count for top event.")


class DashboardTimeseriesPoint(BaseModel):
    bucket: dt.datetime = Field(..., description="Bucket timestamp (UTC).")
    count: int = Field(..., description="Event count in bucket.")


class DashboardTimeseriesResponse(BaseModel):
    points: List[DashboardTimeseriesPoint] = Field(..., description="Timeseries points.")


class DashboardTopEvent(BaseModel):
    name: str = Field(..., description="Event name.")
    count: int = Field(..., description="Event count.")


class DashboardTopEventsResponse(BaseModel):
    items: List[DashboardTopEvent] = Field(..., description="Top events.")


class DashboardSummaryResponse(BaseModel):
    kpis: DashboardKpiResponse = Field(..., description="KPI summary.")
    timeseries: DashboardTimeseriesResponse = Field(..., description="Timeseries.")
    top_events: DashboardTopEventsResponse = Field(..., description="Top events breakdown.")
