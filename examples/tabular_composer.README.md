# Tabular Data Composer

Open `tabular_composer.cxproj` and keep `tabular_composer.data` beside it. The synthetic example has three independent input nodes sharing one NPZ source: labeled temperature history, labeled interface heat flow, and a combined table filtered to Housing values above 40 C. Each feeds a Signal Plot with explicit `time_s` X mapping.

Choose **Configure data...** on any input node. Mapping assigns values, row coordinates and column labels; Add columns combines blocks by row position, while Append rows matches unique column names. Output rules contain saved filters, sorting and explicit row/column selection. Preview paging, finding text, selecting cells and resizing columns do not change output.

Apply commits one undoable configuration. Cancel leaves the node unchanged. Export distinguishes visible preview, selected cell/columns and complete configured output; a dirty configuration is explicitly exported as a draft. Raw ND arrays require a chosen preview plane and can be exported with all dimensions as NPY.

Old projects keep their source choices and switch to full output. A selection-review notice offers to restore old preview hints as deliberate output bounds. Existing Table Filter and Array Slice nodes keep their own selections.

Regenerate the project and synthetic source with:

```powershell
.\venv\Scripts\python.exe .\scripts\generate_tabular_composer_example.py
```

All values are illustrative synthetic data, not engineering predictions.
