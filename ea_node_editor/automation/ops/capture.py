# Purpose: Capture op spec: canvas view / window screenshots returned inline and saved to disk.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from ea_node_editor.automation.op_model import (
    OpSpec,
    array_schema,
    boolean_schema,
    number_schema,
    object_schema,
    string_schema,
)

DOMAIN = "capture"

IMAGE_ROW = object_schema(
    {
        "path": string_schema(),
        "width": number_schema(integer=True),
        "height": number_schema(integer=True),
        "view_id": string_schema(),
        "view_name": string_schema(),
        "png_base64": string_schema("Present when inline=true"),
    },
    additional=True,
)

SCREENSHOT = OpSpec(
    name="capture.screenshot",
    domain=DOMAIN,
    summary="Render canvas views (content-cropped PNGs) or grab the whole window; returns paths and inline PNGs.",
    description=(
        "mode=views uses the canvas export pipeline (node shadows are disabled during the grab so passive "
        "bodies render offscreen). Web panels and 3D viewers are blank in offscreen (private headless) "
        "instances; the result reports fidelity=offscreen_layout or native."
    ),
    params=object_schema(
        {
            "mode": string_schema(enum=("views", "window"), default="views"),
            "view_ids": array_schema(string_schema(), "Views to render; defaults to the active view"),
            "scale": number_schema(minimum=1, maximum=4, default=1, integer=True),
            "crop_to_content": boolean_schema(default=True),
            "output_dir": string_schema("Directory for PNG files; defaults to a per-instance temp folder"),
            "filename_stem": string_schema("Optional file stem for mode=window"),
            "inline": boolean_schema("Include png_base64 in the result", default=True),
        },
    ),
    result=object_schema(
        {
            "images": array_schema(IMAGE_ROW),
            "mode": string_schema(),
            "fidelity": string_schema(enum=("native", "offscreen_layout")),
        },
        additional=True,
    ),
    mcp_tool="capture_screenshot",
)

OPS: tuple[OpSpec, ...] = (SCREENSHOT,)

__all__ = ["DOMAIN", "OPS", "SCREENSHOT"]
