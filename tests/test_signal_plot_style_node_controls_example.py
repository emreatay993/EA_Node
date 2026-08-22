from __future__ import annotations

import importlib.util
from pathlib import Path

from ea_node_editor.runtime_contracts import (
    GRAPH_DICTIONARY_DATA_TYPE_ID,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
)


def _load_example_module():
    path = Path(__file__).parents[1] / "docs" / "examples" / "signal_plot_style_node_controls.py"
    module_spec = importlib.util.spec_from_file_location("signal_plot_style_node_controls_example", path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def test_signal_plot_style_declaration_imports_and_validates_with_the_real_sdk() -> None:
    example = _load_example_module()

    spec = example.validate_declaration()

    assert tuple(group.group_id for group in spec.settings_groups) == ("signal", "display")
    assert spec.icon == "icons/signal-plot.svg"
    assert {port.key for port in spec.ports if port.uses_property_default} == {
        "signal_name",
        "result_bound",
    }
    assert {port.key: port.data_type for port in spec.ports} == {
        "signal_name": STRING_DATA_TYPE_ID,
        "result_bound": INTERVAL_1D_GRAPH_DATA_TYPE_ID,
        "plot_request": GRAPH_DICTIONARY_DATA_TYPE_ID,
    }

    properties = {property_spec.key: property_spec for property_spec in spec.properties}
    assert properties["sample_rate_hz"].inline_editor == "slider"
    assert properties["number_of_sectors"].enabled_when.property_key == "cyclic_symmetry_mode"
    assert properties["color_map"].searchable is True
    assert properties["result_bound"].inline_editor == "interval_slider"
    assert properties["result_bound"].interval_direction == "increasing"
