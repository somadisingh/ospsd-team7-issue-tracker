"""Health check and root endpoints."""

from typing import Dict

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


@router.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint for liveness probes.

    Returns:
        {"status": "ok"} if service is healthy.
    """
    return {"status": "ok"}
