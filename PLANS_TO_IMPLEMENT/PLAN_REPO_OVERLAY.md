# Repo Planning Overlay

This file applies the portable [plan template](./PLAN_TEMPLATE.md) to this repository.
Keep the core plan shape in the portable template. Put only repo-local execution anchors here so the same format can be reused in future repos with a different overlay.

## Local Planning Entry Points

- Plan shapes: [PLAN_TEMPLATE.md](./PLAN_TEMPLATE.md)
- Source, QML, test, and focused-verification routing: [docs/agent_maps/INDEX.md](../docs/agent_maps/INDEX.md) and `.\venv\Scripts\python.exe .\scripts\nav.py find <term>`
- Canonical requirements and retained proof index: [docs/specs/INDEX.md](../docs/specs/INDEX.md)
- Historical packet manifests and templates live only in git history. Recover them only when the user explicitly requests a packet set.

## Local Packetization Defaults

- Do not create a packet map, `P00`, manifests, ledgers, or packet prompts for ordinary planning.
- If the user explicitly requests packetization, reserve `P00` for bootstrap only and split later packets at real ownership, dependency, or verification boundaries.
- A `T0x` task does not automatically require a matching packet.
- Keep explicit packet dependencies forward-only and make later packets inherit earlier contracts instead of reopening them.

## Local Verification Defaults

- Prefer the project venv for Python verification commands: `.\venv\Scripts\python.exe`.
- During implementation, run the smallest changed or new test module, class, or node ID from the owning route. Run the route-owned suite once after the last related task when adjacent proof is useful.
- Route-map verification commands are a menu, not a mandatory bundle. Record each selected command once in the plan and do not rerun it at both task and plan closeout.
- Use `fast` only for cross-route or shared-infrastructure work, impact that cannot be bounded confidently, or requested integration closeout. Use `gui` for broad multi-surface QML work, `slow` for performance closeout, and `full` for shell-wide composition, release confidence, or explicit requests.
- For focused UI, performance, and shell work, run the exact affected tests, benchmark, or shell target instead of the whole mode.

## Local Ownership Notes

- Name one primary source owner and one primary regression owner for both focused and expanded plans.
- Use `scripts/nav.py` and the owning agent map before widening shell, presenter, graph-scene, graph-canvas, edge-rendering, or viewer seams.
- Keep packet-owned QML on focused bridges and helper seams rather than reintroducing raw host globals.
