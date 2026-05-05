# ADR-2026-05-01: Legacy UI (iPad2) Support and Deprecation

## Status
Accepted

## Context
The application provides a legacy slideshow UI at `/legacy` for iPad 2 and similar clients. This path uses different polling intervals and template globals (e.g., `legacy_weather_interval_ms`).

## Decision
- The `/legacy` route and associated templates will be maintained for iPad 2 compatibility until further notice.
- All new features and fixes should target the modern UI; legacy UI receives only critical bug fixes.
- Template globals with `legacy_` prefixes are retained for compatibility with legacy scripts.
- Deprecation of the legacy UI will be announced at least one release in advance.

## Consequences
- Code and templates for the legacy UI must be preserved and tested for as long as iPad 2 support is required.
- Documentation and onboarding should clarify the distinction between modern and legacy UI paths.

## Supersedes
- Any prior informal policy on legacy UI support.
