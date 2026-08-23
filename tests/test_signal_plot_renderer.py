from __future__ import annotations

from pathlib import Path
import pytest

from ea_node_editor.execution.signal_plot_renderer import (
    CATEGORY10,
    LEGEND_LOCATIONS,
    LINE_DASHES,
    MARKERS,
    render_signal_plot,
)
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.integrations_file_io import ImageExportNodePlugin, ImageImportNodePlugin
from ea_node_editor.nodes.builtins.plot.signal import (
    LINE_STYLE_LABELS,
    MARKER_LABELS,
    SIGNAL_PLOT_TYPE_ID,
)
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.runtime_contracts import (
    IMAGE_VALUE_MAX_ENCODED_BYTES,
    DataTree,
    ImageValue,
    Interval1D,
)


INPUT_KEYS = (
    "width",
    "height",
    "title",
    "font_size",
    "labels",
    "show_legend",
    "legend_alignment",
    "values",
    "x_axis_interval",
    "y_axis_interval",
    "colors",
    "line_styles",
    "line_widths",
    "marker_shapes",
    "marker_sizes",
    "x_axis_label",
    "y_axis_label",
    "logarithmic_y_axis",
    "image_background_color",
    "data_background_color",
)


def _tree(*branches: tuple[float, ...]) -> DataTree:
    return DataTree(((index,), branch) for index, branch in enumerate(branches))


def test_signal_plot_contract_is_exact_and_generic_siblings_remain() -> None:
    registry = build_default_registry()
    spec = registry.get_spec(SIGNAL_PLOT_TYPE_ID)
    inputs = tuple(port for port in spec.ports if port.direction == "in")
    outputs = tuple(port for port in spec.ports if port.direction == "out")
    assert tuple(port.key for port in inputs) == INPUT_KEYS
    assert inputs[7].data_access == "tree"
    assert inputs[7].required is True
    assert inputs[7].uses_property_default is False
    assert tuple(port.data_access for port in inputs[4:5] + inputs[10:15]) == ("list",) * 6
    assert tuple(port.key for port in outputs) == ("image",)
    assert outputs[0].data_type == "COREX.DataTypes.Image"
    assert tuple(port.label for port in inputs) == (
        "Width", "Height", "Title", "Font size", "Labels", "Show legend",
        "Legend alignment", "Values", "X axis interval", "Y axis interval",
        "Colors", "Line styles", "Line widths", "Marker shapes", "Marker sizes",
        "X axis label", "Y axis label", "Logarithmic Y axis",
        "Image background color", "Data background color",
    )
    defaults = {prop.key: prop.default for prop in spec.properties}
    assert defaults == {
        "width": 600,
        "height": 400,
        "title": "",
        "font_size": 12,
        "labels": [],
        "show_legend": False,
        "legend_alignment": 8,
        "x_axis_interval": None,
        "y_axis_interval": None,
        "colors": [],
        "line_styles": [1],
        "line_widths": [1],
        "marker_shapes": [1],
        "marker_sizes": [10],
        "x_axis_label": "",
        "y_axis_label": "",
        "logarithmic_y_axis": False,
        "image_background_color": "#ffffff",
        "data_background_color": "#ffffff",
    }
    assert registry.spec_or_none("plot.line") is None
    assert all(registry.spec_or_none(type_id) is not None for type_id in (
        "plot.scatter",
        "plot.bar",
        "plot.histogram",
        "plot.heatmap",
        "plot.contour",
        "plot.surface",
        "plot.point_cloud",
        "plot.streamlines",
        "dpf.plot.line",
    ))


