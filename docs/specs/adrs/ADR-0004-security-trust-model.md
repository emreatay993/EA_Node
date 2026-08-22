# ADR-0004: Script Trust Model

- Status: Historical, non-authoritative
- Date: 2026-03-01

## Current Authority
This ADR is retained as historical context. The current requirements pack supersedes it by requiring plugin, add-on, runtime backend, toolchain, and artifact descriptor contracts before broad foreign-language or compiled-node execution surfaces are treated as public interfaces.

## Decision
Treat custom scripts/plugins as trusted local code in the early skeleton, constrained by explicit descriptor contracts as the platform matures.

## Rationale
- Enables rapid engineering workflow adoption.
- Avoids early sandbox complexity while descriptor-driven plugin and toolchain contracts mature.

## Consequences
- Requires clear warnings and audit logging.
- Strict sandbox/signing is deferred to a future milestone, and descriptor-based capability boundaries remain the authoritative modernization direction.
