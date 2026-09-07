# Purpose: Hold the inert decorated Open Mechanical Model declaration.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_catalogue.py

SOURCE = r'''import corex
from ea_node_editor.addons.mechanical.runtime import execute_open_model

@corex.node(
    id="mechanical.open_model", name="Open Mechanical Model",
    category=("FEA", "ANSYS", "Mechanical"),
    description="Opens a fresh isolated Mechanical model for this run. Interactive sessions are inspection-only after completion.",
    keywords=("mechanical", "ansys", "model", "open"),
    _solution_reuse_scope="never",
)
@corex.path("file", default="", label="File", port=True,
    file_filter="Mechanical (*.mechdat *.mechdb *.mechpz *.wbpj *.wbpz);;All Files (*)",
    _inspector_editor="path", _property_group="Open options",
    _port_value_type="COREX.DataTypes.Path", _port_required=True,
    _port_description="Standalone Mechanical file or native Mechanical/Workbench archive or project.")
@corex.text("system", default="", label="Model / system", port=True,
    _inspector_editor="text", _property_group="Open options",
    _port_value_type="COREX.DataTypes.String", _port_required=False,
    _port_description="Stable Workbench Model/system selector; empty selects the sole distinct model.")
@corex.dropdown("mode", default="background", options=("background", "interactive"), label="Mode", port=True,
    _inspector_editor="enum", _property_group="Open options",
    _port_value_type="COREX.DataTypes.String", _port_description="Background owner or real interactive editor.")
@corex.dropdown("version", default=0, options=("Auto · 2026 R1 or newer", "2026 R1 (261)"), codes=(0, 261), label="Version", port=True,
    _inspector_editor="enum", _property_group="Open options", _property_type="int",
    _port_value_type="COREX.DataTypes.Int", _port_description="0 selects the newest installed Mechanical release 261 or newer.")
@corex.path("working_folder", default="", label="Working folder", port=True,
    _inspector_editor="path", _property_group="Session options",
    _port_value_type="COREX.DataTypes.Path", _port_required=False,
    _port_description="Optional empty folder for this run's disposable native working copy.")
@corex.number("timeout_s", default=600.0, minimum=1.0, maximum=86400.0, step=1.0, label="Timeout (s)", port=True,
    _inspector_editor="text", _property_group="Session options",
    _port_value_type="COREX.DataTypes.Double", _port_description="Native open timeout from 1 to 86400 seconds.")
@corex.output("model", value_type="COREX.Mechanical.Model", label="Model", description="Run-owned Mechanical model state.")
@corex.output("info", value_type="COREX.DataTypes.TableValue", label="Info", description="Bounded session, system, object, property, table, and view descriptors.")
def open_mechanical_model(ctx, settings):
    return execute_open_model(ctx, settings)
'''

__all__ = ["SOURCE"]
