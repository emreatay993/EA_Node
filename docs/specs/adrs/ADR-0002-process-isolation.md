# ADR-0002: Runtime Isolation

- Status: Historical, non-authoritative
- Date: 2026-03-01

## Current Authority
This ADR is retained as historical context. The current requirements pack supersedes it by treating the typed command/event protocol as the planned public headless execution API, with the QML shell as one runtime client.

## Decision
Execute workflow runs in a dedicated worker process communicating with runtime clients via queue-based commands/events.

## Rationale
- Keeps UI responsive under heavy node execution.
- Contains execution crashes and exceptions outside UI process.

## Consequences
- Requires explicit serialization of run payloads.
- Pause/stop semantics must be handled through protocol evolution.
