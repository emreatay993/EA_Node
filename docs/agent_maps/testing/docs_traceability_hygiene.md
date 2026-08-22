# Docs, Traceability, And Hygiene Tests

## Purpose
Use this for docs links, traceability matrix checks, markdown hygiene, dead-code hygiene, and closeout proof checks.

## Start Here
- `scripts/check_markdown_links.py`
- `scripts/check_traceability.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_agent_route_index.py`
- `tests/test_traceability_checker.py`
- `tests/test_dead_code_hygiene.py`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `scripts/generate_agent_route_index.py`
- `docs/agent_route_index.md`
- `docs/agent_route_index.json`
- `scripts/generate_source_test_file_index.py`
- `docs/source_test_file_index.md`
- `scripts/generate_qml_navigation_index.py`
- `docs/qml_navigation_index.md`
- `docs/qml_navigation_index.json`

## Common Changes
- Run markdown links after adding or moving docs.
- Run traceability checks when specs, proof links, QA matrices, or traceability docs change.
- Keep planned requirements in the manifest-owned registry and the separate planned traceability table; exact planned statuses must not cite implementation proof.
- Keep agent maps outside `docs/specs/INDEX.md` unless they become formal proof/spec artifacts.
- Refresh `docs/agent_route_index.md` and `docs/agent_route_index.json` with their generator when map routing, QML metadata, or source/test inventory changes.
- Refresh `docs/source_test_file_index.md` with its generator when the stable source/test path inventory changes; use `scripts/nav.py line` for current locations.
- Refresh `docs/qml_navigation_index.md` and `docs/qml_navigation_index.json` with their generator when QML component routing metadata changes.
- Keep documentation-only executable examples under `docs/examples/` paired with a focused import/registry validation test. Register retained partial proof from `docs/specs/INDEX.md` when a packet needs durable documentation/contract evidence before its visual closeout; the evidence must state outstanding gates rather than claim release acceptance.

## Focused Verification
```powershell
.\venv\Scripts\python.exe .\scripts\check_markdown_links.py
.\venv\Scripts\python.exe .\scripts\generate_agent_route_index.py --check
.\venv\Scripts\python.exe .\scripts\generate_source_test_file_index.py --check
.\venv\Scripts\python.exe .\scripts\generate_qml_navigation_index.py --check
.\venv\Scripts\python.exe -m pytest tests/test_markdown_hygiene.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_agent_route_index.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py --ignore=venv -q
```

## Update Triggers
Update when docs/proof check commands, documentation-example validation, traceability ownership, markdown hygiene rules, generated navigation indexes, or spec-pack links change.
