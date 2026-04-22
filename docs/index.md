# Issue Tracker Client

**OSPSD Team 07** — A component-based issue tracker with an abstract interface, Trello-backed implementation, a deployed FastAPI service, and a service client adapter providing location transparency.

## Overview

This project provides:

- **`issue_tracker_client_api`** — Abstract interface for issue tracker operations (Client, Issue, Board, Member, List)
- **`trello_client_impl`** — Concrete implementation using the [Trello REST API](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/)
- **`issue_tracker_service`** — FastAPI service that wraps the Trello client and exposes it over HTTP with OAuth 1.0a. Also hosts the `/ai/*` routes.
- **`issue_tracker_service_api_client`** — Auto-generated Python client from the service's OpenAPI spec (via `openapi-python-client`)
- **`issue_tracker_adapter`** — Service client adapter that implements the `Client` ABC by delegating to the auto-generated HTTP client
- **`ai_client_api`** *(HW3)* — Provider-agnostic ABC for an AI assistant, plus prompt sanitization helpers
- **`claude_ai_client_impl`** *(HW3)* — Concrete Anthropic Claude implementation with a tool-calling loop and safety-gated tool catalogue

The design supports dependency injection: implementations register at import time, and consumers use a single factory (`get_client`) to obtain the configured client — whether it talks to Trello directly or through the deployed service. The AI integration follows the exact same pattern (see [AI Integration](ai-integration.md)).

## Quick Start

```bash
# Install
uv sync --all-extras
```

### Direct Trello client

```python
import trello_client_impl
from issue_tracker_client_api import get_client, Client

client: Client = get_client(interactive=False)
for board in client.get_boards():
    print(board.name)
```

### Via deployed service (adapter)

```python
from issue_tracker_adapter import register
register()

from issue_tracker_client_api import get_client

client = get_client(
    base_url="https://ospsd-team7-issue-tracker.onrender.com",
    session_token="<session-token-from-oauth>",
)
for board in client.get_boards():
    print(board.name)
```

### Talking to the AI assistant

```bash
curl -X POST https://ospsd-team7-issue-tracker.onrender.com/ai/chat \
  -H "Content-Type: application/json" \
  -H "X-Session-Token: <session-token-from-oauth>" \
  -d '{"prompt":"Summarize the open issues on my main board."}'
```

See [AI Integration](ai-integration.md) for the full contract, safety posture, and examples.

## Project Structure

```
ospsd-team-07/
├── components/
│   ├── issue_tracker_client_api/          # Abstract interface (Client, Issue, Board, Member, List)
│   ├── trello_client_impl/                # Direct Trello implementation
│   ├── issue_tracker_service/             # FastAPI service (OAuth + REST + /ai/*)
│   ├── issue_tracker_service_api_client/  # Auto-generated HTTP client (openapi-python-client)
│   ├── issue_tracker_adapter/             # Service client adapter (Client ABC → HTTP client)
│   ├── ai_client_api/                     # HW3: AIClient ABC + sanitizer + types
│   └── claude_ai_client_impl/             # HW3: Anthropic Claude implementation + tool catalogue
├── tests/
│   ├── integration/                       # DI and interface compliance
│   └── e2e/                               # Full workflow with real API
├── docs/                                  # This documentation
└── pyproject.toml
```

## Documentation

| Section | Description |
|---------|-------------|
| [Architecture](architecture.md) | Component design, dependency injection, and data flow |
| [AI Integration](ai-integration.md) | **HW3** — Claude tool-calling, safety, `/ai/*` endpoints, examples |
| [Deployment](deployment.md) | **HW3** — Render / Vercel / Trello env setup and verification |
| [Issue Tracker Client API](api/issue_tracker_client_api.md) | Abstract interface reference |
| [Trello Client Implementation](api/trello_client_impl.md) | Trello implementation reference |
| [FastAPI Service](api/issue_tracker_service.md) | REST API endpoints, `/ai/*` routes, and auth flow |
| [Service Client Adapter](api/issue_tracker_adapter.md) | Adapter component reference |
| [Code Quality](code-quality.md) | Ruff, mypy, and linting guidelines |
| [CI/CD](ci-cd.md) | CircleCI pipeline, environment variables, Render deploy hook |
