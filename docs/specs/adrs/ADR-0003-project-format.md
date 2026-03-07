# ADR-0003: Project Format

- Status: Accepted
- Date: 2026-03-01

## Decision
Use versioned JSON `.sfe` as canonical persisted project format.

## Rationale
- Human-readable and easy to diff/review.
- Simple migration strategy via schema version.

## Consequences
- Large datasets may need external assets or future binary optimizations.
- Deterministic ordering is required for stable output.
