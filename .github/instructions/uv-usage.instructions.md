---
description: 'Python project management standards using uv'
applyTo: '**/*.py, **/pyproject.toml'
---

# Python Project Management with uv

## Dependency Management

- Use `uv add <package>` to add runtime dependencies.
- Use `uv add --dev <package>` for development dependencies.
- Use `uv sync` to align the environment with `uv.lock`.
- Never use `pip`, `poetry`, or `venv` directly.

## Running Commands

- Prefix all Python command execution with `uv run` (e.g., `uv run pytest`).
- Use `uv tool run <tool>` for one-off CLI tools.

## VS Code Debugging

- The Python interpreter is at `.venv/bin/python` (Unix) or `.venv/Scripts/python.exe` (Windows).
- In `.vscode/launch.json`, use `"python": "${command:python.interpreterPath}"` and select the `.venv` created by `uv` via "Python: Select Interpreter".
- To debug without a `launch.json`:
  ```bash
  uv run python -m debugpy --wait-for-client --listen 5678 your_script.py
  ```
