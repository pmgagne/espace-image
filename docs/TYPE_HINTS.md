# Type Hints and Type Checking in Espace-Image

## Why Type Hints Are Required

Type hints are mandatory throughout the Espace-Image codebase. They provide explicit type information for function signatures, variables, and class attributes. This requirement is enforced to:

- **Improve code clarity and maintainability**: Type hints make code easier to read, understand, and refactor, especially for new contributors or after long periods between changes.
- **Enable robust static analysis**: Tools like Ruff and Pylance/Pyright use type hints to catch bugs, detect ambiguous or unsafe code, and enforce best practices before runtime.
- **Facilitate modern Python development**: Type hints are a core part of modern Python (PEP 484, 585, 604), and their use is considered a best practice in professional projects.

## Enforcement and Style

- **All public functions, methods, and class attributes must have explicit type annotations.**
- **Use modern type hint syntax**: Prefer built-in generics (e.g., `list[str]`, `dict[str, int]`) and union types (`X | None`) over legacy `typing.List`, `Optional`, etc.
- **No ambiguous or partially unknown types**: Avoid `Any` unless strictly necessary. All types must be as specific as possible.
- **Third-party and dynamic APIs**: When using libraries with unclear types, add type comments or use `Any` with a clear justification in a comment.
- **Linting and type checking**: Ruff is configured to enforce type hint presence and style. Pylance/Pyright is used for type checking in VS Code. Both must report a clean state before code is considered ready.

## Example

```python
def fetch_events(source: CalendarSource, tz: ZoneInfo) -> list[CalendarEvent]:
    ...
```

## References
- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
- [PEP 585 – Type Hinting Generics In Standard Collections](https://peps.python.org/pep-0585/)
- [PEP 604 – Allow writing union types as X | Y](https://peps.python.org/pep-0604/)

## See Also
- docs/DB.md (for database model typing)
- .vscode/settings.json (for linter/type checker config)
- pyproject.toml (for Ruff config)
