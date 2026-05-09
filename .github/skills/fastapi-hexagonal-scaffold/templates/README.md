# FastAPI Hexagonal Scaffold Templates

These templates are used by the `fastapi-hexagonal-scaffold` skill to generate a new module quickly.

## Placeholders

- `{{module}}`: module name in snake_case, example `artifacts`
- `{{Entity}}`: entity name in PascalCase, example `Artifact`
- `{{entity}}`: entity name in snake_case, example `artifact`

## Template Files

- `api-interfaces.py.tmpl`
- `api-schemas.py.tmpl`
- `rest-router.py.tmpl`
- `internal-entities.py.tmpl`
- `internal-service.py.tmpl`
- `internal-repository.py.tmpl`
- `module-loader.py.tmpl`

## Usage

1. Copy templates into your target module folders.
2. Replace placeholders.
3. Register router through your application/module bootstrap.
4. Add tests and real persistence logic.
