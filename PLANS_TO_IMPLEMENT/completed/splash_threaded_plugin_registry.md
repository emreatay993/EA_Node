# Threaded Plugin Registry Loading for Splash Screen

> Follow-up to: the M1 Breathe splash implementation at
> [`ea_node_editor/ui/splash/opening_screen.py`](../../ea_node_editor/ui/splash/opening_screen.py),
> wired in [`ea_node_editor/app.py`](../../ea_node_editor/app.py).
> Source design: [`.design_bundle_opening_screen/project/Opening Screen v3.html`](../../.design_bundle_opening_screen/project/Opening Screen v3.html).

## Summary

The M1 Breathe splash currently freezes because `create_shell_window()` runs on the main thread and blocks the Qt event loop for ~4.4s. Startup profiling (env-gated via `EA_PROFILE_STARTUP=1`) showed that a single pure-Python function, `build_default_registry()` at [`ea_node_editor/nodes/bootstrap.py`](../../ea_node_editor/nodes/bootstrap.py), accounts for **3.60s / 65%** of that build. The function does plugin discovery, Ansys DPF backend registration, and dynamic imports — zero Qt widget calls. This plan moves it onto a `QThread` that runs in parallel with the splash's boot animation, so the splash paints smoothly and the shell build on the main thread drops to ~0.8s (dominated by `_run_shell_startup_sequence`, addressed as an optional follow-up).

## Context — why threading, not chunking

The prior plan shape considered two paths:

1. Chunk `create_shell_window()` into phases driven by `QTimer.singleShot(0, …)`. This would be a 3–4 hour refactor of a 723-line file.
2. Move pre-widget I/O off the main thread.

Profiling (captured 2026-04-18) picked path 2 unambiguously:

| Phase | Time | Notes |
|---|---|---|
| `prim.build_default_registry` | **3.60s** | Pure Python, threadable |
| `coord.startup_sequence` | 0.81s | Not yet broken down — optional T03 |
| `bootstrap.import app` | 0.61s | Python import chain, unavoidable cold-start |
| `run.splash_show` | 0.35s | First-paint / font / icon caches |
| All other phases combined | <10ms | Noise |

`ea_node_editor/nodes/bootstrap.py` has no QWidget / QApplication / QPainter / QPixmap / QQuick references, so safe to run off the GUI thread. Costs come from:

- `sync_ansys_dpf_plugin_state(...)` — Ansys DPF state sync.
- `register_plugin_backends(ANSYS_DPF_PLUGIN_BACKENDS, registry, "ea_node_editor.nodes.builtins.ansys_dpf")` — heavy imports.
- `discover_and_load_plugins(registry, extra_dirs=…)` — filesystem scan + dynamic imports.

The user flagged that plugin/library count will grow over time, so the threading fix must be forward-looking: any additional plugin load cost should extend the splash duration gracefully, never reintroduce a freeze.

## Key Changes

- Introduce a `QThread`-hosted `_RegistryLoader` worker in a new
  [`ea_node_editor/ui/splash/registry_loader.py`](../../ea_node_editor/ui/splash/registry_loader.py) that runs `build_default_registry()` and emits `ready(NodeRegistry)` / `failed(Exception)`.
- Make the pre-built `NodeRegistry` injectable through `create_shell_window()`, the `ShellWindowDependencyFactory`, and `_create_shell_primitive_dependencies()`. When a registry is supplied, primitives skip the blocking build; when absent, fall back to the current behaviour (so tests, alternative entry points, and `--no-splash` harnesses stay green).
- Add a `SplashReadyCoordinator` in `app.py` (helper class, not a new module) that waits for **both** `OpeningSplash.boot_completed` and `registry ready` before kicking off `create_shell_window(registry=…)`. If registry loading is slower than the boot animation, the splash stays at 100% "Ready" — still painting (breathing core, sheen) because the main thread is no longer blocked.
- On registry load failure, log the exception and fall back to a main-thread `build_default_registry()` call so the app still boots.
- Retain the env-gated startup profiler in [`ea_node_editor/telemetry/startup_profile.py`](../../ea_node_editor/telemetry/startup_profile.py) for verification before / after.

## Public Interface Changes

