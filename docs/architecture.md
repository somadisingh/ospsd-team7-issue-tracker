# Issue Tracker Client API — System Design Architecture

This document describes the system design architecture for the issue tracker client implementation, including interface choices, design patterns, and relationship guidelines.

---

## 1. Which Classes Should Have Interfaces?

**Best practice:** Define interfaces (or abstract base classes in Python) for any abstraction that has multiple implementations or represents a contract that consumers depend on.

### Recommended Interfaces (Abstract Base Classes)

| Interface | Purpose | Concrete Implementations |
|-----------|---------|--------------------------|
| **Client** | Contract for issue tracker operations (get issues, boards, members, update status, assign) | `TrelloClient`, `ServiceClientAdapter` |
| **Issue** | Contract for issue representation (`id`, `title`, `is_complete`, `list_id`, `board_id`) | `TrelloCard`, `ServiceIssue` |
| **Board** | Contract for board representation (`id`, `name`) | `TrelloBoard`, `ServiceBoard` |
| **List** | Contract for list representation (`id`, `name`, `board_id`) | `TrelloList`, `ServiceList` |
| **Member** | Contract for member representation (`id`, `username`, `is_board_member`) | `TrelloMember`, `ServiceMember` |
| **ClientFactory** | Contract for creating Client instances | `get_client` factory function (Trello or Adapter) |

### Why These Interfaces?

- **Client**: The main operations interface. Consumers depend on `Client`, not `TrelloClient`, keeping the implementation decoupled and testable.
- **Issue, Board, List, Member**: Domain objects returned by `Client`. Interfaces let Trello API responses (Card, Board, List, Member) map to a common contract.
- **ClientFactory**: Decouples client creation from consumers via the `get_client()` factory function and registration.

### Classes That Do NOT Need Interfaces

- **TrelloClient, TrelloCard, TrelloBoard, TrelloList, TrelloMember**: These are concrete implementations; they implement interfaces but are not extended by other classes.
- **Helper/utility classes** (e.g., `_load_token`): Internal implementation details.

---

## Dependency Injection

Implementations register at import time by replacing the global `get_client` factory in `issue_tracker_client_api`. Consumers call `get_client()` and receive whatever implementation was registered — `TrelloClient` (direct) or `ServiceClientAdapter` (via service).

```python
# Registering the Trello implementation
import trello_client_impl  # auto-registers on import

# Registering the adapter implementation
from issue_tracker_adapter import register
register()
```

After registration, consumers only depend on the interface:

```python
from issue_tracker_client_api import get_client
client = get_client(...)
```

---

## 2. Singleton vs Factory — Best Practices

**Recommendation: Use the Factory pattern** (as in the reference UML).

### Factory Pattern (Preferred)

| Benefit | Explanation |
|---------|-------------|
| **Decoupling** | Consumers depend on `Client` interface, not concrete `TrelloClient`. |
| **Testability** | Easy to inject mock clients in tests. |
| **Flexibility** | Different configurations (API keys, tokens) per instance. |

### When NOT to Use Singleton

| Concern | Why |
|---------|-----|
| **Single global instance** | Issue tracker clients often need different credentials or boards per context (e.g., dev vs prod). |
| **Testing** | Singletons make unit testing harder (global state, harder to mock). |
| **Multi-tenancy** | If the app serves multiple users/workspaces, one singleton is insufficient. |

### When Singleton Might Be Acceptable

- A **configuration loader** or **connection pool** where exactly one instance is desired.
- Not for the main `Client` or `ClientFactory` — keep those as factory-created instances.

**Conclusion:** The current design (factory function `get_client()` with registration) aligns with best practices. A formal `ClientFactory` interface with `createClient()` would make the pattern even more explicit (see UML).

---

## 3. Is-a vs Has-a Relationships

Both are used appropriately in the architecture.

### Is-a (Generalization / Realization)

| Relationship | Meaning |
|--------------|---------|
| `TrelloClient` **is-a** `Client` | Implements the `Client` interface. |
| `TrelloCard` **is-a** `Issue` | Implements the `Issue` interface. |
| `TrelloBoard` **is-a** `Board` | Implements the `Board` interface. |
| `TrelloMember` **is-a** `Member` | Implements the `Member` interface. |

**Use is-a when:** A class provides a specific implementation of a contract (interface/ABC). Enables polymorphism.

### Has-a (Association / Composition / Dependency)

| Relationship | Meaning |
|--------------|---------|
| **Consumer** *uses* `get_client()` | Consumer depends on the factory to obtain a `Client`. |
| `get_client()` *creates* `TrelloClient` | Factory function instantiates the Trello client. |
| `TrelloClient` *returns* `Issue`, `Board`, `Member` | Client produces domain objects; it "has" the capability to create them. |
| `TrelloClient` *uses* `requests` (HTTP) | Client depends on HTTP library for API calls. |

**Use has-a when:** One object uses, contains, or creates another. Represents composition, association, or dependency.

### Summary

