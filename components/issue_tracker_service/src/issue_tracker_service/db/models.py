"""ORM models for persistent application state."""

from __future__ import annotations

import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserSessionModel(Base):
    """Stores Trello OAuth access tokens per server-issued session id."""

    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    access_token: Mapped[str] = mapped_column(Text)
    access_token_secret: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
