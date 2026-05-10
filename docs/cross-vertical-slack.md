# Cross-Vertical Chat — Team 9 Slack (HW3 §5)

The issue tracker's AI assistant talks to a chat platform via the
provider-agnostic `chat_client_api.ChatClient` ABC. Two implementations
are wired today:

| Backend  | Package                           | What it is                                                |
| -------- | --------------------------------- | --------------------------------------------------------- |
| `local`  | `chat_client_impl`                | In-memory fake (seeded channels/messages) for local dev   |
| `slack`  | `chat_client_impl.slack`          | Adapter wrapping **Team 9's** `slack_client_impl.SlackClient` |

You select which one is active at runtime by setting `CHAT_BACKEND` in
the environment — no code change.

!!! note "HW3 §5 scope"
    This page covers the **cross-vertical** integration: consuming
    another team's published API, wiring it via DI, and demonstrating
    a transparent provider swap. The AI tool catalogue, system prompt,
    and chat-tool definitions live in `ai-integration.md`; this page
    only covers the chat-backend selection layer.

---

## 1. How it's wired

### Dependency declaration

The Slack implementation is pulled directly from Team 9's GitHub repo
via a uv subdirectory pin, so we install **only** their
`slack_client_impl` package and none of their other workspace
components.

```toml title="pyproject.toml (root)"
[tool.uv.sources]
slack-client-impl = {
  git = "https://github.com/HarshithKoriRaj/CS-GY-9223-Open-Source",
  rev = "91eedf88e6823e1f924cbeb05c6a74aa0a524b34",
  subdirectory = "components/slack_client_impl",
}

# Force their internal chat-client-api copy to resolve to the canonical
# Shared-API repo so uv doesn't refuse over duplicate URLs.
[tool.uv]
override-dependencies = [
  "chat-client-api @ git+https://github.com/HarshithKoriRaj/Shared-API.git@main",
]
```

### Backend selection

```python title="components/issue_tracker_service/src/issue_tracker_service/ai_deps.py"
_CHAT_BACKEND_PACKAGES: dict[str, str] = {
    "local": "chat_client_impl",
    "slack": "chat_client_impl.slack",
}

@lru_cache(maxsize=1)
def _chat_client() -> ChatClient:
    backend = os.getenv("CHAT_BACKEND", "local").lower()
    package = _CHAT_BACKEND_PACKAGES[backend]
    module = importlib.import_module(package)
    register_fn = getattr(module, "register", None)
    if callable(register_fn):
        register_fn()        # last-write-wins into the shared registry
    return get_client()      # canonical chat_client_api factory
```

### The adapter (and why we needed it)

Team 9's `Message.timestamp` is a `str` (Slack's raw `ts`); our
canonical `chat_client_api.Message.timestamp` is a timezone-aware
`datetime`. Their methods raise `ValueError`; ours expect typed
`ChatError` subclasses. The adapter sits **entirely on our side** so we
don't modify Team 9's code (per HW3 §1).

```text
                 ┌────────────────────────┐
ai_deps.py       │ chat_client_api.       │
└─ get_client()─►│   register/get_client  │
                 └─────────┬──────────────┘
                           │
   ┌───────────────────────▼────────────────────────┐
   │  chat_client_impl.slack.SlackChatAdapter       │  ← our shim
   │  · timestamp: str → datetime (UTC)             │
   │  · ValueError → ChatNotFoundError / ChatError  │
   └───────────────────────┬────────────────────────┘
                           │
                ┌──────────▼─────────────┐
                │ slack_client_impl.     │  ← Team 9's package (unmodified)
                │   SlackClient          │
                └──────────┬─────────────┘
                           │
                  Slack Web API (slack-sdk)
```

Source: `components/chat_client_impl/src/chat_client_impl/slack.py`,
tests in `components/chat_client_impl/tests/slack_test.py`.

---

## 2. One-time Slack setup (~5 min)

Skip this section if you already have a `xoxb-…` bot token.

