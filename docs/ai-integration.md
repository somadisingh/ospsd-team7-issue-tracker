# AI Integration (HW3)

This project integrates **external LLMs** into the Trello-backed issue tracker:
**Anthropic Claude** (default) or **OpenAI** (Chat Completions with function tools),
selectable at runtime via `AI_PROVIDER`. Both stacks implement the same
**`AIClient`** contract from package **`ai_client_api`** (see
`components/ai_client_api/src/ai_client_api/client.py` in the repo). FastAPI routes **`GET /ai/health`** and **`POST /ai/chat`**
authenticate with the existing session flow and bind tools to the caller's
Trello OAuth credentials.

!!! note "HW3 requirement"
    *"Every team must integrate an external AI client ... Your AI integration
    should support tool calling so that the AI model can take actions on your
    domain."* — HW3 instructions. This page documents our response.

---

## 1. Component structure

The AI integration adds **three** workspace library components under `components/`
plus service routes. Everything the LLM can read or write flows through `ai_client_api`
and a concrete provider package.

```
components/
├── ai_client_api/                   # Provider-agnostic ABC + shared types + resilience
│   └── src/ai_client_api/
│       ├── client.py                 # AIClient ABC
│       ├── types.py                  # AIReply, ToolAction
│       ├── exceptions.py             # AIError hierarchy (+ AIStructuredOutputError, AIRateLimitError)
│       ├── sanitize.py               # Prompt scrubber
│       ├── resilience.py             # Retries, circuit breaker, idempotency helpers
│       ├── signature_tools.py        # Tool JSON from Python signatures (OpenAI + Anthropic shapes)
│       ├── structured_output.py      # Pydantic envelope for optional structured finals
│       └── tool.py                   # ToolDispatcher Protocol (legacy / docs)
│
├── claude_ai_client_impl/            # Anthropic Messages API
│   └── src/claude_ai_client_impl/
│       ├── client.py                 # ClaudeAIClient — tool loop + resilience
│       ├── config.py                 # ClaudeConfig.from_env()
│       ├── prompt.py                 # System prompt + user scope renderer
│       ├── tools.py                  # Claude ToolDispatcher
│       └── serializers.py            # Shared projections (also used by OpenAI path)
│
└── openai_ai_client_impl/            # OpenAI Chat Completions + function tools
    └── src/openai_ai_client_impl/
        ├── client.py                 # OpenAIAIClient
        ├── config.py                 # OpenAIConfig.from_env()
        └── domain_catalog.py         # SignatureToolCatalog mirroring Claude tools
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
│  ClaudeAIClient  OR  OpenAIAIClient  (per AI_PROVIDER)          │
│        │    uses                                                │
│        ├──▶ Tool catalogue (Claude tools.py or OpenAI           │
│        │         domain_catalog + SignatureToolCatalog)         │
│        │         ├──▶ IssueTrackerClient (TrelloClient impl)   │
│        │         └──▶ ChatClient (local / Slack, CHAT_BACKEND)   │
│        ├──▶ sanitize + prompt (shared prompt module)            │
│        └──▶ Upstream SDK (Anthropic or OpenAI) + resilience    │
│                                                                 │
│  Returns ai_client_api.types.AIReply                             │
└─────────────────────────────────────────────────────────────────┘
```

Consumers depend only on `AIClient` / `AIReply`. `issue_tracker_service.ai_deps.get_ai_client`
returns the correct implementation based on **`AI_PROVIDER`** (`claude` default, `openai`).

---

## 2. Safety posture

The LLM is treated as untrusted. All controls below are enforced in code, not
in the prompt.

| Concern                  | Control                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------- |
| API-key leakage          | Key read only from `ANTHROPIC_API_KEY`; `.env` in `.gitignore`; never forwarded to prompts.          |
| Prompt-size / PII        | `ai_client_api.sanitize` enforces `MAX_PROMPT_CHARS=8000` and redacts keys, bearer tokens, emails, phone numbers, ANSI control chars. |
| Tool surface             | `ToolDispatcher` exposes a hard-coded allow-list. Unknown tool names raise `AIToolError`.            |
| Tool arguments           | Claude: Pydantic models in `tools.py`. OpenAI: auto-generated models in `signature_tools` from registered function signatures. |
| Mutations                | Same tool names; gated by `AI_ALLOW_MUTATIONS` (default **false**). OpenAI path additionally dedupes mutating calls when `context["idempotency_key"]` is set (see below). |
| Data exposure            | `serializers.py` projects Trello / Chat objects into allow-listed dicts only — no raw SDK objects reach the model. |
| Runaway tool use         | The tool-calling loop is bounded by `AI_MAX_TOOL_HOPS` (default 6). On hit, the reply is returned with `truncated=True`. |
| Prompt injection         | The system prompt tells Claude to treat content inside `<ticket>`, `<chat_message>`, and `<tool_result>` as *data*, never as instructions. |
| Cross-origin abuse       | FastAPI CORS middleware; origins allow-listed via `CORS_ALLOW_ORIGINS`.                              |

