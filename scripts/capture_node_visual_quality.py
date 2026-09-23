# Purpose: Capture reproducible production GraphCanvas control and notch evidence.
# Map: feature_routes/performance_harness_graph_stress
# Tests: tests/test_node_visual_quality_tooling.py
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-path", type=Path)
    parser.add_argument("--node-count", type=int, default=9)
    parser.add_argument("--scale-factor", type=float)
    parser.add_argument("--themes", nargs="+", choices=("light", "dark"), default=["light", "dark"])
    parser.add_argument("--zooms", nargs="+", type=float, default=[0.5, 1, 1.25, 2, 3, 5])
    parser.add_argument("--targets", nargs="+", default=["slider", "switch", "switch_off", "collapsed", "left_ports", "right_ports", "general", "signal"])
    parser.add_argument("--fixture-only", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != root:
        raise RuntimeError(f"Run from this source root: {root}")
    sys.path.insert(0, str(root))
    os.environ.update({"QT_QPA_PLATFORM": "windows", "QT_QUICK_CONTROLS_STYLE": "FluentWinUI3",
                       "EA_NODE_EDITOR_QML_HOST": "qquickwidget",
                       "EA_NODE_EDITOR_QSG_RHI_BACKEND": "d3d11", "QSG_INFO": "1",
                       "QML_IMPORT_TRACE": "1"})
    if args.scale_factor is not None:
        os.environ["QT_SCALE_FACTOR"] = str(args.scale_factor)

    from PyQt6.QtCore import QPointF, qInstallMessageHandler
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import QApplication
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.persistence.serializer import JsonProjectSerializer
    from ea_node_editor.ui.perf import performance_harness as harness
    from ea_node_editor.ui.perf.node_visual_quality import (
        TARGET_IDS, WORKSPACE_ID, build_visual_quality_project, capture_viewport_size,
        is_graphics_device_failure, source_runtime_metadata, validate_capture_frame,
    )
    from ea_node_editor.ui_qml.qtquick_backend import configure_qtquick_backend

    args.output.mkdir(parents=True, exist_ok=True)
    diagnostics: list[str] = []
    device_failures: list[str] = []
    def record_message(_kind, _context, message):
        diagnostics.append(message)
        if is_graphics_device_failure(message):
            device_failures.append(message)

    def require_healthy_graphics():
        if device_failures:
            raise RuntimeError(f"Graphics device failure invalidates capture: {device_failures[0]}")

    previous_handler = qInstallMessageHandler(record_message)
    configure_qtquick_backend()
    app = QApplication.instance() or QApplication([])
    screen = app.primaryScreen()
    if screen is None:
        raise RuntimeError("Capture requires an available display")
    available = screen.availableGeometry()
    viewport_size = capture_viewport_size(available.width(), available.height())
    # This host uses no persisted application preferences; its visual settings are fixed.
    serializer = JsonProjectSerializer(build_default_registry())
    if args.project_path:
        fixture_path = args.project_path.resolve()
        doc = json.loads(fixture_path.read_text(encoding="utf-8"))
    else:
        fixture_path = args.output / "controls.cxproj"
        doc = serializer.to_document(build_visual_quality_project(node_count=args.node_count))
        fixture_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    metadata = source_runtime_metadata()
    metadata.update({"fixture_path": str(fixture_path), "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
                     "workspace_id": WORKSPACE_ID, "target_node_ids": TARGET_IDS,
                     "preferences": "isolated fixed benchmark host; no persisted user settings", "captures": [],
                     "capture_status": "pending",
                     "viewport_requested_logical": list(viewport_size),
                     "screen": {"name": screen.name(), "dpr": screen.devicePixelRatio(),
                                "available_logical": [available.x(), available.y(), available.width(), available.height()],
                                "safe_frame_margin_logical": 64}})
    if args.fixture_only:
        metadata["capture_status"] = "fixture_only"
        (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        qInstallMessageHandler(previous_handler)
        return 0

    def settle(milliseconds=260):
        deadline = time.perf_counter() + milliseconds / 1000
        while time.perf_counter() < deadline:
            app.processEvents()
            require_healthy_graphics()
            time.sleep(0.002)

    try:
        with harness._GraphCanvasBenchmarkHost(
            app=app, doc=doc, workspace_id=WORKSPACE_ID, viewport_size=viewport_size,
        ) as host:
            require_healthy_graphics()
            host.scene.bind_graph_theme_bridge(host.graph_theme_bridge)
            metadata["renderer"] = host.renderer_diagnostics()
            if metadata["renderer"].get("graphics_api") != "Direct3D11Rhi":
                raise RuntimeError(f"Expected Direct3D 11: {metadata['renderer']}")
            host.widget.setWindowTitle("COREX visual quality proof")
            host.widget.raise_()
            host.widget.activateWindow()
            metadata["viewport_logical"] = [host.widget.width(), host.widget.height()]
            metadata["canvas_logical"] = [host.canvas.width(), host.canvas.height()]
            view_rect = host.view.viewport().rect()
            metadata["view_logical"] = [view_rect.width(), view_rect.height()]
            if any(tuple(metadata[key]) != viewport_size
                   for key in ("viewport_logical", "canvas_logical", "view_logical")):
                raise RuntimeError("Actual widget/canvas/view dimensions differ from the preselected capture viewport")
            def capture(name, *, theme, zoom, target):
                settle()
                host.render_frame()
                require_healthy_graphics()
                path = args.output / f"{theme}-{name}.png"
                frame = host.grab_frame_image()
                validation = validate_capture_frame(frame, device_failures)
                if not frame.save(str(path)):
                    raise RuntimeError(f"Failed to save {path}")
                metadata["captures"].append({"file": path.name, "theme": theme, "zoom": zoom,
                    "target": target, "native_pixels": [frame.width(), frame.height()],
                    "device_pixel_ratio": frame.devicePixelRatio(), "capture": "production QQuickWidget.grab",
                    "validation": validation})

            for theme in args.themes:
                host.theme_bridge.apply_theme(f"stitch_{theme}")
                host.graph_theme_bridge.apply_theme(f"stitch_{theme}")
                host.view.set_zoom(0.48 * min(viewport_size[0] / 1280, viewport_size[1] / 720))
                host.view.centerOn(640, 660)
                capture("overview", theme=theme, zoom=host.view.zoom, target="fixture")
                for target in args.targets:
                    node_target = "collapsed" if target in ("left_ports", "right_ports") else target
                    node = host.model.project.workspaces[WORKSPACE_ID].nodes[TARGET_IDS[node_target]]
                    for zoom in args.zooms:
                        host.view.set_zoom(zoom)
                        # Locate the production delegate at a broad center before targeting detail.
                        host.view.centerOn(node.x + 120, node.y + 110)
                        settle(80)
                        cards = {str((item.property("nodeData") or {}).get("node_id", "")): item
                                 for item in host._force_visible_node_cards_current()}
                        card = cards.get(node.node_id)
                        if card is None:
                            raise RuntimeError(f"Missing target {node.node_id}")
                        x = float(card.width()) / 2
                        y = float(card.height()) / 2
                        if target == "general":
                            x, y = 130, 100  # width/height sliders and left port joins
                        elif target == "left_ports":
                            x = 35
                        elif target == "right_ports":
                            x = float(card.width()) - 35
                        elif target == "signal":
                            controls = [item for item in harness._iter_quick_item_tree(card)
                                        if str(item.property("propertyKey") or "") in ("logarithmic_y_axis", "sync_fullscreen_ranges")]
                            if controls:
                                point = controls[0].mapToItem(card, QPointF(controls[0].width()/2, controls[0].height()/2))
                                x, y = point.x(), point.y()
                        host.view.centerOn(node.x + x, node.y + y)
                        capture(f"{target}-zoom{round(zoom * 100)}", theme=theme, zoom=host.view.zoom, target=target)
                        metadata["captures"][-1]["node_colors"] = {
                            key: card.property(key).name(QColor.NameFormat.HexArgb) for key in
                            ("surfaceColor", "outlineColor", "inlineInputBackgroundColor", "inlineInputTextColor")
                        }
            metadata["fluent_import_evidence"] = sorted({line for line in diagnostics if "FluentWinUI3" in line})
            if not metadata["fluent_import_evidence"]:
                raise RuntimeError("FluentWinUI3 import was not observed")
        require_healthy_graphics()
        metadata["capture_status"] = "complete"
    except Exception as error:
        metadata["capture_status"] = "failed"
        metadata["failure"] = str(error)
        raise
    finally:
        metadata["graphics_device_failures"] = device_failures
        (args.output / "qt-diagnostics.log").write_text("\n".join(diagnostics), encoding="utf-8")
        (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        qInstallMessageHandler(previous_handler)
    print(json.dumps({"output": str(args.output), "captures": len(metadata["captures"]),
                      "fixture": str(fixture_path), "workspace_id": WORKSPACE_ID}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
