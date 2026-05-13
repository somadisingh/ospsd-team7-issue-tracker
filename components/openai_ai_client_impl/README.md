# OpenAI AI Client Implementation

Concrete [`AIClient`](../ai_client_api) backed by OpenAI **Chat Completions**
with function calling. Tool definitions come from
[`SignatureToolCatalog`](../ai_client_api/src/ai_client_api/signature_tools.py):
JSON schemas are **auto-generated from typed Python function signatures**, and
arguments are validated before dispatch (same logical tools as Claude; see
`domain_catalog.py`).

## Selection

Set **`AI_PROVIDER=openai`** in the environment (default remains **`claude`**).
Requires **`OPENAI_API_KEY`**. Optional **`OPENAI_MODEL`** (default `gpt-4o-mini`).

Shared knobs with Claude: **`AI_MAX_TOOL_HOPS`**, **`AI_MAX_TOKENS`**,
**`AI_ALLOW_MUTATIONS`**, **`AI_STRUCTURED_OUTPUT`**.

## HTTP resilience

**`AI_HTTP_MAX_ATTEMPTS`**, **`AI_HTTP_RETRY_BASE_S`**, **`AI_HTTP_RETRY_MAX_S`**
configure retries with full jitter around `chat.completions.create` (see
`ai_client_api.resilience`).

## Structured final replies

When **`AI_STRUCTURED_OUTPUT=true`**, the client validates the model's final
assistant text as JSON matching **`StructuredAIEnvelope`**
(`reply` required, `rationale` optional). On failure the client raises
**`AIStructuredOutputError`** (mapped to **HTTP 422** by `/ai/chat`).

## Idempotency

**`OpenAIAIClient.send_message(prompt, context={"idempotency_key": "<string>", ...})`**
binds an in-process idempotency scope for the tool loop. Only the first **128**
characters of a non-empty string key are used. **Mutating** tools with the same
name and arguments return a cached result while the key is active. Non-string or
empty values are ignored.

The public **`POST /ai/chat`** JSON body does not yet expose this field; use it
from Python or extend the API if you need HTTP-level dedupe.
