# Trello Client Implementation

## Overview

`trello_client_impl` provides a concrete `issue_tracker_client_api.Client` backed by the [Trello REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/). It returns `TrelloCard` (Issue), `TrelloBoard` (Board), and `TrelloMember` (Member) objects that align with [Trello's object definitions](https://developer.atlassian.com/cloud/trello/guides/rest-api/object-definitions/).

## Purpose

- **Trello API integration:** Uses Trello's Cards, Boards, and Members endpoints.
- **Token-based auth:** Authenticates via API key + token (environment or `token.json`).
- **Full Client implementation:** Implements all abstract `Client` methods (issues, boards, lists CRUD, members).
- **Dependency injection:** Registers itself as the `get_client` implementation on import.

## Architecture

### Authentication

- **`interactive=False`:** Use environment variables or existing `token.json`. Preferred for CI/CD and scripts.
- **`interactive=True`:** Reserved for future browser OAuth flow; currently same as above.

**Credential priority:** `TRELLO_TOKEN` → `token.json` (current directory, key `"token"`) → error if missing.

**Required environment variables:**

- `TRELLO_API_KEY` – Your Trello API key.
- `TRELLO_TOKEN` – Your Trello token (or provide via `token.json`).

### Dependency injection

```python
import trello_client_impl  # rebinds the factory

from issue_tracker_client_api import get_client
client = get_client(interactive=False)
```

## API Reference

### Types

| Type          | API contract        | Description                                      |
|---------------|---------------------|--------------------------------------------------|
| `TrelloCard`  | `Issue`             | Issue (id, title, is_complete) |
| `TrelloBoard` | `Board`             | Board (id, name)       |
| `TrelloList`  | `List`              | List (id, name); maps to Trello lists (columns). |
| `TrelloMember`| `Member`            | Member (id, username, is_board_member) |

### TrelloClient

Implements `issue_tracker_client_api.Client`. Constructor accepts **`status_list_ids: dict[str, str]`** (status name → list ID) so **`update_status(issue_id, status)`** moves the issue to the corresponding list.

#### Issue methods

- **`get_issue(issue_id: str) -> Issue`** – Single issue (GET /cards/{id}).
- **`delete_issue(issue_id: str) -> bool`** – Archive then delete (PUT + DEL /cards/{id}).
- **`create_issue(title, list_id, description=None) -> Issue`** – Create issue (POST /cards).
- **`update_status(issue_id, status) -> bool`** – Move issue to the list for that status (PUT /cards/{id}, idList).
- **`assign_issue(issue_id, member_id) -> bool`** – Add member (POST /cards/{id}/idMembers).

#### Board methods

- **`get_board(board_id: str) -> Board`** – Single board (GET /boards/{id}).
- **`get_boards() -> Iterator[Board]`** – Current user’s boards (GET /members/me/boards).
- **`create_board(name: str) -> Board`** – Create board (POST /boards).
- **`add_member_to_board(board_id, member_id: str) -> Member`** – Add member to board (PUT /boards/{id}/members/{idMember}), then return member (GET /members/{id}). Members are existing Trello users.

#### List methods (status columns)

- **`get_list(list_id: str) -> List`** – Single list (GET /lists/{id}).
- **`get_lists(board_id: str) -> Iterator[List]`** – Lists on board (GET /boards/{id}/lists).
- **`get_issues_in_list(list_id, max_issues=100) -> Iterator[Issue]`** – Issues in list (GET /lists/{id}/cards).
- **`create_list(board_id, name) -> List`** – Create list (POST /lists); adds a status column.
- **`update_list(list_id, name) -> List`** – Rename list (PUT /lists/{id}).
- **`delete_list(list_id: str) -> bool`** – Archive list (PUT /lists/{id}, closed: true).

#### Member methods

- **`get_members_on_issue(issue_id: str) -> list[Member]`** – Members on an issue (GET /cards/{id}/members).

### Factory

- **`get_client_impl(*, interactive: bool = False) -> Client`** – Returns a `TrelloClient` and is assigned to `issue_tracker_client_api.get_client` on import.

## Usage examples

### Basic issue retrieval by list

```python
import trello_client_impl
from issue_tracker_client_api import get_client

client = get_client(interactive=False)
for lst in client.get_lists(board_id):
    for issue in client.get_issues_in_list(lst.id, max_issues=100):
        print(f"{issue.id}: {issue.title} (complete={issue.is_complete})")
```

### Card with Trello fields

```python
import trello_client_impl
from issue_tracker_client_api import get_client

client = get_client(interactive=False)
issue = client.get_issue("issue-id")
print(issue.title)
```

### Boards and members

```python
import trello_client_impl
from issue_tracker_client_api import get_client

client = get_client(interactive=False)
for board in client.get_boards():
    print(board.id, board.name, board.url)
b = client.get_board("board-id")

members = client.get_members_on_issue("issue-id")
for m in members:
    print(m.id, m.username)
```