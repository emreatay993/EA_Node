# ADR-0003: Project Format

- Status: Historical, non-authoritative
- Date: 2026-03-01

## Current Authority
This ADR is retained as historical context. The current requirements pack supersedes it with strict current-schema `.cxproj` loading: because Corex is pre-release, old envelopes and pre-current project documents may be rejected instead of preserved through load-time compatibility shims.

## Decision
Use versioned JSON `.cxproj` as canonical persisted project format.

## Rationale
- Human-readable and easy to diff/review.
- Schema versioning enables strict current-schema validation and explicit offline conversion outside ordinary project load.

## Consequences
- Large datasets may need managed sidecar assets, artifact references, or future binary optimizations.
- Deterministic ordering is required for stable output.
