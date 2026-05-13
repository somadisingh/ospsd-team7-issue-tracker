"""Build Pydantic argument models and provider tool schemas from callables.

Each registered tool is a plain function whose parameters (besides
``self``) become fields on an auto-generated :class:`pydantic.BaseModel`.
OpenAI and Anthropic tool JSON schemas are derived from that model.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from typing import Any, cast, get_type_hints

from pydantic import BaseModel, ValidationError, create_model

from ai_client_api.exceptions import AIToolError
from ai_client_api.resilience import IdempotencyMemory, current_idempotency_key


def build_argument_model(fn: Callable[..., Any]) -> type[BaseModel]:
    """Create a Pydantic model class matching ``fn``'s parameters."""
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn)
    except (NameError, TypeError):
        hints = {}
    fields: dict[str, tuple[Any, Any]] = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            continue
        ann = hints.get(name, Any)
        if param.default is inspect.Parameter.empty:
            fields[name] = (ann, ...)
        else:
            fields[name] = (ann, param.default)
    if not fields:
        return cast(
            "type[BaseModel]", create_model("_EmptyToolArgs", __base__=BaseModel)
        )

    safe_name = (fn.__name__ or "Tool").replace("<", "").replace(">", "")
    model = create_model(f"{safe_name}Args", **fields)  # type: ignore[call-overload]
    return cast("type[BaseModel]", model)


class _RegisteredTool:
    def __init__(
        self,
        *,
        name: str,
        description: str,
        fn: Callable[..., Any],
        arg_model: type[BaseModel],
        mutating: bool,
    ) -> None:
        self.name = name
        self.description = description
        self.fn = fn
        self.arg_model = arg_model
        self.mutating = mutating

    def schema_anthropic(self) -> dict[str, Any]:
        raw = self.arg_model.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": raw.get("properties", {}),
                "required": raw.get("required", []),
                "additionalProperties": False,
            },
        }

    def schema_openai(self) -> dict[str, Any]:
        raw = self.arg_model.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": raw.get("properties", {}),
                    "required": raw.get("required", []),
                    "additionalProperties": False,
                },
            },
        }


class SignatureToolCatalog:
    """Tool catalogue whose JSON schemas are generated from Python signatures."""

    def __init__(
        self,
        *,
        allow_mutations: bool = False,
        idempotency: IdempotencyMemory | None = None,
    ) -> None:
        self._allow_mutations = allow_mutations
        self._idempotency = idempotency
        self._tools: dict[str, _RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        *,
        mutating: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator: ``@catalog.register("x", "desc", mutating=False)``.

        The wrapped function's parameters define the tool argument schema.
        """

        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            model = build_argument_model(fn)
            self._tools[name] = _RegisteredTool(
                name=name,
                description=description,
                fn=fn,
                arg_model=model,
                mutating=mutating,
            )
            return fn

        return deco

    def schemas_anthropic(self) -> list[dict[str, Any]]:
        return [
            t.schema_anthropic()
            for t in self._tools.values()
            if self._allow_mutations or not t.mutating
        ]

    def schemas_openai(self) -> list[dict[str, Any]]:
        return [
            t.schema_openai()
            for t in self._tools.values()
            if self._allow_mutations or not t.mutating
        ]

    def dispatch(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            msg = f"Unknown tool: {name!r}"
            raise AIToolError(msg)
        if tool.mutating and not self._allow_mutations:
            msg = f"Tool {name!r} is mutating but mutations are disabled."
            raise AIToolError(msg)
        try:
            validated = tool.arg_model(**arguments)
        except ValidationError as exc:
            msg = f"Invalid arguments for {name!r}: {exc.errors()}"
            raise AIToolError(msg) from exc

        fp = json.dumps(arguments, sort_keys=True, default=str)
        idem_key = current_idempotency_key()
        if self._idempotency is not None and idem_key is not None and tool.mutating:
            cached = self._idempotency.lookup(idem_key, name, fp)
            if cached is not None:
                return cached

        payload = validated.model_dump()
        result = tool.fn(**payload)

        if self._idempotency is not None and idem_key is not None and tool.mutating:
            self._idempotency.remember(idem_key, name, fp, result)
        return result
