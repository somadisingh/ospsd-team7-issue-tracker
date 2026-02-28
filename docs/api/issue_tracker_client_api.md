# Issue Tracker Client API

Abstract interface for an issue tracker client. Defines the `Client` ABC and data types (`Issue`, `Board`, `Member`).

## Overview

`issue_tracker_client_api` defines the abstract interface for an issue tracker client. Implementations (e.g. `trello_client_impl`) provide the concrete logic. The design is compatible with [Trello's REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/) and [object definitions](https://developer.atlassian.com/cloud/trello/guides/rest-api/object-definitions/).

## Client (abstract)

```python
class Client(ABC):
    def get_issue(self, issue_id: str) -> Issue: ...
    def delete_issue(self, issue_id: str) -> bool: ...
    def update_status(self, issue_id: str, status: str) -> bool: ...
    def get_issues(self, max_issues: int = 10) -> Iterator[Issue]: ...
    def get_board(self, board_id: str) -> Board: ...
    def get_boards(self) -> Iterator[Board]: ...
    def get_lists(self, board_id: str) -> Iterator[List]: ...
    def get_members_on_card(self, issue_id: str) -> list[Member]: ...
    def assign_issue(self, issue_id: str, member_id: str) -> bool: ...
    def create_issue(self, title: str, list_id: str, *, description: str | None = None) -> Issue: ...
```

| Method | Description |
|--------|-------------|
| `get_issue(issue_id)` | Return a single issue by ID |
| `delete_issue(issue_id)` | Remove the issue |
| `update_status(issue_id, status)` | Update status (e.g. 'todo', 'in_progress', 'complete') |
| `get_issues(max_issues)` | Yield issues, up to `max_issues` |
| `get_board(board_id)` | Return a board by ID |
| `get_boards()` | Yield boards for the authenticated user |
| `get_lists(board_id)` | Yield lists on the board |
| `get_members_on_card(issue_id)` | Return members assigned to the issue |
| `assign_issue(issue_id, member_id)` | Assign a member to an issue |
| `create_issue(title, list_id, description)` | Create a new issue in the given list |

## Data Types

| Type | Required Fields |
|------|-----------------|
| **Issue** | `id`, `title`, `is_complete` |
| **Board** | `id`, `name` |
| **List** | `id`, `name` |
| **Member** | `id`, `username`, `is_board_member` |

## Factory

```python
def get_client(*, interactive: bool = False) -> Client
```

Returns the registered implementation or raises `NotImplementedError` if none. Implementations register at import time (see [Architecture](../architecture.md#dependency-injection)).
