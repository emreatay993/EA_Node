from __future__ import annotations

from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type_spec
import csv
import sys
from pathlib import Path
from typing import Any

from ea_node_editor.nodes.builtins.integrations_common import pick_optional_path, pick_path, require_existing_file
from ea_node_editor.nodes.decorators import plugin_descriptor
from ea_node_editor.nodes.output_artifacts import write_managed_output
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.file_dialog_filters import SPREADSHEET_FILES_FILTER
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec
from ea_node_editor.runtime_contracts.data_tree import resolve_single_run_inputs

try:
    import openpyxl  # type: ignore
except Exception:  # noqa: BLE001
    openpyxl = None


def require_openpyxl(*, node_name: str) -> None:
    if openpyxl is None:
        runtime_mode = "packaged" if bool(getattr(sys, "frozen", False)) else "source"
        install_guidance = (
            "Rebuild package with openpyxl installed in the build environment."
            if runtime_mode == "packaged"
            else "Install with: pip install openpyxl"
        )
        raise RuntimeError(
            f"{node_name} requires optional dependency 'openpyxl' for XLSX support. "
            f"Runtime mode: {runtime_mode}. CSV remains supported without this dependency. "
            f"{install_guidance}"
        )


def normalize_headers(values: tuple[Any, ...] | list[Any]) -> list[str]:
    counters: dict[str, int] = {}
    headers: list[str] = []
    for index, value in enumerate(values):
        base = str(value).strip() if value is not None else ""
        if not base:
            base = f"column_{index + 1}"
        count = counters.get(base, 0) + 1
        counters[base] = count
        headers.append(base if count == 1 else f"{base}_{count}")
    return headers


def normalize_rows_input(rows_input: Any) -> list[dict[str, Any]]:
    if not isinstance(rows_input, list) or not rows_input:
        raise ValueError("Excel Write requires 'rows' as a non-empty list of dictionaries.")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows_input, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Excel Write row {index} must be a dictionary.")
        rows.append({str(key): value for key, value in row.items()})
    return rows


def stable_headers(rows: list[dict[str, Any]]) -> list[str]:
    headers = sorted({key for row in rows for key in row})
    if not headers:
        raise ValueError("Excel Write rows must contain at least one column key.")
    return headers


def _write_rows_to_path(path: Path, *, rows: list[dict[str, Any]], headers: list[str]) -> None:
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".csv":
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow({header: row.get(header) for header in headers})
        return

    require_openpyxl(node_name="Excel Write")
    workbook = openpyxl.Workbook()  # type: ignore[union-attr]
    try:
        sheet = workbook.active
        sheet.append(headers)
        for row in rows:
            sheet.append([row.get(header) for header in headers])
        workbook.save(path)
    finally:
        workbook.close()


class ExcelReadNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="io.excel_read",
            display_name="Excel Read",
            category_path=("Input / Output",),
            description="Loads CSV or Excel worksheet rows as dictionaries keyed by column header.",
            keywords=("excel", "csv", "spreadsheet"),
            ports=(
                PortSpec(
                    "path",
                    "in",
                    "data",
                    'COREX.DataTypes.Path',
                    required=True,
                    uses_property_default=True,
                    description="CSV or Excel file path; overrides the configured File Path property.",
                ),
                PortSpec(
                    "rows",
                    "out",
                    "data",
                    'COREX.DataTypes.GraphDictionary',
                    exposed=True,
                    data_access="list",
                    description="Worksheet rows represented as dictionaries keyed by normalized headers.",
                ),
            ),
            properties=(
                PropertySpec(
                    "path",
                    "path",
                    "",
                    "File Path",
                    file_filter=SPREADSHEET_FILES_FILTER,
                ),
                PropertySpec("sheet_name", "str", "", "Sheet Name"),
            ),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        path = pick_path(ctx, input_key="path", property_key="path", node_name="Excel Read")
        require_existing_file(path, node_name="Excel Read")
        suffix = path.suffix.lower()

        rows: list[dict[str, Any]] = []
        if suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                header_row = next(reader, None)
                if header_row is not None:
                    headers = normalize_headers(header_row)
                    for source_row in reader:
                        rows.append(
                            {
                                headers[index]: source_row[index] if index < len(source_row) else ""
                                for index in range(len(headers))
                            }
                        )
        elif suffix in {".xlsx", ".xlsm"}:
            require_openpyxl(node_name="Excel Read")
            workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)  # type: ignore[union-attr]
            sheet_name = str(ctx.properties.get("sheet_name", "")).strip()
            if sheet_name:
                if sheet_name not in workbook.sheetnames:
                    available = ", ".join(workbook.sheetnames)
                    raise ValueError(
                        f"Excel Read sheet '{sheet_name}' was not found. Available sheets: {available}"
                    )
                sheet = workbook[sheet_name]
            else:
                sheet = workbook.active
            try:
                iterator = sheet.iter_rows(values_only=True)
                header_row = next(iterator, None)
                if header_row is not None:
                    headers = normalize_headers(list(header_row))
                    for source_row in iterator:
                        values = list(source_row)
                        rows.append(
                            {
                                headers[index]: values[index] if index < len(values) else None
                                for index in range(len(headers))
                            }
                        )
            finally:
                workbook.close()
        else:
            raise ValueError(
                "Excel Read supports only .csv, .xlsx, and .xlsm files. "
                f"Received: {path.suffix or '<no extension>'}"
            )
        return NodeResult(outputs={"rows": rows})


class ExcelWriteNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="io.excel_write",
            display_name="Excel Write",
            category_path=("Input / Output",),
            description="Writes dictionary rows to a CSV or Excel workbook.",
            keywords=("excel", "csv", "export"),
            ports=(
                PortSpec(
                    "rows",
                    "in",
                    "data",
                    'COREX.DataTypes.GraphDictionary',
                    required=True,
                    data_access="tree",
                    description="Dictionary rows to write using their keys as column headers.",
                ),
                PortSpec(
                    "path",
                    "in",
                    "data",
                    'COREX.DataTypes.Path',
                    required=False,
                    uses_property_default=True,
                    data_access="tree",
                    description="Optional CSV or Excel output path; a managed CSV is created when empty.",
                ),
                PortSpec(
                    "written_path",
                    "out",
                    "data",
                    'COREX.DataTypes.Path',
                    exposed=True,
                    description="Path or managed artifact reference for the written spreadsheet.",
                ),
            ),
            properties=(
                PropertySpec(
                    "path",
                    "path",
                    "output.csv",
                    "Output Path",
                    file_filter=SPREADSHEET_FILES_FILTER,
                ),
            ),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        ctx.inputs = resolve_single_run_inputs(
            ctx.inputs,
            node_name="Excel Write",
            list_ports=("rows",),
        )
        rows = normalize_rows_input(ctx.inputs.get("rows"))
        headers = stable_headers(rows)
        path = pick_optional_path(ctx, input_key="path", property_key="path")
        if path is None:
            write_result = write_managed_output(
                ctx,
                output_key="written_path",
                default_suffix=".csv",
                write_payload=lambda output_path: _write_rows_to_path(
                    output_path,
                    rows=rows,
                    headers=headers,
                ),
            )
            return NodeResult(outputs={"written_path": write_result.artifact_ref})

        suffix = path.suffix.lower()
        if suffix not in {".csv", ".xlsx", ".xlsm"}:
            raise ValueError(
                "Excel Write supports only .csv, .xlsx, and .xlsm output formats. "
                f"Received: {path.suffix or '<no extension>'}"
            )
        if path.exists() and path.is_dir():
            raise ValueError(f"Excel Write path must be a file, not a directory: {path}")

        _write_rows_to_path(path, rows=rows, headers=headers)
        return NodeResult(outputs={"written_path": str(path)})


SPREADSHEET_NODE_DESCRIPTORS = (
    plugin_descriptor(ExcelReadNodePlugin),
    plugin_descriptor(ExcelWriteNodePlugin),
)
