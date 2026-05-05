# ADR-2026-05-04-modular-monolith-presenter-pattern.md

## Title
Adopt Modular Monolith, Presenter Pattern, and API/GUI Split for Espace-Image

## Status
Accepted

## Context
Espace-Image is evolving to support maintainable, testable, and scalable development. The legacy codebase mixed API, GUI, and business logic, making it hard to test, extend, or refactor. We need a clear separation of concerns, atomic service APIs, and a robust pattern for GUI rendering.

## Decision
- **Modular Monolith**: All business logic is organized into modules under `app/modules/<name>/`, each with clear boundaries and ownership of its infrastructure.
- **API/GUI Split**: All service APIs return DTOs (never HTML). GUI rendering is handled by dedicated presenter adapters in each module's infrastructure.
- **Presenter Pattern**: Each module exposes a `presenter.py` in `internal/infrastructure/` for rendering HTML fragments. Routers call presenters for GUI endpoints; services never return HTML.
- **Thin Routers**: Routers only parse requests, inject dependencies, and render responses (HTML or JSON). No business logic or template rendering in routers.
- **Unit Tests for Presenters**: Each presenter has minimal unit tests to prevent template drift and ensure correct rendering.
- **Strict DTO Boundaries**: All cross-layer data is passed as DTOs, never as raw ORM models or HTML.

## Consequences
- **Maintainability**: Clear module boundaries and separation of concerns make the codebase easier to maintain and extend.
- **Testability**: Presenter unit tests and atomic service APIs enable robust automated testing.
- **Scalability**: The modular monolith can be split into microservices if needed.
- **Template Safety**: Presenter tests catch template drift and rendering errors early.

## Alternatives Considered
- **Classic MVC**: Rejected due to tight coupling of business logic and rendering.
- **Service Layer with Embedded Templates**: Rejected to avoid mixing HTML with business logic.

## Implementation Notes
- All new modules must follow this pattern.
- Refactors must migrate legacy rendering to presenters.
- LLMs and code generation tools should be instructed to use this architecture (see LLM-instructions file).

## Architectural Overview (Consolidated)

### System Context
```
flowchart TD
	User[Admin/User]
	Browser[Web Browser]
	API[REST API / FastAPI]
	GUI[HTMX/HTML GUI]
	DB[(SQLite DB)]
	Scheduler[APScheduler]

	User -->|HTTP/HTMX| Browser
	Browser -->|HTTP| API
	Browser -->|HTML/HTMX| GUI
	API -->|SQLModel| DB
	GUI -->|SQLModel| DB
	API -->|Scheduler jobs| Scheduler
```
Espace-Image sits between users (via browser) and a SQLite database, exposing both RESTful APIs and HTML GUI endpoints. All business logic is encapsulated in module services, with GUI rendering handled by presenter adapters.

### Component Architecture
```
flowchart LR
	subgraph Module
		Service[Application Service]
		Presenter[Presenter Adapter]
		Infra[Infrastructure]
	end
	Router[FastAPI Router]
	DB[(SQLite DB)]
	Router --> Service
	Service --> Infra
	Router --> Presenter
	Presenter --> Infra
	Infra --> DB
```
- Routers are thin: parse requests, inject dependencies, render responses.
- Services expose atomic DTO-based APIs (no HTML returned).
- Presenters render HTML fragments for GUI routes only.
- Infrastructure handles DB, file, and external API integration.

### Deployment Architecture
```
flowchart TD
	Dev[Dev/Local]
	Staging[Staging]
	Prod[Production]
	App[Uvicorn FastAPI App]
	DB[(SQLite DB)]
	Static[Static Files]

	Dev --> App
	Staging --> App
	Prod --> App
	App --> DB
	App --> Static
```
- Single-process FastAPI app (Uvicorn)
- SQLite DB (file-based)
- Static files served by FastAPI
- APScheduler for background jobs
- Environments: dev, staging, prod (configurable)

### Data Flow
```
flowchart LR
	User -->|HTTP/HTMX| Router
	Router -->|DTO| Service
	Service -->|DB/Infra| Infrastructure
	Service -->|DTO| Router
	Router -->|HTML| Presenter
	Presenter -->|HTML| Router
	Router -->|HTML| User
```
- All data flows through DTOs (no HTML in services)
- Presenters only render HTML for GUI endpoints
- DB access and file ops isolated in infrastructure

### Key Workflows
```
sequenceDiagram
	participant User
	participant Browser
	participant Router
	participant Service
	participant Presenter
	participant DB
	User->>Browser: Request page
	Browser->>Router: HTTP/HTMX request
	Router->>Service: Get data (DTO)
	Service->>DB: Query/update
	Service-->>Router: Return DTO
	Router->>Presenter: Render HTML fragment
	Presenter-->>Router: HTML
	Router->>Browser: HTML response
```
- GUI routes: Router gets DTO from service, passes to presenter, returns HTML
- API routes: Router gets DTO from service, returns JSON

### Phased Development
#### Phase 1: Initial Implementation
- Migrate all presenter logic to `internal/infrastructure/presenter.py`
- Refactor routers to use presenters for HTML
- Ensure all services return DTOs only
- Add unit tests for presenters

#### Phase 2+: Final Architecture
- Centralize all GUI rendering in presenters
- Remove all HTML from service contracts
- Add more granular API endpoints as needed
- Expand test coverage for all modules

#### Migration Path
- Move inline/legacy rendering to presenters
- Refactor routers to call presenters
- Remove HTML from services
- Add/expand tests

### Non-Functional Requirements Analysis
#### Scalability
- Modular boundaries allow future extraction to microservices
- Stateless FastAPI app, can be containerized
#### Performance
- Thin routers, atomic services, and presenters keep request latency low
- SQLite is sufficient for current scale; can migrate to Postgres if needed
#### Security
- No business logic in routers; all input validated in services
- Admin UI protected by route-level controls
#### Reliability
- APScheduler for background jobs
- All times stored in UTC
#### Maintainability
- Clear module boundaries
- Presenter pattern isolates GUI rendering
- Unit tests for all presenters

### Risks and Mitigations
- Risk: Template drift between presenters and HTML — Mitigation: unit tests for presenters
- Risk: Tight coupling of GUI and service — Mitigation: strict DTO boundaries
- Risk: SQLite scalability — Mitigation: migration path to Postgres

### Technology Stack Recommendations
- FastAPI, SQLModel, APScheduler, HTMX, Jinja2
- Use `uv` for dependency management and scripts

### Next Steps
- Continue adding/expanding presenter tests
- Document presenter pattern in CONTRIBUTING
- Monitor for template drift and maintain test coverage

---
**See also:** LLM_ARCHITECTURE_INSTRUCTIONS.md for LLM/codegen guidance.
