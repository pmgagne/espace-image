---
description: 'Python coding conventions and guidelines'
applyTo: '**/*.py'
---

# Python Coding Conventions

## Code Style

- Follow PEP 8. Use 4-space indentation. Max line length: 100 characters.
- Use `ruff` for linting and formatting. Enabled rule sets: `E`, `F`, `I`, `UP`, `B`, `N`.
  - Ignore `B008` for tool configuration defaults (e.g., FastMCP).
- Place docstrings immediately after `def` or `class`.
- Separate functions, classes, and logical blocks with blank lines.

## Type Hints

- Use strict Python 3.13+ type hints on all function signatures and complex variables.
- Avoid `typing.Any`; prefer explicit types.

## Functions and Documentation

- Use descriptive function names. Add docstrings following PEP 257.
- Write inline comments for non-obvious logic.
- Break complex functions into smaller, focused helpers.
- Comment on the purpose of external dependencies at their usage site.

## Async

- Default to `async`/`await` for I/O-bound and service-level code.
- Use synchronous code only for simple standalone scripts.

## Standalone Scripts

- Use the `uv` shebang and PEP 723 metadata block:
  ```python
  #!/usr/bin/env -S uv run
  # /// script
  # requires-python = ">=3.13"
  # dependencies = ["..."]
  # ///
  ```

## Testing

- Use `pytest` for all tests. Run with `uv run pytest -q`.
- Write tests for all critical code paths.
- Cover edge cases: empty inputs, invalid types, boundary values.
- Document each test function with a docstring describing what it verifies.

## General

- Prioritize readability. Explain *why* behind non-obvious design decisions.
- Handle edge cases explicitly with clear exception handling.
