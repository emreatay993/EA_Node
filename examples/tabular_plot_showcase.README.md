# Tabular Plot Showcase

`tabular_plot_showcase.cxproj` and `tabular_plot_showcase_direct.cxproj` are self-contained example projects that load different tabular sources and route them into Signal Plot and seven specialized generic plot types.

For specialized plots, the original showcase keeps the adapter-based flow:

`Tabular Data Input -> Python Script adapter -> Plot node`

The direct showcase exercises hybrid tabular auto-plotting without adapter nodes:

`Tabular Data Input -> Plot node`

The project-managed sources live in each project's sibling `.data` directory:

- `tabular_plot_showcase.data/nodes/<input-node-folder>/in/tabular/source/`
- `tabular_plot_showcase_direct.data/nodes/<input-node-folder>/in/tabular/source/`

Both projects use `Tabular Data Input -> Signal Plot -> Media Panel` for line and
scatter workflows. Scatter uses Line styles None and Filled circle markers;
line plots disable markers. Expand the Media Panel for interactive inspection.

Both projects cover CSV, TSV, XLSX, TXT, NPY, NPZ, Parquet, and HDF5 inputs. Run
the workflow to render line/scatter Signal Plots and the specialized bar,
histogram, heatmap, contour, surface, point cloud, and streamline plots.
`corex_plot_live_line.cxproj` demonstrates a compact Signal Plot/Media Panel
pipeline; `corex_plot_archive_exports.cxproj` retains Bar's paired export ports.

Regenerate both examples with:

```powershell
.\venv\Scripts\python.exe .\scripts\generate_tabular_plot_showcase_example.py
```
