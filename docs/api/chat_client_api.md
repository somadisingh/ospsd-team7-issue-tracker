# Chat Client API

This project now integrates the shared chat client contract from `chat-client-api`.

The chat API is installed from the GitHub repository:

- https://github.com/HarshithKoriRaj/Shared-API

## Contract

The shared contract defines the following public types and methods:

- `ChatClient` — abstract base class for chat implementations
- `Channel` — a chat room or conversation
- `Message` — a chat message
- `get_client()` — returns the registered client implementation
- `register_client(factory)` — registers a concrete implementation factory

### Supported chat methods

- `send_message(channel_id, text) -> Message`
- `get_channels() -> list[Channel]`
- `get_channel(channel_id) -> Channel`
- `get_messages(channel_id, limit=10, cursor=None) -> list[Message]`
- `get_message(message_id) -> Message`
- `delete_message(message_id) -> None`

## Local implementation

A local in-memory implementation is provided by `chat-client-impl`.
This package registers itself when imported, so `get_client()` can be used directly.

```python
import chat_client_impl
from chat_client_api import get_client

client = get_client()
channels = client.get_channels()
print([channel.name for channel in channels])

message = client.send_message("general", "Hello from the local chat client")
print(message)
```

## Notes

- The local implementation stores messages in memory and is useful for tests and demos.
- It does not track channel objects, so `get_channels()` returns an empty list and `get_channel()` always raises `ChannelNotFoundError`.
- `cursor` is accepted by `get_messages` but this local implementation ignores it, which is valid for simple providers.
- `message_id` is opaque and is generated as `"<channel_id>:<timestamp>"` in this example.
