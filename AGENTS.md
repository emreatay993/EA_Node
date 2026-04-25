# Workspace Instructions

- Keep this file as an agent-facing map, not a full project manual. Put durable details in the repo docs or executable scripts, then point agents to those sources from here.
- Always check for and prefer the project-local virtual environment before using the shell default Python.
- For this repository, the primary interpreter is `venv/Scripts/python.exe` because the project uses a Windows-style virtualenv layout even when accessed from `bash`.
- Before claiming Python, PyQt6, Qt, `pytest`, or QML tooling is unavailable, verify them with the project venv first.
- When running tests, startup smoke checks, or Qt/QML validation, try the project venv interpreter before falling back to system Python.
- The canonical source/dev launch command is `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`. Treat root-level launch scripts or older `.\\main.py` references as legacy or packaging context unless the task explicitly asks about them.
- Install/update dependencies through the project venv, usually `.\venv\Scripts\python.exe -m pip install -e ".[all,dev]"`. `requirements.txt` is a convenience path, not a separate source of dependency truth.

## Repository Map and Authority

- Treat `ea_node_editor/` as layered source, not one flat feature area:
  - `graph/` owns graph domain objects, invariants, transforms, hierarchy, effective-port rules, and mutation boundaries.
  - `execution/` owns runtime snapshot assembly, protocol/client/worker flow, and execution-time payloads.
  - `persistence/` owns `.sfe` project codecs, migrations, serializers, session/project document conversion, and legacy document rejection.
  - `nodes/` owns built-in node definitions, registries, package management, and plugin loading.
  - `ui/` and `ui_qml/` own shell composition, Qt/QML bridges, graph-scene/viewer-session surfaces, and presentation logic.
  - `workspace/`, `custom_workflows/`, and `telemetry/` are support layers with their own ownership; do not fold their concerns into graph, persistence, or UI code just because a feature crosses layers.
- Treat `docs/specs/INDEX.md` as the authoritative specs entry point. `PROGRAM_REQUIREMENTS.txt` is upstream/draft input, not the final requirements source.
- When docs mention generated architecture diagrams or exported artifacts, regenerate them with the documented script such as `.\venv\Scripts\python.exe .\scripts\export_architecture_diagrams.py`; do not hand-edit generated outputs.
- App graphics/preferences are app-wide and live outside project `.sfe` persistence. Do not store app settings in project documents unless an existing spec explicitly requires it.

## Architecture Boundaries

- Keep `ea_node_editor.graph` independent of UI and persistence implementation details. Boundary adapters should flow in from composition/bridge code, not through global installation or imports from UI modules inside graph.
- Use graph-owned mutation paths. Do not bypass invariants by adding public raw-write helpers; current guardrails expect mutation services to use private model record writers such as `_add_node_record` and related internal methods.
- Keep execution snapshot assembly in `ea_node_editor.execution`. Runtime snapshot and worker runtime code should not import persistence codecs, migration overlays, or serializer internals directly.
- Keep `.sfe` document conversion and legacy-envelope handling in `ea_node_editor.persistence`; do not reintroduce graph-domain persistence overlay state.
- Treat shell-backed modules, `ui/shell/composition.py`, `ui_qml/graph_scene_bridge.py`, `ui_qml/viewer_session_bridge.py`, plugin loading, and QML graph-surface code as high-risk surfaces. Prefer focused tests around these files before broader edits.
- For startup changes, preserve the package bootstrap/composition path in `ea_node_editor.bootstrap` and `ea_node_editor.app`; do not move startup authority into root scripts.

## Verification Commands

- Prefer the repo-owned verification runner over ad hoc broad `pytest`:

```powershell
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full
```

- Use `fast` for the normal day-to-day regression slice. Use `gui` for QML-heavy changes, `slow` for performance/long-running checks, and `full` when shell-backed behavior or release confidence matters. `full` owns the dedicated shell-isolation phase.
- For graph-surface or passive-node UI work, run the focused graph-surface gate when practical:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m unittest `
  tests.test_graph_surface_input_contract `
  tests.test_graph_surface_input_inline `
  tests.test_passive_graph_surface_host `
  tests.test_passive_image_nodes -v
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

- After changing specs, traceability, release docs, proof links, or verification docs, run the relevant docs/proof checks:

```powershell
.\venv\Scripts\python.exe .\scripts\check_traceability.py
.\venv\Scripts\python.exe .\scripts\check_markdown_links.py
.\venv\Scripts\python.exe .\scripts\check_context_budgets.py
```

- `scripts/verification_manifest.py` is the canonical place for verification mode facts, shell-isolation targets, context-budget command strings, and published proof command constants. Update it together with docs when the workflow changes.

## Exploration and Editing