- **Is-a**: For polymorphism and interface implementation (dashed arrows to interfaces).
- **Has-a**: For creation responsibility, dependencies, and usage (solid arrows, "uses" stereotype).

---

## 4. Architecture Overview

### Direct Path (Trello Client)

```
┌─────────────────┐     uses      ┌──────────────────┐
│   Consumer      │ ────────────► │  get_client()   │
│   (Solution)    │               │  (Factory)      │
└─────────────────┘               └────────┬─────────┘
                                           │
                                           ▼
                                ┌────────────────────┐
                                │  TrelloClient      │
                                │  (implements       │
                                │   Client)          │
                                └────────┬───────────┘
                                         │ creates
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
           ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
           │ TrelloCard   │    │ TrelloBoard  │    │ TrelloMember │
           │ (Issue)      │    │ (Board)      │    │ (Member)     │
           └──────────────┘    └──────────────┘    └──────────────┘
```

### Service Path (Adapter)

```
┌──────────┐  uses  ┌──────────────┐  delegates  ┌───────────────────┐  HTTP  ┌──────────────┐  API  ┌────────┐
│ Consumer │──────► │ Client ABC   │───────────► │ ServiceClient-    │──────► │ FastAPI      │─────► │ Trello │
│          │        │ get_client() │             │ Adapter           │        │ Service      │       │ API    │
└──────────┘        └──────────────┘             └───────────────────┘        └──────────────┘       └────────┘
                                                       │ uses
                                                       ▼
                                                 ┌───────────────────┐
                                                 │ Auto-Generated    │
                                                 │ HTTP Client       │
                                                 │ (openapi-python-  │
                                                 │  client)          │
                                                 └───────────────────┘
```

The adapter achieves **location transparency**: consumer code uses the same `Client` ABC and `get_client()` factory regardless of whether it talks to Trello directly or through the deployed service.

### UML Class Diagram

![Issue Tracker Client Architecture](uml.png)

The diagram is available as `docs/uml.png`. The source is in `docs/architecture.puml` (PlantUML) — you can render it with [PlantUML](https://www.plantuml.com/plantuml/uml/) or the `plantuml` CLI.

---

## 5. AI Vertical (HW3)

HW3 adds an AI assistant that reuses the same interface/implementation pattern.
Full details (safety posture, tool catalogue, endpoints, examples) are in the
[AI Integration](ai-integration.md) page. The high-level wiring:

```
┌────────┐  HTTP   ┌────────────────────┐   DI     ┌──────────────────┐
│ Client │────────▶│ FastAPI            │─────────▶│ ClaudeAIClient   │
│ (web/  │         │ /ai/chat           │          │ (implements      │
│  curl) │         │ routes/ai.py       │          │  AIClient ABC)   │
└────────┘         └────────┬───────────┘          └────────┬─────────┘
                            │                               │
                            │ Depends(ai_deps.get_ai_client)│
                            ▼                               ▼
                  ┌──────────────────┐           ┌────────────────────┐
                  │ TrelloClient     │◀──────────│ ToolDispatcher     │
                  │ (user-scoped via │  tool     │ (allow-listed, arg-│
                  │  X-Session-Token)│  dispatch │  validated, safety-│
                  └──────────────────┘           │  gated mutations)  │
                                                 └────────┬───────────┘
                                                          │
                                                          ▼
                                                ┌──────────────────┐
                                                │ ChatClient ABC   │
                                                │ (MockChatClient  │
                                                │  today; real chat│
                                                │  impl later)     │
                                                └──────────────────┘
```

### Interface / implementation split

| Interface (ABC)     | Location                          | Concrete implementation        |
| ------------------- | --------------------------------- | ------------------------------ |
| `AIClient`          | `ai_client_api.client`            | `claude_ai_client_impl.ClaudeAIClient` |
| `ToolDispatcher` (Protocol) | `ai_client_api.tool`      | `claude_ai_client_impl.ToolDispatcher` |
| `Client` (issue tracker) | `issue_tracker_client_api`   | `trello_client_impl.TrelloClient`, `issue_tracker_adapter.ServiceClientAdapter` |
| `ChatClient`        | `chat_client_api` (git dep)       | `claude_ai_client_impl.MockChatClient` (dev); pluggable real impl later |

Consumers (the FastAPI route, tests) depend only on the ABCs. A second AI
provider (OpenAI, Gemini) could be added by writing another
`*_ai_client_impl` package with no route-level changes.

### Why this pattern?

- **Provider-agnostic route.** `routes/ai.py` knows nothing about Anthropic.
  Swapping providers is a one-line change in `ai_deps.get_ai_client`.
- **Hard safety boundary.** Tool allow-list, Pydantic arg validation, and
  serializer projections live in the impl package — not in the model prompt.
  The LLM cannot talk to Trello directly; it can only ask the dispatcher.
- **Per-request auth scope.** The Trello client passed to the dispatcher is
  the user's authenticated one (from `X-Session-Token`), so the LLM always
  runs under the same privileges as the caller, never more.
