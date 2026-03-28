# Workspace Instructions

- Always check for and prefer the project-local virtual environment before using the shell default Python.
- For this repository, the primary interpreter is `venv/Scripts/python.exe` because the project uses a Windows-style virtualenv layout even when accessed from `bash`.
- Before claiming Python, PyQt6, Qt, `pytest`, or QML tooling is unavailable, verify them with the project venv first.
- When running tests, startup smoke checks, or Qt/QML validation, try the project venv interpreter before falling back to system Python.
- In this workspace's PowerShell environment, the Codex-bundled `rg.exe` resolves on `PATH` but is not runnable and fails with `Access is denied`. Do not probe or prefer `rg` here unless a different working `rg.exe` is installed earlier on `PATH`; use PowerShell-native search commands (`Get-ChildItem`, `Select-String`) by default.
