from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import issue_tracker_client_api
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from trello_client_impl.client import TrelloClient


app = FastAPI(title="Issue Tracker Service", version="0.1.0")

# In-memory state (mini-demo). Replace with per-user DB for production.
oauth1_request_secrets: Dict[str, str] = {}
user_sessions: Dict[str, Dict[str, str]] = {}


def _trello_config() -> Dict[str, str]:
    from os import environ

    try:
        return {
            "api_key": environ["TRELLO_API_KEY"],
            "secret": environ["TRELLO_API_SECRET"],
            "callback_url": environ.get("TRELLO_CALLBACK_URL", "http://localhost:8000/auth/callback"),
        }
    except KeyError as exc:
        raise RuntimeError("Missing Trello OAuth credentials in environment") from exc


def _board_to_response(board: issue_tracker_client_api.Board) -> BoardResponse:
    return BoardResponse(id=board.id, name=board.name)


def _list_to_response(list_obj: issue_tracker_client_api.List) -> ListResponse:
    return ListResponse(id=list_obj.id, name=list_obj.name, board_id=list_obj.board_id or "")


def _issue_to_response(issue: issue_tracker_client_api.Issue) -> IssueResponse:
    return IssueResponse(
        id=issue.id,
        title=issue.title,
        list_id=issue.list_id,
        board_id=issue.board_id or "",
        is_complete=issue.is_complete,
    )


def _member_to_response(member: issue_tracker_client_api.Member) -> MemberResponse:
    return MemberResponse(id=member.id, full_name=member.full_name, username=member.username)


class BoardResponse(BaseModel):
    id: str
    name: str
    url: Optional[str] = None


class ListResponse(BaseModel):
    id: str
    name: str
    board_id: str


class IssueResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    list_id: str
    board_id: str
    is_complete: bool


class MemberResponse(BaseModel):
    id: str
    full_name: str
    username: str


class CreateBoardRequest(BaseModel):
    name: str


class CreateListRequest(BaseModel):
    board_id: str
    name: str


class CreateIssueRequest(BaseModel):
    title: str
    list_id: str
    description: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str


class AuthCallbackResponse(BaseModel):
    session_token: str
    session_user_token: str


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/auth/login")
async def auth_login() -> RedirectResponse:
    config = _trello_config()
    client = TrelloClient(api_key=config["api_key"], secret=config["secret"])
    auth_url = client.get_authorization_url(callback_url=config["callback_url"])
    parsed = parse_qs(urlparse(auth_url).query)
    request_token = parsed.get("oauth_token", [None])[0]
    if not request_token:
        raise HTTPException(status_code=500, detail="Failed to fetch oauth_token from Trello")

    if not client.request_token_secret:
        raise HTTPException(status_code=500, detail="Missing request token secret from Trello client")

    oauth1_request_secrets[request_token] = client.request_token_secret

    return RedirectResponse(auth_url)


@app.get("/auth/callback", response_model=AuthCallbackResponse)
async def auth_callback(
    oauth_token: str = Query(...),
    oauth_verifier: str = Query(...),
) -> AuthCallbackResponse:
    config = _trello_config()
    request_token_secret = oauth1_request_secrets.pop(oauth_token, None)
    if not request_token_secret:
        raise HTTPException(status_code=400, detail="Unknown or expired oauth_token")

    client = TrelloClient(
        api_key=config["api_key"],
        secret=config["secret"],
        request_token_secret=request_token_secret,
    )
    client._request_token = oauth_token
    client.exchange_request_token(oauth_token=oauth_token, oauth_verifier=oauth_verifier)

    if not client.token or not client._access_token_secret:
        raise HTTPException(status_code=500, detail="Failed to obtain access token")

    session_token = uuid4().hex
    user_sessions[session_token] = {
        "access_token": client.token,
        "access_token_secret": client._access_token_secret,
    }

    return AuthCallbackResponse(session_token=session_token, session_user_token=client.token)


def get_authenticated_client(x_session_token: str = Header(..., alias="X-Session-Token")) -> TrelloClient:
    config = _trello_config()
    session = user_sessions.get(x_session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

    return TrelloClient(
        api_key=config["api_key"],
        secret=config["secret"],
        access_token=session["access_token"],
        access_token_secret=session["access_token_secret"],
    )


@app.get("/boards", response_model=List[BoardResponse])
async def list_boards(client: TrelloClient = Depends(get_authenticated_client)) -> list[BoardResponse]:
    return [_board_to_response(board) for board in client.get_boards()]


@app.get("/boards/{board_id}", response_model=BoardResponse)
async def get_board(board_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> BoardResponse:
    board = client.get_board(board_id)
    return _board_to_response(board)


@app.post("/boards", response_model=BoardResponse)
async def create_board(
    req: CreateBoardRequest, client: TrelloClient = Depends(get_authenticated_client)
) -> BoardResponse:
    board = client.create_board(name=req.name)
    return _board_to_response(board)


@app.get("/lists/{list_id}", response_model=ListResponse)
async def get_list(list_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> ListResponse:
    lst = client.get_list(list_id)
    return _list_to_response(lst)


@app.post("/lists", response_model=ListResponse)
async def create_list(req: CreateListRequest, client: TrelloClient = Depends(get_authenticated_client)) -> ListResponse:
    lst = client.create_list(board_id=req.board_id, name=req.name)
    return _list_to_response(lst)


@app.get("/lists/{list_id}/issues", response_model=List[IssueResponse])
async def get_issues_in_list(
    list_id: str,
    max_issues: int = Query(100, ge=1, le=500),
    client: TrelloClient = Depends(get_authenticated_client),
) -> list[IssueResponse]:
    return [_issue_to_response(issue) for issue in client.get_issues_in_list(list_id=list_id, max_issues=max_issues)]


@app.get("/issues/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> IssueResponse:
    issue = client.get_issue(issue_id)
    return _issue_to_response(issue)


@app.post("/issues", response_model=IssueResponse)
async def create_issue(req: CreateIssueRequest, client: TrelloClient = Depends(get_authenticated_client)) -> IssueResponse:
    issue = client.create_issue(title=req.title, list_id=req.list_id, description=req.description)
    return _issue_to_response(issue)


@app.put("/issues/{issue_id}/status", response_model=Dict[str, bool])
async def update_issue_status(
    issue_id: str,
    body: UpdateStatusRequest,
    client: TrelloClient = Depends(get_authenticated_client),
) -> Dict[str, bool]:
    success = client.update_status(issue_id=issue_id, status=body.status)
    return {"success": success}


@app.delete("/issues/{issue_id}", response_model=Dict[str, bool])
async def delete_issue(issue_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> Dict[str, bool]:
    result = client.delete_issue(issue_id)
    return {"success": result}


@app.get("/issues/{issue_id}/members", response_model=List[MemberResponse])
async def get_issue_members(issue_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> list[MemberResponse]:
    members = client.get_members_on_issue(issue_id)
    return [_member_to_response(m) for m in members]


@app.post("/issues/{issue_id}/assign", response_model=Dict[str, bool])
async def assign_issue(issue_id: str, member_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> Dict[str, bool]:
    success = client.assign_issue(issue_id=issue_id, member_id=member_id)
    return {"success": success}
