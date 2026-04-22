"""Health check and root endpoints."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


def _check_database() -> bool:
    """Attempt a lightweight ``SELECT 1`` against the configured database.

    Returns ``True`` when the query succeeds, ``False`` otherwise.
    """
    from issue_tracker_service.db import get_db

    db_gen = get_db()
    try:
        session = next(db_gen)
        session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        try:
            db_gen.close()
        except Exception:
            pass


@router.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint for liveness probes.

    When a database is configured (``DATABASE_URL`` is set), verifies
    connectivity by executing ``SELECT 1``.

    Returns:
        200 with ``{"status": "ok", "database": "connected"}`` when DB is reachable.
        503 with ``{"status": "degraded", "database": "unavailable"}`` when DB is unreachable.
        200 with ``{"status": "ok"}`` when no ``DATABASE_URL`` is configured (local dev).
    """
    # If DATABASE_URL is not configured, return simple OK (local dev fallback)
    if not os.environ.get("DATABASE_URL"):
        return JSONResponse(status_code=200, content={"status": "ok"})

    try:
        if _check_database():
            return JSONResponse(
                status_code=200,
                content={"status": "ok", "database": "connected"},
            )
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable"},
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable"},
        )
