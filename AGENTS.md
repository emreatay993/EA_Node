# Workspace Instructions

- Keep this file as an agent-facing map, not a full project manual. Put durable details in repo docs or executable scripts, then link to those sources here.
- Prefer the project venv for all Python, PyQt6, Qt, pytest, QML, startup, smoke, and validation commands. The primary interpreter is `venv/Scripts/python.exe`, even from `bash`.
- Canonical source/dev launch: `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`. Treat root scripts and `.\main.py` references as legacy/packaging context unless the task explicitly targets them.
- Fresh setup: `py -3.11 -m venv venv`, then `.\venv\Scripts\python.exe -m pip install --upgrade pip`, then usually `.\venv\Scripts\python.exe -m pip install -e ".[all,dev]"`. `requirements.txt` is a convenience path, not separate dependency truth.
- Editable installs expose `corex-node-editor` and `corex-runtime`, but prefer the package-module launch command for source/dev sessions.

## Coding Communication Style

Use short, plain progress updates explaining what you are reading, checking, changing, or verifying and why. Finish with the concrete change, proving check, and material limitations.

## Repository Map and Authority

- Treat `ea_node_editor/` as layered source:
  - `graph/`: graph domain objects, invariants, transforms, hierarchy, effective-port rules, and mutation boundaries.
  - `execution/`: runtime snapshot assembly, protocol/client/worker flow, and execution-time payloads.
  - `persistence/`: `.cxproj` codecs, migrations, serializers, session/project conversion, and legacy document rejection.
  - `nodes/`: built-in node definitions, registries, package management, and plugin loading.
  - `ui/` and `ui_qml/`: shell composition, Qt/QML bridges, graph-scene/viewer-session surfaces, and presentation logic.
  - `workspace/`, `custom_workflows/`, and `telemetry/`: support layers with their own ownership; do not fold them into graph, persistence, or UI just because a feature crosses layers.
- Before broad exploration, consult `docs/agent_maps/INDEX.md` and the relevant coverage row. After implementation or architecture/feature changes, update affected agent maps and `docs/agent_maps/COVERAGE.md` in the same change; if no map update is needed, state that in the final response.
- `docs/specs/INDEX.md` is the authoritative specs entry point. `PROGRAM_REQUIREMENTS.txt` is upstream/draft input.
- Register durable packet closeout proof, such as QA matrices, from `docs/specs/INDEX.md` so the spec pack stays navigable.
- Regenerate generated architecture diagrams or exported artifacts with the documented script, for example `.\venv\Scripts\python.exe .\scripts\export_architecture_diagrams.py`; do not hand-edit generated outputs.
- App graphics/preferences are app-wide and live outside project `.cxproj` persistence. Do not store app settings in project documents unless an existing spec requires it.
- When app icon source assets change, regenerate the committed icon set with `.\venv\Scripts\python.exe .\scripts\generate_app_icons.py`.

## Compatibility Policy

- COREX is unreleased and unused. Do not preserve old internal APIs, aliases, legacy bridges, compatibility shims, or fallback paths by default.
- Prefer direct removals, renames, and call-site updates over adapter layers.
- Add or keep compatibility behavior only for a current spec, active test contract, external file-format migration, or explicit user request.
- If code appears legacy but may still be intended architecture, call it out directly instead of silently preserving it.

## Architecture Boundaries

- Keep `ea_node_editor.graph` independent of UI and persistence implementation details. Boundary adapters should flow from composition/bridge code, not through global installation or UI imports inside graph.
- Use graph-owned mutation paths. Do not bypass invariants with public raw-write helpers; current guardrails expect mutation services to use private model record writers such as `_add_node_record`.
- Keep execution snapshot assembly in `ea_node_editor.execution`. Runtime snapshot and worker runtime code must not import persistence codecs, migration overlays, or serializer internals directly.
- Keep `.cxproj` document conversion and legacy-envelope handling in `ea_node_editor.persistence`; do not reintroduce graph-domain persistence overlay state.
- Treat shell-backed modules, the `ui/shell/composition/` package, `ui_qml/graph_scene_bridge.py`, `ui_qml/viewer_session_bridge.py`, plugin loading, and QML graph-surface code as high-risk surfaces. Prefer focused tests around these files before broader edits.
- For startup changes, preserve the package bootstrap/composition path in `ea_node_editor.bootstrap` and `ea_node_editor.app`; do not move startup authority into root scripts.

