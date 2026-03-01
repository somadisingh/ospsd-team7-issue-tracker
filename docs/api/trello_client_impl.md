# Trello Client Implementation

Concrete implementation of the issue tracker API using the [Trello REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/).

## Overview

`trello_client_impl` provides a concrete `issue_tracker_client_api.Client` backed by Trello's REST API. It returns `TrelloCard` (Issue), `TrelloBoard` (Board), and `TrelloMember` (Member) objects.

## TrelloClient

Implements `issue_tracker_client_api.Client`.

### Issue / Card methods

| Method | Trello API | Description |
|--------|------------|-------------|
| `get_issue(issue_id: str) -> Issue` | GET /cards/{id} | Single issue |
| `create_issue(title, list_id, description) -> Issue` | POST /cards | Create issue in list |
| `delete_issue(issue_id: str) -> bool` | PUT (archive) + DEL /cards/{id} | Archive then delete |
| `update_status(issue_id, status) -> bool` | PUT /cards/{id} | Move card to list for status (via idList) |
| `assign_issue(issue_id, member_id) -> bool` | POST /cards/{id}/idMembers | Add member to issue |

### Board and list methods

| Method | Trello API | Description |
|--------|------------|-------------|
| `get_board(board_id: str) -> Board` | GET /boards/{id} | Single board |
| `get_boards() -> Iterator[Board]` | GET /members/me/boards | Current user's boards |
| `create_board(name: str) -> Board` | POST /boards | Create board |
| `add_member_to_board(board_id, member_id: str) -> bool` | PUT /boards/{id}/members/{idMember} | Add member to board |
| `get_list(list_id: str) -> List` | GET /lists/{id} | Single list |
| `get_lists(board_id: str) -> Iterator[List]` | GET /boards/{id}/lists | Lists on a board |
| `get_issues_in_list(list_id, max_issues) -> Iterator[Issue]` | GET /lists/{id}/cards | Issues in list |
| `create_list(board_id, name) -> List` | POST /lists | Create list on board |
| `update_list(list_id, name) -> List` | PUT /lists/{id} | Rename list |
| `delete_list(list_id: str) -> bool` | PUT /lists/{id} | Archive list (closed: true) |

### Member methods

| Method | Trello API | Description |
|--------|------------|-------------|
| `get_members_on_issue(issue_id: str) -> list[Member]` | GET /cards/{id}/members | Members on an issue |

## Data Types

| Type | API contract | Description |
|-----|--------------|-------------|
| `TrelloCard` | `Issue` | Issue (id, title, is_complete, list_id, board_id; maps Trello dueComplete) |
| `TrelloBoard` | `Board` | Board (id, name) |
| `TrelloList` | `List` | List (id, name, board_id) |
| `TrelloMember` | `Member` | Member (id, username, is_board_member; maps Trello confirmed) |

## Factory

- **`get_client_impl(*, interactive: bool = False) -> Client`** — Returns a `TrelloClient`. Assigned to `issue_tracker_client_api.get_client` on package import.

## Authentication

- **Environment:** `TRELLO_API_KEY`, `TRELLO_TOKEN`
- **File:** `token.json` (key `"token"`) in the current directory
- **Priority:** `TRELLO_TOKEN` → `token.json` → error if missing
