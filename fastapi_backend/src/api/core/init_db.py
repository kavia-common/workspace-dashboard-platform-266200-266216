from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.models import Base
from src.api.core.db import engine


def init_db() -> None:
    """Initialize database schema.

    For MVP simplicity, we auto-create tables if they don't exist.
    In more mature setups, this should be replaced by migrations (Alembic).
    """
    Base.metadata.create_all(bind=engine)


def check_db(db: Session) -> None:
    """Run a lightweight DB connectivity check."""
    db.execute(text("SELECT 1"))