## Verification Commands

- Use the smallest route-owned test module, class, or node ID that proves the changed behavior during implementation. Use the repo-owned verification runner for broader integration lanes:

```powershell
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full
```

- After the last task in a related group, run the owning route's focused suite once. Route-map commands are a menu of relevant checks, not a mandatory bundle, and the same command should not be repeated at task and plan closeout.
- Escalate to `fast` only for cross-route or shared-infrastructure changes, impact that cannot be bounded confidently, or an explicitly requested integration closeout. Use `gui` for broad multi-surface QML work, `slow` for performance closeout, and `full` for shell-wide composition changes, release confidence, or explicit requests. For a focused UI, performance, or shell fix, run the exact affected tests, benchmark, or shell target instead.
- For agent-run broad verification, prefer `--summarize-output` so phase logs go under `artifacts/verification_logs/` and only bounded failure tails enter context.
- For work packets, use the narrowest packet-owned verification commands recorded in the prompt or wrap-up when they prove the changed surface; do not replace them with broader repo-wide runs unless the packet asks for that or the escalation rules above apply.
- For graph-surface or passive-node UI work, run this focused gate when practical:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m unittest `
  tests.test_graph_surface_input_contract `
  tests.test_graph_surface_input_inline `
  tests.test_passive_graph_surface_host `
  tests.test_passive_image_nodes -v
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

- After changing specs, traceability, release docs, proof links, or verification docs, run:

```powershell
.\venv\Scripts\python.exe .\scripts\check_traceability.py
.\venv\Scripts\python.exe .\scripts\check_markdown_links.py
```

- After editing any `docs/agent_maps/**` map or regenerating `docs/agent_route_index.*`, run `.\venv\Scripts\python.exe .\scripts\check_agent_maps.py` to confirm every cited path still resolves. It also runs under `--mode fast` via `tests/test_agent_maps_hygiene.py`. Regenerate the route index with `.\venv\Scripts\python.exe .\scripts\generate_agent_route_index.py` when map citations change.
- For release/docs/verification closeout, also run the targeted pytest hygiene gates named by the owning packet or release doc, commonly `tests/test_run_verification.py`, `tests/test_traceability_checker.py`, `tests/test_packaging_configuration.py`, `tests/test_dead_code_hygiene.py`, and `tests/test_markdown_hygiene.py`.
- For graph/canvas performance work, use `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness ...`; treat offscreen/software runs as regression evidence, not display-attached release acceptance.
- Context-budget checks are historical/optional diagnostics only. Do not require `scripts/check_context_budgets.py` unless a task explicitly asks for that legacy diagnostic.
- `scripts/verification_manifest.py` is canonical for verification mode facts, shell-isolation targets, and published proof command constants. Update it together with docs when the workflow changes.

## Packaging and Generated Assets

- Default Windows package build: `.\scripts\build_windows_package.ps1 -PackageProfile base -Clean`. It runs an offscreen packaged-app startup smoke by default; use `-SkipSmoke` only intentionally.
- Default installer build from an existing package: `.\scripts\build_windows_installer.ps1 -PackageProfile base`.
- Signing verification: `.\scripts\sign_release_artifacts.ps1 -PackageProfile base -VerifyOnly`. Strict signing uses `-RequireSignedArtifacts` or `EA_SIGN_REQUIRE_SIGNED=1` with configured certificate/timestamp inputs.
- When touching `web/excalidraw_host` or `ea_node_editor/web_assets/excalidraw_host`, run `.\scripts\build_excalidraw_host.ps1`; it rebuilds the local bundle and fails if generated assets contain remote URL references.

## Exploration and Editing

