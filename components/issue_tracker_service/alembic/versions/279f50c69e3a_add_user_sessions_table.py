"""add_user_sessions_table

Revision ID: 279f50c69e3a
Revises:
Create Date: 2026-04-21 21:18:33.192464

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "279f50c69e3a"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ``user_sessions`` for Trello OAuth tokens keyed by server session id."""
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_token", sa.String(length=64), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("access_token_secret", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_sessions_session_token",
        "user_sessions",
        ["session_token"],
        unique=True,
    )


def downgrade() -> None:
    """Drop ``user_sessions``."""
    op.drop_index("ix_user_sessions_session_token", table_name="user_sessions")
    op.drop_table("user_sessions")
