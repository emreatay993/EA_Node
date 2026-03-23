# EA Node Editor Spec Pack

This is the canonical requirements/specification set for the Windows-first PyQt6 skeleton core implementation.

`PROGRAM_REQUIREMENTS.txt` remains an upstream source draft. This spec pack is authoritative for implementation.

## Spec Modules

1. [Architecture](requirements/10_ARCHITECTURE.md)
2. [UI/UX](requirements/20_UI_UX.md)
3. [Graph Model](requirements/30_GRAPH_MODEL.md)
4. [Node SDK](requirements/40_NODE_SDK.md)
5. [Node Execution Model](requirements/45_NODE_EXECUTION_MODEL.md)
6. [Execution Engine](requirements/50_EXECUTION_ENGINE.md)
7. [Persistence](requirements/60_PERSISTENCE.md)
8. [Integrations](requirements/70_INTEGRATIONS.md)
9. [Performance](requirements/80_PERFORMANCE.md)
10. [QA + Acceptance](requirements/90_QA_ACCEPTANCE.md)
11. [Traceability Matrix](requirements/TRACEABILITY_MATRIX.md)

Work-packet manifests and wrap-ups under `docs/specs/work_packets/` are kept local and are not published in Git.

## ADRs

1. [ADR-0001 UI Stack](adrs/ADR-0001-ui-stack.md)
2. [ADR-0002 Runtime Isolation](adrs/ADR-0002-process-isolation.md)
3. [ADR-0003 Project Format](adrs/ADR-0003-project-format.md)
4. [ADR-0004 Script Trust Model](adrs/ADR-0004-security-trust-model.md)
