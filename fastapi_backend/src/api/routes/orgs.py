import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.core.auth import get_current_user
from src.api.core.db import get_db
from src.api.models import Membership, Organization, User, Workspace
from src.api.schemas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    WorkspaceCreateRequest,
    WorkspaceResponse,
)

router = APIRouter(prefix="/orgs", tags=["Organizations"])


def _require_org_membership(db: Session, user_id: uuid.UUID, org_id: uuid.UUID) -> Membership:
    membership = db.execute(
        select(Membership).where(Membership.user_id == user_id, Membership.organization_id == org_id)
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    return membership


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List my organizations",
    description="Returns organizations the current user belongs to.",
    operation_id="orgs_list",
)
def list_orgs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrganizationResponse]:
    """List orgs for current user."""
    orgs = (
        db.execute(
            select(Organization)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == current_user.id)
            .order_by(Organization.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [OrganizationResponse.model_validate(o) for o in orgs]


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Creates a new organization and makes the current user an admin member.",
    operation_id="orgs_create",
)
def create_org(
    payload: OrganizationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """Create org and admin membership."""
    org = Organization(name=payload.name)
    db.add(org)
    db.flush()  # obtain org.id

    membership = Membership(user_id=current_user.id, organization_id=org.id, role="admin")
    db.add(membership)

    db.commit()
    db.refresh(org)
    return OrganizationResponse.model_validate(org)


# PUBLIC_INTERFACE
@router.get(
    "/{org_id}/workspaces",
    response_model=list[WorkspaceResponse],
    summary="List workspaces",
    description="Lists workspaces for the given organization (requires membership).",
    operation_id="workspaces_list",
)
def list_workspaces(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkspaceResponse]:
    """List workspaces in an org."""
    _require_org_membership(db, current_user.id, org_id)
    workspaces = (
        db.execute(select(Workspace).where(Workspace.organization_id == org_id).order_by(Workspace.created_at.desc()))
        .scalars()
        .all()
    )
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


# PUBLIC_INTERFACE
@router.post(
    "/{org_id}/workspaces",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workspace",
    description="Creates a workspace within an organization (requires membership).",
    operation_id="workspaces_create",
)
def create_workspace(
    org_id: uuid.UUID,
    payload: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    """Create workspace in org."""
    _require_org_membership(db, current_user.id, org_id)

    existing = db.execute(
        select(Workspace).where(Workspace.organization_id == org_id, Workspace.name == payload.name)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace name already exists")

    ws = Workspace(organization_id=org_id, name=payload.name)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return WorkspaceResponse.model_validate(ws)
