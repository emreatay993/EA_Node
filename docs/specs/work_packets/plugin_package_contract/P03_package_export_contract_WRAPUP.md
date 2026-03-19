# P03 Package Export Contract Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/plugin-package-contract/p03-package-export-contract`
- Commit Owner: `worker`
- Commit SHA: `60c18f0a372abfff47f81d9448e8b3071c89cfbe`
- Changed Files: `ea_node_editor/nodes/package_manager.py`, `tests/test_package_manager.py`, `docs/specs/work_packets/plugin_package_contract/P03_package_export_contract_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/plugin_package_contract/P03_package_export_contract_WRAPUP.md`, `ea_node_editor/nodes/package_manager.py`, `tests/test_package_manager.py`
- Export contract: `export_package()` now validates a real explicit source set, requires at least one discoverable top-level module plus non-empty manifest node metadata, and rejects reserved or duplicate archive member names before writing any archive.
- Archive publication safety: exports are staged into a temporary sibling archive and re-validated with the import-side archive checker before the final `.eanp` path is replaced, so success means the emitted archive matches the repaired P01/P02 contract.
- Regression proof: focused tests now cover empty-source rejection, hidden-only source rejection, placeholder-manifest rejection, and an export-to-import-to-loader round-trip using explicit archive member names.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py -q`
- PASS: `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py tests/test_plugin_loader.py -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: do not use `File > Export Node Package` yet; `P04` still owns the shell wiring. Use the repo venv and call `ea_node_editor.nodes.package_manager.export_package(...)` directly with explicit source files.
- Export a package from one public plugin module plus any helper modules, using `PackageManifest(name=..., nodes=[...])`, and confirm the call creates a `.eanp` archive whose root contains `node_package.json` plus only top-level `.py` files.
- Import that archive with `import_package()` or the existing package-import action, then trigger plugin discovery and confirm the exported node type loads from `plugins/<package_name>/`.
- Try exporting with `[]`, an all-hidden source set such as `_helper.py`, or a manifest with `nodes=[]`, and confirm export fails without leaving the requested final archive path behind.

## Residual Risks

- `P04` still needs to update the shell export workflow to provide real package source files to this lower-level contract; until then, the existing UI export path will fail fast instead of producing a placeholder archive.

## Ready for Integration

- Yes: the lower-level export contract now rejects empty or undiscoverable packages, the round-trip proof passes, and the final packet diff stays inside the P03 write scope.
