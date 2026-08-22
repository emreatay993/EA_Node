# Improve Ansys Mechanical Skills And Add 2026 R1 Guide Source

## Summary
Update existing Ansys skills and add the full Release 2026 R1 Mechanical scripting guide as a versioned source-of-truth. Create a docs/RAG-style folder in the Ansys MCP plugin, copy the Markdown guide and assets exactly from the terminal, and point related skills to that canonical copy.

## Key Changes
- Create `C:\Users\emre_\plugins\ansys-mcp\docs\ansys-mechanical-2026r1-scripting-guide\`.
- Copy, using PowerShell `Copy-Item`, not AI rewrite:
  - `Ansys_Scripting_in_Mechanical_Guide.md`
  - `Ansys_Scripting_in_Mechanical_Guide_assets\`
- Add a small `index.md` beside the copied guide with release metadata, source path, asset count/size, and `rg` search phrases for major guide sections.
- Mirror the docs folder into the installed plugin cache only if needed for current-session discoverability: `C:\Users\emre_\.codex\plugins\cache\local\ansys-mcp\0.1.0\docs\...`.
- Update `ansys-mcp` skill text to treat that docs folder as the canonical Mechanical 2026 R1 scripting source.
- Update `ansys-mechanical-ironpython` as the main consumer: add concise workflow guidance plus references for CPython/Python.NET migration, tree/property APIs, `SolverData`, worksheets, messages, graphics/export, `PlotData`, and in-Mechanical DPF.
- Add small cross-references in `ansys-mechanical-model-debugger`, `ansys-apdl-command-debugger`, and `ansys-dpf-core-rst*` so they know when to consult the 2026 R1 guide.

## Test Plan
- Verify copied source integrity with file hash comparison for the `.md`.
- Verify asset copy with file count and total byte comparison; expected source scan found 284 files and 48,146,378 bytes.
- Run skill validation with `quick_validate.py` on changed skill folders.
- Run focused `rg` checks against the copied guide for section names such as `Migrating from IronPython to CPython`, `Solver Data`, `Command Snippets`, and `Data Processing Framework`.

## Assumptions
- The Markdown guide plus assets are the RAG/source-of-truth artifact; the PDF is not copied unless explicitly requested.
- The durable plugin source is `C:\Users\emre_\plugins\ansys-mcp`; the `.codex\plugins\cache` copy is secondary.
- The guide is version-scoped to Ansys Mechanical 2026 R1 / v261 and should not silently override older-version behavior.