def test_signal_plot_static_ui_metadata_is_exact() -> None:
    spec = build_default_registry().get_spec(SIGNAL_PLOT_TYPE_ID)
    properties = {prop.key: prop for prop in spec.properties}
    assert tuple(group.label for group in spec.settings_groups) == (
        "General options",
        "Signal plot options",
    )
    assert tuple(item.property_key for item in spec.settings_groups[0].items) == (
        "width", "height", "title", "font_size", "labels", "show_legend",
        "legend_alignment", "image_background_color", "data_background_color",
    )
    assert tuple(item.property_key for item in spec.settings_groups[1].items) == (
        "x_axis_interval", "y_axis_interval", "logarithmic_y_axis", "colors",
        "line_styles", "line_widths", "marker_shapes", "marker_sizes",
        "x_axis_label", "y_axis_label",
    )
    assert (properties["width"].inline_editor, properties["width"].minimum, properties["width"].maximum) == ("slider", 2, 3840)
    assert (properties["height"].inline_editor, properties["height"].minimum, properties["height"].maximum) == ("slider", 2, 2160)
    assert (properties["font_size"].minimum, properties["font_size"].maximum) == (1, 72)
    assert properties["show_legend"].inline_editor == "toggle"
    assert properties["legend_alignment"].enum_values == (
        "Upper left", "Upper center", "Upper right", "Middle left", "Middle center",
        "Middle right", "Lower left", "Lower center", "Lower right",
    )
    assert properties["line_styles"].list_item_enum_values == LINE_STYLE_LABELS
    assert properties["marker_shapes"].list_item_enum_values == MARKER_LABELS
    assert (properties["line_widths"].list_item_minimum, properties["line_widths"].list_item_maximum) == (0, 5)
    assert (properties["marker_sizes"].list_item_minimum, properties["marker_sizes"].list_item_maximum) == (1, 72)
    assert properties["x_axis_interval"].inline_editor == "interval_fields"
    assert properties["x_axis_interval"].nullable is True
    assert all(port.description for port in spec.ports)


def test_signal_plot_renders_all_style_codes_and_deterministic_png() -> None:
    branch_count = len(MARKERS)
    values = _tree(*(tuple(float(index + offset) for index in range(8)) for offset in range(branch_count)))
    request = {
        "values": values,
        "labels": [f"signal-{index}" for index in range(branch_count)],
        "show_legend": True,
        "legend_alignment": len(LEGEND_LOCATIONS) - 1,
        "colors": list(CATEGORY10[:3]),
        "line_styles": list(range(len(LINE_DASHES))),
        "line_widths": [1, 2, 3, 4, 5],
        "marker_shapes": list(range(len(MARKERS))),
        "marker_sizes": [4, 8, 12],
        "x_axis_interval": Interval1D(0.0, 7.0),
        "y_axis_interval": Interval1D(0.1, 30.0),
    }
    first, warnings = render_signal_plot(request)
    second, second_warnings = render_signal_plot(request)
    assert type(first) is ImageValue
    assert (first.width, first.height) == (600, 400)
    assert first.encoded_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert first == second
    assert warnings == second_warnings == ()


def test_signal_plot_log_gaps_and_validation_are_clear() -> None:
    image, warnings = render_signal_plot(
        {
            "values": _tree((1.0, 0.0, -1.0, float("nan"), 10.0)),
            "logarithmic_y_axis": True,
            "marker_shapes": [0],
        }
    )
    assert type(image) is ImageValue
    assert warnings and "gaps" in warnings[0]

    invalid_cases = (
        ({"values": _tree(())}, "non-empty"),
        ({"values": _tree((0.0, -1.0)), "logarithmic_y_axis": True}, "no positive"),
        ({"values": _tree((1.0, 2.0)), "line_styles": []}, "Line styles"),
        ({"values": _tree((1.0, 2.0)), "marker_shapes": [18]}, "Marker shapes"),
        ({"values": _tree((1.0, 2.0)), "labels": ["a", "b"]}, "exactly one"),
        ({"values": _tree((1.0, 2.0)), "x_axis_interval": Interval1D(2.0, 1.0)}, "increasing"),
        ({"values": _tree((1.0, 2.0)), "width": 16384, "height": 16384}, "64 megapixels"),
    )
    for payload, message in invalid_cases:
        with pytest.raises(ValueError, match=message):
            render_signal_plot(payload)


def test_image_export_is_atomic_png_only_and_honors_overwrite(tmp_path: Path) -> None:
    image, _warnings = render_signal_plot({"values": _tree((1.0, 2.0, 3.0)), "marker_shapes": [0]})
    plugin = ImageExportNodePlugin()
    output = tmp_path / "signal.png"

    def context(path: Path, *, overwrite: bool = True, value: object = image) -> ExecutionContext:
        return ExecutionContext(
            run_id="run_image_export",
            node_id="node_image_export",
            workspace_id="workspace_image_export",
            inputs={"image": DataTree.from_item(value), "path": DataTree.from_item(str(path)), "overwrite": DataTree.from_item(overwrite)},
            properties={"path": str(path), "overwrite": overwrite},
            emit_log=lambda _level, _message: None,
            trigger={},
        )

    result = plugin.execute(context(output))
    assert result.outputs == {"written_path": str(output)}
    assert output.read_bytes() == image.encoded_bytes
    assert {prop.key: prop.default for prop in plugin.spec().properties}["overwrite"] is True
    plugin.execute(context(output))
    with pytest.raises(FileExistsError):
        plugin.execute(context(output, overwrite=False))
    with pytest.raises(ValueError, match=".png"):
        plugin.execute(context(tmp_path / "signal.jpg"))
    with pytest.raises(ValueError, match="COREX Image"):
        plugin.execute(context(tmp_path / "bad.png", value="not-an-image"))


