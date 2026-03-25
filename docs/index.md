# Issue Tracker Client

**OSPSD Team 07** — An abstract interface and Trello-backed implementation for an issue tracker client.

## Overview

This project provides:

- **`issue_tracker_client_api`** — Abstract interface for issue tracker operations (Client, Issue, Board, Member)
- **`trello_client_impl`** — Concrete implementation using the [Trello REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/)

The design supports dependency injection: implementations register at import time, and consumers use a single factory (`get_client`) to obtain the configured client.

## Quick Start

```bash
# Install
uv sync --all-extras

# Use the client
```

```python
import trello_client_impl
from issue_tracker_client_api import get_client, Client

client: Client = get_client(interactive=False)
for board in client.get_boards():
    for lst in client.get_lists(board.id):
        for issue in client.get_issues_in_list(lst.id, max_issues=100):
            print(issue.title)
```

## Project Structure

```
ospsd-team-07/
├── components/
│   ├── issue_tracker_client_api/   # Abstract interface (Client, Issue, Board, Member)
│   └── trello_client_impl/         # Trello implementation
├── tests/
│   ├── integration/                # DI and interface compliance
│   └── e2e/                        # Full workflow with real API
├── docs/                           # This documentation
└── pyproject.toml
```

## Documentation

| Section | Description |
|---------|-------------|
| [Architecture](architecture.md) | Component design, dependency injection, and data flow |
| [API Reference](api/issue_tracker_client_api.md) | Interface and Trello implementation API docs |
| [Code Quality](code-quality.md) | Ruff, mypy, and linting guidelines |
| [CI/CD](ci-cd.md) | CircleCI pipeline and local parity |
