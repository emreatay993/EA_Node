# Workspace Instructions

- Keep this file as an agent-facing map, not a full project manual. Put durable details in repo docs or executable scripts, then link to those sources here.
- Prefer the project venv for all Python, PyQt6, Qt, pytest, QML, startup, smoke, and validation commands. The primary interpreter is `venv/Scripts/python.exe`, even from `bash`.
- Canonical source/dev launch: `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`. Treat root scripts and `.\main.py` references as legacy/packaging context unless the task explicitly targets them.
- Fresh setup: `py -3.10 -m venv venv`, then `.\venv\Scripts\python.exe -m pip install --upgrade pip`, then usually `.\venv\Scripts\python.exe -m pip install -e ".[all,dev]"`. `requirements.txt` is a convenience path, not separate dependency truth.
- Editable installs expose `corex-node-editor` and `corex-runtime`, but prefer the package-module launch command for source/dev sessions.

## Coding Communication Style

While coding, use plain running commentary instead of technical status language.

- Prefer short first-person sentences: "Now checking X", "Let me read Y", "I found Z", "Wiring A into B".
- Use concrete verbs like read, check, wire, launch, stop, render, fix, run, verify.
- Avoid abstract phrases like "implementation surface", "integration boundary", "behavioral contract", "high-risk area", and "validation strategy" unless they are necessary.
- Explain reasons briefly in practical terms: "to catch QML errors fast", "so the setting stays in sync", "before I edit the real files".
- Use casual transitions such as "Got it", "I have the picture", "Next I'm...", and "That's enough context".
- During longer coding work, narrate progress in the style of a pair programmer watching the task happen.
- Keep final summaries concrete: what changed, what command passed, what is still worth checking.

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

- Use exploration subagents wherever practical for codebase discovery. Frame each task as one concrete question with explicit scope, expected output, and stopping point. Set `model` and `reasoning_effort` explicitly when spawning.
- For narrow tasks with an exact file, symbol, UI label, error, setting, or test name, start from bounded source evidence with `rg`, inspect the first useful hits, then use `./venv/Scripts/python.exe scripts/nav.py source <path>` only when owner or focused-test context helps. Do not run a fuzzy `nav.py find` first as ceremony.
- Treat `scripts/nav.py` as an advisory compression layer, not ownership authority. `find` labels exact alias/title/component matches separately; "No confident owner" results are candidates that must be verified against source before choosing an owner or insertion point. Use `route`, `qml`, or `source` when that index family is already known, and do not read the raw 0.6 MB/3.4 MB indexes unless the compact CLI under-resolves.
- For broad or cross-layer codebase exploration, start with the committed navigation layer: `docs/agent_maps/INDEX.md`, `docs/agent_maps/COVERAGE.md`, `docs/agent_route_index.md`, and `docs/agent_route_index.json`. Open the relevant subsystem, feature-route, or testing map before reading source.
- For broad or ambiguous QML-heavy exploration, use `nav.py qml <term>` before widening into `ea_node_editor\ui_qml`; exact component/property/signal names should start with a bounded source search.
- For source/test ownership lookup, check `docs/source_test_file_index.md` after the route index identifies the likely area. Use it as a path inventory, not as ownership authority.
- For docs/spec/process questions, start with `docs/specs/INDEX.md` for requirements/proof authority and `docs/agent_maps/` for navigation ownership. Keep agent maps outside the spec index unless they become formal proof/spec artifacts.
- Before any broad text or file search such as `ea_node_editor\**`, `tests\**`, or `Get-ChildItem -Recurse`, record the map/index candidates already checked and why they are insufficient. Use one bounded exact-anchor search only inside the candidate subsystem, feature route, test family, or QML family when possible.
- Parent threads should record a compact navigation audit before broad/cross-layer edits: route index or map entries checked, source/test/QML candidates used, maps consulted, any broad searches used, and why the opened files are now safe to inspect.
- When spawning a broad or cross-layer explorer, include advisory map/index confirmation instructions. Exact narrow explorers should start from the named evidence and stop once the fact is supported. Explorer outputs should distinguish verified owners from weak or discarded navigation candidates and justify any broad searches.
- Explorer prompts for broad or cross-layer discovery should set a search budget and require every broad `rg`, `Select-String`, or recursive file search to be justified in the navigation audit.
- Explorer outputs should include a compact navigation audit with `Route index entries checked`, `Maps consulted`, `Source candidates`, `QML candidates`, `Test candidates`, `Searches run`, and `Fallback reason`. This keeps false starts visible without letting them drive implementation.
- Read-only explorers should not run tests, verification commands, package builds, or long-running repro commands unless the parent prompt explicitly asks for execution. They should list focused verification commands in their output and return the requested answer before any optional follow-up work.
- Exact-file, exact-symbol, UI-label, error-text, and setting-key lookups should start with a bounded exact-anchor search. Map consultation is optional unless ownership, architectural boundaries, or the proving test remain uncertain.
- While exploration is active, do not edit and do not assign editing work until the active explorer(s) return or terminate with an explicit error. Do not interrupt or reprompt an active repository explorer.
- For large or broad searches, split by focused scopes such as `core`, `ui`, `tests`, or `build/config`. Ignore duplicated/generated trees unless explicitly requested: `.claude/worktrees`, `build`, `artifacts`, `venv`, `__pycache__`, and `*.egg-info`.
- Before adding new utility/helper modules, perform a duplicate-abstraction check. Search by exact names and semantic terms, inspect common/shared helper folders, and use `$spark-fast-lookup` for a narrow existing-helper lookup when the likely area is known. Prefer reusing or promoting an existing helper over creating subsystem-local parallel helpers. When a new helper is still warranted, state why existing helpers do not fit.
- `ea_node_editor/common/` is the canonical home for dependency-light helpers shared by 2+ subsystems (`protocols.py`, `coercions.py`, `payload_tools.py`). Check there first; a utility used by two or more subsystems belongs there rather than as a subsystem-local copy. Keep `common/` a leaf — it must not import from `graph`, `ui`, `ui_qml`, `execution`, `persistence`, or `nodes`.
- Significant source files carry a top-of-file banner so an agent can orient from the first ~30 lines instead of reading the whole file: `# Purpose:` (one line), `# Map: <feature_routes/...|subsystems/...>` (owning agent map), `# Tests: tests/...` (focused test), and for files >1000 lines `# Landmarks:` (key classes / entry points). Keep these accurate when ownership or tests move; `scripts/check_agent_maps.py` validates that every `# Map:`/`# Tests:` header resolves.
- Explorer model defaults:
  - Project agent `spark_lookup` (`gpt-5.3-codex-spark` with `xhigh`): one tiny lookup only after a known file family or route-index/map entry narrows the target to one crisp fact.
  - `gpt-5.6-luna` with `xhigh`: optional high-volume exact lookups only when deterministic verification or automatic fallback is available; do not replace `spark_lookup` without a dedicated head-to-head benchmark.
  - `gpt-5.6-terra` with `xhigh`: default for repository navigation, from small map-bounded synthesis through broad or cross-layer feature tracing, ownership, insertion-point decisions, and new-feature mapping.
  - `gpt-5.6-sol` with `xhigh`: escalation when Terra leaves contradictory or insufficient evidence, or when navigation is part of high-risk architecture, implementation, security, performance, independent review, or genuinely long-context work.
