# P02 Package Import Layout Wrap-Up

## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/plugin-package-contract/p02-package-import-layout`
- Commit Owner: `worker`
- Commit SHA: `240cf4954c581d7a6682d61f33c2817a7477e935`
- Changed Files: `ea_node_editor/nodes/package_manager.py`, `tests/test_package_manager.py`, `docs/specs/work_packets/plugin_package_contract/P02_package_import_layout_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/plugin_package_contract/P02_package_import_layout_WRAPUP.md`, `ea_node_editor/nodes/package_manager.py`, `tests/test_package_manager.py`
- Import contract: `.eanp` archives are now accepted only when they contain `node_package.json` plus top-level `.py` files that install into `plugins/<package_name>/`, matching the package-directory loader contract from `P01`.
- Install safety: package installs are staged into a hidden sibling directory and swapped into place so replacements do not leave partially merged package contents behind.
- Package inventory alignment: `list_installed_packages()` and `uninstall_package()` now follow the same canonical package-directory naming rules and ignore hidden staging leftovers.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py -q`
- PASS: `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py tests/test_plugin_loader.py -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: prepare a hand-authored `.eanp` archive that contains `node_package.json` plus top-level plugin `.py` files; do not rely on `Export Node Package` yet because `P03` still owns the export contract repair.
- Import one valid package through the app’s `Import Node Package...` action, then confirm the package lands in the user plugins root as `plugins/<package_name>/` and the packaged node appears in the Node Library after startup.
- Try importing one malformed archive that includes an extra non-`.py` file or a nested path such as `nested/plugin.py`, and confirm the import fails without leaving a new installed package directory behind.
- Re-import an updated archive for an already installed package, then confirm the package directory contains only the new package files and the app no longer exposes behavior from any removed module in the previous install.

## Residual Risks

- `P03` still needs to make `export_package()` emit archives that always satisfy this stricter import contract; the importer is now stricter than the current lower-level export path.

## Ready for Integration

- Yes: the packet review gate and full verification command both pass, and the final diff stays within the P02 write scope.
