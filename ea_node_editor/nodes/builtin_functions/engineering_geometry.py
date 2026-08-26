# Purpose: Hold inert decorated source for geometry and mesh built-ins.
# Map: feature_routes/neutral_cad_fe_engineering_viewer.md
# Tests: tests/test_geometry_primitives.py

SOURCE = r'''import corex

from ea_node_editor.nodes.builtins.geometry_primitives import (
    execute_construct_zone,
    execute_cylinder,
)
from ea_node_editor.nodes.builtins.mesh_contracts import (
    execute_deconstruct_mesh_face,
)


def _outputs(ctx, result, code):
    for warning in result.warnings:
        ctx.warn(warning, code=code)
    return result.outputs


@corex.node(
    id="geometry.cylinder",
    name="Cylinder",
    category=("Geometry", "Primitive"),
    icon="cylinder",
    description="Creates an OCP cylinder along a Plane normal over an interval.",
    keywords=("geometry", "primitive", "cylinder", "body", "OCP"),
)
@corex.input(
    "plane",
    value_type="COREX.DataTypes.Plane",
    required=True,
    label="Plane",
)
@corex.input(
    "radius",
    value_type="COREX.DataTypes.Double",
    required=True,
    label="Radius",
)
@corex.input(
    "interval",
    value_type="COREX.DataTypes.Interval1D",
    required=True,
    label="Interval",
)
@corex.output(
    "body",
    value_type="COREX.Geometry.OCPBody",
    label="Body",
)
def cylinder(ctx, plane, radius, interval):
    return _outputs(ctx, execute_cylinder(ctx), "geometry_cylinder")


@corex.node(
    id="fea.construct_zone",
    name="Construct Zone",
    category=("FEA", "Model"),
    icon="select_all",
    description="Groups ordered OCP bodies and per-body tolerances into a Zone.",
    keywords=("FEA", "zone", "geometry", "tolerance"),
)
@corex.input(
    "name",
    value_type="COREX.DataTypes.String",
    required=True,
    label="Name",
)
@corex.input(
    "geometry",
    value_type="COREX.Geometry.OCPBody",
    structure="list",
    required=True,
    label="Geometry",
)
@corex.input(
    "tolerances",
    value_type="COREX.DataTypes.Double",
    structure="list",
    required=False,
    label="Tolerances",
)
@corex.output(
    "zone",
    value_type="COREX.DataTypes.Zone",
    label="Zone",
)
def construct_zone(ctx, name, geometry, tolerances):
    return _outputs(ctx, execute_construct_zone(ctx), "fea_construct_zone")


@corex.node(
    id="mesh.deconstruct_mesh_face",
    name="Deconstruct Mesh Face",
    category=("Mesh", "Analyse"),
    icon="grid_on",
    description="Deconstruct a mesh face into its vertex indices.",
    keywords=("mesh", "face", "indices"),
)
@corex.input(
    "face",
    value_type="COREX.DataTypes.MeshFace",
    required=True,
    label="Face",
    description="Face of a mesh containing its vertex indices.",
)
@corex.output(
    "index_a",
    value_type="COREX.DataTypes.Int",
    label="Index A",
    description="Index of the first vertex.",
)
@corex.output(
    "index_b",
    value_type="COREX.DataTypes.Int",
    label="Index B",
    description="Index of the second vertex.",
)
@corex.output(
    "index_c",
    value_type="COREX.DataTypes.Int",
    label="Index C",
    description="Index of the third vertex.",
)
@corex.output(
    "index_d",
    value_type="COREX.DataTypes.Int",
    label="Index D",
    description="Index of the fourth vertex. For a triangle this can be -1 or equal to the third index.",
)
def deconstruct_mesh_face(ctx, face):
    return _outputs(
        ctx,
        execute_deconstruct_mesh_face(ctx),
        "mesh_deconstruct_mesh_face",
    )
'''

__all__ = ["SOURCE"]
