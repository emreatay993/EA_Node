# Purpose: Automation example: text, media panel (generated PNG), path pointer, and panel wrapped in a titled group with comments and a URL link, then a screenshot.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_docgen.py
"""Annotated media board via the COREX automation API.

Run from the repository root::

    .\\venv\\Scripts\\python.exe examples\\automation\\annotated_media_board.py
    .\\venv\\Scripts\\python.exe examples\\automation\\annotated_media_board.py --no-headless --output-dir C:\\temp\\corex

The PNG shown in the media panel is generated here with ``zlib`` / ``struct``
(no imaging library). In ``private`` mode the board is saved as
``annotated_media_board.cxproj`` so the staged image is published next to it.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

try:
    from ea_node_editor.automation.client import CorexClient
except ImportError:  # running from a checkout without an editable install
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ea_node_editor.automation.client import CorexClient

from ea_node_editor.automation.errors import AutomationOpError

WORKSPACE_NAME = "Media board example"
BRIEF_MARKDOWN = (
    "## Mesh review\n"
    "- Global element size **2 mm**\n"
    "- Refine the root fillet to 0.5 mm\n"
    "- Accept when max skewness < 0.85"
)
PANEL_TEXT = "Elements: 1 248 332\nNodes: 1 902 114\nMax skewness: 0.81"
REFERENCE_URL = "https://en.wikipedia.org/wiki/Mesh_generation"


class ExampleFailure(RuntimeError):
    """A check in this example failed."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an annotated media board in COREX through the automation API.")
    parser.add_argument("--mode", choices=("auto", "attach", "private"), default="private", help="launch mode (default: private)")
    parser.add_argument("--headless", dest="headless", action="store_true", default=True, help="private mode renders offscreen (default)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="private mode opens a real window")
    parser.add_argument("--output-dir", type=Path, default=None, help="where the PNGs and .cxproj go (default: a new temp folder)")
    parser.add_argument("--instance-id", default=None, help="attach to this discovery instance id")
    parser.add_argument("--startup-timeout", type=float, default=120.0, help="seconds to wait for a spawned instance")
    return parser.parse_args(argv)


def write_mesh_png(path: Path, width: int = 240, height: int = 150, pitch: int = 20) -> Path:
    """Write an RGB PNG: a blue-to-orange gradient under a triangulated grid (looks like a coarse mesh)."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type: none
        for x in range(width):
            if x % pitch == 0 or y % pitch == 0 or (x - y) % pitch == 0:
                raw += bytes((32, 36, 48))
                continue
            t = x / (width - 1)
            s = y / (height - 1)
            raw += bytes((int(40 + 200 * t), int(110 + 60 * s), int(210 - 170 * t)))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB, no interlace
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    return path


def is_sandbox(corex: CorexClient) -> bool:
    handle = corex.handle
    return handle is not None and handle.owned and handle.private


def prepare_workspace(corex: CorexClient, sandbox: bool) -> None:
    status = corex.app.status()
    busy = {key: value for key, value in (status.get("busy") or {}).items() if value}
    if busy:
        raise ExampleFailure(f"COREX is busy ({', '.join(sorted(busy))}); close dialogs or wait, then retry")
    if not sandbox:
        corex.workspaces.create(WORKSPACE_NAME)
        return
    project = corex.project.new(discard_unsaved=True)
    try:
        corex.workspaces.rename(str(project["active_workspace_id"]), WORKSPACE_NAME)
    except AutomationOpError as exc:
        if exc.code != "NO_EFFECT":
            raise


def run(corex: CorexClient, output_dir: Path) -> dict[str, str]:
    sandbox = is_sandbox(corex)
    prepare_workspace(corex, sandbox)
    image = write_mesh_png(output_dir / "mesh_preview.png")

    text = corex.nodes.add_text(
        BRIEF_MARKDOWN,
        0,
        0,
        width=360,
        height=180,
        style={"font_size": 16, "horizontal_alignment": "left", "color": "#1F4E79"},
    )
    media = corex.nodes.add_media(str(image), 420, 0, title="Mesh preview", width=320, height=220, fit_mode="contain")
    pointer = corex.nodes.add_path_pointer(str(image), 0, 260, mode="file", title="Preview file")
    panel = corex.nodes.add_panel(420, 300, title="Mesh stats", properties={"value": PANEL_TEXT})
    member_ids = [text["node_id"], media["node_id"], pointer["node_id"], panel["node_id"]]
    print(f"text node content key: {text.get('content_key')}; media staged as {media.get('artifact_ref') or media.get('source')}")

    group = corex.structure.wrap_group(member_ids, title="Mesh review board")

    media_id = media["node_id"]
    first = corex.annotations.comment(media_id, "Root fillet still shows coarse elements.", author="reviewer")
    comment_id = str(first["comment_id"])
    corex.annotations.reply(media_id, comment_id, "Refined to 0.5 mm in iteration 2.", author="analyst")
    corex.annotations.resolve(media_id, comment_id)
    corex.annotations.link_url(text["node_id"], "Meshing background", REFERENCE_URL, subtitle="Reference")

    media_detail = corex.graph.get_node(media_id)
    text_detail = corex.graph.get_node(text["node_id"])
    if len(media_detail.get("comments", [])) < 2:
        raise ExampleFailure(f"expected a comment and a reply on the media node, got {media_detail.get('comments')}")
    if not text_detail.get("links"):
        raise ExampleFailure("the URL link was not stored on the text node")
    print(f"group {group['group_node_id']} wraps {len(group['member_node_ids'])} nodes; "
          f"{len(media_detail['comments'])} comments, {len(text_detail['links'])} link(s)")

    corex.workspaces.frame_all()
    artifacts: dict[str, str] = {"generated_png": str(image)}
    if sandbox:
        saved = corex.project.save_as(output_dir / "annotated_media_board.cxproj")
        artifacts["project"] = str(saved.get("project_path") or output_dir / "annotated_media_board.cxproj")
    else:
        print("skipped project save: the attached COREX belongs to the user (use --mode private to save)")
    shot = corex.capture.screenshot_to(output_dir / "screenshots")
    paths = [path for path in shot.get("saved_paths", []) if Path(path).is_file()]
    if not paths:
        raise ExampleFailure("capture.screenshot produced no PNG file")
    for index, path in enumerate(paths, start=1):
        artifacts[f"screenshot_{index}"] = path
    artifacts["fidelity"] = str(shot.get("fidelity", ""))
    return artifacts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = (args.output_dir or Path(tempfile.mkdtemp(prefix="corex-media-board-"))).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with CorexClient.launch(
            args.mode,
            headless=args.headless,
            instance_id=args.instance_id,
            startup_timeout_s=args.startup_timeout,
        ) as corex:
            artifacts = run(corex, output_dir)
    except AutomationOpError as exc:
        print(f"FAILED {exc.code}: {exc.message}", file=sys.stderr)
        print(f"  hint: {exc.hint}", file=sys.stderr)
        if exc.details:
            print(f"  details: {json.dumps(exc.details, default=str)[:1200]}", file=sys.stderr)
        return 1
    except ExampleFailure as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    for label, value in artifacts.items():
        print(f"{label}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
