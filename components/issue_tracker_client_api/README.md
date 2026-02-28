# Issue Tracker API

## Overview

`issue_tracker_client_api` defines the abstract interface for an issue tracker client: **Client**, **Issue** (card), **Board**, and **Member**. Implementations (e.g. `trello_client_impl`) provide the concrete logic. The design is compatible with [Trello’s REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/) and [object definitions](https://developer.atlassian.com/cloud/trello/guides/rest-api/object-definitions/).

## Purpose

- Document the operations available to consumers.
- Provide a single factory (`get_client`) that implementations override.
- Keep types explicit: `Issue`, `Board`, `Member` in their own modules.

## Architecture

### Component design

- **Client (ABC):** Issue operations (get, delete, mark complete, update status, assign), board operations (get, list), and members-on-card.
- **Issue (ABC):** Issue with required `id`, `title`, `is_complete`.
- **Board (ABC):** Board with `id` and `name`.
- **Member (ABC):** Member with `id`, `username`, and `is_board_member`.

### API integration

```python
from issue_tracker_client_api import Client, get_client, Issue, Board, Member

client: Client = get_client()
for issue in client.get_issues(max_issues=5):
    print(issue.title)
for board in client.get_boards():
    print(board.name)
```

### Dependency injection

Implementations register by replacing the factory at import time:

```python
import trello_client_impl  # rebinds issue_tracker_client_api.get_client
from issue_tracker_client_api import get_client
client = get_client(interactive=False)
```

## API Reference

### Client (abstract)

```python
class Client(ABC):
    def get_issue(self, issue_id: str) -> Issue: ...
    def delete_issue(self, issue_id: str) -> bool: ...
    def get_issues(self, max_issues: int = 10) -> Iterator[Issue]: ...
    def get_board(self, board_id: str) -> Board: ...
    def get_boards(self) -> Iterator[Board]: ...
    def get_lists(self, board_id: str) -> Iterator[List]: ...
    def get_members_on_card(self, issue_id: str) -> list[Member]: ...
    def update_status(self, issue_id: str, status: str) -> bool: ...
    def assign_issue(self, issue_id: str, member_id: str) -> bool: ...
    def create_issue(self, title: str, list_id: str, *, description: str | None = None) -> Issue: ...
```

- **`get_issue(issue_id)`** – Return a single issue.
- **`delete_issue(issue_id)`** – Remove the issue.
- **`update_status(issue_id, status)`** – Update status (e.g. 'todo', 'in_progress', 'complete').
- **`get_issues(max_issues)`** – Yield issues, up to `max_issues`.
- **`get_board(board_id)`** – Return a board by ID.
- **`get_boards()`** – Yield boards (e.g. current user’s boards).
- **`get_lists(board_id)`** – Yield lists on the board.
- **`get_members_on_card(issue_id)`** – Return members assigned to the issue.
- **`assign_issue(issue_id, member_id)`** – Assign a member to an issue.
- **`create_issue(title, list_id, description)`** – Create a new issue in the given list.

### Issue (abstract)

Required: **`id`**, **`title`**, **`is_complete`**

### Board (abstract)

Required: **`id`**, **`name`**

### List (abstract)

Required: **`id`**, **`name`**

### Member (abstract)

Required: **`id`**, **`username`**, **`is_board_member`**.

### Factory

- **`get_client(*, interactive: bool = False) -> Client`** – Returns the registered implementation or raises `NotImplementedError` if none.

## Usage examples

### Basic operations

```python
from issue_tracker_client_api import get_client

client = get_client(interactive=False)
for issue in client.get_issues(max_issues=3):
    print(f"{issue.id}: {issue.title}")
```

### Issue and board

```python
from issue_tracker_client_api import get_client

client = get_client(interactive=False)
issue = client.get_issue("first-issue-in-project")
print(issue.title)
board = client.get_board("board-id")
print(board.name)
```

### Implementation checklist

1. Implement every abstract method on `Client` (issue, board, member methods).
2. Return types compatible with `Issue`, `Board`, and `Member` (e.g. concrete subclasses).
3. Publish a factory (e.g. `get_client_impl`) and assign it to `issue_tracker_client_api.get_client` (e.g. on package import).
4. Honor the `interactive` flag if the implementation supports interactive auth.

## Testing

From the repository root:

```bash
uv run pytest components/issue_tracker_client_api/tests/ -q
uv run pytest components/issue_tracker_client_api/tests/ --cov=src/issue_tracker_client_api --cov-report=term-missing
```
