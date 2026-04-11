# Plan: Global Repo-Aware `pymechanical-fixture-builder`

## Summary
Create a global Codex skill named `pymechanical-fixture-builder` under the global skills area so it can be reused across repos. The skill auto-triggers for requests about creating or modifying ANSYS Mechanical test inputs/outputs, adapts itself to repo-local fixture/test conventions when they are discoverable, and otherwise asks or fails clearly instead of guessing.

The skill’s default job is end-to-end fixture work: create or modify Mechanical examples in place, solve them in batch mode, emit the full reproducibility bundle, place artifacts where the repo expects them, and smoke-validate the outputs through the repo’s DPF-style consumption path when applicable.

## Key Changes
### Skill behavior
- Use `ansys.mechanical.core.launch_mechanical(...)` as the primary execution backend, batch-only.
- Default Mechanical target is ANSYS 2023 R2 (`v232`); if the user explicitly asks for “newest”, resolve and use the newest installed release.
- Treat local 2023 R2 syntax sources as authoritative: shipped XML docs and shipped Mechanical scripts first, venv stubs only as secondary hints.
- Auto-trigger on relevant requests involving Mechanical fixture generation/modification; no explicit skill name is required.

### Output contract
- Default output bundle for each fixture directory:
  - editable Mechanical project, preferring `.mechdat`
  - solved result files (`.rst`, `.rth`, or both as applicable)
  - the automation script used to create/modify the fixture
  - a machine-readable manifest
- Modifications are in-place by default.
- In-place updates must refresh the bundle and prune stale generated artifacts so the fixture directory remains coherent.

### Repo-aware behavior
- Detect repo conventions from existing fixture/test layout and place outputs in the local fixture area the repo already expects.
- If repo detection is not confident, ask or fail clearly; do not guess a path.
- Run downstream DPF smoke validation after solve when the repo exposes a DPF consumption path.

### Fixture/catalog scope
- V1 catalog centers on a reusable family: `cantilever core + bolted-contact variant`.
- Prefer small fixtures by default, but include one heavier template for edge-case/stress testing.
- Initial analysis coverage:
  - static structural
  - modal
  - steady-state thermal
  - transient thermal
  - transient structural
  - harmonic response
- Heavy template focus: high-mesh single-body transient structural case.
- Named selections are authored by default so downstream scoping has stable handles.
- Determinism target is `stable enough`, not strict exact-ID reproducibility.

## Public Interfaces
- Skill name: `pymechanical-fixture-builder`
- Invocation style:
  - automatic for relevant Mechanical fixture requests
  - natural-language inputs such as “create a small harmonic response Mechanical output fixture” or “modify this example in place to add a transient thermal result”
- Standard manifest fields:
  - analysis type
  - target Mechanical version
  - project file path
  - result file paths
  - units
  - named selections
  - expected result families / readable outputs
  - DPF-readable handles or assumptions
  - selected numeric expectations as tolerance ranges
- Default failure policy:
  - batch only
  - no UI fallback
  - no best-effort repo-path guessing

## Test Plan
- Verify creation of a small fixture for each supported analysis family using the V1 template family.
- Verify one heavier high-mesh transient structural fixture path.
- Verify in-place modification updates project/results/script/manifest and prunes stale artifacts.
- Verify manifest generation contains the agreed contract fields and tolerance-based numeric checks.
- Verify named selections are present and usable for DPF scoping.
- Verify DPF smoke validation succeeds for repos with existing DPF readers/tests.
- Verify “newest available” release targeting works when explicitly requested.
- Verify repo-detection failure produces a precise ask/fail outcome instead of silent fallback.

## Assumptions And Defaults
- Install as a global skill, not a repo-local-only skill.
- Use repo-aware scanning rather than requiring repo-local companion config in V1.
- Prefer `.mechdat` for saved projects unless an existing example already dictates otherwise.
- Use local `Ansys.ACT.WB1.xml` and shipped 2023 R2 scripts as the primary syntax authority.
- Numeric assertions are sparse and tolerance-based, not exact-value regression locks.
- The first implementation should bias toward DPF-consumable fixtures over broader Mechanical feature coverage.