- Start exact file, symbol, UI-label, error, setting, and test lookups with a bounded source search. Use `scripts/nav.py source <path>` only when owner or focused-test context is needed; do not begin a known-target lookup with fuzzy `nav.py find`.
- The [TypeSafe navigation pilot](docs/COREX_TYPESAFE_NAVIGATION.md) is available as `python -m scripts.nav_assist "<task>" [--json]` for explicitly requested development lookups. Routine agent invocation is disabled until its documented qualification gates pass. Inspect suggested source and test assertions before treating a candidate as an owner or proof.
- For broad or uncertain ownership, consult `docs/agent_maps/INDEX.md`, the relevant row in `docs/agent_maps/COVERAGE.md`, and one relevant subsystem, feature-route, or testing map. Query `docs/agent_route_index.md` and `docs/agent_route_index.json` through `scripts/nav.py` instead of reading large raw indexes when the compact query is sufficient.
- Treat maps and navigation results as advisory. Verify ownership against current source before editing; a fuzzy candidate is not an established owner. Stop when the requested answer and necessary proving-test context are supported; widen only for ambiguity, contradictory evidence, or an explicitly broader trace.
- Before broad source or test searches, identify the candidate subsystem using the route index plus maps, briefly explain why narrower evidence is insufficient, and cap the results. Report supporting source and remaining uncertainty without a mandatory audit form or field list.
- For ambiguous QML work, use `scripts/nav.py qml <term>` before widening into `ea_node_editor/ui_qml`; exact component/property/signal names still start with a bounded search. Use `route`, `qml`, or `source` when the index family is known.
- Use `docs/source_test_file_index.md` as a path inventory after identifying the relevant route, not as ownership authority. For requirements/proof questions, start with `docs/specs/INDEX.md`; agent maps remain navigation references unless formally registered as proof/spec artifacts.
- Before adding a helper, search exact names and semantic equivalents and inspect `ea_node_editor/common/`. Reuse or promote an existing helper when suitable; explain any new helper's need. Helpers shared by two or more subsystems belong in `common/`, which must remain a leaf with no imports from graph, UI/QML, execution, persistence, or nodes.
- Preserve source banners: `# Purpose:`, an owning `# Map:`, and focused `# Tests:` paths; files over 1000 lines also need `# Landmarks:`. Keep them accurate when ownership or tests move; `scripts/check_agent_maps.py` validates cited map/test paths.
- Prefer plain `rg`/`rg --files` so `.rgignore` excludes generated, vendor, cache, and worktree noise. Bound searches to the candidate subsystem; ignore `.claude/worktrees`, `build`, `artifacts`, `venv`, `__pycache__`, and `*.egg-info` unless explicitly needed. Use `--hidden`, `-u`, or `--no-ignore` only for a task that requires ignored paths.
- In PowerShell, use `rg` only when `Get-Command rg.exe -All` shows a working non-Codex installation first on `PATH` and `rg --version` succeeds. Otherwise use `Get-ChildItem`/`Select-String`.
- Do not bundle many large file additions into one patch. Historical work-packet manifests/ledgers remain in Git history; use work-packet runners only with an explicitly supplied external packet set and its verification requirements.

## Third-party capability research and publication

- Begin with authorized public documentation. Inspect an installed product only when the user explicitly authorizes it and keep the inspection read-only.
- This repository may be public. Original COREX source, tests, requirements, design decisions, and factual comparisons may name Synera or another product when the reference is relevant and the wording clearly distinguishes public facts, observations, and inferences from COREX behavior.
- Do not commit credentials, license material, non-public vendor documents, copied proprietary source or binaries, model weights, customer data, or substantial copyrighted content. Keep such material outside the repository or under an existing ignored local artifact root; confirm new research paths with `git check-ignore -v` and never force-add them.
- Do not treat product names, public file-format names, public namespaces, versions, citations, compatibility notes, or comparative labels as publication blockers by themselves.
- Before a commit or push that includes third-party research material, inspect the staged content for secrets and non-public or copied proprietary artifacts. Resolve concrete findings; do not stop publication merely because Synera or another vendor is mentioned.
