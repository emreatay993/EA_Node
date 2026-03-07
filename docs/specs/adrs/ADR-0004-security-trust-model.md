# ADR-0004: Script Trust Model

- Status: Accepted
- Date: 2026-03-01

## Decision
Treat custom scripts/plugins as trusted local code in v1 skeleton.

## Rationale
- Enables rapid engineering workflow adoption.
- Avoids early sandbox complexity while core platform matures.

## Consequences
- Requires clear warnings and audit logging.
- Strict sandbox/signing is deferred to future milestone.
