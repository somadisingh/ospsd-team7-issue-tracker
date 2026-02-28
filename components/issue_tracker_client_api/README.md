# Issue Tracker API

## Overview

`issue_tracker_client_api` defines the abstract interface for an issue tracker client: **Client**, **Issue**, **Board**, and **Member**. Implementations (e.g. `trello_client_impl`) provide the concrete logic. The design is compatible with [Trello’s REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/) and [object definitions](https://developer.atlassian.com/cloud/trello/guides/rest-api/object-definitions/).

## Purpose

- Document the operations available to consumers.
- Provide a single factory (`get_client`) that implementations override.
- Keep types explicit: `Issue`, `Board`, `Member` in their own modules.

## Architecture

### Component design

- **Client (ABC):** Issue operations (get, delete, update status, create, assign), board operations (get, list), list CRUD (get, create, update, delete), and members-on-issue.
- **Issue (ABC):** Issue with required `id`, `title`, `is_complete`.
- **Board (ABC):** Board with `id` and `name`.
- **Member (ABC):** Member with `id`, `username`, and `is_board_member`.

### API integration

```python
from issue_tracker_client_api import Client, get_client, Issue, Board, List, Member

client: Client = get_client()
for board in client.get_boards():
    for lst in client.get_lists(board.id):
        for issue in client.get_issues_in_list(lst.id, max_issues=100):
            print(issue.title)
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
    def get_board(self, board_id: str) -> Board: ...
    def get_boards(self) -> Iterator[Board]: ...
    def create_board(self, name: str) -> Board: ...
    def add_member_to_board(self, board_id: str, member_id: str) -> Member: ...
    def get_list(self, list_id: str) -> List: ...
    def get_lists(self, board_id: str) -> Iterator[List]: ...
    def get_issues_in_list(self, list_id: str, max_issues: int = 100) -> Iterator[Issue]: ...
    def create_list(self, board_id: str, name: str) -> List: ...
    def update_list(self, list_id: str, name: str) -> List: ...
    def delete_list(self, list_id: str) -> bool: ...
    def get_members_on_issue(self, issue_id: str) -> list[Member]: ...
    def update_status(self, issue_id: str, status: str) -> bool: ...
    def assign_issue(self, issue_id: str, member_id: str) -> bool: ...
    def create_issue(self, title: str, list_id: str, *, description: str | None = None) -> Issue: ...
```

- **`get_issue(issue_id)`** – Return a single issue.
- **`delete_issue(issue_id)`** – Remove the issue.
- **`update_status(issue_id, status)`** – Update status (e.g. 'todo', 'in_progress', 'complete'); implementations map status to list/column.
- **`get_board(board_id)`** – Return a board by ID.
- **`get_boards()`** – Yield boards (e.g. current user’s boards).
- **`create_board(name)`** – Create a new board and return it.
- **`add_member_to_board(board_id, member_id)`** – Add an existing member to the board and return the member (members are existing users; they are not created via the API).
- **`get_list(list_id)`** – Return a single list by ID.
- **`get_lists(board_id)`** – Yield lists on the board (status columns).
- **`get_issues_in_list(list_id, max_issues)`** – Yield issues in that list.
- **`create_list(board_id, name)`** – Create a list on the board; updates available statuses.
- **`update_list(list_id, name)`** – Rename a list.
- **`delete_list(list_id)`** – Archive/remove a list.
- **`get_members_on_issue(issue_id)`** – Return members assigned to the issue.
- **`assign_issue(issue_id, member_id)`** – Assign a member to an issue.
- **`create_issue(title, list_id, description)`** – Create a new issue in the given list.

### Issue (abstract)

Required: **`id`**, **`title`**, **`is_complete`**, **`list_id`** (`str` – ID of the list this issue belongs to; use to group issues by list when displaying a board).

**List-centric vs issue-centric:** Use **`get_issues_in_list(list_id)`** to fetch all issues in a list (e.g. one request per column). Each issue also has **`issue.list_id`** so you can show which list an issue belongs to when viewing a single issue (e.g. from **`get_issue()`**).

### Board (abstract)

Required: **`id`**, **`name`**

### List (abstract)

Required: **`id`**, **`name`**, **`board_id`** (`str` – ID of the board this list belongs to).

### Member (abstract)

Required: **`id`**, **`username`**, **`is_board_member`**.

### Factory

- **`get_client(*, interactive: bool = False) -> Client`** – Returns the registered implementation or raises `NotImplementedError` if none.

## Usage examples

### Basic operations

```python
from issue_tracker_client_api import get_client

client = get_client(interactive=False)
for board in client.get_boards():
    for lst in client.get_lists(board.id):
        for issue in client.get_issues_in_list(lst.id, max_issues=100):
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

1. Implement every abstract method on `Client` (issue, board, list CRUD, member methods).
2. Return types compatible with `Issue`, `Board`, `List`, and `Member` (e.g. concrete subclasses).
3. Publish a factory (e.g. `get_client_impl`) and assign it to `issue_tracker_client_api.get_client` (e.g. on package import).
4. Honor the `interactive` flag if the implementation supports interactive auth.

## Testing

From the repository root:

```bash
uv run pytest components/issue_tracker_client_api/tests/ -q
uv run pytest components/issue_tracker_client_api/tests/ --cov=src/issue_tracker_client_api --cov-report=term-missing
```
