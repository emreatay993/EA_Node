# Chromium Website/HTML Viewer Node Plan

Target plan document: `C:\Users\emre_\PycharmProjects\EA_Node_Editor\PLANS_TO_IMPLEMENT\in_progress\Chromium Website HTML Viewer Node Plan.md`

## Summary
- Build a reusable Chromium/QWebEngine surface foundation first, then ship a passive browser-like `web.page_viewer` node as the first consumer. The node must view standalone offline HTML files, local relative assets, intranet/SharePoint pages, and internet pages when available. The architecture must stay generic enough for future Plotly, browser-app viewer, and controlled browser-interaction nodes.

## Key Changes
- Add a generic WebEngine navigation/policy layer under `ea_node_editor/web_host/` instead of extending the Excalidraw-only bridge shape.
- Add a reusable QML `WebPageHost` with browser controls: address bar, back, forward, reload/stop, home, zoom, fullscreen, detached window.
- Add a passive built-in node `web.page_viewer` in category `Web`, with `surface_family="web"` and `surface_variant="page_viewer"`.
- Extend surface/fullscreen payload routing with a new `content_kind="web_page"` without breaking the existing Excalidraw `web_editor`.
- Keep arbitrary webpages unprivileged by default: no QWebChannel graph bridge exposed to external/local user pages unless a future trusted surface explicitly opts in.

## Public Interface Changes
- New node type: `web.page_viewer`, display name `Web Page Viewer`.
- Node properties:
  - `start_location: str`: URL or local file path.
  - `home_location: str`: optional home URL/path.
  - `access_profile: enum`: `standard_browser`, `restricted`, `offline_local_only`.
  - `allowed_origins: json`: used by `restricted`.
  - `blocked_origins: json`: explicit deny list.
  - `persist_browser_state: bool`: default `true`.
  - hidden `browser_state: json`: current URL, zoom, scroll/navigation state where safe.
  - hidden `preview_ref: json`: optional preview artifact/status for embedded surface.
- New reusable surface content kind: `web_page`.
- New internal policy types should be implemented around `WebAccessProfile`, `WebNavigationPolicy`, and `WebNavigationDecision`.

## Execution Tasks

### T01 WebEngine Foundation And Policy
- Goal: create a generic Chromium/WebEngine policy layer reusable by HTML viewer, Plotly, and future browser nodes.
- Preconditions: existing `ea_node_editor/web_host/webengine.py` availability checks remain authoritative.
- Conservative write scope: `ea_node_editor/web_host/`, focused policy tests under `tests/test_webengine_*.py`.
- Deliverables: URL/path normalization, scheme allowlist for `file`, `http`, `https`, access profiles, origin allow/block evaluation, WebEngine availability payloads.
- Verification: unit tests for local paths, `file://`, intranet hostnames, SharePoint-style HTTPS URLs, blocked schemes, restricted allowlists, and offscreen WebEngine disabled behavior.
- Non-goals: browser automation, DOM extraction, proxy/VPN/auth integration, Plotly backend.
- Packetization notes: becomes `P01 WebEngine Foundation`.

### T02 Generic Web Surface Host
- Goal: add reusable fullscreen and detached browser surfaces.
- Preconditions: T01 policy payload exists.
- Conservative write scope: `ea_node_editor/ui_qml/components/web/`, `ea_node_editor/ui_qml/content_fullscreen_bridge.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`.
- Deliverables: `WebPageHost.qml`, detached web window component/service, browser toolbar, load/error status, policy denial page, WebEngine unavailable page.
- Verification: QML/payload tests with WebEngine unavailable; optional gated WebEngine smoke with `COREX_ENABLE_OFFSCREEN_WEBENGINE=1`.
- Non-goals: interactive embedded WebEngine inside graph nodes, multi-tab browser, persistent browser session manager.
- Packetization notes: becomes `P02 Generic Web Surfaces`.

### T03 Web Page Viewer Node
- Goal: register the first browser-like passive node.
- Preconditions: T01 and T02 are merged.
- Conservative write scope: `ea_node_editor/nodes/builtins/web_viewer.py`, `ea_node_editor/nodes/bootstrap.py`, `ea_node_editor/ui_qml/surface_contracts.py`.
- Deliverables: `web.page_viewer` descriptor, properties, passive execute behavior, surface spec, palette entry, fullscreen/detached actions.
- Verification: node descriptor tests, registry tests, payload builder tests, persistence round-trip tests for node properties.
- Non-goals: execution outputs, screenshot output ports, page title output, automation commands.
- Packetization notes: becomes `P03 Web Viewer Node`.

### T04 Offline/Intranet Hardening
- Goal: prove the viewer works for secure offline/intranet use.
- Preconditions: T03 node exists.
- Conservative write scope: tests, docs/comments near WebEngine policy, packaging data only if needed.
- Deliverables: local HTML fixture with relative CSS/JS/image assets, intranet-style URL policy tests, SharePoint-style HTTPS policy tests, no-network local smoke path.
- Verification: local fixture loads without internet; restricted profile allows configured intranet origins and blocks public internet; `offline_local_only` blocks remote URLs.
- Non-goals: downloading remote pages for offline mirroring, credential management, SSO integration.
- Packetization notes: becomes `P04 Offline/Intranet Hardening`.

### T05 Closeout And Future Chromium Hooks
- Goal: document the reusable contract for future Plotly and browser-app nodes.
- Preconditions: T01-T04 complete.
- Conservative write scope: plan wrap-up/docs, focused tests, `docs/specs/INDEX.md` only if converted to formal specs.
- Deliverables: concise developer note explaining how future Chromium consumers provide URL/HTML payloads without receiving privileged bridges by default.
- Verification: markdown links, focused web tests, `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast` when practical.
- Non-goals: implementing Plotly, browser automation, multi-tab sessions.
- Packetization notes: becomes `P05 Closeout`.

## Work Packet Conversion Map
1. `P00 Bootstrap`: manifest, status ledger, prompts, and index registration if this becomes a formal packet set.
2. `P01 WebEngine Foundation`: derived from T01.
3. `P02 Generic Web Surfaces`: derived from T02.
4. `P03 Web Viewer Node`: derived from T03.
5. `P04 Offline/Intranet Hardening`: derived from T04.
6. `P05 Closeout`: derived from T05.

## Test Plan
- `.\venv\Scripts\python.exe -m pytest tests/test_webengine_navigation_policy.py tests/test_web_page_viewer_node.py --ignore=venv -q`
- `.\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_viewer_surface_contract.py --ignore=venv -q`
- Offscreen-safe tests must pass when WebEngine is unavailable or intentionally disabled.
- Add an optional gated live WebEngine smoke for local HTML only; skip unless WebEngine is available and explicitly enabled.
- Run `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast` at closeout when practical.

## Assumptions
- v1 is a passive browser-like viewer, not an automation/scraping node.
- v1 includes lightweight embedded preview/status, fullscreen interactive WebEngine, and detached single-window WebEngine.
- Default `standard_browser` allows `file`, `http`, and `https`; secure deployments can use `restricted` or `offline_local_only`.
- Local HTML files must work without internet, including relative local assets.
- Cookies/cache/session storage live in the WebEngine app profile, not project `.cxproj`; project files store node configuration and safe navigation state only.
- Excalidraw remains on its existing `web_editor` path unless a later refactor deliberately migrates it onto the generic host.
