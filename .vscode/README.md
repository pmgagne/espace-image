# VS Code Setup Guide

## Quick Start

### 1. Install Recommended Extensions
When you open the workspace, VS Code will prompt to install recommended extensions. Click **"Install All"** or:

```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
code --install-extension GitHub.copilot
code --install-extension GitHub.copilot-chat
```

### 2. Configure Python Environment
1. Open Command Palette: `Cmd+Shift+P`
2. Search: "Python: Select Interpreter"
3. Choose `.venv` or use `uv`

### 3. Verify Setup
- Open a Python file and check for linting squiggles
- Type code and Copilot should suggest completions
- Test formatting: `Cmd+Shift+X` → Format Document

---

## Configuration Files Overview

### `.vscode/settings.json`
**Project-specific VS Code settings**
- Ruff auto-format on save
- Strict Pylance type checking
- Copilot enabled for all file types
- 100-char line ruler
- Auto-import organization

### `.vscode/extensions.json`
**Recommended extension list**
- Automatically prompts for installation
- Ensures team consistency

### `.vscode/launch.json`
**Debug configurations** (F5 to run)
- **FastAPI**: Runs dev server with hot-reload
- **Pytest**: Runs all tests with verbose output
- **Current File**: Quick debug of active script

### `.vscode/tasks.json`
**Build/run tasks** (Cmd+Shift+B or Terminal → Run Task)
- `uv: sync dependencies` - Install/update deps
- `ruff: lint and check` - Run linter
- `ruff: format code` - Auto-format all files
- `pytest: run all tests` - Run test suite
- `pytest: run with coverage` - Coverage report
- `docker: build image` - Build Docker image
- `docker: run container` - Start via docker-compose

### `.editorconfig`
**Cross-editor consistency**
- Enforced indentation, line endings, charset
- Applies to all IDEs/editors that support it

### `pyproject.toml`
**Python project metadata & tooling config**
- Ruff linting rules (E, W, F, I, C, B, UP, etc.)
- Pytest discovery and output format
- Pyright strict type checking

---

## Key Features

### ✅ Auto-Formatting
Files auto-format on save with Ruff:
- Organize imports
- Fix simple errors
- Format to 100-char line length
- Double quotes for strings

### ✅ Code Quality
- Linting runs in background
- Errors/warnings appear in Problems panel
- Quick fixes available with `Cmd+.`

### ✅ Debugging
Press **F5** to launch debug configuration:
```
FastAPI → Starts at http://localhost:8000 with hot-reload
Pytest → Runs test suite with breakpoint support
```

### ✅ Copilot Integration
- Inline suggestions as you type
- Chat: `Cmd+Shift+I` for Copilot Chat
- Context-aware thanks to Pylance type info

### ✅ Testing
- Pytest Test Explorer visible in left sidebar
- Run/debug individual tests
- Coverage reports via tasks

---

## Common Commands

| Action | Shortcut |
|--------|----------|
| Quick Fix | `Cmd+.` |
| Format Document | `Cmd+Shift+X` |
| Copilot Chat | `Cmd+Shift+I` |
| Start Debugging | `F5` |
| Run Task | `Cmd+Shift+B` |
| Command Palette | `Cmd+Shift+P` |
| Open Problems | `Cmd+Shift+M` |
| Source Control | `Ctrl+Shift+G` |

---

## Troubleshooting

### Ruff not formatting on save
1. Verify extension installed: `ms-python.python` + `charliermarsh.ruff`
2. Check `.vscode/settings.json` has `"editor.defaultFormatter": "charliermarsh.ruff"`
3. Reload window: `Cmd+Shift+P` → "Reload Window"

### Copilot not suggesting code
1. Sign in: `Cmd+Shift+P` → "GitHub Copilot: Sign in"
2. Verify in settings: `"github.copilot.enable": { "*": true }`
3. Check Copilot status in Activity Bar

### Tests not discovered
1. Run `uv sync` to install pytest
2. Verify `pyproject.toml` has `testpaths = ["tests"]`
3. File names must match `test_*.py` pattern

### Python interpreter issues
1. `Cmd+Shift+P` → "Python: Clear Cached Interpreter"
2. Select interpreter again (choose `.venv`)
3. `uv sync` to ensure deps are installed

---

## Next Steps

1. **Run sync**: `Cmd+Shift+B` → "uv: sync dependencies"
2. **Check linting**: `Cmd+Shift+B` → "ruff: lint and check"
3. **Start developing**: Create files in `app/` or `tests/`
4. **Use Copilot**: Ask in chat or type code for suggestions
5. **Debug**: Press F5 to run FastAPI or Pytest

---

## Resources

- [VS Code Python Docs](https://code.visualstudio.com/docs/languages/python)
- [Ruff Docs](https://docs.astral.sh/ruff/)
- [Copilot Docs](https://github.com/features/copilot)
- [Pylance Docs](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance)
