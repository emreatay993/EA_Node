# Purpose: Compare computation content separately from execution-occurrence provenance.
# Map: subsystems/execution.md
# Tests: tests/test_runtime_retained_sources.py
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Any

from ea_node_editor.runtime_contracts import DataTree, PlotValue
from ea_node_editor.runtime_contracts.data_types import DataTypeCatalog
from ea_node_editor.runtime_contracts.settled_results import (
    SettledPortResult,
    settled_outputs_to_payload,
)
from ea_node_editor.runtime_contracts.value_codec import serialize_runtime_value


def computational_output_digest(
    outputs: Mapping[str, SettledPortResult],
    *,
    catalog: DataTypeCatalog,
    result_digest: str,
) -> str:
    """Exclude only exact PlotValue's run occurrence; retain all other identities."""

    def contains_plot(value: Any) -> bool:
        if type(value) is PlotValue:
            return True
        if isinstance(value, Mapping):
            return any(contains_plot(item) for item in value.values())
        if isinstance(value, (tuple, list)):
            return any(contains_plot(item) for item in value)
        return False

    if not any(contains_plot(result.value) for result in outputs.values()):
        return result_digest

    def content(value: Any) -> Any:
        if type(value) is PlotValue:
            image = value.preview
            return [
                "plot",
                value.data_signature,
                value.settings_signature,
                [
                    image.sha256,
                    image.format,
                    image.width,
                    image.height,
                    image.schema_version,
                ],
                value.provenance.workspace_id,
                value.provenance.node_id,
            ]
        if isinstance(value, DataTree):
            return [
                "tree",
                [
                    [path, [content(item) for item in items]]
                    for path, items in value.branches
                ],
            ]
        if isinstance(value, Mapping):
            return ["mapping", [[key, content(value[key])] for key in sorted(value)]]
        if isinstance(value, (tuple, list)):
            return ["sequence", [content(item) for item in value]]
        return ["value", serialize_runtime_value(value, catalog=catalog)]

    payload = {
        key: [result.status, content(result.value)]
        if result.status == "value"
        else settled_outputs_to_payload({key: result}, catalog=catalog)[key]
        for key, result in outputs.items()
    }
    encoded = json.dumps(
        ["corex-computational-output-v1", payload],
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
