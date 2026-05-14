# Service Client Adapter

Implements the `issue_tracker_client_api.Client` ABC by delegating to the auto-generated HTTP client (`issue_tracker_service_api_client`). This achieves **location transparency**: consumers program against the same interface whether the implementation talks to Trello directly or through the deployed FastAPI service.

## Overview

`issue_tracker_adapter` wraps the auto-generated client (produced by `openapi-python-client`) behind the original `Client` abstract interface. Consumers never deal with HTTP details — they call the same methods as they would with `trello_client_impl`.

## Usage

```python
from issue_tracker_adapter import register

register()

from issue_tracker_client_api import get_client

client = get_client(
    base_url="https://ospsd-team7-issue-tracker.onrender.com",
    session_token="<session-token-from-oauth-flow>",
)

for board in client.get_boards():
    print(board.name)
```

## Dependency Injection

Calling `register()` replaces the global `get_client` factory in `issue_tracker_client_api` with `issue_tracker_adapter.client.get_client_impl`. After registration, any call to `get_client(base_url=..., session_token=...)` returns a `ServiceClientAdapter` instance.

## Domain Objects

The adapter converts auto-generated response models to domain objects that implement the abstract interfaces:

| Response Model | Adapter Domain Object | Implements |
|---------------|----------------------|------------|
| `BoardResponse` | `ServiceBoard` | `Board` ABC |
| `IssueResponse` | `ServiceIssue` | `Issue` ABC |
| `ListResponse` | `ServiceList` | `List` ABC |
| `MemberResponse` | `ServiceMember` | `Member` ABC |

## Supported Operations

All `Client` ABC methods that the FastAPI service exposes are supported:

| Method | Description |
|--------|-------------|
| `get_board(board_id)` | Get a board by ID |
| `get_boards()` | List all boards |
| `create_board(name)` | Create a new board |
| `get_list(list_id)` | Get a list by ID |
| `create_list(board_id, name)` | Create a new list |
| `get_issue(issue_id)` | Get an issue by ID |
| `get_issues_in_list(list_id)` | List issues in a list |
| `create_issue(title, list_id)` | Create a new issue |
| `update_status(issue_id, status)` | Update issue status |
| `delete_issue(issue_id)` | Delete an issue |
| `get_members_on_issue(issue_id)` | Get assigned members |
| `assign_issue(issue_id, member_id)` | Assign a member |

Methods not exposed by the service (`add_member_to_board`, `get_lists`, `update_list`, `delete_list`, and OAuth methods) raise `NotImplementedError`.

## Architecture

```
Consumer  →  Client ABC  →  ServiceClientAdapter  →  Auto-Generated Client  →  FastAPI Service  →  Trello
```
