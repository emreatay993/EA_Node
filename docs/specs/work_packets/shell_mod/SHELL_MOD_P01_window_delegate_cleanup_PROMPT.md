Implement `SHELL_MOD_P01_window_delegate_cleanup.md` exactly.

Before editing:
1. Read `docs/specs/work_packets/shell_mod/SHELL_MOD_MANIFEST.md`.
2. Read `docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md`.
3. Read `docs/specs/work_packets/shell_mod/SHELL_MOD_P01_window_delegate_cleanup.md`.

Constraints:
- Implement only `P01` on branch `codex/shell-mod/p01-window-delegate-cleanup`.
- Remove dynamic `_DELEGATED_METHODS` + `__getattr__` from `ShellWindow`.
- Replace with explicit delegation helpers and keep QML slot/property signatures unchanged.
- Do not start `P02`.

Deliverables:
1. Explicit static delegation structure.
2. Verification output summary.
3. `SHELL_MOD_STATUS.md` update for `P01`.
