# Issue Tracker Service (FastAPI)

REST API service that wraps the `issue_tracker_client_api` and exposes Trello operations over HTTP. Deployed on [Render](https://ospsd-team7-issue-tracker.onrender.com).

## Overview

`issue_tracker_service` is a FastAPI application that:

1. Handles **OAuth 1.0a** authentication with Trello via `/auth/login` and `/auth/callback`.
2. Manages per-user sessions (in-memory) keyed by a `session_token`.
3. Exposes CRUD endpoints that delegate to `TrelloClient` (the `issue_tracker_client_api.Client` implementation).

Consumers send the `X-Session-Token` header with every request after authenticating.

## Authentication Flow

```
Browser → GET /auth/login → Redirect to Trello
                                  ↓
Trello → GET /auth/callback?oauth_token=...&oauth_verifier=...
                                  ↓
             ← { "session_token": "..." }
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET | Initiates OAuth flow; redirects to Trello |
| `/auth/callback` | GET | Exchanges tokens; returns `session_token` |

## Board Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/boards` | GET | List all boards for the authenticated user |
| `/boards/{board_id}` | GET | Get a single board by ID |
| `/boards` | POST | Create a new board (`{"name": "..."}`) |

## List Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/lists/{list_id}` | GET | Get a single list by ID |
| `/lists` | POST | Create a list (`{"board_id": "...", "name": "..."}`) |
| `/lists/{list_id}/issues` | GET | Get issues in a list (`?max_issues=100`) |

## Issue Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/issues/{issue_id}` | GET | Get a single issue by ID |
| `/issues` | POST | Create an issue (`{"title": "...", "list_id": "...", "description": "..."}`) |
| `/issues/{issue_id}/status` | PUT | Update issue status (`{"status": "..."}`) |
| `/issues/{issue_id}` | DELETE | Delete an issue |

## Member Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/issues/{issue_id}/members` | GET | Get members assigned to an issue |
| `/issues/{issue_id}/assign` | POST | Assign a member (`?member_id=...`) |

## Utility Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Redirects to `/docs` (Swagger UI) |
| `/health` | GET | Health check — returns `{"status": "ok"}` |

## Request/Response Models

| Model | Fields |
|-------|--------|
| `BoardResponse` | `id`, `name`, `url` (optional) |
| `ListResponse` | `id`, `name`, `board_id` |
| `IssueResponse` | `id`, `title`, `description` (optional), `list_id`, `board_id`, `is_complete` |
| `MemberResponse` | `id`, `username` |
| `CreateBoardRequest` | `name` |
| `CreateListRequest` | `board_id`, `name` |
| `CreateIssueRequest` | `title`, `list_id`, `description` (optional) |
| `UpdateStatusRequest` | `status` |

## Configuration

Environment variables required for deployment:

| Variable | Description |
|----------|-------------|
| `TRELLO_API_KEY` | Trello API key |
| `TRELLO_API_SECRET` | Trello API secret (OAuth 1.0a) |
| `TRELLO_CALLBACK_URL` | OAuth callback URL (default: `http://localhost:8000/auth/callback`) |