- `ea_node_editor.ui.shell.composition.create_shell_window(registry: NodeRegistry | None = None)` — optional keyword, default `None` preserves existing callers.
- `ea_node_editor.ui.shell.composition.build_shell_window_composition(host, registry=None)` — same optional keyword.
- `ea_node_editor.ui.shell.composition.ShellWindowDependencyFactory.__init__(host, registry=None)` — same.
- `_create_shell_primitive_dependencies(host, state, registry=None)` — new keyword.
- New public-ish symbol: `ea_node_editor.ui.splash.registry_loader._RegistryLoader` is intentionally underscore-prefixed; only `app.py` instantiates it.

No QML, no settings, no persisted state touched.

## Execution Tasks

### T01 — Inject pre-built registry through the shell composition seam

- Goal: plumb an optional `NodeRegistry` argument through `create_shell_window` → `ShellWindowDependencyFactory` → `_create_shell_primitive_dependencies` with a safe `None` fallback, so the main-thread build can be skipped when the splash has already built the registry on a worker thread.
- Preconditions: `none`.
- Conservative write scope:
  - `ea_node_editor/ui/shell/composition.py` — add the keyword to `create_shell_window`, `build_shell_window_composition`, `ShellWindowDependencyFactory.__init__`, and `_create_shell_primitive_dependencies`; when a registry is passed, use it instead of calling `build_default_registry()`.
- Deliverables:
  - Signature change as above, fully backward-compatible (default `None`).
  - The existing `with phase("prim.build_default_registry"): …` block now wraps either the fallback call or a zero-cost `assert registry is not None` — adjust to reflect that it measures only the blocking case.
- Verification:
  - `./venv/Scripts/python.exe -c "from ea_node_editor.ui.shell.composition import create_shell_window; print('OK')"`.
  - Existing smoke `EA_PROFILE_STARTUP=1 EA_PROFILE_AUTOQUIT=1 ./venv/Scripts/python.exe main.py` still prints the same phase list (no functional change yet; registry is still built on the main thread because nothing passes it in).
  - `./venv/Scripts/python.exe -m pytest -n auto tests/` passes unchanged.
- Non-goals: do not introduce the worker thread or touch `app.py` in this task; do not widen the seam to also accept other pre-built primitives.
- Packetization notes: this is the seam-widening slice; safe to land on its own without T02.

### T02 — QThread-hosted registry loader + splash coordinator

- Goal: spin up `build_default_registry()` on a `QThread` when the splash is shown, and only kick off `create_shell_window(registry=…)` when **both** the splash boot sequence and the registry load are done. Fall back to main-thread build on failure.
- Preconditions: T01 landed (`registry=` kwarg exists).
- Conservative write scope:
  - New: `ea_node_editor/ui/splash/registry_loader.py` — defines a `QObject` worker class that owns the registry build, plus a `_RegistryLoader` handle that creates the `QThread`, moves the worker onto it, starts it, and emits `ready(NodeRegistry)` / `failed(str)` signals (pass the exception as a string to avoid cross-thread object ownership questions; log the original exception inside the worker).
  - `ea_node_editor/ui/splash/__init__.py` — re-export `_RegistryLoader` under an explicit name (e.g. `RegistryLoader`).
  - `ea_node_editor/app.py` — create the loader right after `splash.show_centered()`, hold state for `(boot_done, registry_or_error)`, and when both are present call `create_shell_window(registry=…)`, then `splash.finish(window)`. On `failed`, log and call `create_shell_window()` (no registry) — current slow path.
- Deliverables:
  - New loader module with a clean one-shot lifecycle: start once, emit once, thread and worker tear down cleanly via `QThread.quit()` + `wait()` wired to the emission.
  - `app.py` orchestration that is trivially readable: small inline coordinator class or pair of slots.
  - A one-line docstring on the loader documenting that `build_default_registry()` must stay Qt-widget-free (link to this plan).
