# Purpose: Execute validated complete output queries in an isolated native process.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_saved_queries.py
from __future__ import annotations

import json
import math
import sys
from typing import Any

from ea_node_editor.runtime_contracts.data_view import DataViewDefinition


def _missing(column: str, dtype: str) -> str:
    if dtype in {"FLOAT", "DOUBLE"}:
        return f"({column} IS NULL OR NOT isfinite({column}))"
    if dtype == "VARCHAR":
        return f"({column} IS NULL OR trim({column}) = '')"
    return f"({column} IS NULL)"


def _predicate(rule: dict[str, Any], field: str, dtype: str, parameters: dict[str, Any], logical_type: str = "") -> str:
    op, value = rule["op"], rule["value"]
    missing = _missing(field, dtype)
    if op == "is_missing":
        return missing
    if op == "is_present":
        return f"NOT {missing}"
    if op in {"contains", "not_contains", "starts_with", "ends_with"}:
        if dtype != "VARCHAR":
            raise ValueError(f"{rule['column']}: text matching requires a text column")
        function = {"contains": "contains", "not_contains": "contains", "starts_with": "starts_with", "ends_with": "ends_with"}[op]
        key = f"value{len(parameters)}"
        parameters[key] = value.lower()
        clause = f"{function}(lower({field}), ${key})"
        return f"({missing} OR NOT {clause})" if op == "not_contains" else f"(NOT {missing} AND {clause})"
    operation = {"eq": "=", "ne": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">="}[op]
    key = f"value{len(parameters)}"
    target = f"${key}"
    from ea_node_editor.addons.tabular_data.composition import _dtype
    temporal = bool(logical_type) and _dtype(logical_type).kind == "M"
    if temporal:
        import numpy as np
        import pandas as pd
        stamp = pd.Timestamp(value)
        if pd.isna(stamp):
            raise ValueError("Use a missing-value condition for NaT")
        zone = logical_type.split("tz=", 1)[1].rstrip("]").strip() if "tz=" in logical_type else None
        if zone and stamp.tzinfo is None:
            stamp = stamp.tz_localize(zone)
        if stamp.tzinfo is not None:
            stamp = stamp.tz_convert("UTC").tz_localize(None)
        native = stamp.to_datetime64()
        converted = native.astype(_dtype(logical_type))
        if converted.astype(native.dtype) != native:
            raise ValueError(f"{rule['column']}: condition precision exceeds the column precision")
        literal = int(converted.view(np.int64))
    elif dtype == "VARCHAR":
        field = f"lower(trim({field}))"
        literal: Any = value.strip().lower()
    elif "INT" in dtype:
        literal = int(value)
    elif dtype in {"FLOAT", "DOUBLE", "REAL"} or dtype.startswith("DECIMAL"):
        literal = float(value)
        if not math.isfinite(literal):
            raise ValueError("Use a missing-value condition for non-finite values")
    elif dtype == "BOOLEAN":
        if value.lower() not in {"true", "false"} or op not in {"eq", "ne"}:
            raise ValueError("Boolean conditions require equals/not-equals and true/false")
        literal = value.lower() == "true"
    elif dtype in {"DATE", "TIME", "TIMESTAMP", "TIMESTAMP_NS", "TIMESTAMP_MS", "TIMESTAMP_S", "TIMESTAMP WITH TIME ZONE"}:
        literal = value
        target = f"CAST(${key} AS {dtype})"
    else:
        raise ValueError(f"Unsupported condition type {dtype}")
    parameters[key] = literal
    return f"(NOT {missing} AND {field} {operation} {target})"


def run_query(request: dict[str, Any]) -> dict[str, Any]:
    # This module's executable entry is the only DuckDB import site. The Qt
    # process imports the parent-side adapter, never this native implementation.
    import duckdb

    view = DataViewDefinition(request["definition"]).to_payload()
    names = request["columns"]
    if not isinstance(names, list) or any(not isinstance(name, str) for name in names) or len(names) != len(set(names)):
        raise ValueError("Query columns must be unique names")
    fields = {name: f'"c{index}"' for index, name in enumerate(names)}
    with duckdb.connect(":memory:", config={"memory_limit": "512MB", "threads": 2}) as connection:
        connection.execute("SET temp_directory = ?", [request["temporary_directory"]])
        connection.execute("SET max_temp_directory_size = ?", [request.get("temporary_budget", "20GB")])
        schema = connection.execute("DESCRIBE SELECT * FROM read_parquet(?)", [request["input_path"]]).fetchall()
        types = {name: dtype for name, dtype, *_ in schema}
        parameters: dict[str, Any] = {"source": request["input_path"]}
        conditions = []
        for rule in view["query"]["filters"]:
            if rule["column"] not in fields:
                raise ValueError(f"Unknown condition column {rule['column']!r}")
            field = fields[rule["column"]]
            conditions.append(_predicate(rule, field, types[field.strip('"')], parameters, request.get("column_types", {}).get(rule["column"], "")))
        predicate = (" AND " if view["query"]["match"] == "all" else " OR ").join(conditions) or "TRUE"
        sort_keys = []
        for directive in view["query"]["sort"]:
            if directive["column"] not in fields:
                raise ValueError(f"Unknown sort column {directive['column']!r}")
            field = fields[directive["column"]]
            dtype = types[field.strip('"')]
            sort_keys.append(f"{_missing(field, dtype)} ASC")
            value_key = f"lower({field})" if dtype == "VARCHAR" else field
            key = f"CASE WHEN {_missing(field, dtype)} THEN NULL ELSE {value_key} END"
            sort_keys.append(f"{key} {'DESC' if directive['descending'] else 'ASC'} NULLS LAST")
        sort_keys.append('"__row_ordinal" ASC')
        selected = view["output"]["columns"] or names
        output_names = [names[item] if type(item) is int else item for item in selected]
        if any(name not in fields for name in output_names):
            raise ValueError("Unknown output column")
        projected = ", ".join(fields[name] for name in output_names)
        sql = f"SELECT {projected} FROM read_parquet($source) WHERE ({predicate}) ORDER BY {', '.join(sort_keys)}"
        if view["output"]["row_limit"]:
            sql += " LIMIT $limit"
            parameters["limit"] = view["output"]["row_limit"]
        sql += " OFFSET $offset"
        parameters["offset"] = view["output"]["row_offset"]
        parameters["target"] = request["output_path"]
        connection.execute(f"COPY ({sql}) TO $target (FORMAT PARQUET, ROW_GROUP_SIZE 65536)", parameters)
    import pyarrow.parquet as pq

    with pq.ParquetFile(request["output_path"]) as parquet:
        return {"row_count": parquet.metadata.num_rows, "columns": output_names}


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Query request exceeds 1 MiB")
        result = run_query(json.loads(raw.decode("utf-8")))
        print(json.dumps({"ok": True, **result}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)[:2000]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
