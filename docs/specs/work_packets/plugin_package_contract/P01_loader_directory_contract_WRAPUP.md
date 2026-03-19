# P01 Loader Directory Contract Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/plugin-package-contract/p01-loader-directory-contract`
- Commit Owner: `executor-pending`
- Commit SHA: `n/a`
- Changed Files: `ea_node_editor/nodes/plugin_loader.py`, `tests/test_plugin_loader.py`, `docs/specs/work_packets/plugin_package_contract/P01_loader_directory_contract_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/plugin_package_contract/P01_loader_directory_contract_WRAPUP.md`, `ea_node_editor/nodes/plugin_loader.py`, `tests/test_plugin_loader.py`
- Canonical package-directory contract: installed packages are discovered from immediate child directories under the plugins root at `plugins/<package_name>/`; the loader imports public top-level `*.py` modules in that directory inside one synthetic package namespace so sibling relative imports work, while raw single-file drop-ins remain `plugins/*.py`.
- Discovery tolerance: a failing root plugin file or package module logs a warning and does not block remaining filesystem or entry-point discovery.

## Verification

- FAIL: `./venv/Scripts/python.exe -m pytest -n auto tests/test_plugin_loader.py -q` (`WinError 1920` during pytest collection when xdist inspects the packet worktree's symlinked `venv`)
- FAIL: `./venv/Scripts/python.exe -m pytest -n auto tests/test_plugin_loader.py tests/test_main_bootstrap.py -q` (`WinError 1920` during pytest collection when xdist inspects the packet worktree's symlinked `venv`)
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_main_bootstrap.py -q --ignore=venv`
- Final Verification Verdict: `FAIL`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: use a clean user plugins root so the check is limited to the packet contract at `plugins/*.py` and `plugins/<package_name>/*.py`.
- Create one valid single-file plugin at `plugins/root_dropin.py`, launch the app, and confirm its node appears alongside built-ins without changing existing startup behavior.
- Create one package directory at `plugins/example_package/` with a helper module plus a plugin module that imports that helper via a sibling relative import, launch the app, and confirm the packaged node loads successfully.
- Add one intentionally broken module beside a valid plugin module under the same plugins root, relaunch the app, and confirm the valid plugin still loads while the broken module only emits a warning.

## Residual Risks

- The packet's required xdist-based pytest commands do not currently run in this dedicated worktree because Windows pytest collection hits `WinError 1920` on the symlinked `venv` entry before packet tests execute.

## Ready for Integration

- No: the packet code is implemented and the focused non-xdist rerun passes, but the required worktree verification commands are still blocked by the external `venv` symlink collection issue.
