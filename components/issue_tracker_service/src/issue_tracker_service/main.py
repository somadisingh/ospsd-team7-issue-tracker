from __future__ import annotations

from typing import Dict, List, Optional

import issue_tracker_client_api
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from trello_client_impl.client import TrelloClient
from .routes.health import router as health_router
from .routes.auth import _trello_config, router as auth_router


app = FastAPI(title="Issue Tracker Service", version="0.1.0")

# Include routers
app.include_router(health_router)
app.include_router(auth_router)

# In-memory state (mini-demo). Replace with per-user DB for production.
user_sessions: Dict[str, Dict[str, str]] = {}


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
    return MemberResponse(
        id=member.id,
        username=member.username or "",
    )


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
    username: str


class CreateBoardRequest(BaseModel):
    name: str


class CreateListRequest(BaseModel):
    board_id: str
    name: str


class UpdateListRequest(BaseModel):
    name: str


class AddMemberToBoardRequest(BaseModel):
    member_id: str


class CreateIssueRequest(BaseModel):
    title: str
    list_id: str
    description: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str


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


@app.post("/boards/{board_id}/members", response_model=Dict[str, bool])
async def add_member_to_board(
    board_id: str,
    body: AddMemberToBoardRequest,
    client: TrelloClient = Depends(get_authenticated_client),
) -> Dict[str, bool]:
    success = client.add_member_to_board(board_id=board_id, member_id=body.member_id)
    return {"success": success}


@app.get("/boards/{board_id}/lists", response_model=List[ListResponse])
async def get_lists(board_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> list[ListResponse]:
    return [_list_to_response(lst) for lst in client.get_lists(board_id)]


@app.get("/lists/{list_id}", response_model=ListResponse)
async def get_list(list_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> ListResponse:
    lst = client.get_list(list_id)
    return _list_to_response(lst)


@app.post("/lists", response_model=ListResponse)
async def create_list(req: CreateListRequest, client: TrelloClient = Depends(get_authenticated_client)) -> ListResponse:
    lst = client.create_list(board_id=req.board_id, name=req.name)
    return _list_to_response(lst)


@app.put("/lists/{list_id}", response_model=ListResponse)
async def update_list(
    list_id: str,
    body: UpdateListRequest,
    client: TrelloClient = Depends(get_authenticated_client),
) -> ListResponse:
    lst = client.update_list(list_id=list_id, name=body.name)
    return _list_to_response(lst)


@app.delete("/lists/{list_id}", response_model=Dict[str, bool])
async def delete_list(list_id: str, client: TrelloClient = Depends(get_authenticated_client)) -> Dict[str, bool]:
    result = client.delete_list(list_id)
    return {"success": result}


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
async def create_issue(
    req: CreateIssueRequest, client: TrelloClient = Depends(get_authenticated_client)
) -> IssueResponse:
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
async def get_issue_members(
    issue_id: str, client: TrelloClient = Depends(get_authenticated_client)
) -> list[MemberResponse]:
    members = client.get_members_on_issue(issue_id)
    return [_member_to_response(m) for m in members]


@app.post("/issues/{issue_id}/assign", response_model=Dict[str, bool])
async def assign_issue(
    issue_id: str, member_id: str, client: TrelloClient = Depends(get_authenticated_client)
) -> Dict[str, bool]:
    success = client.assign_issue(issue_id=issue_id, member_id=member_id)
    return {"success": success}
