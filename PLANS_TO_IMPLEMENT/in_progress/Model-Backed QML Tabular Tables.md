# Model-Backed QML Tabular Tables

## Summary

Replace the current custom QML tabular grid with a real `QML TableView + HorizontalHeaderView + VerticalHeaderView` backed by a Python `QAbstractTableModel`. Apply this to both inline tabular node previews and the fullscreen tabular surface, for both table and array previews. This is a clean migration with no compatibility shim for the old hidden/custom grid.

## Key Changes

- Add a read-only `TabularPreviewTableModel(QAbstractTableModel)` QML type, registered under the existing `EA.NodeEditor 1.0` import.
- The model consumes the existing bounded preview payload from `TabularPreviewProvider`; it does not fetch data itself.
- Implement `rowCount`, `columnCount`, `data`, `headerData`, `roleNames`, and read-only `flags`.
- Table mode maps columns from `window.columns` and row objects from `window.rows`; array mode maps values from `slice_2d.values` and generates headers like `C{absolute_column_index}`.
- Replace `TabularDataGrid.qml` with a new shared `TabularTableViewport.qml`.
- `GraphTabularPreviewSurface.qml` and `TabularFullscreenSurface.qml` become wrappers around the shared viewport.
- Keep fullscreen-only controls such as paging, search, filter, sort, metadata sidebar, and copy button in `TabularFullscreenSurface.qml`.

## Public Interface Changes

- Register `TabularPreviewTableModel` as a QML-visible type in the existing `EA.NodeEditor 1.0` namespace.
- Add the hidden `tabular_table_view_state` node property for persisted per-node table viewport state.
- Add a fullscreen bridge save hook for writing the same table viewport state from fullscreen tabular previews.

## Header Behavior

- Use `HorizontalHeaderView` and `VerticalHeaderView` synced to the main `TableView`.
- Enable column drag-resize in both inline and fullscreen surfaces.
- Add double-click autofit on the horizontal header resize edge.
- Autofit uses the currently loaded bounded preview window, not the whole source file.
- Persist column widths per node in project data using a hidden JSON node property:
  `tabular_table_view_state`.
- Schema:
  ```json
  {
    "version": 1,
    "column_widths": {
      "table:<column_label>": 140,
      "array:<absolute_column_index>": 96
    }
  }
  ```
- Clamp persisted widths to a sane range, e.g. `48..480` px.
- Duplicate table column labels share one persisted width in v1.
- Vertical headers show row labels/offsets, but row-height resizing is out of v1.

## Persistence And Bridge Flow

- Add hidden `PropertySpec("tabular_table_view_state", "json", {}, ..., inspector_visible=False)` to the tabular input node spec.
- Ensure tabular execution/load-option parsing ignores `tabular_table_view_state`.
- Inline surface persists width changes through the existing graph canvas `set_node_property(node_id, key, value)` bridge.
- Fullscreen surface gets a small bridge slot such as `save_tabular_table_view_state(state)` on `ContentFullscreenBridge`, which writes the same hidden node property.
- The model remains per surface instance; do not share one model between inline and fullscreen.

## Execution Tasks

- Add and register the Python table model.
- Replace the custom QML grid with the shared `TableView` viewport.
- Wire inline and fullscreen column-width persistence through existing node-property writes.
- Update tabular tests and focused QML surface checks.

## Work Packet Conversion Map

- Model and registration: `ui_qml` bridge/model work.
- Inline and fullscreen surfaces: QML tabular surface work.
- Persistence and hidden property: tabular input node plus project serialization checks.
- Verification: focused tabular/QML tests and fast verification rerun.

## Test Plan

- Add unit tests for `TabularPreviewTableModel`:
  table payload row/column counts, cell display, horizontal/vertical headers, array headers, reset behavior, read-only flags, and autofit width calculation.
- Update QML surface tests to assert the real `TableView`, `HorizontalHeaderView`, and `VerticalHeaderView` exist for inline and fullscreen surfaces.
- Add array-mode QML coverage for the shared viewport.
- Update fullscreen bridge tests to cover saving `tabular_table_view_state`.
- Update tabular node tests to verify the hidden property exists, persists through `.cxproj`, stays hidden from the inspector, and is ignored by load options.
- Run:
  ```powershell
  $env:QT_QPA_PLATFORM = "offscreen"
  .\venv\Scripts\python.exe -m unittest tests.test_passive_graph_surface_host tests.test_content_fullscreen_bridge tests.test_tabular_input_node -v
  Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
  .\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast
  ```

## Assumptions

- No cell editing, formulas, fill handles, multi-cell paste, or column reordering in this pass.
- No compatibility with old object names such as `graphNodeTabularVirtualTableView`; tests should move to the new component names.
- Persisting this state in `.cxproj` is intentional because the user selected project persistence and the state is node-specific.
- Qt basis: [`TableView`](https://doc.qt.io/qt-6/qml-qtquick-tableview.html), [`HorizontalHeaderView`](https://doc.qt.io/qt-6/qml-qtquick-controls-horizontalheaderview.html), and [`QAbstractTableModel`](https://doc.qt.io/qt-6/qabstracttablemodel.html).
