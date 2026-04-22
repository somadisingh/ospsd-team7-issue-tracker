# ai_client_api

Provider-agnostic abstract contract for an AI assistant that can be plugged
into the issue-tracker service. Zero runtime dependencies.

## What's here

| Module              | Role                                                           |
| ------------------- | -------------------------------------------------------------- |
| `client.py`         | `AIClient` ABC + `get_client()` factory.                       |
| `types.py`          | Data classes used at the boundary (`AIReply`, `ToolAction`).    |
| `tool.py`           | `Tool` / `ToolDispatcher` `Protocol`s.                         |
| `sanitize.py`       | Secret/PII scrubbing helpers used before hitting the provider. |
| `exceptions.py`     | `AIError` hierarchy.                                           |

## Contract

```python
class AIClient(ABC):
    @abstractmethod
    def send_message(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AIReply: ...
```

Concrete providers (Claude, OpenAI, Gemini, …) live in separate
`<provider>_ai_client_impl` packages and depend on this one.
