"""Tests for :mod:`ai_client_api.signature_tools`."""

from __future__ import annotations

import pytest
from ai_client_api.exceptions import AIToolError
from ai_client_api.resilience import IdempotencyMemory, idempotency_scope
from ai_client_api.signature_tools import SignatureToolCatalog, build_argument_model


def test_build_argument_model_skips_var_keyword_only() -> None:
    def only_var_kw(**kwargs: int) -> int:
        return len(kwargs)

    m = build_argument_model(only_var_kw)
    assert m().model_dump() == {}


def test_build_argument_model_skips_var_positional_only() -> None:
    def only_var_args(*parts: int) -> int:
        return len(parts)

    m = build_argument_model(only_var_args)
    assert m().model_dump() == {}


def test_build_argument_model_skips_parameter_named_self() -> None:
    class Host:
        @staticmethod
        def tool(self: int) -> int:  # noqa: PLW0211
            return self

    m = build_argument_model(Host.tool)
    assert m().model_dump() == {}


def test_build_argument_model_type_hints_name_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_fn: object, **_kwargs: object) -> dict[str, object]:
        raise NameError("boom")

    monkeypatch.setattr("ai_client_api.signature_tools.get_type_hints", boom)

    def ok(a: int) -> int:
        return a

    m = build_argument_model(ok)
    assert m(a=1).model_dump() == {"a": 1}


def test_build_argument_model_type_hints_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_fn: object, **_kwargs: object) -> dict[str, object]:
        raise TypeError("boom")

    monkeypatch.setattr("ai_client_api.signature_tools.get_type_hints", boom)

    def ok(a: int) -> int:
        return a

    m = build_argument_model(ok)
    assert m(a=1).model_dump() == {"a": 1}


def test_build_argument_model_empty_and_fields() -> None:
    def no_args() -> int:
        return 1

    m0 = build_argument_model(no_args)
    assert m0().model_dump() == {}

    def with_args(x: int, label: str = "a") -> str:
        return f"{x}-{label}"

    m1 = build_argument_model(with_args)
    assert set(m1.model_fields) == {"x", "label"}


def test_signature_catalog_dispatch_and_idempotency() -> None:
    mem = IdempotencyMemory()
    cat = SignatureToolCatalog(allow_mutations=True, idempotency=mem)
    called = {"n": 0}

    @cat.register("add", "Add two ints", mutating=True)
    def add(a: int, b: int) -> int:
        called["n"] += 1
        return a + b

    assert cat.dispatch("add", {"a": 2, "b": 3}) == 5
    with pytest.raises(AIToolError):
        cat.dispatch("missing", {})

    with idempotency_scope("idem-1"):
        assert cat.dispatch("add", {"a": 1, "b": 1}) == 2
        assert cat.dispatch("add", {"a": 1, "b": 1}) == 2
    assert called["n"] == 2

    anth = cat.schemas_anthropic()
    oa = cat.schemas_openai()
    assert len(anth) == 1
    assert anth[0]["name"] == "add"
    assert oa[0]["type"] == "function"
    assert oa[0]["function"]["name"] == "add"


def test_dispatch_invalid_arguments_raises() -> None:
    cat = SignatureToolCatalog(allow_mutations=True)

    @cat.register("echo", "Echo", mutating=False)
    def echo(n: int) -> int:
        return n

    with pytest.raises(AIToolError):
        cat.dispatch("echo", {"n": "not-int"})


def test_dispatch_mutating_when_mutations_disabled() -> None:
    cat = SignatureToolCatalog(allow_mutations=False)

    @cat.register("m", "mut", mutating=True)
    def m() -> int:
        return 1

    with pytest.raises(AIToolError, match="mutations are disabled"):
        cat.dispatch("m", {})
