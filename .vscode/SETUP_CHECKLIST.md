# VS Code Setup Checklist

Complete these steps to get your VS Code workspace fully configured:

## ✅ Phase 1: Extensions (5 min)

- [ ] Open `.vscode/extensions.json` (you'll see a prompt on workspace open)
- [ ] Click "Install Recommendations" button
  - Or manually run: `code --install-extension ms-python.python charliermarsh.ruff GitHub.copilot GitHub.copilot-chat`
- [ ] Wait for all extensions to finish installing
- [ ] Verify in Extensions sidebar:
  - [ ] `ms-python.python` (Python)
  - [ ] `ms-python.vscode-pylance` (Pylance)
  - [ ] `charliermarsh.ruff` (Ruff)
  - [ ] `GitHub.copilot`
  - [ ] `GitHub.copilot-chat`

## ✅ Phase 2: Python Interpreter (3 min)

- [ ] Press `Cmd+Shift+P` → "Python: Select Interpreter"
- [ ] Choose `./.venv` (if using venv) or workspace Python
- [ ] Verify status bar shows Python version (bottom right)
  - Should show: `Python 3.13.x` or similar
- [ ] Run task: `Cmd+Shift+B` → "uv: sync dependencies"
  - Terminal should complete with ✓

## ✅ Phase 3: Copilot Authentication (2 min)

- [ ] Press `Cmd+Shift+P` → "GitHub Copilot: Sign in"
- [ ] Follow browser auth flow (GitHub login)
- [ ] Return to VS Code - should say "✓ Authenticated"
- [ ] Open Copilot Chat: `Cmd+Shift+I`
  - Should show chat panel ready for input

## ✅ Phase 4: Verify Settings (2 min)

- [ ] Open `.vscode/settings.json`
- [ ] Press `Cmd+Shift+P` → "Preferences: Open Settings (JSON)"
- [ ] Verify these are set:
  ```json
  "editor.defaultFormatter": "charliermarsh.ruff"
  "editor.formatOnSave": true
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit"
    }
  }
  ```

## ✅ Phase 5: Test Formatting (2 min)

- [ ] Create/open a Python file: `app/test_copilot.py`
- [ ] Add messy code:
  ```python
  import os,sys
  def  foo(  ):
    x=1
    return x
  ```
- [ ] Press `Cmd+Shift+X` (Format Document)
- [ ] Should auto-format to Ruff style (correct spacing, line length)
- [ ] Delete the test file: `rm app/test_copilot.py`

## ✅ Phase 6: Test Linting (2 min)

- [ ] Run task: `Cmd+Shift+B` → "ruff: lint and check"
- [ ] Terminal shows results (should be mostly ✓)
- [ ] Open Problems panel: `Cmd+Shift+M`
- [ ] Should see Python linting feedback
- [ ] Verify no errors on legitimate code

## ✅ Phase 7: Test Pytest (3 min)

- [ ] Run task: `Cmd+Shift+B` → "pytest: run all tests"
- [ ] Terminal runs: `uv run pytest tests/ -v`
- [ ] All tests should pass (or show failures if any)
- [ ] Click test icons in left margin to run individual tests
  - If not visible: `Cmd+Shift+P` → "Python: Discover Tests"

## ✅ Phase 8: Test Debugging (3 min)

- [ ] Open `app/main.py`
- [ ] Add breakpoint: Click left margin next to a line number (red dot appears)
- [ ] Press `F5` → "FastAPI" debug configuration
- [ ] Should start server: "Uvicorn running on http://localhost:8000"
- [ ] Open browser: `http://localhost:8000`
- [ ] Should hit breakpoint (highlights line, shows variables)
- [ ] Press `F5` or `Ctrl+C` in terminal to stop

## ✅ Phase 9: Test Copilot Suggestions (3 min)

- [ ] Create file: `app/demo.py`
- [ ] Type comment: `# Function to calculate factorial`
- [ ] Press `Enter` and wait - Copilot should suggest code
- [ ] Tab to accept or keep typing to customize
- [ ] Type: `def process_image(` and wait for parameter suggestions
- [ ] Delete test file: `rm app/demo.py`

## ✅ Phase 10: Final Verification (1 min)

- [ ] Check status bar indicators:
  - [ ] ✓ Python version shown (bottom right)
  - [ ] ✓ Ruff linter active (may show "0" issues)
  - [ ] [ ] Copilot authenticated (Copilot icon in editor)
- [ ] Extensions sidebar shows 5+ Python-related extensions installed
- [ ] No red error icons in Problems panel for legitimate code

---

## 🎉 You're Done!

Your VS Code is now configured for optimal Copilot-assisted development:
- ✅ Auto-formatting on save
- ✅ Real-time linting feedback
- ✅ Type checking (strict mode)
- ✅ Copilot code suggestions
- ✅ Debug configurations ready
- ✅ Test discovery & execution
- ✅ Consistent coding standards

## Quick Reference

| Action | Shortcut |
|--------|----------|
| Format | `Cmd+Shift+X` |
| Copilot Chat | `Cmd+Shift+I` |
| Debug | `F5` |
| Run Task | `Cmd+Shift+B` |
| Problems | `Cmd+Shift+M` |
| Tests | Look for ▶️ icons in editor |

## Troubleshooting

If anything isn't working:
1. **Restart VS Code**: `Cmd+Shift+P` → "Reload Window"
2. **Check Python path**: `Cmd+Shift+P` → "Python: Clear Cached Interpreter"
3. **Reinstall extensions**: Uninstall and reinstall from Extensions
4. **Read `.vscode/README.md`** for detailed troubleshooting
5. **Check console logs**: View → Output → Select channel (Python, Pylance, Ruff)

Happy coding! 🚀