- Verification:
  - Manual: `./venv/Scripts/python.exe main.py` — splash must animate continuously, breathing core must never freeze mid-progress, shell appears shortly after "Ready".
  - Profiling: `EA_PROFILE_STARTUP=1 EA_PROFILE_AUTOQUIT=1 ./venv/Scripts/python.exe main.py` — `prim.build_default_registry` should drop to <5ms (registry pre-supplied) and overall `run.create_shell_window` should drop from ~4.4s to ~0.8s.
  - Failure-path probe: temporarily raise inside `build_default_registry()`, confirm the fallback path still brings up the shell. Revert after.
  - `./venv/Scripts/python.exe -m pytest -n auto tests/` passes.
- Non-goals: do not try to chunk `coord.startup_sequence`; do not add progress reporting from inside the worker; do not expose the loader as a general-purpose background-work framework.
- Packetization notes: self-contained; depends only on T01. Safe to merge on its own once T01 is in.

### T03 — (optional) Break down and address `coord.startup_sequence`

- Goal: if the residual ~0.8s `coord.startup_sequence` freeze is visible after T02, instrument and reduce it. Likely drivers are session restore / workspace state load / QML component warm-up inside `_run_shell_startup_sequence(host)` at [`composition.py:673`](../../ea_node_editor/ui/shell/composition.py).
- Preconditions: T02 landed and the perceived freeze is still user-visible.
- Conservative write scope: `ea_node_editor/ui/shell/composition.py` (sub-phase instrumentation inside `_run_shell_startup_sequence`), plus whichever specific call site turns out to dominate — scope defined by the profile, not up front.
- Deliverables: sub-phase numbers for the top-level steps of `_run_shell_startup_sequence`; a targeted fix if any single step is >200ms and moveable; otherwise a note in this plan confirming it's acceptable.
- Verification: same profiler commands as T02.
- Non-goals: general refactor of startup sequence; do not chase phases under 50ms.
- Packetization notes: diagnostic-first task — do not open until T02 is in and the UX is still unsatisfactory. May also resolve as "wontfix".

## Work Packet Conversion Map

This plan is small enough that a full P00/P01/P02 packet split is overkill. If it does later fan out:

1. `P00 Bootstrap` — `none` (no manifest/ledger needed; plan is single-owner UI work).
2. `P01 Composition seam widening` — derived from T01.
3. `P02 Threaded registry loader` — derived from T02.
4. `P03 Startup-sequence reduction` — derived from T03, only if opened.

## Test Plan

- **Smoke imports.** `./venv/Scripts/python.exe -c "from ea_node_editor.app import run; from ea_node_editor.ui.splash import OpeningSplash"` — both tasks, before and after.
- **Profile capture, baseline vs. after.**
  - Baseline (T01 only): `prim.build_default_registry ~ 3600 ms`, shell build ~4400 ms.
  - After T02: `prim.build_default_registry ~ 0 ms`, shell build ~800 ms, total splash duration ≈ max(boot animation, registry load) + shell build.
- **Manual splash UX check.** Launch normally. Confirm the breathing core, sheen, and boot labels animate continuously from 0% through 100%. Confirm the shell appears shortly after "Ready".
- **Failure path.** Temporary raise inside `build_default_registry()`. Confirm the app still starts via the fallback main-thread build, and the failure is logged.
- **Regression tests.** `./venv/Scripts/python.exe -m pytest -n auto tests/` before each task.
- **Telemetry cleanliness.** With `EA_PROFILE_STARTUP` unset, no `[startup] …` lines appear on stderr.

## Assumptions

- `build_default_registry()` will remain Qt-widget-free. If a future plugin registration path needs to touch a QWidget, this assumption breaks and the worker must surface the work back to the main thread (deferred).
- `NodeRegistry` is a plain Python object; transferring it across a queued Qt signal keeps it on the main thread at consumption time.
- Python's import lock does not deadlock when imports happen from the worker thread alongside the main thread's Qt init. Empirically safe for this codebase (same pattern used in other Python Qt apps), but if we see hangs, fall back to starting the worker *after* the main-thread `QApplication` init (already the case — the worker starts after `splash.show_centered()`).
- The 1.2s minimum visible time on the splash (`finish(min_visible_ms=0)` currently disables it after T02 since the boot sequence itself now dictates duration) is adequate UX. We can revisit if the splash feels too short on fast machines.
- `_run_shell_startup_sequence` cost is acceptable as a <1s tail freeze at 100% "Ready" for now. T03 only opens if the user reports it feels stuck.
