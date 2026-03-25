# Code Formatting & Static Analysis

This document describes the code quality tooling configured for this project. All configuration lives in the **root `pyproject.toml`** — no tool-specific config files elsewhere in the repository.

## Tools Overview

| Tool | Purpose | Command |
|------|---------|---------|
| **ruff format** | Code formatting (replaces Black, isort) | `uv run ruff format .` |
| **ruff check** | Linting (replaces Flake8, pylint, and many others) | `uv run ruff check .` |
| **mypy** | Static type checking | `uv run mypy .` |

---

## Ruff — Formatting & Linting

[Ruff](https://docs.astral.sh/ruff/) is an extremely fast Python linter and formatter written in Rust. It replaces multiple tools (Black, Flake8, isort, pyupgrade, etc.) in a single binary.

### Formatting

Ruff's formatter enforces a consistent code style across the entire project.

**Configuration** (in `pyproject.toml`):

```toml
[tool.ruff]
line-length = 88
target-version = "py312"
```

**Key decisions:**

- **Line length of 88**: This is the default used by Black and Ruff. It provides a good balance between readability and fitting code on screen.

**Usage:**

```bash
# Format all files
uv run ruff format .

# Check formatting without modifying files
uv run ruff format --check .
```

### Linting

All available Ruff rules are enabled (`select = ["ALL"]`), as required by the course. Only rules that conflict with each other are disabled, with justification.

**Configuration** (in `pyproject.toml`):

```toml
[tool.ruff.lint]
select = ["ALL"]
ignore = [
  "D203",   # Conflicts with D211 (see justification below)
  "D213",   # Conflicts with D212 (see justification below)
  "COM812", # Conflicts with ruff formatter (see justification below)
]
```

### Disabled Rules — Justifications

| Rule | Name | Reason |
|------|------|--------|
| `D203` | `one-blank-line-before-class` | **Conflicts with `D211`** (`no-blank-line-before-class`). These two rules are mutually exclusive. We follow `D211`. |
| `D213` | `multi-line-summary-second-line` | **Conflicts with `D212`** (`multi-line-summary-first-line`). These two rules are mutually exclusive. We follow `D212`. |
| `COM812` | `missing-trailing-comma` | **Conflicts with the ruff formatter.** The formatter handles trailing commas automatically, so this lint rule is redundant and can produce conflicting edits. |

### Per-File Rule Exceptions (Tests)

Test files (`**/tests/**/*.py`) have relaxed rules because test code follows different conventions than production code:

| Rule | Name | Justification |
|------|------|---------------|
| `S101` | Use of `assert` | `assert` is the standard way to write test assertions in pytest. |
| `PLR2004` | Magic value comparisons | Tests frequently compare against literal expected values (e.g., `assert result == 42`). |
| `D100` | Missing module docstring | Test modules are self-documenting by their file names and test function names. |
| `D103` | Missing function docstring | Test functions like `test_login_success()` describe their intent through naming. |
| `ANN401` | Dynamically typed expressions (`Any`) | Mocking and fixtures may require `Any` types. |
| `ARG001` | Unused function argument | Pytest fixtures appear as unused arguments but are injected by the framework. |
| `ARG002` | Unused method argument | Same as `ARG001`. |
| `SLF001` | Private member access | Tests may need to verify internal state of objects. |
| `TRY300` | Return inside try block | Common pattern in test error handling. |
| `BLE001` | Blind exception catch | Tests may catch broad exceptions intentionally. |
| `E501` | Line too long | Test assertions and setup can be verbose. |
| `S105` | Hardcoded password in variable | Tests use fake credentials as string literals. |
| `S106` | Hardcoded password in function arg | Same as `S105`. |
| `INP001` | Missing `__init__.py` | Test directories must not have `__init__.py` per hw1 requirements. |
| `PLC0415` | Import not at top of file | Tests may import inside functions for isolation or setup. |

**Usage:**

```bash
# Run linting
uv run ruff check .

# Auto-fix all fixable issues
uv run ruff check --fix .

# Show what would be fixed without applying
uv run ruff check --fix --diff .
```

---

## Mypy — Static Type Checking

[Mypy](https://mypy.readthedocs.io/) is a static type checker that enforces type annotations throughout the codebase, catching bugs before runtime.

**Configuration** (in `pyproject.toml`):

```toml
[tool.mypy]
strict = true
explicit_package_bases = true  # Required for src layout
mypy_path = ["components/issue_tracker_client_api/src", "components/trello_client_impl/src"]
ignore_missing_imports = false
show_error_codes = true
```

### What `strict = true` Enables

The `strict` flag is equivalent to turning on all of the following options:

| Flag | What it does |
|------|-------------|
| `disallow_untyped_defs` | Every function must have type annotations |
| `disallow_incomplete_defs` | If you annotate some parameters, you must annotate all |
| `check_untyped_defs` | Type-check function bodies even without annotations |
| `no_implicit_optional` | `x: int = None` is an error — must write `x: int \| None = None` |
| `warn_return_any` | Warn if a function returns `Any` type |
| `warn_unused_configs` | Warn about unused mypy config options |
| `warn_redundant_casts` | Warn about unnecessary `cast()` calls |
| `warn_unused_ignores` | Warn if a `# type: ignore` is unnecessary |
| `warn_no_return` | Warn if a function might not return a value |
| `warn_unreachable` | Warn about dead / unreachable code |

### Guidelines

- **Do NOT use `# type: ignore`** unless you have a specific, documented reason. An error from mypy indicates a real issue with type safety.
- If an external library lacks type stubs, add a `[[tool.mypy.overrides]]` section for that specific module rather than ignoring all import errors globally.

**Usage:**

```bash
# Run type checking on the entire project
uv run mypy .

# Run type checking on a specific component
uv run mypy components/issue_tracker_client_api/
```

---

## Running All Checks

Run all code quality checks in sequence:

```bash
# 1. Format code
uv run ruff format .

# 2. Lint (and auto-fix)
uv run ruff check --fix .

# 3. Type check
uv run mypy .
```

!!! tip "Run checks early and often"
    Don't wait until you're done coding to run these tools. Run them frequently
    as you write code to catch issues early and keep the codebase clean.

---

## Adding New Rule Exceptions

If you need to disable a ruff rule or add a `# type: ignore`, you **must**:

1. Provide a clear justification in a comment or in this document.
2. Prefer per-file ignores (in `pyproject.toml`) over inline `# noqa` comments.
3. Keep the number of exceptions minimal — a clean codebase has very few suppressed warnings.