1. Open <https://api.slack.com/apps> → **Create New App** → **From
   scratch**. Name it (e.g. `team7-ai-demo`), pick a workspace you own
   (free workspace at <https://slack.com/get-started> is fine).
2. Left sidebar → **OAuth & Permissions** → **Bot Token Scopes** →
   add the three scopes Team 9's `SlackClient` calls:

    | Scope              | Used by                                                                  |
    | ------------------ | ------------------------------------------------------------------------ |
    | `chat:write`       | `send_message`, `delete_message` → `chat.postMessage` / `chat.delete`    |
    | `channels:read`    | `get_channels`, `get_channel` → `conversations.list` / `conversations.info` |
    | `channels:history` | `get_messages`, `get_message` → `conversations.history`                   |

3. Scroll up → **Install to Workspace** → **Allow**.
4. Copy the resulting **Bot User OAuth Token** (`xoxb-…`) into your
   backend `.env`:

    ```bash
    SLACK_BOT_TOKEN=xoxb-...your-token...
    ```

5. In your Slack workspace, invite the bot to a channel:

    ```
    /invite @team7-ai-demo
    ```

    Channel listing works without membership, but **posting and reading
    history require it**.

---

## 3. Run the backend with Slack as the provider

```bash
cd ospsd-team7-issue-tracker
CHAT_BACKEND=slack uv run uvicorn issue_tracker_service.main:app --reload --port 8000
```

!!! info "Lazy wiring"
    `_chat_client()` is `@lru_cache`'d and only runs on the first
    `/ai/chat` request, not at startup. So the proof line below
    appears after you make the first request, not in the initial
    startup logs.

After the first AI request, the uvicorn terminal logs:

```text
INFO:issue_tracker_service.ai_deps: Wiring chat backend: slack (package=chat_client_impl.slack)
```

That single line is the visible proof of the transparent swap.

---

## 4. Verify (curl)

Get a session token (assumes Trello OAuth was completed at least once
— see `index.md` for the OAuth walkthrough):

```bash
TOKEN=$(sqlite3 dev.db "SELECT session_token FROM user_sessions LIMIT 1;")
```

### List channels

```bash
curl -s -H "X-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -X POST http://localhost:8000/ai/chat \
  -d '{"prompt":"Use list_channels and tell me what channels you can see."}'
```

```json
{
  "reply": "I can see 3 channels: ...",
  "actions": [{"tool": "list_channels", "ok": true, "error": null}],
  "truncated": false
}
```

### Send a message

```bash
curl -s -H "X-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -X POST http://localhost:8000/ai/chat \
  -d '{"prompt":"Send the message \"hello from team 7 AI\" to channel new-channel"}'
```

```json
{
  "reply": "Message sent successfully to new-channel! ...",
  "actions": [{"tool": "send_chat_message", "ok": true, "error": null}],
  "truncated": false
}
```

The message should appear in the Slack channel in real time.

### Read recent messages (chained tool calls)

```bash
curl -s -H "X-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -X POST http://localhost:8000/ai/chat \
  -d '{"prompt":"What were the last 3 messages in new-channel?"}'
```

```json
{
  "reply": "The last 3 messages in **new-channel** are: ...",
  "actions": [
    {"tool": "list_channels",       "ok": true, "error": null},
    {"tool": "get_recent_messages", "ok": true, "error": null}
  ],
  "truncated": false
}
```

Two tool calls in one response: Claude first calls `list_channels` to
resolve the channel ID, then `get_recent_messages` with that ID. This
exercises the chained-tool-use loop in `claude_ai_client_impl/client.py`.

---

## 5. Prove the swap is transparent

Stop uvicorn, restart with the local backend:

```bash
CHAT_BACKEND=local uv run uvicorn issue_tracker_service.main:app --reload --port 8000
```

Re-run the **exact same** curl from §4. You'll see:

- A different startup log line: `Wiring chat backend: local (package=chat_client_impl)`
- A different reply mentioning the seeded fake channels in
  `chat_client_impl/client.py` (e.g. `general`, `dev`, `random`)
  instead of your real Slack channels.
- The frontend, `routes/ai.py`, and `claude_ai_client_impl/client.py`
  did **not** change a single line.

That's the rubric §5 "transparent swap" requirement, demonstrated.

---

## 6. Where to look in the codebase

| Concern                                        | File                                                                                       |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Pin Team 9's package via subdirectory          | `pyproject.toml` (root) — `[tool.uv.sources] slack-client-impl`                              |
| Override their internal `chat-client-api` URL  | `pyproject.toml` (root) — `[tool.uv] override-dependencies`                                 |
| Adapter (timestamp normalize, exception map)   | `components/chat_client_impl/src/chat_client_impl/slack.py` (`SlackChatAdapter`)            |
| `register()` for the slack adapter             | same file, bottom (`register_client(make_slack_adapter)`)                                   |
| Backend selection at runtime                   | `components/issue_tracker_service/src/issue_tracker_service/ai_deps.py::_chat_client()`     |
| Adapter unit tests                             | `components/chat_client_impl/tests/slack_test.py`                                           |
| AI ↔ chat integration tests                    | `tests/integration/ai_chat_integration_tests.py`                                            |

---

## 7. Troubleshooting

| Symptom                                        | Cause / fix                                                                       |
| ---------------------------------------------- | --------------------------------------------------------------------------------- |
| Logs say `Wiring chat backend: local` after env change | `CHAT_BACKEND` not set in the **shell** that ran uvicorn. Set inline as above.    |
| `not_in_channel` in the action                 | Bot wasn't `/invite`d to that channel. Add the bot.                               |
| `missing_scope`                                | Missing one of the three scopes; add it then **Reinstall to Workspace**.          |
| `invalid_auth` / `not_authed`                  | Token typo or revoked. Re-copy from OAuth & Permissions.                          |
| `AttributeError: 'str' object has no attribute 'isoformat'` | Adapter bypassed; `chat_client_impl.slack.register()` didn't run. Verify `_chat_client()` log line says `package=chat_client_impl.slack`. |
| Channels listed but message doesn't appear in Slack | Bot posted to a different workspace. Check `xoxb-` token's workspace matches the one you're looking at. |
