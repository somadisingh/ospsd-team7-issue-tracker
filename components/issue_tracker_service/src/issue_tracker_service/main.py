"""FastAPI service exposing the shared issue-tracker API over HTTP.

Implements the vertical's shared Board/Issue contract plus
internal List and Member endpoints.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import issue_tracker_client_api
from api.issue import Status
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from issue_tracker_client_api.exceptions import (
    AuthenticationError,
    IssueTrackerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from trello_client_impl.client import TrelloClient

from .db import get_db, get_session_credentials, init_db
from .routes.auth import _trello_config, router as auth_router
from .routes.health import router as health_router
from .telemetry import setup_telemetry

logger = logging.getLogger(__name__)


def _set_error_kind(request: Request, *, kind: str) -> None:
    """Store domain vs infrastructure error class for telemetry middleware."""
    request.state.error_kind = kind


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="Issue Tracker Service",
    version="0.3.0",
    lifespan=lifespan,
)

# Allow the deployed frontend (and local dev server) to call us. The
# actual origins list is read from CORS_ALLOW_ORIGINS (comma-separated);
# we default to the local Next.js dev host so `npm run dev` works.
_cors_origins = [
    origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
# AI router is included lazily so tests that don't need it don't force-import
# the Anthropic SDK.
try:  # pragma: no cover - exercised via integration tests
    from .routes.ai import router as ai_router

    app.include_router(ai_router)
except ImportError as _ai_import_err:  # pragma: no cover
    logger.warning("AI router not loaded: %s", _ai_import_err)

# ------------------------------------------------------------------ #
# Exception handlers
# ------------------------------------------------------------------ #


@app.exception_handler(ResourceNotFoundError)
async def _resource_not_found_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    _set_error_kind(request, kind="domain")
    logger.warning("Resource not found: %s", exc)
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(AuthenticationError)
async def _authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    _set_error_kind(request, kind="domain")
    logger.warning("Upstream authentication error: %s", exc)
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(ServiceUnavailableError)
async def _service_unavailable_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    _set_error_kind(request, kind="infrastructure")
    logger.error("Upstream service unavailable: %s", exc)
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(IssueTrackerError)
async def _issue_tracker_error_handler(request: Request, exc: IssueTrackerError) -> JSONResponse:
    _set_error_kind(request, kind="infrastructure")
    logger.error("Issue tracker error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Upstream service error: {exc}"},
    )


# ------------------------------------------------------------------ #
# Response / request models
# ------------------------------------------------------------------ #


class BoardResponse(BaseModel):
    id: str
    board_name: str


class IssueResponse(BaseModel):
    id: str
    title: str
    desc: str
    members: list[str] | None = None
    due_date: str | None = None
    status: str
    board_id: str


class ListResponse(BaseModel):
    id: str
    name: str
    board_id: str


class MemberResponse(BaseModel):
    id: str
    username: str


class CreateBoardRequest(BaseModel):
    name: str


class UpdateBoardRequest(BaseModel):
    name: str | None = None


class CreateIssueRequest(BaseModel):
    title: str
    board_id: str
    desc: str | None = None
    members: list[str] | None = None
    due_date: str | None = None
    status: str = Status.TO_DO.value


class UpdateIssueRequest(BaseModel):
    title: str | None = None
    desc: str | None = None
    members: list[str] | None = None
    due_date: str | None = None
    status: str | None = None
    board_id: str | None = None


class CreateListRequest(BaseModel):
    board_id: str
    name: str


class UpdateListRequest(BaseModel):
    name: str


class AddMemberToBoardRequest(BaseModel):
    member_id: str


class AssignIssueRequest(BaseModel):
    member_id: str


# ------------------------------------------------------------------ #
# Converters
# ------------------------------------------------------------------ #


def _board_to_response(board: issue_tracker_client_api.Board) -> BoardResponse:
    return BoardResponse(id=board.id, board_name=board.board_name)


def _issue_to_response(issue: issue_tracker_client_api.Issue) -> IssueResponse:
    return IssueResponse(
        id=issue.id,
        title=issue.title,
        desc=issue.desc,
        members=issue.members,
        due_date=issue.due_date,
        status=issue.status.value,
        board_id=issue.board_id,
    )


def _list_to_response(list_obj: issue_tracker_client_api.List) -> ListResponse:
    return ListResponse(id=list_obj.id, name=list_obj.name, board_id=list_obj.board_id or "")


def _member_to_response(member: issue_tracker_client_api.Member) -> MemberResponse:
    return MemberResponse(
        id=member.id,
        username=member.username or "",
    )


# ------------------------------------------------------------------ #
# Auth dependency
# ------------------------------------------------------------------ #


def get_authenticated_client(
    x_session_token: str = Header(..., alias="X-Session-Token"),
    db: Session = Depends(get_db),
) -> TrelloClient:
    creds = get_session_credentials(db, x_session_token)
    if not creds:
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

    config = _trello_config()
    return TrelloClient(
        api_key=config["api_key"],
        secret=config["secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )


# ------------------------------------------------------------------ #
# Board endpoints  (shared API)
# ------------------------------------------------------------------ #


@app.get("/boards", response_model=list[BoardResponse])
async def list_boards(client: TrelloClient = Depends(get_authenticated_client)) -> list[BoardResponse]:
    return [_board_to_response(board) for board in client.get_boards()]


@app.get("/boards/{board_id}", response_model=BoardResponse)
async def get_board(board_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> BoardResponse:
    return _board_to_response(client.get_board(board_id))


@app.post("/boards", response_model=BoardResponse)
async def create_board(
    req: CreateBoardRequest, client: TrelloClient = Depends(get_authenticated_client)
) -> BoardResponse:
    return _board_to_response(client.create_board(name=req.name))


@app.put("/boards/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: str,
    body: UpdateBoardRequest,
    client: TrelloClient = Depends(get_authenticated_client),
) -> BoardResponse:
    return _board_to_response(client.update_board(board_id=board_id, name=body.name))


@app.delete("/boards/{board_id}", response_model=dict[str, bool])
async def delete_board(board_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> dict[str, bool]:
    return {"success": client.delete_board(board_id)}


# ------------------------------------------------------------------ #
# Issue endpoints  (shared API)
# ------------------------------------------------------------------ #


@app.get("/boards/{board_id}/issues", response_model=list[IssueResponse])
async def get_issues(board_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> list[IssueResponse]:
    return [_issue_to_response(issue) for issue in client.get_issues(board_id)]


@app.get("/issues/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> IssueResponse:
    return _issue_to_response(client.get_issue(issue_id))


@app.post("/issues", response_model=IssueResponse)
async def create_issue(
    req: CreateIssueRequest, client: TrelloClient = Depends(get_authenticated_client)
) -> IssueResponse:
    status = Status(req.status)
    return _issue_to_response(
        client.create_issue(
            title=req.title,
            board_id=req.board_id,
            desc=req.desc,
            members=req.members,
            due_date=req.due_date,
            status=status,
        )
    )


@app.put("/issues/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: str,
    body: UpdateIssueRequest,
    client: TrelloClient = Depends(get_authenticated_client),
) -> IssueResponse:
    status = Status(body.status) if body.status is not None else None
    return _issue_to_response(
        client.update_issue(
            issue_id=issue_id,
            title=body.title,
            desc=body.desc,
            members=body.members,
            due_date=body.due_date,
            status=status,
            board_id=body.board_id,
        )
    )


@app.delete("/issues/{issue_id}", response_model=dict[str, bool])
async def delete_issue(issue_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> dict[str, bool]:
    return {"success": client.delete_issue(issue_id)}


# ------------------------------------------------------------------ #
# Internal List endpoints
# ------------------------------------------------------------------ #


@app.get("/boards/{board_id}/lists", response_model=list[ListResponse])
async def get_lists(board_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> list[ListResponse]:
    return [_list_to_response(lst) for lst in client.get_lists(board_id)]


@app.get("/lists/{list_id}", response_model=ListResponse)
async def get_list(list_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> ListResponse:
    return _list_to_response(client.get_list(list_id))


@app.post("/lists", response_model=ListResponse)
async def create_list(req: CreateListRequest, client: TrelloClient = Depends(get_authenticated_client)) -> ListResponse:
    return _list_to_response(client.create_list(board_id=req.board_id, name=req.name))


@app.put("/lists/{list_id}", response_model=ListResponse)
async def update_list(
    list_id: str,
    body: UpdateListRequest,
    client: TrelloClient = Depends(get_authenticated_client),
) -> ListResponse:
    return _list_to_response(client.update_list(list_id=list_id, name=body.name))


@app.delete("/lists/{list_id}", response_model=dict[str, bool])
async def delete_list(list_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> dict[str, bool]:
    return {"success": client.delete_list(list_id)}


@app.get("/lists/{list_id}/issues", response_model=list[IssueResponse])
async def get_issues_in_list(
    list_id: str,
    max_issues: int = Query(100, ge=1, le=500),
    client: TrelloClient = Depends(get_authenticated_client),
) -> list[IssueResponse]:
    return [_issue_to_response(issue) for issue in client.get_issues_in_list(list_id=list_id, max_issues=max_issues)]


# ------------------------------------------------------------------ #
# Internal Member endpoints
# ------------------------------------------------------------------ #


@app.post("/boards/{board_id}/members", response_model=dict[str, bool])
async def add_member_to_board(
    board_id: str,
    body: AddMemberToBoardRequest,
    client: TrelloClient = Depends(get_authenticated_client),
) -> dict[str, bool]:
    return {"success": client.add_member_to_board(board_id=board_id, member_id=body.member_id)}


@app.get("/issues/{issue_id}/members", response_model=list[MemberResponse])
async def get_issue_members(
    issue_id: str, client: TrelloClient = Depends(get_authenticated_client)
) -> list[MemberResponse]:
    return [_member_to_response(m) for m in client.get_members_on_issue(issue_id)]


@app.post("/issues/{issue_id}/assign", response_model=dict[str, bool])
async def assign_issue(
    issue_id: str, body: AssignIssueRequest, client: TrelloClient = Depends(get_authenticated_client)
) -> dict[str, bool]:
    success = client.assign_issue(issue_id=issue_id, member_id=body.member_id)
    return {"success": success}


setup_telemetry(app)
