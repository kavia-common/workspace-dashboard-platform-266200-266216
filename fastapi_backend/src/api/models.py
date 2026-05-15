import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """Authenticated user."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC))

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    events = relationship("AnalyticsEvent", back_populates="user")


class Organization(Base):
    """Organization (tenant)."""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC))

    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    memberships = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")


class Workspace(Base):
    """Workspace within an organization."""

    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.UTC))

    organization = relationship("Organization", back_populates="workspaces")
    events = relationship("AnalyticsEvent", back_populates="workspace")

    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_workspace_org_name"),)


class Membership(Base):
    """User membership in an organization with a role."""

    __tablename__ = "memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False, default="member")  # admin | member

    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")

    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),)


class AnalyticsEvent(Base):
    """Raw analytics event ingested from clients."""

    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(200), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: dt.datetime.now(dt.UTC))
    properties = Column(JSON, nullable=False, default=dict)

    workspace = relationship("Workspace", back_populates="events")
    user = relationship("User", back_populates="events")


Index("ix_events_workspace_ts", AnalyticsEvent.workspace_id, AnalyticsEvent.ts)
