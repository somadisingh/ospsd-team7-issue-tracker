# AI Integration (HW3)

This project integrates an **external LLM (Anthropic Claude)** into the Trello-backed
issue tracker, fulfilling the *AI Integration* requirement of HW3. The integration
follows the same **interface / implementation** pattern used elsewhere in the
workspace: a provider-agnostic ABC in `ai_client_api`, plus a concrete provider
implementation in `claude_ai_client_impl`. A new pair of FastAPI routes
(`/ai/health`, `/ai/chat`) exposes the AI capabilities over HTTP, wired to the
user's already-authenticated Trello session.

!!! note "HW3 requirement"
    *"Every team must integrate an external AI client ... Your AI integration
    should support tool calling so that the AI model can take actions on your
    domain."* — HW3 instructions. This page documents our response.

---

## 1. Component structure

The AI integration adds two new workspace components next to the existing
issue-tracker ones. Everything the LLM can read or write flows through these
two packages.

```
components/
├── ai_client_api/                   # Provider-agnostic ABC + shared types
│   └── src/ai_client_api/
│       ├── client.py                 # AIClient ABC + register/get factory
│       ├── types.py                  # AIReply, ToolAction dataclasses
│       ├── exceptions.py             # AIError hierarchy (Provider/Tool/Unsafe/HopLimit)
│       ├── sanitize.py               # Prompt scrubber (length cap + secret/PII redaction)
│       └── tool.py                   # ToolDispatcher Protocol
│
└── claude_ai_client_impl/            # Concrete Anthropic Claude provider
    └── src/claude_ai_client_impl/
        ├── client.py                 # ClaudeAIClient — tool-calling loop + hop limit
        ├── config.py                 # ClaudeConfig.from_env()
        ├── prompt.py                 # System prompt + user scope renderer
        ├── tools.py                  # ToolDispatcher (allow-listed tools, mutation gate)
        ├── serializers.py            # Allow-listed projections of Trello/Chat objects
        └── mock_chat.py              # In-memory ChatClient (dev/tests)
```

The FastAPI service adds:

```
components/issue_tracker_service/src/issue_tracker_service/
├── ai_deps.py                        # DI wiring: auth → Trello + Claude per request
└── routes/ai.py                      # /ai/health and /ai/chat endpoints
```

### Dependency graph

```
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI route  /ai/chat                                        │
│  (routes/ai.py)                                                 │
│        │  builds per request via ai_deps.get_ai_client          │
│        ▼                                                        │
│  ClaudeAIClient  (claude_ai_client_impl.client)                 │
│        │    uses                                                │
│        ├──▶ ToolDispatcher (claude_ai_client_impl.tools)        │
│        │         ├──▶ IssueTrackerClient  (issue_tracker_      │
│        │         │     client_api.Client — TrelloClient impl)   │
│        │         └──▶ ChatClient          (chat_client_api ABC  │
│        │                                   — MockChatClient)    │
│        ├──▶ sanitize.py  (ai_client_api)                        │
│        ├──▶ SYSTEM_PROMPT (claude_ai_client_impl.prompt)        │
│        └──▶ anthropic.Anthropic  (upstream SDK, injected)       │
│                                                                 │
│  Returns ai_client_api.types.AIReply  (reply, actions, truncated)│
└─────────────────────────────────────────────────────────────────┘
```

Consumers (the FastAPI route, and tests) depend only on `AIClient` and
`AIReply` from `ai_client_api`. The concrete `claude_ai_client_impl` is
swappable — you could add `openai_ai_client_impl` or `gemini_ai_client_impl`
later without touching any route code.

---

## 2. Safety posture

The LLM is treated as untrusted. All controls below are enforced in code, not
in the prompt.

| Concern                  | Control                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------- |
| API-key leakage          | Key read only from `ANTHROPIC_API_KEY`; `.env` in `.gitignore`; never forwarded to prompts.          |
| Prompt-size / PII        | `ai_client_api.sanitize` enforces `MAX_PROMPT_CHARS=8000` and redacts keys, bearer tokens, emails, phone numbers, ANSI control chars. |
| Tool surface             | `ToolDispatcher` exposes a hard-coded allow-list. Unknown tool names raise `AIToolError`.            |
| Tool arguments           | Every tool's arguments are validated by a Pydantic model before any backend call.                    |
| Mutations                | `create_board`, `rename_board`, `create_issue`, `update_issue_status`, `send_chat_message` are gated by `AI_ALLOW_MUTATIONS` (default **false**). There are **no** `delete_*` tools at all. |
| Data exposure            | `serializers.py` projects Trello / Chat objects into allow-listed dicts only — no raw SDK objects reach the model. |
| Runaway tool use         | The tool-calling loop is bounded by `AI_MAX_TOOL_HOPS` (default 6). On hit, the reply is returned with `truncated=True`. |
| Prompt injection         | The system prompt tells Claude to treat content inside `<ticket>`, `<chat_message>`, and `<tool_result>` as *data*, never as instructions. |
| Cross-origin abuse       | FastAPI CORS middleware; origins allow-listed via `CORS_ALLOW_ORIGINS`.                              |

