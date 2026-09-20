# Purpose: Hold inert decorated source for CAD, mesh, and FE import built-ins.
# Map: feature_routes/neutral_cad_fe_engineering_viewer.md
# Tests: tests/test_engineering_import_nodes.py

SOURCE = r'''import corex

from ea_node_editor.nodes.builtins.engineering_imports import execute_engineering_import


@corex.node(
    id="engineering.fe_import",
    _solution_reuse_scope="session",
    name="FE Import",
    category=("Engineering", "Import"),
    icon="integrations/download.svg",
    description="Imports a neutral finite-element file as a prepared COREX scene.",
    keywords=("finite element", "mesh", "import"),
)
@corex.path(
    "path",
    default="",
    label="FE File",
    file_filter="Neutral FE Files (*.vtk *.vtu *.vtm *.vtkhdf *.e *.exo *.ex2 *.xdmf *.xmf);;All Files (*)",
    port=True,
    _inline_editor="",
    _inspector_editor="",
    _port_accepted_data_types=(),
    _port_description="Path to the neutral finite-element file to import.",
    _port_label="",
    _port_required=True,
    _port_structure="item",
    _port_value_type="COREX.DataTypes.Path",
)
@corex.output(
    "scene",
    value_type="COREX.Engineering.Scene",
    label="",
    description="Prepared finite-element scene for viewing or downstream processing.",
)
@corex.dropdown(
    "length_unit",
    default="file",
    options=("file", "m", "mm", "cm", "in", "ft"),
    label="Length Unit",
    _inline_editor="",
    _inspector_editor="",
    _property_group="Import",
)
def fe_import(ctx, settings):
    result = execute_engineering_import(ctx, source_kind="fe")
    for warning in result.warnings:
        ctx.warn(warning, code="fe_import")
    return dict(result.outputs)


@corex.node(
    id="engineering.cad_import",
    _solution_reuse_scope="session",
    name="CAD Import",
    category=("Engineering", "Import"),
    icon="integrations/download.svg",
    description="Imports a STEP, IGES, or BREP model as exact geometry. Mixed or unsupported STEP units cannot be overridden with one Length Unit choice.",
    keywords=("cad", "geometry", "import"),
)
@corex.path(
    "path",
    default="",
    label="CAD File",
    file_filter="CAD Files (*.step *.stp *.iges *.igs *.brep);;All Files (*)",
    port=True,
    _inline_editor="",
    _inspector_editor="",
    _port_accepted_data_types=(),
    _port_description="Path to the neutral CAD file to import.",
    _port_label="",
    _port_required=True,
    _port_structure="item",
    _port_value_type="COREX.DataTypes.Path",
)
@corex.output(
    "model",
    value_type="COREX.Geometry.CADModel",
    label="CAD Model",
    description="Exact CAD model with original part hierarchy and source metadata.",
)
@corex.dropdown(
    "length_unit",
    default="file",
    options=("file", "m", "mm", "cm", "in", "ft"),
    label="Length Unit",
    _inline_editor="",
    _inspector_editor="",
    _property_group="Import",
)
def cad_import(ctx, settings):
    result = execute_engineering_import(ctx, source_kind="cad")
    for warning in result.warnings:
        ctx.warn(warning, code="cad_import")
    return dict(result.outputs)


@corex.node(
    id="engineering.mesh_import",
    _solution_reuse_scope="session",
    name="Mesh Import",
    category=("Engineering", "Import"),
    icon="integrations/download.svg",
    description="Imports an STL surface mesh as a reusable model for viewing.",
    keywords=("stl", "surface mesh", "import"),
)
@corex.path(
    "path",
    default="",
    label="Mesh File",
    file_filter="STL Files (*.stl);;All Files (*)",
    port=True,
    _inline_editor="",
    _inspector_editor="",
    _port_accepted_data_types=(),
    _port_description="Path to the STL surface mesh to import.",
    _port_label="",
    _port_required=True,
    _port_structure="item",
    _port_value_type="COREX.DataTypes.Path",
)
@corex.output(
    "model",
    value_type="COREX.Mesh.SurfaceModel",
    label="Surface Mesh",
    description="Reusable surface mesh normalized to millimetres.",
)
@corex.dropdown(
    "length_unit",
    default="choose",
    options=("choose", "m", "mm", "cm", "in", "ft"),
    label="Source Length Unit",
    _inline_editor="",
    _inspector_editor="",
    _property_group="Import",
)
def mesh_import(ctx, settings):
    result = execute_engineering_import(ctx, source_kind="mesh")
    for warning in result.warnings:
        ctx.warn(warning, code="mesh_import")
    return dict(result.outputs)
'''

__all__ = ["SOURCE"]
