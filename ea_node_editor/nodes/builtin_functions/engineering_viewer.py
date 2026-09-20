# Purpose: Hold inert decorated source for the Model Viewer built-in.
# Map: feature_routes/viewer_session_overlay_fullscreen.md
# Tests: tests/test_engineering_viewer_node.py

SOURCE = r"""import corex

from ea_node_editor.nodes.builtins.engineering_viewer import execute_engineering_viewer


@corex.node(
    id="model.viewer",
    _solution_reuse_scope="session",
    name="Model Viewer",
    category=("Engineering", "Viewer"),
    icon="deployed_code",
    description="Displays CAD models, surface meshes, OCP bodies, CAD assemblies, and FE models together with per-model appearance.",
    keywords=("viewer", "cad", "finite element"),
    _surface_family="viewer",
    _render_quality_tiers=("full", "proxy"),
)
@corex.output(
    "session",
    value_type="COREX.Viewer.Session",
    label="",
    description="Viewer session payload for embedded and fullscreen presentation.",
)
@corex.output(
    "selections",
    value_type="COREX.Engineering.SelectionSet",
    label="",
    description="Saved entity selections for the displayed scene layers.",
)
@corex.switch(
    "show_mesh_edges", affects_execution=False,
    default=False,
    label="Show Mesh Edges",
    _inline_editor="",
    _property_group="View",
)
@corex.dropdown(
    "representation", affects_execution=False,
    default="surface_with_edges",
    options=(
        "surface",
        "surface_with_edges",
        "wireframe",
        "wireframe_visible_edges",
        "points",
    ),
    label="Representation",
    _inline_editor="",
    _property_group="View",
)
@corex.switch(
    "show_attribute_colors", affects_execution=False,
    default=False,
    label="Show Attribute Colors",
    _inline_editor="",
    _property_group="View",
)
@corex.switch(
    "show_orientation_triad", affects_execution=False,
    default=True,
    label="Show Orientation Triad",
    _inline_editor="",
    _property_group="View",
)
@corex.switch(
    "show_view_cube", affects_execution=False,
    default=True,
    label="Show View Cube",
    _inline_editor="",
    _property_group="View",
)
@corex.switch(
    "show_world_axes", affects_execution=False,
    default=False,
    label="Show World Axes",
    _inline_editor="",
    _property_group="View",
)
@corex.text(
    "scene_input_ids",
    default="",
    label="Model Inputs",
    _inline_editor="",
    _inspector_visible=False,
    _property_type="json",
    _property_default=["scene_1"],
)
@corex.text(
    "scene_styles", affects_execution=False,
    default="",
    label="Model Appearance",
    _inline_editor="",
    _inspector_visible=False,
    _property_type="json",
    _property_default={},
)
@corex.switch(
    "clip_enabled", affects_execution=False,
    default=False,
    label="Enable Clipping",
    _inline_editor="",
    _inspector_visible=False,
)
@corex.dropdown(
    "clip_axis", affects_execution=False,
    default="x",
    options=("x", "y", "z"),
    label="Clipping Axis",
    _inline_editor="",
    _inspector_visible=False,
)
@corex.number(
    "clip_offset", affects_execution=False,
    default=0.0,
    label="Clipping Offset",
    _inline_editor="",
    _inspector_visible=False,
)
@corex.switch(
    "parallel_projection", affects_execution=False,
    default=False,
    label="Parallel Projection",
    _inline_editor="",
    _property_group="View",
)
@corex.dropdown(
    "viewer_background", affects_execution=False,
    default="theme",
    options=("theme", "white", "black", "gray"),
    label="Background",
    _inline_editor="",
    _property_group="View",
)
@corex.text(
    "saved_selections",
    default="",
    label="Saved Selections",
    _inline_editor="",
    _inspector_visible=False,
    _property_type="json",
    _property_default={
        "schema": "engineering_selection_set.v2",
        "scene_fingerprint": "",
        "published_name": "",
        "selections": [],
    },
)
@corex.text(
    "camera_bookmarks", affects_execution=False,
    default="",
    label="Camera Bookmarks",
    _inline_editor="",
    _inspector_visible=False,
    _property_type="json",
    _property_default=[],
)
def model_viewer(ctx, settings):
    del settings
    result = execute_engineering_viewer(ctx)
    for warning in result.warnings:
        ctx.warn(warning, code="model_viewer")
    return dict(result.outputs)
"""

__all__ = ["SOURCE"]