### Tool catalogue (source of truth: `claude_ai_client_impl/tools.py`)

| Tool                       | Mutating | Purpose                                           |
| -------------------------- | -------- | ------------------------------------------------- |
| `list_boards`              | no       | List all boards the user can access.              |
| `get_board`                | no       | Fetch a single board by id.                       |
| `list_issues_on_board`     | no       | List issues on a board.                           |
| `get_issue`                | no       | Fetch one issue.                                  |
| `list_channels`            | no       | List chat channels visible to the bot.            |
| `get_channel`              | no       | Fetch one chat channel.                           |
| `get_recent_messages`      | no       | Read the last N messages in a channel.            |
| `create_board`             | yes      | Create a new empty board.                         |
| `rename_board`             | yes      | Rename an existing board.                         |
| `create_issue`             | yes      | Open a new issue on a board.                      |
| `update_issue_status`      | yes      | Move an issue between `to_do`/`in_progress`/`completed`. |
| `send_chat_message`        | yes      | Post a message to a chat channel.                 |

When `AI_ALLOW_MUTATIONS=false` the mutating tools are **absent from the schema
list handed to Claude**, so the model cannot even propose them. A defense-in-depth
check in `dispatch()` also rejects them if they sneak in.

---

## 3. Environment variables

| Variable              | Required | Default                  | Purpose                                                                 |
| --------------------- | -------- | ------------------------ | ----------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY`   | **yes**  | —                        | Anthropic API key. Without it `/ai/health` returns `status=unconfigured` and `/ai/chat` fails. |
| `CLAUDE_MODEL`        | no       | `claude-sonnet-4-5`      | Anthropic model id.                                                     |
| `AI_MAX_TOOL_HOPS`    | no       | `6`                      | Max model ↔ tool round trips per request.                               |
| `AI_MAX_TOKENS`       | no       | `1024`                   | Max tokens per Claude reply.                                            |
| `AI_ALLOW_MUTATIONS`  | no       | `false`                  | When `true`, the mutating tools are exposed to Claude.                  |
| `CORS_ALLOW_ORIGINS`  | yes[^1]  | `http://localhost:3000`  | Comma-separated origins allowed to call the AI routes from a browser.   |

[^1]: Required when a frontend (e.g. the Next.js app on Vercel) calls `/ai/chat` directly.

See also: `TRELLO_API_KEY`, `TRELLO_API_SECRET`, `TRELLO_CALLBACK_URL` —
already documented in [FastAPI Service](api/issue_tracker_service.md).

---

## 4. API reference

### `GET /ai/health`

Liveness/readiness probe for the AI stack. Does **not** call Claude — it only
checks whether `ClaudeConfig.from_env()` succeeds.

```bash
curl -s http://localhost:8000/ai/health | jq
```

```json
{
  "status": "ok",
  "model": "claude-sonnet-4-5",
  "allow_mutations": false,
  "api_key_loaded": true
}
```

If `ANTHROPIC_API_KEY` is missing the response is:

```json
{"status":"unconfigured","model":"","allow_mutations":false,"api_key_loaded":false}
```

### `POST /ai/chat`

Send a prompt to Claude. The authenticated user's Trello session is used
automatically — Claude never sees the OAuth tokens.

**Request**

| Field        | Type             | Description                                                           |
| ------------ | ---------------- | --------------------------------------------------------------------- |
| `prompt`     | string, 1–8000   | Free-form user text. Sanitized server-side before leaving the box.    |
| `board_id`   | string, optional | If set, the model receives `[scope] board_id="…"` in the user header. |
| `channel_id` | string, optional | Same, for chat-scoped prompts.                                        |

Auth: `X-Session-Token: <from /auth/callback>`.

**Response**

```json
{
  "reply": "Your board 'Alpha' has 3 open tickets: #abc (To Do), #def …",
  "actions": [
    {"tool": "list_boards",          "ok": true,  "error": null},
    {"tool": "list_issues_on_board", "ok": true,  "error": null}
  ],
  "truncated": false
}
```

| Field       | Meaning                                                                                     |
| ----------- | ------------------------------------------------------------------------------------------- |
| `reply`     | Final natural-language answer from Claude.                                                  |
| `actions`   | Ordered audit log of every tool Claude executed during this turn.                           |
| `truncated` | `true` iff the tool-hop budget was exhausted and `reply` is a best-effort partial answer.   |

**Error mapping**

| HTTP | Raised by                                   | Meaning                                              |
| ---- | ------------------------------------------- | ---------------------------------------------------- |
| 400  | `AIUnsafeRequestError`, `AIToolError`       | Prompt too long, or tool args invalid / mutation blocked. |
| 401  | `_authenticated_issue_tracker` (missing/bad `X-Session-Token`) | No Trello session.                    |
| 502  | `AIProviderError`                           | Upstream Anthropic failure (rate limit, 5xx, timeout). |
| 500  | Any other `AIError`                         | Unexpected failure; stack trace in server logs.      |

---

## 5. Usage examples

### 5.1 From `curl`

