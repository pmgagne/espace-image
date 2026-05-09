# Agentic FastAPI Hexagonal Guide

This document explains how to use the agentic assets added to this repository to scaffold or refactor FastAPI backends into a hexagonal architecture.

## Assets Included

### Prompt
- Path: `.github/prompts/recreate-fastapi-hexagonal-backend.prompt.md`
- Purpose: One-shot, guided execution to create a new backend/module structure.
- Best for: Quick bootstrap with explicit input variables.

### Agent
- Path: `.github/agents/fastapi-hexagonal-architect.agent.md`
- Purpose: Interactive specialist that enforces hexagonal boundaries and OpenAPI-first organization.
- Best for: Ongoing implementation conversations and iterative changes.

### Refactor Skill
- Path: `.claude/skills/fastapi-hexagonal-refactor/SKILL.md`
- Purpose: Migrate an existing FastAPI backend to `api/rest/internal` layout incrementally.
- Best for: Existing codebases where API contract stability matters.

### Scaffold Skill
- Path: `.claude/skills/fastapi-hexagonal-scaffold/SKILL.md`
- Purpose: Generate a fresh module with standard files and DI wiring.
- Best for: Greenfield modules and new services.

### Scaffold Templates
- Path: `.claude/skills/fastapi-hexagonal-scaffold/templates/`
- Purpose: Canonical code stubs used by the scaffold skill.
- Best for: Consistent outputs and reduced prompting variance.

## Copy Checklist (For Another Project)

Copy these files and folders together to preserve behavior:

1. `.github/prompts/recreate-fastapi-hexagonal-backend.prompt.md`
2. `.github/agents/fastapi-hexagonal-architect.agent.md`
3. `.claude/skills/fastapi-hexagonal-refactor/SKILL.md`
4. `.claude/skills/fastapi-hexagonal-scaffold/SKILL.md`
5. `.claude/skills/fastapi-hexagonal-scaffold/templates/README.md`
6. `.claude/skills/fastapi-hexagonal-scaffold/templates/api-interfaces.py.tmpl`
7. `.claude/skills/fastapi-hexagonal-scaffold/templates/api-schemas.py.tmpl`
8. `.claude/skills/fastapi-hexagonal-scaffold/templates/rest-router.py.tmpl`
9. `.claude/skills/fastapi-hexagonal-scaffold/templates/internal-entities.py.tmpl`
10. `.claude/skills/fastapi-hexagonal-scaffold/templates/internal-service.py.tmpl`
11. `.claude/skills/fastapi-hexagonal-scaffold/templates/internal-repository.py.tmpl`
12. `.claude/skills/fastapi-hexagonal-scaffold/templates/module-loader.py.tmpl`

Optional but recommended:

13. `docs/technotes/agentic-fastapi-hexagonal-guide.md`

## Decision Guide

- Use the prompt when you want one focused run with explicit inputs.
- Use the agent when you want iterative collaboration and architecture enforcement.
- Use the refactor skill for migration of existing routes/services.
- Use the scaffold skill for new modules.

## How To Use (Prompt, Agent, Skills)

### Prompt Usage
- Run the prompt file directly from Copilot Chat prompt picker.
- Select `recreate-fastapi-hexagonal-backend.prompt.md`.
- Provide requested inputs (`targetRoot`, `serviceName`, `moduleName`).

### Agent Usage
- Select the `FastAPI Hexagonal Architect` agent in Chat mode.
- Ask for concrete work, for example:
   - "Scaffold module artifacts with route prefix /artifacts."
   - "Refactor module artifacts to api/rest/internal while preserving OpenAPI."

### Skill Usage
- Skills are guidance packs used by compatible agent runtimes.
- In practice, usage is most reliable when you ask explicitly, for example:
   - "Use the fastapi-hexagonal-refactor skill to migrate module artifacts."
   - "Use the fastapi-hexagonal-scaffold skill to create module artifacts."
- If the runtime supports auto-selection, it may apply a skill automatically when your request matches; do not rely on this for critical tasks.

## Suggested Workflow

1. Choose the entry point:
   - Existing backend: start with `fastapi-hexagonal-refactor`.
   - New module/service: start with `fastapi-hexagonal-scaffold`.
2. Define module boundaries and target tree.
3. Generate or move files into `api/`, `rest/`, `internal/`.
4. Wire router registration in module/app bootstrap.
5. Validate OpenAPI output and run tests.
6. Repeat module-by-module for refactors.

## Architecture Rules to Keep

- `api/` contains public contracts (interfaces and DTOs).
- `rest/` is HTTP adapter only.
- `internal/` contains business logic and persistence.
- Avoid cross-module imports of `internal/` code.
- Keep external API behavior stable unless intentionally changed.

## Template Placeholder Conventions

In `.claude/skills/fastapi-hexagonal-scaffold/templates/`:
- `{{module}}`: module name in snake_case (example: `artifacts`)
- `{{Entity}}`: entity name in PascalCase (example: `Artifact`)
- `{{entity}}`: entity name in snake_case (example: `artifact`)

## Minimal Validation Checklist

- Imports resolve.
- Router is included in app/module bootstrap.
- Endpoints appear in OpenAPI docs.
- Response models match schema declarations.
- Boundaries are respected.

## Notes

These assets are designed to be reused in other repositories. Copy the prompt, agent, skills, and templates together to preserve behavior consistency.

Automatic behavior note:
- Prompt and agent usage is explicit (you select them).
- Skill usage may be automatic in some agent runtimes, but explicit invocation in your request gives the most predictable result.
