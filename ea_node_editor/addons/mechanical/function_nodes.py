# Purpose: Hold inert decorated Mechanical Open, Search, and FEA Table declarations.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_catalogue.py, tests/mechanical_catalogue/test_search_tree.py, tests/mechanical_catalogue/test_definition_tables.py

SOURCE = r'''import corex
from ea_node_editor.addons.mechanical.runtime import execute_open_model
from ea_node_editor.addons.mechanical.runtime import execute_search_tree
from ea_node_editor.addons.mechanical.runtime import execute_fea_table

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

@corex.node(
    id="mechanical.search_tree", name="Search Mechanical Tree",
    category=("FEA", "ANSYS", "Mechanical"),
    description="Searches the current model snapshot with eleven COREX background data filters without changing the Mechanical Outline.",
    keywords=("mechanical", "ansys", "tree", "search", "property"),
    _solution_reuse_scope="never",
)
@corex.input("model", value_type="COREX.Mechanical.Model", required=True,
    label="Model", description="Run-owned Mechanical model state.")
@corex.dropdown("filter", default="name",
    options=("name", "tag", "type", "state", "coordinate_system", "model", "graphics", "environment", "scoping", "property_name", "property_value"),
    label="Filter", port=True, _inspector_editor="enum", _property_group="Search",
    _port_value_type="COREX.DataTypes.String", _port_description="COREX background data-query category.")
@corex.text("query", default="", label="Query", port=True,
    _inspector_editor="text", _property_group="Search",
    _port_value_type="COREX.DataTypes.String", _port_description="Text query or accepted typed picker identity.")
@corex.dropdown("match", default="contains", options=("contains", "exact"), label="Match", port=True,
    _inspector_editor="enum", _property_group="Match options",
    _port_value_type="COREX.DataTypes.String", _port_description="Whole-query Contains or Exact matching.")
@corex.switch("case_sensitive", default=False, label="Case sensitive", port=True,
    _inspector_editor="toggle", _property_group="Match options",
    _port_value_type="COREX.DataTypes.Bool", _port_description="Use case-sensitive text matching.")
@corex.switch("include_hidden_properties", default=False, label="Include hidden properties", port=True,
    _inspector_editor="toggle", _property_group="Match options",
    _port_value_type="COREX.DataTypes.Bool", _port_description="Include non-visible properties without changing tree suppression.")
@corex.switch("invert", default=False, label="Invert results", port=True,
    _inspector_editor="toggle", _property_group="Match options",
    _port_value_type="COREX.DataTypes.Bool", _port_description="Invert only complete available applicable predicates.")
@corex.output("objects", value_type="COREX.Mechanical.Object", structure="list", label="Objects", description="Deduplicated matching objects in tree order.")
@corex.output("properties", value_type="COREX.Mechanical.Property", structure="list", label="Properties", description="Matching or discoverable properties in object order.")
@corex.output("found", value_type="COREX.DataTypes.Bool", label="Found", description="True when the complete search found an object or property.")
@corex.output("details", value_type="COREX.DataTypes.TableValue", label="Details", description="One data-only row per search match.")
def search_mechanical_tree(ctx, model, settings):
    return execute_search_tree(ctx, model, settings)

@corex.node(
    id="mechanical.fea_table", name="FEA Table",
    category=("FEA", "ANSYS", "Mechanical"),
    description="Extracts supported Mechanical model definitions into immutable COREX tables without solving.",
    keywords=("mechanical", "ansys", "fea", "table", "definition"),
    _solution_reuse_scope="never",
)
@corex.input("model", value_type="COREX.Mechanical.Model", required=True,
    label="Model", description="Run-owned Mechanical model state.")
@corex.input("source", value_type="COREX.Mechanical.Object",
    _accepted_data_types=("COREX.Mechanical.Property",), structure="list", required=True,
    label="Source", description="Ordered Mechanical Object or Property selectors to extract.",
    section="Table selection")
@corex.dropdown("family", default="auto",
    options=("auto", "model_definition", "result_history_summary", "spatial_samples", "supported_worksheet"),
    label="Family", port=True, _inspector_editor="enum", _property_group="Table selection",
    _port_value_type="COREX.DataTypes.String", _port_description="Table family; T07 supports Auto and Model definition.")
@corex.text("table", default="", label="Table / property", port=True,
    _inspector_editor="text", _property_group="Table selection",
    _port_value_type="COREX.DataTypes.String", _port_description="Exact table/property selector; empty requires one applicable table.")
@corex.text("component", default="all", label="Component", port=True,
    _inspector_editor="text", _property_group="Table selection",
    _port_value_type="COREX.DataTypes.String", _port_description="All or one exact component exposed by accepted metadata.")
@corex.dropdown("units", default="source", options=("source", "si"),
    label="Units", port=True, _inspector_editor="enum",
    _property_group="Values and units", _port_value_type="COREX.DataTypes.String",
    _port_description="Preserve source units or convert quantity samples with native Ansys SI facilities.")
@corex.list("sets", default=[], item_type=int, label="Rows / sets", port=True,
    _property_group="Values and units", _port_description="Stored result-set IDs; inactive for model definitions and worksheets.")
@corex.output("tables", value_type="COREX.DataTypes.TableValue", structure="list",
    label="Tables", description="Full-fidelity immutable tables in source order.")
@corex.output("definitions", value_type="COREX.DataTypes.TableValue", label="Definitions",
    description="Column units, identities, formulas, locations, and definition metadata.")
def fea_table(ctx, model, source, settings):
    return execute_fea_table(ctx, model, source, settings)
'''

__all__ = ["SOURCE"]
