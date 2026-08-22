# Core Web Host Layer For Excalidraw

## Summary
Build the prerequisite COREX host layer before implementing the full Excalidraw plugin. The first milestone is a passive web-editor surface that can load a bundled React app, exchange JSON state with Python, persist state in node properties, and open from a graph node into fullscreen editing.

## Key Changes
- Add `PyQt6-WebEngine>=6.10` as a core runtime dependency and keep startup graceful only for unsupported/headless WebEngine fallback environments.
- Add a COREX web-surface bridge using Qt WebChannel:
  - Python exposes `load_state`, `save_state`, `asset_request`, and `export_preview` style methods.
  - JavaScript sends debounced scene updates as plain JSON.
  - Bridge must reject oversized/non-JSON payloads with visible error state.
- Add a passive node/editor hook:
  - Node type: `excalidraw.board`
  - `runtime_behavior="passive"`
  - hidden JSON property: `excalidraw_state`
  - optional preview ref property for exported PNG/SVG artifact.
- Add QML host plumbing:
  - compact graph-node preview surface
  - fullscreen editor action
  - missing-WebEngine fallback panel explaining the dependency is unavailable.
- Add package-data and PyInstaller handling for bundled web assets:
  - include `*.html`, `*.css`, `*.js`, chunks, fonts, SVG/images
  - add a packaging smoke check that verifies the frozen app can locate and load the bundle.

## Implementation Shape
- Use Qt WebEngine as the browser runtime, not an external browser process.
- Keep the React app isolated under a dedicated asset folder, loaded from local packaged files.
- Store drawing JSON only in declared node properties; store binary/image assets through the existing project artifact store.
- Do not add collaboration, remote rooms, or execution semantics in this milestone.
- Do not make external plugins responsible for registering arbitrary UI surfaces yet; this is a COREX-owned host capability.

## Test Plan
- Unit tests for bridge payload validation, state round-trip, and missing-WebEngine fallback.
- Persistence test proving `excalidraw_state` survives save/load and registry normalization.
- Runtime test proving `excalidraw.board` is omitted from compiled execution.
- QML/graph-surface test for preview/fullscreen action wiring.
- Packaging test proving web assets and WebEngine runtime resources are present in the frozen dist.
- Run:
  - `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_passive_runtime_wiring.py -q`
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`

## Assumptions
- Initial target is local/offline editing.
- Excalidraw state is project data, not app settings.
- WebEngine licensing/package-size impact is acceptable for an optional feature profile.
- The first milestone proves the host layer with a minimal placeholder React page before wiring the full Excalidraw editor.