- Spark explorer responses must be compact: direct answer, relevant files/symbols, then uncertainties or an escalation note. Do not use Spark for ownership tracing, insertion-point choice, "find all uses", feature flow, context/action wiring, or cross-layer QML/Python work. Query/search first, sample snippets second, keep the working set tiny, return once supported, and stop/escalate to `gpt-5.6-terra` if the first result fans out. Escalate Terra to `gpt-5.6-sol` only under the Sol conditions above.
- Use large wait windows for explorers, normally 180-300 seconds or longer for broad scopes.
- For work packets run via `subagent-work-packet-executor`, avoid status-check chatter; do not check status until at least 45 minutes have elapsed unless the packet finishes or hits a real blocker.
- Historical work-packet manifests and ledgers live only in git history. Use `docs/specs/INDEX.md` and `docs/specs/perf/` for retained QA evidence; use the work-packet runner scripts only with an explicitly supplied external packet set.
- Default to plain `rg`/`rg --files` so `.rgignore` keeps generated, vendor, cache, and worktree noise out of searches. Use broad `rg` only after the route index plus maps identify a candidate subsystem or small path set; when searching broadly is still necessary, cap or narrow output before reading it into context. After the first few useful `rg` hits, stop searching and return to the relevant map or generated index with those exact anchors before opening broad source ranges. Use `--hidden`, `-u`, or `--no-ignore` only when the task explicitly needs ignored paths.
- In this PowerShell environment, `rg` is acceptable only when `Get-Command rg.exe -All` shows a working non-Codex install earlier on `PATH` and `rg --version` succeeds. Otherwise use PowerShell-native `Get-ChildItem`/`Select-String`.
- Do not bundle many large file additions into one patch.
- Perform exact file moves/copies from the terminal with native commands such as `Move-Item` or `Copy-Item`, not by model rewrite.

## Third-party capability research

- Begin with authorized online documentation. Inspect an installed product only when the user explicitly authorizes it, keep the inspection read-only, and keep detailed evidence in the private corpus rather than this repository.

## Public repository privacy

- Treat vendor or competitor study material and its provenance as private unless the user explicitly approves publication.
- Use COREX or neutral functional terminology in tracked files, paths, generated outputs, commit messages, branch names, pull requests, and issues.
- Never publish study product names, proprietary file formats or namespaces, source identifiers, installed paths or versions, screenshots, hashes, comparative labels, or reverse-engineering notes.
- Keep private research outside the repository or under an existing ignored local artifact root. Confirm new research paths with `git check-ignore -v` before writing and never force-add them.
- Before every commit and push, inspect staged filenames, staged content, generated files, and the proposed commit message for private study provenance. Stop if publication status is unclear.
