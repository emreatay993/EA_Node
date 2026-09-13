# Purpose: Orchestrate isolated CDB snapshot export and preserve Save catalogue identity.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_cdb_save.py
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from ea_node_editor.addons.mechanical.cdb_export import validate_cdb_receipt
from ea_node_editor.addons.mechanical.contracts import catalogue_table
from ea_node_editor.addons.mechanical.saving import (
    SaveStaging,
    save_receipt_message,
    validate_model_export_save_receipt,
    validate_native_save_receipt,
)
from ea_node_editor.runtime_contracts import TableValue


def validate_analysis_choice(value: object) -> dict[str, Any]:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"ordinal", "name"}
        or type(value["ordinal"]) is not int
        or value["ordinal"] < 1
        or type(value["name"]) is not str
        or not value["name"].strip()
    ):
        raise ValueError("mechanical.save_failed: invalid source-qualified CDB analysis")
    return dict(value)


def export_snapshot(
    ctx, *, metadata: Mapping[str, Any], snapshot: SaveStaging,
    snapshot_receipt: object, staging: SaveStaging, workbench_source: bool,
    analysis: Mapping[str, Any], content: str, load_step: int, owner_factory,
) -> dict[str, Any]:
    validate_snapshot = (
        validate_model_export_save_receipt if workbench_source else validate_native_save_receipt
    )
    snapshot_receipt = validate_snapshot(snapshot_receipt, format_code="mechdb", staging=snapshot)
    analysis = validate_analysis_choice(analysis)
    if ctx.should_stop():
        raise RuntimeError("mechanical.operation_failed: CDB export cancelled")
    owner_root = staging.root / "cdb-owner"
    owner = owner_factory(work_root=owner_root)
    try:
        ctx.register_cancel(owner.close)
        if ctx.should_stop():
            raise RuntimeError("mechanical.operation_failed: CDB export cancelled")
        response = owner.request(
            run_id=ctx.run_id, session_id=uuid4().hex,
            workspace_id=ctx.workspace_id, expected_revision=0,
            operation="export_cdb_snapshot", timeout_sec=600.0,
            args={
                "snapshot_path": str(snapshot.primary),
                "snapshot_receipt": snapshot_receipt,
                "snapshot_sha256": hashlib.sha256(snapshot.primary.read_bytes()).hexdigest(),
                "workbench_source": workbench_source,
                "stage_path": str(staging.primary),
                "work_root": str(owner_root / "native"),
                "content": content, "analysis": analysis, "load_step": load_step,
                "release_code": metadata["release_code"], "timeout_sec": 600.0,
            },
        )
    finally:
        owner.close()
    if ctx.should_stop():
        raise RuntimeError("mechanical.operation_failed: CDB export cancelled")
    if not isinstance(response, Mapping) or set(response) != {"status", "native_save"} or response["status"] != "staged":
        raise RuntimeError("mechanical.save_failed: invalid CDB owner response")
    receipt = validate_cdb_receipt(response["native_save"], stage_path=staging.primary)
    if (
        receipt["content"] != content
        or {key: receipt["analysis"][key] for key in ("ordinal", "name")} != analysis
        or receipt["load_step"] != (load_step if content == "full" else None)
        or receipt["release_code"] != metadata["release_code"]
    ):
        raise RuntimeError("mechanical.save_failed: CDB receipt does not match the requested export")
    return receipt


def replace_snapshot_report(
    report: object, *, identity: Mapping[str, Any], receipt: Mapping[str, Any],
    source: Path, destination: Path, overwrite: bool,
) -> TableValue:
    if type(report) is not TableValue or not report.row_count:
        raise RuntimeError("mechanical.save_failed: invalid CDB source catalogue")
    frame = report.to_pandas()
    rows = frame.astype(object).where(frame.notna(), None).to_dict("records")
    if any(rows[0].get(key) != value for key, value in identity.items()):
        raise RuntimeError("mechanical.save_failed: CDB source catalogue identity mismatch")
    operations = [row for row in rows if row["record_kind"] == "operation"]
    if len(operations) != 1:
        raise RuntimeError("mechanical.save_failed: CDB snapshot save receipt is missing or ambiguous")
    previous = json.loads(operations[0]["message"])
    if previous.get("format") != "mechdb" or previous.get("source") != str(source):
        raise RuntimeError("mechanical.save_failed: CDB snapshot Report has invalid source or format")
    operation = save_receipt_message(
        destination=destination, source=source, format_code="cdb",
        files=[destination], overwrite=overwrite,
        archive_policy={
            "results_consumed": False, "user_files_consumed": False,
            "external_imported_files_consumed": False, "complete": False,
            "exclusions": ["solved state and history", "archive resources"],
        },
    )
    message = json.loads(operation["message"])
    message["cdb"] = dict(receipt)
    operation["message"] = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    operations[0].update(operation)
    return catalogue_table(rows)
