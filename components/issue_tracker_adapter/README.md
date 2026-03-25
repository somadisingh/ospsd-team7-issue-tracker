# Issue Tracker Adapter

Service client adapter that implements the `issue_tracker_client_api.Client` ABC by delegating to the auto-generated HTTP client (`issue_tracker_service_client`).

This component achieves **location transparency**: consumers program against the same abstract interface regardless of whether the underlying implementation talks to Trello directly (`trello_client_impl`) or goes through the deployed FastAPI service (this adapter).

## Usage

```python
from issue_tracker_adapter import register

# Switch the global factory to use the service adapter
register()

from issue_tracker_client_api import get_client

client = get_client(
    base_url="https://ospsd-team7-issue-tracker.onrender.com",
    session_token="<session-token-from-oauth-flow>",
)

# All calls now go through the deployed service
for board in client.get_boards():
    print(board.name)
```

## Architecture

```
Consumer  →  Client ABC  →  ServiceClientAdapter  →  Auto-Generated Client  →  FastAPI Service  →  Trello
```