### Tool catalogue (Claude: `claude_ai_client_impl/tools.py`; OpenAI: `openai_ai_client_impl/domain_catalog.py`)

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
| `assign_issue`             | yes      | Assign a board member to an issue (`issue_id`, `member_id`). |
| `send_chat_message`        | yes      | Post a message to a chat channel.                 |

When `AI_ALLOW_MUTATIONS=false` the mutating tools are **absent from the schema
list handed to the model**, so it cannot even propose them. A defense-in-depth
check in each provider's `dispatch()` also rejects them if they sneak in.

---

## 3. Environment variables

### Provider selection

| Variable        | Required | Default   | Purpose |
| --------------- | -------- | --------- | ------- |
| `AI_PROVIDER`   | no       | `claude`  | `claude` uses Anthropic; `openai` uses OpenAI Chat Completions. Any other value fails at client construction. |

### Claude (`AI_PROVIDER=claude` or unset)

| Variable              | Required | Default                  | Purpose                                                                 |
| --------------------- | -------- | ------------------------ | ----------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY`   | **yes**  | —                        | Anthropic API key. Without it `/ai/health` returns `status=unconfigured` and `/ai/chat` fails at config load. |
| `CLAUDE_MODEL`        | no       | `claude-sonnet-4-5`      | Anthropic model id.                                                     |

### OpenAI (`AI_PROVIDER=openai`)

| Variable            | Required | Default        | Purpose |
| ------------------- | -------- | -------------- | ------- |
| `OPENAI_API_KEY`    | **yes**  | —              | OpenAI API key. Missing key → `/ai/health` reports `unconfigured` for provider `openai`. |
| `OPENAI_MODEL`      | no       | `gpt-4o-mini`  | Chat model id. |

### Shared AI tuning (both providers)

| Variable                 | Required | Default | Purpose |
| ------------------------ | -------- | ------- | ------- |
| `AI_MAX_TOOL_HOPS`       | no       | `6`     | Max model ↔ tool round trips per request. |
| `AI_MAX_TOKENS`          | no       | `1024`  | Max tokens per upstream completion (provider-specific caps still apply). |
| `AI_ALLOW_MUTATIONS`     | no       | `false` | When `true`, mutating tools are exposed. |
| `AI_STRUCTURED_OUTPUT`   | no       | `false` | When `true`, the final assistant message must be JSON `{"reply": "…", "rationale": …}` (`StructuredAIEnvelope`). Invalid output raises `AIStructuredOutputError` → **HTTP 422** from `/ai/chat`. |

### HTTP resilience (both providers)

Upstream SDK calls are wrapped with retries (full jitter) and optional failure classification:

| Variable                 | Default | Purpose |
| ------------------------ | ------- | ------- |
| `AI_HTTP_MAX_ATTEMPTS`   | `4`     | Max attempts per HTTP call (including the first try). Non-integer values fall back to default. |
| `AI_HTTP_RETRY_BASE_S`   | `0.1`   | Base seconds for exponential backoff cap (see `ai_client_api.resilience.RetryPolicy`). |
| `AI_HTTP_RETRY_MAX_S`    | `2.0`   | Upper bound on per-retry sleep cap. |

### Chat backend (unchanged)

| Variable        | Required | Default | Purpose |
| --------------- | -------- | ------- | ------- |
| `CHAT_BACKEND`  | no       | `local` | `local` or `slack` (see [Cross-vertical Slack](cross-vertical-slack.md)). |

### Idempotency (OpenAI tool path)

When calling `AIClient.send_message(prompt, context=...)`, you may set **`context["idempotency_key"]`** to a **non-empty string** (only the first **128** characters are used). While that key is active, **mutating** tool invocations with identical tool name and arguments are served from an in-process cache (`IdempotencyMemory`) instead of re-executing. The FastAPI **`POST /ai/chat`** body today only passes `board_id` and `channel_id`; callers using the Python `AIClient` directly (or a future API extension) can supply `idempotency_key` for safe retries of user-visible mutations.

### Other

| Variable              | Required | Default                  | Purpose                                                                 |
| --------------------- | -------- | ------------------------ | ----------------------------------------------------------------------- |
| `CORS_ALLOW_ORIGINS`  | yes[^1]  | `http://localhost:3000`  | Comma-separated origins allowed to call the AI routes from a browser.   |