- Use exploration subagents wherever practical for codebase discovery to reduce main-thread context usage.
- Frame each exploration subagent task as one concrete question with an explicit scope, expected output, and stopping point. Prefer asks like "find the owner of X under `ea_node_editor/graph` and list up to 3 relevant files" over open-ended "understand X across the repo" prompts.
- If a prompt asks for more than one deliverable such as location plus owner plus insertion point plus existence check, treat it as a multi-step exploration task and start with `gpt-5.4-mini` instead of Spark.
- For large codebases or broad search tasks, the parent thread should recognize when one wide exploration pass is likely to bloat context or risk compaction, split the work into focused scopes (for example by directory, subsystem, or feature area), and spawn multiple dedicated explorer subagents when helpful. Prefer several narrow, explicit passes such as `core`, `ui`, `tests`, or `build/config` over one catch-all exploration pass.
- Unless explicitly requested, exploration should ignore duplicated or generated trees such as `.claude/worktrees`, `build`, `artifacts`, `venv`, `__pycache__`, and `*.egg-info` so searches stay on the live source tree.
- For `gpt-5.3-codex-spark` exploration, keep each agent to one exact lookup target in one already-identified area. Do not ask Spark for repo-wide synthesis, broad architecture tracing, completeness passes, ownership tracing across modules, or any task where the search area is still uncertain.
- If the parent thread spawns an explorer subagent for repository exploration, treat that explorer as the active exploration pass. The parent thread must not interrupt, reprompt, or otherwise interfere with that explorer before it either returns output to the parent thread or terminates with an explicit terminal error.
- Do not start editing, and do not send editing work to any subagent, until the active exploration subagent(s) have either returned output to the parent thread or ended with a terminating error, and their findings have been incorporated.
- When spawning explorer subagents, set `model` and `reasoning_effort` explicitly. Do not rely on inherited defaults from the parent thread.
- Use large wait windows for exploration subagents so parent threads do not repeatedly interrupt or crowd the exploration pass while it is still running. Prefer waits in the 180-300 second range or longer per exploration-agent invocation when the task scope justifies it.
- For work packets run via `subagent-work-packet-executor`, avoid status-check chatter. Do not perform or report a status check until at least 45 minutes have elapsed, unless the packet finishes or hits a real blocker.
- Default explorer model selection:
  - Use `gpt-5.3-codex-spark` with `xhigh` only for extremely narrow lookups where the parent already knows the likely directory or file family and needs one fact such as one symbol definition, one settings key, one file path, or one short usage check.
  - Use `gpt-5.4-mini` with `xhigh` by default for exploration work, including most repository scans, feature tracing, symbol usage searches, and light synthesis across more than a couple of files.
  - Use `gpt-5.4` with `xhigh` only for genuinely deep exploration that needs substantial cross-module reasoning, ambiguous architecture tracing, or long-context synthesis across many files.
- Operational rules for `gpt-5.3-codex-spark` explorers:
  - Require a compact response shape: direct answer first, then relevant files/symbols, then uncertainties or an escalation note.
  - Spark is only for one factual lookup. If the prompt asks both "where is it" and "where should I insert a change" or asks for likely ownership, use `gpt-5.4-mini`.
  - Use Spark only when the parent can name the likely directory, subsystem, or file family up front. If the search space is still unknown, start with `gpt-5.4-mini`.
  - Use Spark only when the expected result is small and crisp. If the likely answer needs comparison, synthesis, or ranking across multiple candidates, start with `gpt-5.4-mini`.
  - Do not use Spark for "find all uses", "understand the flow", "which module owns this behavior", "trace this feature", "where is the action wiring", "what is the likely insertion point", or anything likely to fan out across directories.
  - Do not use Spark for cross-layer questions that may touch more than one stack such as QML plus Python, UI plus command bridge, or menu declaration plus action dispatch.
  - Search first and sample snippets second; avoid whole-file reads unless a file is short and clearly central.
  - Return as soon as the first useful answer is supported. Do not keep searching for exhaustive coverage after the main hits are found.
  - Keep the working set very small: target 1 directory, at most 4 file opens, or roughly 250 total lines read per Spark pass.
  - If the first search produces many hits, multiple plausible owners, or results across subsystem boundaries, stop immediately and escalate to `gpt-5.4-mini` instead of continuing.
- If the task is mostly "find where X is defined/used" or "list the places related to Y", use `gpt-5.4-mini` by default unless the parent already knows the exact directory or a very small file family to search.
- Questions like "where is the context menu or action wiring for comment nodes or graph items defined, and what is the likely insertion point for a comment-node-only action?" must start with `gpt-5.4-mini`, not Spark.
- In this workspace's PowerShell environment, the Codex-bundled `rg.exe` resolves on `PATH` but is not runnable and fails with `Access is denied`. Do not probe or prefer `rg` here unless a different working `rg.exe` is installed earlier on `PATH`; use PowerShell-native search commands (`Get-ChildItem`, `Select-String`) by default.
- Do not bundle many large file additions into one patch.
- Perform exact file move/copy operations from the terminal rather than by AI rewrite, because rewrites can miss details in long documents.
- When a task requires a file move or an exact file copy, perform that operation directly from the terminal with native file commands such as `Move-Item` or `Copy-Item` instead of rewriting the document through the model, because long-document rewrites can miss details.
