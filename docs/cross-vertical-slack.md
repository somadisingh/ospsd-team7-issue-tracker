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

## 6. Combined demo — Trello + Slack from the SPA

The AI tool catalogue exposes **both** the issue-tracker tools (`list_boards`,
`create_issue`, `update_issue_status`, …) **and** the chat tools
(`list_channels`, `send_chat_message`, …). They're usable in the same
prompt because `ClaudeAIClient` runs a tool-use loop until the model
says "done" (up to `AI_MAX_TOOL_HOPS=6`). This is what makes the
end-to-end demo possible from a single chat box.

### Setup

Three windows / tabs visible at once:

| Window           | Purpose                                  | URL                                       |
| ---------------- | ---------------------------------------- | ----------------------------------------- |
| Browser tab A    | The Next.js SPA, signed in via Trello    | `http://localhost:3000`                   |
| Browser tab B    | A Trello board you'll watch update       | `https://trello.com/b/<your-board-id>`    |
| Slack workspace  | The channel the bot was `/invite`d to    | `#new-channel` (or yours)                 |

Backend running with `CHAT_BACKEND=slack` (§3).

In tab A, click a board on the **left** so the AI knows which board
"this board" refers to.

### Act 1 — Read Trello (sanity check)

In the SPA's right-hand chat panel, type:

> *List the issues on this board.*

Action log should be `list_issues`. Switch to tab B and confirm the
issues match — the AI sees real Trello state.

### Act 2 — Cross-vertical: one prompt, two backends

> *Create an issue titled "fix login redirect bug" on this board, then post a message in #new-channel announcing the new issue with its title and id.*

Action log should be:

```text
✓ create_issue
✓ list_channels        (or get_channel)
✓ send_chat_message
```

Watch in this order:

1. **Right pane** — the action log appears with three green ticks.
2. **Left pane** — board browser auto-refreshes; the new card appears
   (this is the `MUTATING_TOOLS` watcher in `AIChat.tsx:47`).
3. **Trello tab B** — refresh; same card with the right title.
4. **Slack** — bot has posted *"📌 New issue created: fix login redirect bug (id: …)"*.

Three windows, one prompt, two verticals touched, all DI-wired.

### Act 3 — Status change with audit trail

> *Move that issue to in_progress, and post the status change to #new-channel as if you were a CI bot.*

Action log:

```text
✓ list_issues             (resolves the id we just made)
✓ update_issue_status
✓ send_chat_message
```

Trello card moves to "In Progress"; Slack gets a CI-style notification.

### Act 4 — Read-back from Slack

Closing the loop the other direction:

> *Read the last 3 messages in #new-channel and tell me what changed.*

Action log:

```text
✓ list_channels
✓ get_recent_messages
```

The reply summarises the two announcements you just posted. The AI is
now using Slack as an external memory.

### Act 5 — One-line "transparent swap"

Stop uvicorn. Restart with the local backend (§5) and re-run *Act 4*.
The reply now references seeded fake channels (`general`, `dev`,
`random`) instead of your real Slack ones. **No frontend, AI, or route
code changed.** Switch back to slack to continue.

---

## 7. Capabilities — what the bot can and can't do

### The 4 chat tools the AI can call

Registered in `claude_ai_client_impl/tools.py:306-330`. The AI may call
any of these in any order, in any combination, in a single prompt.

| Tool                  | Slack API call          | Effect                                      |
| --------------------- | ----------------------- | ------------------------------------------- |
| `list_channels`       | `conversations.list`    | All channels visible to the bot              |
| `get_channel`         | `conversations.info`    | One channel's name + ID + privacy            |
| `get_recent_messages` | `conversations.history` | Last N (≤50) messages from a channel         |
| `send_chat_message`   | `chat.postMessage`      | Posts a new message to a channel             |

### Deliberately NOT exposed

| Method on Team 9's `SlackClient` | Why hidden                                                                |
| -------------------------------- | ------------------------------------------------------------------------- |
| `delete_message`                 | Hard rule in `tools.py:12` — **"No `delete_*` tools."**                    |
| `get_message`                    | Redundant with `get_recent_messages`; not interesting for tool use         |

### Slack-side limits (would need new code)

The integration is **outbound only**: the AI calls Slack. Slack does
not call us. So the following do **not** work and are out of scope:

- **Receive messages.** No Slack Events API subscription. Typing in
  Slack does not trigger anything on our backend.
- **Slash commands.** No `/issue create …` from inside Slack. No
  webhook endpoint listens for them.
- **DM the bot.** Disabled by default for new Slack apps; the
  "Sending messages to this app has been turned off" notice is from
  Slack, not us.
- **`@mentions` of the bot.** Same reason — no Events API listener.
- **Edit / delete its own posts.** `chat.update` isn't wrapped by
  Team 9's `SlackClient`; `chat.delete` is wrapped but not exposed.
- **Threads.** `chat.postMessage` in their wrapper doesn't take
  `thread_ts`.
- **Reactions, file uploads, user lookup by name.** None of these
  exist in Team 9's published surface.

Net effect: think of Slack here as a **write-mostly audit and
notification channel** that the AI also occasionally reads from. To
make Slack drive the issue tracker (slash commands, mentions) you'd
need to add a separate inbound webhook on the FastAPI side — that's
not what HW3 §5 is asking for, so we haven't built it.

```text
What HW3 §5 requires:    Trello service ──► Slack         ✅  (we have this)
What it does NOT require: Trello service ◄── Slack        (would need an inbound webhook)
```

---

## 8. Where to look in the codebase

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

## 9. Troubleshooting

| Symptom                                        | Cause / fix                                                                       |
| ---------------------------------------------- | --------------------------------------------------------------------------------- |
| Logs say `Wiring chat backend: local` after env change | `CHAT_BACKEND` not set in the **shell** that ran uvicorn. Set inline as above.    |
| `not_in_channel` in the action                 | Bot wasn't `/invite`d to that channel. Add the bot.                               |
| `missing_scope`                                | Missing one of the three scopes; add it then **Reinstall to Workspace**.          |
| `invalid_auth` / `not_authed`                  | Token typo or revoked. Re-copy from OAuth & Permissions.                          |
| `AttributeError: 'str' object has no attribute 'isoformat'` | Adapter bypassed; `chat_client_impl.slack.register()` didn't run. Verify `_chat_client()` log line says `package=chat_client_impl.slack`. |
| Channels listed but message doesn't appear in Slack | Bot posted to a different workspace. Check `xoxb-` token's workspace matches the one you're looking at. |