```bash
# 1. Configure local dev
cd ospsd-team7-issue-tracker
cp .env.example .env        # then edit; set ANTHROPIC_API_KEY at minimum
uv sync --all-extras

# 2. Boot the service
uv run uvicorn issue_tracker_service.main:app --reload --port 8000

# 3. Open http://localhost:8000/auth/login in a browser, finish Trello OAuth,
#    and copy the returned {"session_token": "..."} value.
TOKEN=<paste session token>

# 4. Ask Claude (read-only is enough)
curl -s -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -H "X-Session-Token: $TOKEN" \
  -d '{"prompt":"Summarize all my open issues across boards."}' | jq
```

### 5.2 Scoping to a board

```bash
curl -s -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -H "X-Session-Token: $TOKEN" \
  -d '{"prompt":"Which tickets here are in progress?","board_id":"68f3…"}' | jq
```

The service prepends `[scope] board_id="68f3…"` to the user turn so Claude
does not have to guess which board the user is looking at.

### 5.3 Mutating prompts (needs `AI_ALLOW_MUTATIONS=true`)

```bash
# Make sure AI_ALLOW_MUTATIONS=true is set in .env and you restarted the server.
curl -s -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -H "X-Session-Token: $TOKEN" \
  -d '{"prompt":"Create a board called HW3 Demo and open a ticket in it titled Kickoff."}' | jq
```

Expected `actions` (order may vary):

```json
[
  {"tool":"create_board","ok":true},
  {"tool":"create_issue","ok":true}
]
```

### 5.4 From the Next.js frontend

The frontend at `ospsd-team7-issue-tracker-front` already calls `/ai/chat`
from `src/components/AIChat.tsx`. When a mutating action is returned, the
board browser auto-refreshes — see that component's `MUTATING_TOOLS` set and
the `onAfterAIMutation` prop wiring.

### 5.5 From Python (using the ABC directly)

```python
import os
from claude_ai_client_impl import ClaudeAIClient, ClaudeConfig, MockChatClient
from trello_client_impl.client import TrelloClient

ai = ClaudeAIClient(
    issue_tracker=TrelloClient(
        api_key=os.environ["TRELLO_API_KEY"],
        secret=os.environ["TRELLO_API_SECRET"],
        access_token=os.environ["TRELLO_ACCESS_TOKEN"],
        access_token_secret=os.environ["TRELLO_ACCESS_TOKEN_SECRET"],
    ),
    chat=MockChatClient(),
    config=ClaudeConfig.from_env(),
)

reply = ai.send_message("How many boards do I have?")
print(reply.reply)
for a in reply.actions:
    print("-", a.tool, "ok" if a.ok else a.error)
```

---

## 6. Testing

All new code has dedicated unit tests under each component's `tests/`
directory. Run them as part of the normal suite:

```bash
uv run pytest -q \
  components/ai_client_api/tests \
  components/claude_ai_client_impl/tests \
  components/issue_tracker_service/tests
```

| Area                                   | Where                                                     |
| -------------------------------------- | --------------------------------------------------------- |
| Prompt scrubber (PII/secret redaction) | `components/ai_client_api/tests/sanitize_tests.py`        |
| Factory registry + contract            | `components/ai_client_api/tests/client_tests.py`          |
| `AIReply` / `ToolAction` invariants    | `components/ai_client_api/tests/types_tests.py`           |
| Config parsing + env defaults          | `components/claude_ai_client_impl/tests/config_tests.py`  |
| Tool dispatch, arg validation, mutation gate | `components/claude_ai_client_impl/tests/tools_tests.py` |
| Serializer allow-list                  | `components/claude_ai_client_impl/tests/serializers_tests.py` |
| Tool-calling loop (stubbed Anthropic)  | `components/claude_ai_client_impl/tests/client_tests.py`  |
| `/ai/health` & `/ai/chat` routes       | `components/issue_tracker_service/tests/ai_test.py`       |

The Anthropic SDK is **never called** from the test suite — a stub client
drives the loop. This keeps CI hermetic: no `ANTHROPIC_API_KEY` needed in
CircleCI.

---

## 7. Deploying to production

See [Deployment](deployment.md) for the full Render / CircleCI / Vercel
checklist. TL;DR:

1. Add the env vars from §3 to the **Render** service (not CircleCI — see
   [CI/CD](ci-cd.md)).
2. Add the Render service URL to **CORS_ALLOW_ORIGINS** so the Vercel
   frontend can reach it, and to the Trello Power-Up "Allowed origins".
3. Merge → CircleCI builds → the `deploy` job triggers the Render webhook
   → Render rebuilds with the new env vars → `curl .../ai/health` confirms
   `status=ok`.

---

## 8. Extending the integration

- **Add another provider** — create `openai_ai_client_impl` with an
  `OpenAIAIClient(AIClient)` class and register a factory. No route changes.
- **Add a tool** — append a `_Tool(...)` entry in `claude_ai_client_impl.tools.ToolDispatcher._build_tools`,
  add a Pydantic arg model, and (if mutating) cover it with the mutation-gate test.
- **Swap the mock chat client** — replace the body of `ai_deps._chat_client()`
  with `SlackChatClient.from_env()` (or similar). No other code changes
  because everything consumes the `chat_client_api.ChatClient` ABC.
