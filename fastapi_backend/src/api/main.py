from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.config import get_settings
from src.api.core.db import SessionLocal
from src.api.core.init_db import check_db, init_db
from src.api.routes.analytics import router as analytics_router
from src.api.routes.auth import router as auth_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.orgs import router as orgs_router

settings = get_settings()

openapi_tags = [
    {"name": "Health", "description": "Service health checks."},
    {"name": "Auth", "description": "Authentication and user profile endpoints."},
    {"name": "Organizations", "description": "Organization and workspace management endpoints."},
    {"name": "Analytics", "description": "Analytics ingestion endpoints."},
    {"name": "Dashboard", "description": "Aggregated dashboard endpoints for the frontend."},
]

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for the Workspace Dashboard Platform.\n\n"
        "Env requirements:\n"
        "- DATABASE_URL: Postgres connection string (postgresql+psycopg://...)\n"
        "- JWT_SECRET_KEY: secret used to sign JWTs\n"
    ),
    version=settings.app_version,
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(orgs_router)
app.include_router(analytics_router)
app.include_router(dashboard_router)


@app.on_event("startup")
def _on_startup() -> None:
    """Initialize DB schema and verify connectivity on startup."""
    init_db()
    db = SessionLocal()
    try:
        check_db(db)
    finally:
        db.close()


# PUBLIC_INTERFACE
@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Simple service health endpoint.",
    operation_id="health_check",
)
def health_check():
    """Return health status."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/docs/help",
    tags=["Health"],
    summary="API usage help",
    description="Quick notes on auth and the main API flows for this backend.",
    operation_id="docs_help",
)
def docs_help():
    """Provide quick help for using this API."""
    return {
        "auth": {
            "register": "POST /auth/register {email,password,name?} -> {access_token}",
            "login": "POST /auth/login {email,password} -> {access_token}",
            "me": "GET /auth/me (Authorization: Bearer <token>)",
        },
        "orgs": {
            "list_orgs": "GET /orgs",
            "create_org": "POST /orgs {name}",
            "list_workspaces": "GET /orgs/{org_id}/workspaces",
            "create_workspace": "POST /orgs/{org_id}/workspaces {name}",
        },
        "analytics": {
            "ingest": "POST /analytics/ingest {workspace_id, events:[{name, ts?, properties?}]}",
        },
        "dashboard": {
            "summary": "GET /dashboard/summary?workspace_id=...&start=...&end=...",
            "kpis": "GET /dashboard/kpis?workspace_id=...&start=...&end=...",
            "timeseries": "GET /dashboard/timeseries?workspace_id=...&granularity=day|hour&start=...&end=...",
            "top_events": "GET /dashboard/top-events?workspace_id=...&limit=10&start=...&end=...",
        },
    }