def test_image_import_and_export_round_trip_validated_image_value(tmp_path: Path) -> None:
    registry = build_default_registry()
    import_spec = registry.get_spec("io.image_import")
    assert [(port.key, port.direction, port.uses_property_default) for port in import_spec.ports] == [
        ("path", "in", True),
        ("image", "out", False),
    ]
    image, _warnings = render_signal_plot({"values": _tree((1.0, 2.0)), "marker_shapes": [0]})
    source = tmp_path / "source.png"
    source.write_bytes(image.encoded_bytes)
    imported = ImageImportNodePlugin().execute(
        ExecutionContext(
            run_id="run_import",
            node_id="node_import",
            workspace_id="workspace_import",
            inputs={"path": DataTree.from_item(str(source))},
            properties={"path": ""},
            emit_log=lambda _level, _message: None,
            trigger={},
        )
    ).outputs["image"]
    assert imported == image
    destination = tmp_path / "roundtrip.png"
    ImageExportNodePlugin().execute(
        ExecutionContext(
            run_id="run_export",
            node_id="node_export",
            workspace_id="workspace_export",
            inputs={
                "image": DataTree.from_item(imported),
                "path": DataTree.from_item(str(destination)),
                "overwrite": DataTree.from_item(False),
            },
            properties={"path": "", "overwrite": False},
            emit_log=lambda _level, _message: None,
            trigger={},
        )
    )
    assert ImageValue.from_png(destination.read_bytes()) == image
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not-png")
    with pytest.raises(ValueError, match="PNG"):
        ImageImportNodePlugin().execute(
            ExecutionContext(
                run_id="run_bad_import",
                node_id="node_bad_import",
                workspace_id="workspace_import",
                inputs={"path": DataTree.from_item(str(bad))},
                properties={"path": ""},
                emit_log=lambda _level, _message: None,
                trigger={},
            )
        )
    oversized = tmp_path / "oversized.png"
    with oversized.open("wb") as stream:
        stream.seek(IMAGE_VALUE_MAX_ENCODED_BYTES)
        stream.write(b"\x00")
    with pytest.raises(ValueError, match="64 MiB"):
        ImageImportNodePlugin().execute(
            ExecutionContext(
                run_id="run_oversized_import",
                node_id="node_oversized_import",
                workspace_id="workspace_import",
                inputs={"path": DataTree.from_item(str(oversized))},
                properties={"path": ""},
                emit_log=lambda _level, _message: None,
                trigger={},
            )
        )


def test_signal_plot_preserves_color_alpha_and_rejects_invalid_corex_color(monkeypatch) -> None:  # noqa: ANN001
    import ea_node_editor.execution.signal_plot_renderer as renderer

    captured: dict[str, object] = {}
    original_line = renderer.xy.line
    original_theme = renderer.xy.theme

    def line(*args, **kwargs):  # noqa: ANN002, ANN003
        captured["series"] = kwargs.get("color")
        return original_line(*args, **kwargs)

    def theme(*args, **kwargs):  # noqa: ANN002, ANN003
        captured["background"] = kwargs.get("background")
        captured["plot_background"] = kwargs.get("plot_background")
        return original_theme(*args, **kwargs)

    monkeypatch.setattr(renderer.xy, "line", line)
    monkeypatch.setattr(renderer.xy, "theme", theme)
    renderer.render_signal_plot(
        {
            "values": _tree((1.0, 2.0)),
            "colors": [{"R": 1.0, "G": 0.0, "B": 0.0, "A": 0.25, "IsValid": True}],
            "image_background_color": {"R": 0.0, "G": 1.0, "B": 0.0, "A": 0.0},
            "data_background_color": {"R": 0.0, "G": 0.0, "B": 1.0, "A": 0.5},
            "marker_shapes": [0],
        }
    )
    assert captured == {
        "series": "#ff000040",
        "background": "#00ff0000",
        "plot_background": "#0000ff80",
    }
    with pytest.raises(ValueError, match="marked invalid"):
        renderer.render_signal_plot(
            {
                "values": _tree((1.0, 2.0)),
                "colors": [{"R": 1.0, "G": 0.0, "B": 0.0, "IsValid": False}],
                "marker_shapes": [0],
            }
        )