[^1]: Required when a frontend (e.g. the Next.js app on Vercel) calls `/ai/chat` directly.

Trello OAuth and database URLs are documented in [FastAPI Service](api/issue_tracker_service.md).

## 4. API reference

### `GET /ai/health`

Liveness probe for the AI stack. Does **not** call the LLM — configuration only.
The JSON includes **`provider`** (`claude` or `openai`) from `AI_PROVIDER`.

**Claude (default)** — checks `ClaudeConfig.from_env()`.

```bash
curl -s http://localhost:8000/ai/health | jq
```

```json
{
  "status": "ok",
  "provider": "claude",
  "model": "claude-sonnet-4-5",
  "allow_mutations": false,
  "api_key_loaded": true
}
```

If `ANTHROPIC_API_KEY` is missing:

```json
{"status":"unconfigured","provider":"claude","model":"","allow_mutations":false,"api_key_loaded":false}
```

**OpenAI** (`AI_PROVIDER=openai`) — checks `OpenAIConfig.from_env()`. With `OPENAI_API_KEY` set, `provider` is `openai` and `model` reflects `OPENAI_MODEL`. Without the key, `status` is `unconfigured` and `api_key_loaded` is `false`.

### `POST /ai/chat`

Send a prompt to the configured LLM. The authenticated user's Trello session is used
automatically — the model never sees OAuth tokens.

**Request**

| Field        | Type             | Description                                                           |
| ------------ | ---------------- | --------------------------------------------------------------------- |
| `prompt`     | string, 1–8000   | Free-form user text. Sanitized server-side before leaving the box.    |
| `board_id`   | string, optional | If set, passed in the `context` dict to the provider as `board_id`.  |
| `channel_id` | string, optional | Same for `channel_id`.                                                |

Optional **`idempotency_key`** is not part of the public JSON schema today; use
`AIClient.send_message(..., context={"idempotency_key": "…"})` from Python when
you need OpenAI mutating-tool dedupe (see §3).

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
| `reply`     | Final natural-language answer from the model.                         |
| `actions`   | Ordered audit log of every tool the model executed during this turn. |
| `truncated` | `true` iff the tool-hop budget was exhausted and `reply` is partial. |

**Error mapping**

| HTTP | Raised by                                   | Meaning                                              |
| ---- | ------------------------------------------- | ---------------------------------------------------- |
| 400  | `AIUnsafeRequestError`, `AIToolError`       | Prompt rejected by sanitizer, or tool args invalid / mutation blocked. |
| 401  | `_authenticated_issue_tracker` (missing/bad `X-Session-Token`) | No Trello session.                    |
| 422  | `AIStructuredOutputError`                  | Structured final JSON invalid when `AI_STRUCTURED_OUTPUT=true`. |
| 502  | `AIProviderError`                           | Upstream LLM failure (rate limit, 5xx, timeout). |
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
  components/openai_ai_client_impl/tests \
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
| OpenAI client + config + domain tools  | `components/openai_ai_client_impl/tests/`                  |
| `/ai/health` & `/ai/chat` routes       | `components/issue_tracker_service/tests/ai_test.py`         |
| `AI_PROVIDER` / chat backend DI        | `components/issue_tracker_service/tests/ai_deps_test.py`   |

The Anthropic / OpenAI network SDKs are **not** called from CI unit tests — stubs
and fakes drive the loops. Set keys in `.env` for manual integration against real APIs.

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

- **Add another provider** — implement `AIClient`, add config `from_env`, wire `AI_PROVIDER` in `ai_deps.get_ai_client`.
- **Add a tool** — update both `claude_ai_client_impl.tools` and `openai_ai_client_impl.domain_catalog` (or share a single registry later).
- **Swap the mock chat client** — replace the body of `ai_deps._chat_client()`
  with `SlackChatClient.from_env()` (or similar). No other code changes
  because everything consumes the `chat_client_api.ChatClient` ABC.
