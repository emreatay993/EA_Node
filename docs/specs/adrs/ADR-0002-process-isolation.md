# ADR-0002: Runtime Isolation

- Status: Accepted
- Date: 2026-03-01

## Decision
Execute workflow runs in a dedicated worker process communicating with UI via queue-based commands/events.

## Rationale
- Keeps UI responsive under heavy node execution.
- Contains execution crashes and exceptions outside UI process.

## Consequences
- Requires explicit serialization of run payloads.
- Pause/stop semantics must be handled through protocol evolution.
