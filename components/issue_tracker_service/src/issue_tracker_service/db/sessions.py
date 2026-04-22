"""Persistence for Trello OAuth sessions (per X-Session-Token)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import UserSessionModel


def get_session_credentials(
    db: Session,
    session_token: str,
) -> dict[str, str] | None:
    """Load ``access_token`` and ``access_token_secret`` for a valid session, or None."""
    row = db.scalars(
        select(UserSessionModel).where(UserSessionModel.session_token == session_token)
    ).first()
    if row is None:
        return None
    return {
        "access_token": row.access_token,
        "access_token_secret": row.access_token_secret,
    }


def create_session(
    db: Session,
    *,
    session_token: str,
    access_token: str,
    access_token_secret: str,
) -> None:
    """Store a new server session after OAuth callback."""
    db.add(
        UserSessionModel(
            session_token=session_token,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
    )
    db.commit()
