# Purpose: Decode retired node property representations at document and fragment boundaries.
# Map: feature_routes/serialization_migration_legacy_rejection.md
# Tests: tests/test_panel_node.py
from collections.abc import Mapping
from typing import Any
import copy


def migrate_panel_properties(type_id: str, properties: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve the old opt-in numeric interpretation when importing saved nodes."""
    migrated = dict(properties)
    if type_id == "data.panel" and "parse_numbers" in migrated:
        legacy_value = migrated.pop("parse_numbers")
        migrated.setdefault("interpretation", "auto" if legacy_value is True else "text")
    return migrated


def migrate_tabular_properties(type_id: str, properties: Mapping[str, Any]) -> dict[str, Any]:
    """Convert input selection hints into a review notice, never an implicit range."""
    migrated = copy.deepcopy(dict(properties))
    if type_id != "tabular.input":
        return migrated
    if "data_view" not in migrated:
        migrated["data_view"] = {"version": 1, "mode": "source", "member": str(migrated.get("selected_object", "") or "")}
        previous = {key: migrated[key] for key in ("array_slice_2d", "tabular_selected_columns") if key in migrated}
        if previous:
            migrated["data_view_migration_notice"] = {"version": 1, "previous_selection": previous}
    for key in ("selected_object", "array_slice_2d", "tabular_selected_columns"):
        migrated.pop(key, None)
    return migrated


def migrate_node_properties(type_id: str, properties: Mapping[str, Any]) -> dict[str, Any]:
    return migrate_tabular_properties(type_id, migrate_panel_properties(type_id, properties))
