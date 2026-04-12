# Repo Planning Overlay

This file applies the portable [plan template](./PLAN_TEMPLATE.md) to this repository.
Keep the core plan shape in the portable template. Put only repo-local execution anchors here so the same format can be reused in future repos with a different overlay.

## Local Planning Entry Points

- Canonical packet/spec index: [docs/specs/INDEX.md](../docs/specs/INDEX.md)
- UI packet ownership map: [docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md](../docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md)
- UI packet authoring template: [docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md](../docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md)
- Multi-thread packet planning skill: [.agents/skills/work-packet-planner/SKILL.md](../.agents/skills/work-packet-planner/SKILL.md)

## Local Packetization Defaults

- If a plan becomes a work-packet set, reserve `P00` for bootstrap only.
- Treat each `T0x` execution task as the default starting point for one follow-on packet boundary.
- When a task crosses a stable subsystem seam, split it before packetization instead of expanding the packet write scope.
- Keep packet dependencies forward-only and make later packets inherit earlier contracts instead of reopening them.

## Local Verification Defaults

- Prefer the project venv for Python verification commands: `.\venv\Scripts\python.exe`.
- When the scope enters packet-owned UI seams, inherit verification anchors from the owning source packet and owning regression packet rather than inventing a fresh ad hoc test surface.
- Keep the verification scope as narrow as the task or packet boundary allows.

## Local Ownership Notes

- For packetized UI work, name one primary source owner and one primary regression owner.
- Reuse the UI subsystem packet index and the feature packet template above before widening shell, presenter, graph-scene, graph-canvas, edge-rendering, or viewer seams.
- Keep packet-owned QML on focused bridges and helper seams rather than reintroducing raw host globals.
