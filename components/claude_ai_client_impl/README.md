# claude_ai_client_impl

Anthropic Claude implementation of the `ai_client_api.AIClient` ABC.

## Modules

| File            | Role                                                                  |
| --------------- | --------------------------------------------------------------------- |
| `client.py`     | `ClaudeAIClient` — runs the Claude tool-use loop.                     |
| `config.py`     | `ClaudeConfig` — env-driven knobs (model, hop limit, mutations flag). |
| `tools.py`      | Tool catalogue + dispatcher (issue tracker + chat).                   |
| `serializers.py`| Allow-listed projections for Board/Issue/Channel/Message.             |
| `prompt.py`     | System prompt template.                                               |
| `mock_chat.py`  | In-memory `ChatClient` used for dev + tests before T2 lands.          |

## Wiring

```python
from claude_ai_client_impl import ClaudeAIClient, ClaudeConfig
from trello_client_impl.client import TrelloClient
from chat_client_api import ChatClient

ai = ClaudeAIClient(
    issue_tracker=TrelloClient(...),
    chat=chat_impl,   # or MockChatClient()
    config=ClaudeConfig.from_env(),
)

reply = ai.send_message("Summarize overdue tickets on board abc.")
```

## Environment variables

| Name                    | Required | Default                  |
| ----------------------- | -------- | ------------------------ |
| `ANTHROPIC_API_KEY`     | yes      | —                        |
| `CLAUDE_MODEL`          | no       | `claude-sonnet-4-5`      |
| `AI_MAX_TOOL_HOPS`      | no       | `6`                      |
| `AI_ALLOW_MUTATIONS`    | no       | `false`                  |
| `AI_MAX_TOKENS`         | no       | `1024`                   |
