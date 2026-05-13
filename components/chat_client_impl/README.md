# Local Chat Client Implementation

This package provides a simple in-memory implementation of the shared `chat-client-api` contract.

- It uses `chat-client-api` from `https://github.com/HarshithKoriRaj/Shared-API.git`.
- It registers a local chat client implementation on import.
- It is useful for local development and tests without needing a real chat platform.

## Usage

```python
import chat_client_impl
from chat_client_api import get_client

client = get_client()
message = client.send_message("general", "Hello from local chat")
print(message.text)
```
