"""Drive smart guides through the real graph canvas: live drag snaps, release commits with and without
grid snap (an alignment kept as shown, a spacing guide kept only where it snaps to the same value at the
other axis' grid value, never a guide the drag did not show), clicks that never snap, Alt bypass, the
preference, zoom, multi-selection, Groups, equal spacing and resize handles, including a handle destroyed
mid-gesture and a scene change mid-resize; a trimmed snapshot retaken by the drop-gap rule (its floor,
zoom and trimmed flag) on a long drag or resize, before a left-out Group can draw a gap, and still ranked
at the moving corner after a scene change; the retake interval that holds those retakes back (never a
session's first snapshot, a view change or a scene change; resizes alike; a release keeps the snapshot
whose retake it held back; the real canvas on the wall clock); the overlay's header-band gap markers,
pieces that never paint a pixel twice, the view centre, other pixel ratios, the piece pool, colours and
gap labels; and a right press during a left press (a live drag canceled with the menu under the pointer,
a press not yet dragging, a Group dragged over a wire).

Purpose: Prove GraphCanvasSmartGuides.qml, GraphCanvasSmartGuideOverlay.qml and the node drag/resize
wiring end to end on real GraphNodeHost items inside GraphCanvas.qml.
Map: docs/agent_maps/feature_routes/graph_canvas_input_layers.md
Tests: tests/test_graph_canvas_smart_guides.py
Landmarks: _CANVAS_HELPERS; _STUB_GUIDES_HARNESS; GraphCanvasSmartGuideTests; test_release_keeps_a_guide_only_where_it_holds_at_the_other_axis_grid_value; test_grid_release_never_lands_on_a_guide_the_drag_did_not_show; test_crossing_and_coinciding_guides_never_paint_a_pixel_twice; test_piece_pool_splits_as_many_crossings_as_it_has_room_for; test_right_press_mid_drag_cancels_the_drag_before_the_context_menu; test_resize_handle_snaps_moving_edges_after_the_pointer_moves; test_a_long_drag_past_a_trimmed_snapshot_retakes_it_near_the_destination; test_a_trimmed_snapshot_is_retaken_only_once_a_left_out_candidate_could_join_a_band; test_within_the_retake_interval_the_drop_gap_rule_does_not_retake; test_a_release_keeps_the_snapshot_whose_retake_the_interval_held_back; test_the_canvas_retakes_at_most_once_per_retake_interval_of_wall_clock; test_scene_change_mid_resize_retakes_the_snapshot_and_keeps_the_session; test_host_alt_drag_marks_offsets_and_release_as_snap_bypass
"""
from __future__ import annotations

import unittest

from tests.graph_surface.environment import PassiveGraphSurfaceHostTestBase

# Shared by every canvas probe. Nodes are core.constant (210 x 74) unless noted, the view is 1280 x 720
# centred on the scene origin at zoom 1, so the 6 px guide threshold is 6 scene units and a scene point
# (x, y) sits at screen (640 + x, 360 + y).
_CANVAS_HELPERS = """
            from PyQt6.QtCore import Q_ARG, QCoreApplication
            from PyQt6.QtGui import QColor, QMouseEvent

            registry = build_default_registry()
            CONSTANT = "core.constant"
            PROCESS = "passive.flowchart.process"
            GROUP = "passive.annotation.group_backdrop"

            def new_scene(*, snap_to_grid=False, smart_guides=True):
                model = GraphModel()
                scene = GraphSceneBridge()
                scene.set_workspace(model, registry, model.active_workspace.workspace_id)
                shell = CanvasShellSource({
                    "snap_to_grid_enabled": snap_to_grid,
                    "graphics_smart_guides_enabled": smart_guides,
                })
                return scene, shell

            def add_group(scene, x, y, width, height):
                group_id = scene.add_node_from_type(GROUP, x, y)
                scene.set_node_geometry(group_id, x, y, width, height)
                return group_id

            def open_canvas(scene, shell, *, with_window=False):
                view = ViewportBridge()
                view.set_viewport_size(1280.0, 720.0)
                view.set_view_state(1.0, 0.0, 0.0)
                canvas = create_component(
                    graph_canvas_qml_path,
                    {
                        "mainWindowBridge": shell,
                        "sceneBridge": scene,
                        "viewBridge": view,
                        "width": 1280.0,
                        "height": 720.0,
                    },
                )
                window = attach_host_to_window(canvas, 1280, 720) if with_window else None
                settle_events(3)
                return canvas, view, window

            def close_canvas(canvas, window):
                if window is not None:
                    dispose_host_window(canvas, window)
                else:
                    canvas.deleteLater()
                    app.processEvents()

            def payload_of(scene, node_id):
                for payload in [*scene.nodes_model, *scene.backdrop_nodes_model]:
                    if payload["node_id"] == node_id:
                        return payload
                raise AssertionError(f"Missing payload for {node_id!r}")

            def position(scene, node_id):
                payload = payload_of(scene, node_id)
                return float(payload["x"]), float(payload["y"])

            def card_for(canvas, node_id, object_name="graphNodeCard"):
                for item in named_child_items(canvas, object_name):
                    if str((variant_value(item.property("nodeData")) or {}).get("node_id", "")) == node_id:
                        return item
                raise AssertionError(f"Missing {object_name} for {node_id!r}")

            def smart_guides(canvas):
                guides = canvas.findChild(QObject, "graphCanvasSmartGuides")
                assert guides is not None
                return guides

            def guide_overlay(canvas):
                overlay = canvas.findChild(QObject, "graphCanvasSmartGuideOverlay")
                assert overlay is not None
                return overlay

            def guide_lines(guides):
                return list(variant_value(guides.property("lines")) or [])

            def guide_gaps(guides):
                return list(variant_value(guides.property("gaps")) or [])

            def live_offset(canvas):
                return float(canvas.property("liveDragDx")), float(canvas.property("liveDragDy"))

            def live_drag(canvas, card, node_id, dx, dy, axis_lock="", snap_bypass=False):
                card.dragOffsetChanged.emit(node_id, float(dx), float(dy), axis_lock, snap_bypass)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                return live_offset(canvas)

            # A release the way GraphNodeHostGestureLayer sends it: the last offset, then dragFinished.
            def drop(scene, card, node_id, dx, dy, axis_lock="", snap_bypass=False):
                x, y = position(scene, node_id)
                card.dragOffsetChanged.emit(node_id, float(dx), float(dy), axis_lock, snap_bypass)
                card.dragFinished.emit(node_id, x + float(dx), y + float(dy), True, axis_lock, snap_bypass)
                app.processEvents()
                return position(scene, node_id)

            def host_rect(card):
                offset = float(card.property("worldOffset"))
                return (
                    float(card.x()) - offset,
                    float(card.y()) - offset,
                    float(card.width()),
                    float(card.height()),
                )

            def assert_rect(card, expected):
                actual = host_rect(card)
                assert all(abs(a - e) < 0.01 for a, e in zip(actual, expected)), (actual, expected)

            def move_with(window, point, modifiers=Qt.KeyboardModifier.NoModifier):
                # QTest.mouseMove always sends NoModifier in Qt 6.
                event = QMouseEvent(
                    QEvent.Type.MouseMove,
                    QPointF(point),
                    QPointF(window.mapToGlobal(point)),
                    Qt.MouseButton.NoButton,
                    Qt.MouseButton.LeftButton,
                    modifiers,
                )
                QCoreApplication.sendEvent(window, event)
                settle_events(2)

            def bind_history(scene):
                from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory

                history = RuntimeGraphHistory()
                scene.bind_runtime_history(history)
                history.clear_workspace(scene.workspace_id)
                return history

            def guide_counts(guides):
                return int(guides.property("profileSnapshotCount")), int(guides.property("profileResolveCount"))

            def selected_ids(canvas):
                return sorted(str(value) for value in (variant_value(canvas.selectedNodeIds()) or []))

            def click_card(window, card, modifiers=Qt.KeyboardModifier.NoModifier):
                # Wait out the double-click interval so consecutive clicks stay single clicks.
                QTest.qWait(int(app.styleHints().mouseDoubleClickInterval()) + 50)
                point = hover_host_local_point(window, card, 100.0, 45.0)
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, modifiers, point)
                settle_events(4)

            def set_smart_guides_preference(canvas, shell, enabled):
                shell.graphics_smart_guides_enabled = bool(enabled)
                canvas.property("canvasStateBridge").graphics_preferences_changed.emit()
                settle_events(2)

            def corner_handle(card, role):
                return [
                    item
                    for item in named_child_items(card, "graphNodeResizeHandle")
                    if str(item.property("cornerRole")) == role
                ][0]

            def guide_pieces(overlay, part=None):
                # The overlay's painted pieces as sorted (x, y, width, height); part "line", "gapLine" or
                # "gapTick". The probe runs at a device pixel ratio of 1, so these are whole pixels.
                pieces = []
                for item in named_child_items(overlay, "graphCanvasSmartGuidePiece"):
                    if not item.isVisible() or (part is not None and str(item.property("part")) != part):
                        continue
                    pieces.append((float(item.x()), float(item.y()), float(item.width()), float(item.height())))
                return sorted(pieces)

            def painted_pixels(pieces):
                # One entry per pixel each piece paints, so a pixel painted twice appears twice.
                pixels = []
                for x, y, width, height in pieces:
                    for px in range(int(round(x)), int(round(x + width))):
                        for py in range(int(round(y)), int(round(y + height))):
                            pixels.append((px, py))
                return pixels

            def assert_no_pixel_painted_twice(pieces):
                counts = {}
                for pixel in painted_pixels(pieces):
                    counts[pixel] = counts.get(pixel, 0) + 1
                twice = sorted(pixel for pixel, count in counts.items() if count > 1)
                assert not twice, twice

            def argb(value):
                return QColor(value).name(QColor.NameFormat.HexArgb).upper()

            def label_items(overlay):
                return named_child_items(overlay, "graphCanvasSmartGuideGapLabel")

            def set_canvas_background(canvas, shell, variant):
                shell.graphics_canvas_background_variant = variant
                canvas.property("canvasStateBridge").graphics_preferences_changed.emit()
                settle_events(2)
"""

# The controller alone over stubs: a state bridge that records the offset each snapshot is ranked around
# and, like a trimmed snapshot, only knows the candidates near it (past offset x 600, the "target" and not
# the "near" ones), with the drop gaps it is told to report; a view at zoom 1 (threshold 6, re-snapshot
# floor 40 scene units) and an 800 x 600 visible rect. The moving rect is x 100..300, y 100..200. The
# controller's clock (_nowMs) is the harness's `nowMs`, which stays at 0 until a probe moves it, so a
# probe about the drop-gap rule alone sets retakeMinIntervalMs to 0. Probe bodies get `guides`, `stub`,
# `view`, `offsets()`, `at(ms)` (sets the clock), `drag(points)` (a move session through `points`,
# returning the ranking offsets it took), `drag_at(frames)` (the same through (ms, dx, dy) frames) and
# `resize(rect, ...)`, and delete `stage` when done.
_STUB_GUIDES_HARNESS = """
            harness_qml = '''
            import QtQuick 2.15
            import "../graph_canvas" as GraphCanvasComponents

            Item {
                QtObject {
                    id: stateBridge
                    objectName: "stubStateBridge"
                    property bool trimmed: true
                    property bool reportGaps: true
                    property real dropGapX: 150.0
                    property real dropGapY: 150.0
                    property var offsets: []
                    function smart_guide_snapshot(nodeIds, sceneRect, options) {
                        offsets = offsets.concat([[Number(options.offset_x), Number(options.offset_y)]]);
                        var far = Number(options.offset_x) > 600.0;
                        var snapshot = {
                            "moving": [{"node_id": "resized", "x": 100.0, "y": 100.0, "width": 200.0, "height": 100.0}],
                            "candidates": far
                                ? [{"node_id": "target", "x": 1100.0, "y": -300.0, "width": 200.0, "height": 50.0},
                                   {"node_id": "other", "x": 1100.0, "y": 900.0, "width": 50.0, "height": 50.0}]
                                : [{"node_id": "near", "x": 103.0, "y": -300.0, "width": 200.0, "height": 50.0},
                                   {"node_id": "shelf", "x": 600.0, "y": 900.0, "width": 50.0, "height": 50.0}],
                            "trimmed": trimmed
                        };
                        if (trimmed && reportGaps) {
                            snapshot["dropGapX"] = dropGapX;
                            snapshot["dropGapY"] = dropGapY;
                        }
                        return snapshot;
                    }
                }

                QtObject {
                    id: viewStub
                    objectName: "viewStub"
                    property real zoom_value: 1.0
                    property real center_x: 0.0
                    property real center_y: 0.0
                }

                QtObject {
                    id: canvasStub
                    property var visibleSceneRectPayload: ({"x": -400.0, "y": -300.0, "width": 800.0, "height": 600.0})
                }

                GraphCanvasComponents.GraphCanvasSmartGuides {
                    property real nowMs: 0.0
                    function _nowMs() {
                        return nowMs;
                    }
                    canvasItem: canvasStub
                    canvasStateBridge: stateBridge
                    viewBridge: viewStub
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(
                harness_qml.encode("utf-8"),
                QUrl.fromLocalFile(str(components_dir / "graph" / "SmartGuideStubHarness.qml")),
            )
            assert component.status() == QQmlComponent.Status.Ready, [error.toString() for error in component.errors()]
            stage = component.create()
            assert stage is not None
            guides = stage.findChild(QObject, "graphCanvasSmartGuides")
            stub = stage.findChild(QObject, "stubStateBridge")
            view = stage.findChild(QObject, "viewStub")
            assert guides is not None and stub is not None and view is not None

            def offsets():
                return [tuple(float(value) for value in entry) for entry in variant_value(stub.property("offsets"))]

            def at(ms):
                guides.setProperty("nowMs", float(ms))

            def drag(points):
                stub.setProperty("offsets", [])
                guides.beginMove(["resized"])
                for dx, dy in points:
                    guides.resolveMove(float(dx), float(dy), "", False)
                guides.endMove()
                return offsets()

            def drag_at(frames):
                stub.setProperty("offsets", [])
                guides.beginMove(["resized"])
                for ms, dx, dy in frames:
                    at(ms)
                    guides.resolveMove(float(dx), float(dy), "", False)
                guides.endMove()
                return offsets()

            def resolve_dx(ms, dx, dy, commit=False):
                # One frame (or the release's resolve) at `ms`: the snapped x offset.
                at(ms)
                resolve = guides.resolveCommit if commit else guides.resolveMove
                return float(variant_value(resolve(float(dx), float(dy), "", False))["dx"])

            def resize(rect, moving_left=False, moving_top=False):
                spec = {
                    "movingLeft": moving_left,
                    "movingTop": moving_top,
                    "horizontalOnly": False,
                    "aspectRatio": 0.0,
                    "minWidth": 40.0,
                    "minHeight": 40.0,
                }
                left, top, right, bottom = rect
                result = variant_value(
                    guides.resolveResize({"left": left, "top": top, "right": right, "bottom": bottom}, spec, False)
                )
                placed = result["rect"]
                return tuple(float(placed[key]) for key in ("left", "top", "right", "bottom"))
"""


class GraphCanvasSmartGuideTests(PassiveGraphSurfaceHostTestBase):
    def _run_canvas_probe(self, label: str, body: str) -> None:
        self._run_qml_probe(label, _CANVAS_HELPERS + body)

    def test_live_drag_snaps_within_threshold_draws_guides_and_snapshots_once(self) -> None:
        self._run_canvas_probe(
            "smart-guides-live-drag",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            moving_id = scene.add_node_from_type(CONSTANT, 100.0, 100.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                overlay = guide_overlay(canvas)
                assert bool(guides.property("enabled"))
                assert not bool(guides.property("active"))
                assert int(guides.property("profileSnapshotCount")) == 0

                # One snapshot per gesture however many frames resolve.
                for step in range(12):
                    live_drag(canvas, card, moving_id, -300.0 - step * 5.0, 7.0)
                assert int(guides.property("profileSnapshotCount")) == 1
                assert int(guides.property("profileResolveCount")) == 12
                assert bool(guides.property("active"))

                # Pointer events coalesce: several offsets, one resolve for the flushed frame.
                for dx in (-320.0, -360.0, -397.0):
                    card.dragOffsetChanged.emit(moving_id, dx, 7.0, "", False)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                assert int(guides.property("profileResolveCount")) == 13
                # 10 px from the neighbour's left, right and centre lines: no snap.
                assert live_offset(canvas) == (-397.0, 7.0), live_offset(canvas)
                assert guide_lines(guides) == []
                assert int(overlay.property("visibleLineCount")) == 0
                assert not bool(overlay.property("visible"))

                # 4 px away: the left, centre and right edges land on the neighbour's.
                assert live_drag(canvas, card, moving_id, -403.0, 7.0) == (-407.0, 7.0)
                assert abs(float(card.property("liveDragDx")) + 407.0) < 0.01
                lines = guide_lines(guides)
                assert sorted((line["axis"], line["value"]) for line in lines) == [
                    ("x", -307.0), ("x", -202.0), ("x", -97.0)
                ], lines
                assert all((line["start"], line["end"]) == (-200.0, 181.0) for line in lines), lines
                assert guide_gaps(guides) == []
                assert int(overlay.property("visibleLineCount")) == 3
                assert bool(overlay.property("visible"))
                assert int(guides.property("profileSnapshotCount")) == 1

                # Screen space, one pixel wide, 4 px overshoot past the span.
                shown = guide_pieces(overlay)
                assert [piece[0] for piece in shown] == [333.0, 438.0, 543.0], shown
                assert shown[0] == (333.0, 156.0, 1.0, 389.0), shown
                assert guide_pieces(overlay, "line") == shown

                card.dragCanceled.emit(moving_id)
                app.processEvents()
                assert live_offset(canvas) == (0.0, 0.0)
                assert guide_lines(guides) == []
                assert not bool(guides.property("active"))
                assert not bool(overlay.property("visible"))
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_release_keeps_the_guided_axis_exact_and_grid_snaps_the_other(self) -> None:
        self._run_canvas_probe(
            "smart-guides-commit",
            """
            scene, shell = new_scene(snap_to_grid=False)
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            moving_id = scene.add_node_from_type(CONSTANT, 100.0, 100.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)

                # Grid off: X lands on the guide, Y keeps the raw offset.
                assert drop(scene, card, moving_id, -403.0, 7.0) == (-307.0, 107.0)
                assert live_offset(canvas) == (0.0, 0.0)
                assert guide_lines(guides) == []
                assert not bool(guides.property("active"))

                # Grid on: the guided X stays off grid, Y snaps to the 20-unit grid. The release resolves
                # once: X is an edge alignment, which holds at any Y, so it is not resolved again at the grid
                # Y; the discarded pending offset flushed after the commit resolves raw.
                shell.snap_to_grid_enabled = True
                assert bool(canvas.snapToGridEnabled())
                scene.move_node(moving_id, 100.0, 100.0)
                app.processEvents()
                before = guide_counts(guides)
                assert drop(scene, card, moving_id, -403.0, 7.0) == (-307.0, 100.0)
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (1, 1)

                # A drag cancelled before its first frame spends no snapshot and no snap.
                before = guide_counts(guides)
                card.dragOffsetChanged.emit(moving_id, -403.0, 7.0, "", False)
                card.dragCanceled.emit(moving_id)
                app.processEvents()
                assert guide_counts(guides) == before
                assert not bool(guides.property("active"))

                # Alt: no guide and no grid, live or on release.
                scene.move_node(moving_id, 100.0, 100.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, -403.0, 7.0, snap_bypass=True) == (-403.0, 7.0)
                assert guide_lines(guides) == []
                assert drop(scene, card, moving_id, -403.0, 7.0, snap_bypass=True) == (-303.0, 107.0)

                # Shift lock: X on the guide, the locked Y neither guided nor grid-snapped.
                scene.move_node(moving_id, 100.0, 107.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, -403.0, 0.0, axis_lock="horizontal") == (-407.0, 0.0)
                assert drop(scene, card, moving_id, -403.0, 0.0, axis_lock="horizontal") == (-307.0, 107.0)

                # The commit never starts a guide session: a dragFinished with no live offset before it
                # (the gesture layer always sends one first) meets the grid alone.
                scene.move_node(moving_id, 100.0, 100.0)
                app.processEvents()
                before = guide_counts(guides)
                card.dragFinished.emit(moving_id, 100.0 - 403.0, 107.0, True, "", False)
                app.processEvents()
                assert position(scene, moving_id) == (-300.0, 100.0)
                assert guide_counts(guides) == before
                assert not bool(guides.property("active"))
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_release_keeps_a_guide_only_where_it_holds_at_the_other_axis_grid_value(self) -> None:
        self._run_canvas_probe(
            "smart-guides-commit-grid-settled",
            """
            scene, shell = new_scene(snap_to_grid=True)
            # Two nodes in a row (y 3..77). Centred between them (x -150) the moving node sits 40 from each.
            scene.add_node_from_type(CONSTANT, -400.0, 3.0)
            scene.add_node_from_type(CONSTANT, 100.0, 3.0)
            moving_id = scene.add_node_from_type(CONSTANT, -200.0, 200.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)

                # Raw top 70.5 still overlaps the row by 6.5, so X snaps 3 to the centred slot with two gap
                # markers. Nothing guides Y: the top is 6.5 from the row's bottom, past the 6 threshold.
                assert live_drag(canvas, card, moving_id, 53.0, -129.5) == (50.0, -129.5)
                assert [gap["axis"] for gap in guide_gaps(guides)] == ["x", "x"], guide_gaps(guides)
                assert guide_lines(guides) == []
                # The grid puts the top at 80, below the row, where no gap justifies x -150: the release
                # resolves X again from -150 with Y at its grid value, finds no guide there and grid-snaps X
                # too.
                before = guide_counts(guides)
                landed = drop(scene, card, moving_id, 53.0, -129.5)
                assert landed == (-140.0, 80.0), landed
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (0, 2)

                # Raw top 63 grid-snaps to 60, still in the row: the spacing guide holds there at the same x
                # and X keeps it.
                scene.move_node(moving_id, -200.0, 200.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, 53.0, -137.0) == (50.0, -137.0)
                before = guide_counts(guides)
                landed = drop(scene, card, moving_id, 53.0, -137.0)
                assert landed == (-150.0, 60.0), landed
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (0, 2)

                # Both axes guided (X the spacing slot, Y the row's top edge 4 up): the grid moves neither,
                # so nothing is resolved again.
                scene.move_node(moving_id, -200.0, 200.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, 53.0, -193.0) == (50.0, -197.0)
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [
                    ("y", 3.0), ("y", 40.0), ("y", 77.0)
                ], guide_lines(guides)
                before = guide_counts(guides)
                landed = drop(scene, card, moving_id, 53.0, -193.0)
                assert landed == (-150.0, 3.0), landed
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (0, 1)

                # Shift lock: the locked Y never meets the grid, so X is not resolved again either, although
                # the grid Y (80) would take the rect (top 76, 1 into the row) out of the row.
                scene.move_node(moving_id, -200.0, 76.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, 53.0, 0.0, axis_lock="horizontal") == (50.0, 0.0)
                before = guide_counts(guides)
                landed = drop(scene, card, moving_id, 53.0, 0.0, axis_lock="horizontal")
                assert landed == (-150.0, 76.0), landed
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (0, 1)

                # Grid off: the other axis keeps its raw value, so the spacing guide is not resolved again.
                shell.snap_to_grid_enabled = False
                assert not bool(canvas.snapToGridEnabled())
                scene.move_node(moving_id, -200.0, 200.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, 53.0, -129.5) == (50.0, -129.5)
                before = guide_counts(guides)
                landed = drop(scene, card, moving_id, 53.0, -129.5)
                assert landed == (-150.0, 70.5), landed
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (0, 1)
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_grid_release_never_lands_on_a_guide_the_drag_did_not_show(self) -> None:
        self._run_canvas_probe(
            "smart-guides-commit-grid-unshown",
            """
            # An alignment the live frame showed holds at any Y: the grid Y cannot trade it for the equal
            # spacing that only exists there. L and R are a row 100 apart (y -72..2) and P's left edge is 23.
            scene, shell = new_scene(snap_to_grid=True)
            scene.add_node_from_type(CONSTANT, -595.0, -72.0)
            scene.add_node_from_type(CONSTANT, -285.0, -72.0)
            scene.add_node_from_type(CONSTANT, 23.0, 250.0)
            moving_id = scene.add_node_from_type(CONSTANT, -300.0, 150.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                # Raw left 27 is 4 from P's: X aligns there. Nothing guides Y: the top 8.5 is 6.5 below the
                # row, so the row's equal spacing is out of reach.
                assert live_drag(canvas, card, moving_id, 327.0, -141.5) == (323.0, -141.5)
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [
                    ("x", 23.0), ("x", 128.0), ("x", 233.0)
                ], guide_lines(guides)
                assert guide_gaps(guides) == []
                # The grid puts the top at 0, inside the row, where the slot one L-R gap past R (left 25) is
                # closer than P's edge. The release keeps the alignment it showed, without resolving again.
                before = guide_counts(guides)
                landed = drop(scene, card, moving_id, 327.0, -141.5)
                assert landed == (23.0, 0.0), landed
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (0, 1)
            finally:
                close_canvas(canvas, window)

            # An equal-spacing X the live frame showed that no longer holds at the grid Y goes to the grid,
            # even where another guide holds there: Q's left edge (-146) is 3 right of the centred slot
            # (-150) between the row's two nodes (y 3..77), but the raw left (-149) is closer to the slot.
            scene, shell = new_scene(snap_to_grid=True)
            scene.add_node_from_type(CONSTANT, -400.0, 3.0)
            scene.add_node_from_type(CONSTANT, 100.0, 3.0)
            scene.add_node_from_type(CONSTANT, -146.0, 250.0)
            moving_id = scene.add_node_from_type(CONSTANT, -200.0, 200.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                assert live_drag(canvas, card, moving_id, 51.0, -129.5) == (50.0, -129.5)
                assert [gap["axis"] for gap in guide_gaps(guides)] == ["x", "x"], guide_gaps(guides)
                assert guide_lines(guides) == []
                # At the grid Y (top 80, below the row) the slot is gone and Q's edge, 4 from it, would snap:
                # a guide the drag never showed. Both axes take the grid instead.
                before = guide_counts(guides)
                landed = drop(scene, card, moving_id, 51.0, -129.5)
                assert landed == (-140.0, 80.0), landed
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (0, 2)
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_grid_release_settles_a_vertical_spacing_guide_at_the_grid_x(self) -> None:
        self._run_canvas_probe(
            "smart-guides-commit-grid-settled-y",
            """
            scene, shell = new_scene(snap_to_grid=True)
            # A column (x 10..220) of two nodes, y -290..-216 and 110..184: centred between them the moving
            # node's top is -90, 126 from each.
            scene.add_node_from_type(CONSTANT, 10.0, -290.0)
            scene.add_node_from_type(CONSTANT, 10.0, 110.0)
            moving_id = scene.add_node_from_type(CONSTANT, 300.0, 300.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)

                # Raw right edge 17 overlaps the column by 7, so Y snaps 3 to the centred slot with two gap
                # markers. Nothing guides X: the right edge is 7 from the column's left.
                assert live_drag(canvas, card, moving_id, -493.0, -387.0) == (-493.0, -390.0)
                assert [gap["axis"] for gap in guide_gaps(guides)] == ["y", "y"], guide_gaps(guides)
                assert guide_lines(guides) == []
                # The grid puts the left at -200, the right edge on the column's left: out of the column, the
                # slot is gone, so Y is resolved again at the grid X, finds no guide and meets the grid too.
                before = guide_counts(guides)
                landed = drop(scene, card, moving_id, -493.0, -387.0)
                assert landed == (-200.0, -80.0), landed
                assert tuple(b - a for a, b in zip(before, guide_counts(guides))) == (0, 2)

                # Raw left -187 grid-snaps to -180, still 20 into the column: the slot holds there, Y keeps it.
                scene.move_node(moving_id, 300.0, 300.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, -487.0, -387.0) == (-487.0, -390.0)
                landed = drop(scene, card, moving_id, -487.0, -387.0)
                assert landed == (-180.0, -90.0), landed
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_disabled_preference_neither_snaps_nor_snapshots(self) -> None:
        self._run_canvas_probe(
            "smart-guides-preference-off",
            """
            scene, shell = new_scene(smart_guides=False)
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            moving_id = scene.add_node_from_type(CONSTANT, 100.0, 100.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                assert not bool(guides.property("enabled"))
                assert live_drag(canvas, card, moving_id, -403.0, 7.0) == (-403.0, 7.0)
                assert guide_lines(guides) == []
                assert int(guide_overlay(canvas).property("visibleLineCount")) == 0
                assert drop(scene, card, moving_id, -403.0, 7.0) == (-303.0, 107.0)
                assert int(guides.property("profileSnapshotCount")) == 0
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_multi_selection_snaps_its_union_bounds(self) -> None:
        self._run_canvas_probe(
            "smart-guides-multi-selection",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            anchor_id = scene.add_node_from_type(CONSTANT, 100.0, 100.0)
            other_id = scene.add_node_from_type(CONSTANT, 60.0, 250.0)
            scene.select_node(anchor_id, False)
            scene.select_node(other_id, True)
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, anchor_id)
                guides = smart_guides(canvas)
                # The union's left edge (the other node's) is 4 px from the neighbour's left edge; the
                # anchor's own edges align with nothing.
                assert live_drag(canvas, card, anchor_id, -363.0, 0.0) == (-367.0, 0.0)
                assert set(variant_value(canvas.property("liveDragNodeLookup"))) == {anchor_id, other_id}
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", -307.0)]
                assert abs(float(card_for(canvas, other_id).property("liveDragDx")) + 367.0) < 0.01

                card.dragFinished.emit(anchor_id, 100.0 - 363.0, 100.0, True, "", False)
                app.processEvents()
                assert position(scene, anchor_id) == (-267.0, 100.0)
                assert position(scene, other_id) == (-307.0, 250.0)
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_group_member_ignores_its_group_and_a_dragged_group_snaps_to_a_node(self) -> None:
        self._run_canvas_probe(
            "smart-guides-groups",
            """
            scene, shell = new_scene()
            group_id = add_group(scene, -400.0, -300.0, 700.0, 500.0)
            member_id = scene.add_node_from_type(CONSTANT, -396.0, -100.0)
            peer_id = scene.add_node_from_type(CONSTANT, -150.0, 60.0)
            outside_id = scene.add_node_from_type(CONSTANT, 310.0, -100.0)
            scene.clear_selection()
            assert payload_of(scene, member_id)["owner_backdrop_id"] == group_id
            assert payload_of(scene, peer_id)["owner_backdrop_id"] == group_id
            assert payload_of(scene, outside_id)["owner_backdrop_id"] == ""
            canvas, _view, window = open_canvas(scene, shell)
            try:
                member_card = card_for(canvas, member_id)
                # 5 px from its own Group's left edge: the Group is no candidate.
                assert live_drag(canvas, member_card, member_id, 1.0, 0.0) == (1.0, 0.0)
                assert all(line["value"] != -400.0 for line in guide_lines(smart_guides(canvas)))
                # A node in the same Group still guides: 3 px from the peer's left edge.
                assert live_drag(canvas, member_card, member_id, 243.0, 0.0) == (246.0, 0.0)
                member_card.dragCanceled.emit(member_id)
                app.processEvents()

                group_card = card_for(canvas, group_id, "graphGroupBackdropInputCard")
                # The Group's right edge (its members move with it) lands on the outside node's left edge.
                assert live_drag(canvas, group_card, group_id, 6.0, 0.0) == (10.0, 0.0)
                assert set(variant_value(canvas.property("liveDragNodeLookup"))) == {group_id, member_id, peer_id}
                assert ("x", 310.0) in [(line["axis"], line["value"]) for line in guide_lines(smart_guides(canvas))]
                group_card.dragFinished.emit(group_id, -400.0 + 6.0, -300.0, True, "", False)
                app.processEvents()
                assert position(scene, group_id) == (-390.0, -300.0)
                assert position(scene, member_id) == (-386.0, -100.0)
                assert position(scene, outside_id) == (310.0, -100.0)
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_equal_spacing_snaps_between_neighbours_and_marks_the_gaps(self) -> None:
        self._run_canvas_probe(
            "smart-guides-equal-spacing",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -400.0, 0.0)
            scene.add_node_from_type(CONSTANT, 100.0, 0.0)
            moving_id = scene.add_node_from_type(CONSTANT, -200.0, 200.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                overlay = guide_overlay(canvas)
                # Centred between the neighbours (40 units each side, 3 px away) and top-aligned (2 px away).
                assert live_drag(canvas, card, moving_id, 47.0, -198.0) == (50.0, -200.0)
                gaps = guide_gaps(guides)
                assert sorted(
                    (gap["axis"], gap["start"], gap["end"], gap["cross"], gap["crossStart"], gap["crossEnd"], gap["size"])
                    for gap in gaps
                ) == [
                    ("x", -190.0, -150.0, 37.0, 0.0, 74.0, 40.0),
                    ("x", 60.0, 100.0, 37.0, 0.0, 74.0, 40.0),
                ], gaps
                assert sorted((line["axis"], line["value"]) for line in guide_lines(guides)) == [
                    ("y", 0.0), ("y", 37.0), ("y", 74.0)
                ]
                assert int(overlay.property("visibleGapCount")) == 2

                # Top, middle and bottom lines across all three nodes (screen x 240..950, 4 px overshoot).
                assert guide_pieces(overlay, "line") == [
                    (236.0, 360.0, 718.0, 1.0), (236.0, 397.0, 718.0, 1.0), (236.0, 434.0, 718.0, 1.0)
                ], guide_pieces(overlay, "line")
                # Each marker ticks the first and the last pixel column of its gap (screen x 450..490 and
                # 700..740) and draws its line only between them, in the header band: 16 below the shared
                # top (screen y 360), well clear of the middle line.
                assert guide_pieces(overlay, "gapTick") == [
                    (450.0, 373.0, 1.0, 7.0), (489.0, 373.0, 1.0, 7.0), (700.0, 373.0, 1.0, 7.0), (739.0, 373.0, 1.0, 7.0)
                ], guide_pieces(overlay, "gapTick")
                assert guide_pieces(overlay, "gapLine") == [(451.0, 376.0, 38.0, 1.0), (701.0, 376.0, 38.0, 1.0)], (
                    guide_pieces(overlay, "gapLine")
                )
                assert len(guide_pieces(overlay)) == 9
                assert_no_pixel_painted_twice(guide_pieces(overlay))

                assert drop(scene, card, moving_id, 47.0, -198.0) == (-150.0, 0.0)
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_horizontal_gap_markers_sit_in_the_header_band_and_never_past_the_middle(self) -> None:
        self._run_canvas_probe(
            "smart-guides-header-band",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -400.0, 0.0)
            scene.add_node_from_type(CONSTANT, 100.0, 0.0)
            moving_id = scene.add_node_from_type(CONSTANT, -200.0, 200.0)
            scene.clear_selection()
            canvas, view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                overlay = guide_overlay(canvas)
                assert float(overlay.property("horizontalGapHeaderOffset")) == 16.0

                def marker_rows():
                    return sorted({piece[1] for piece in guide_pieces(overlay, "gapLine")})

                # A tall pair shares the whole 74-unit height: the markers run 16 below its top (screen y 360).
                assert live_drag(canvas, card, moving_id, 50.0, -200.0) == (50.0, -200.0)
                assert marker_rows() == [376.0], guide_pieces(overlay)

                # The offset is in scene units, so the markers stay in the header band at any zoom: 32 px at
                # zoom 2, where the first gap spans screen x 260..340.
                view.set_view_state(2.0, 0.0, 0.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, 50.0, -200.0) == (50.0, -200.0)
                assert marker_rows() == [392.0], guide_pieces(overlay)
                assert guide_pieces(overlay, "gapLine")[0] == (261.0, 392.0, 78.0, 1.0), guide_pieces(overlay)
                view.set_view_state(1.0, 0.0, 0.0)
                app.processEvents()

                # A short pair shares only y 54..74: 16 below its top (70) would pass the middle (64), so the
                # markers stop at the middle.
                assert live_drag(canvas, card, moving_id, 50.0, -146.0) == (50.0, -146.0)
                spans = sorted((gap["crossStart"], gap["cross"], gap["crossEnd"]) for gap in guide_gaps(guides))
                assert spans == [(54.0, 64.0, 74.0), (54.0, 64.0, 74.0)], spans
                assert marker_rows() == [424.0], guide_pieces(overlay)
                assert_no_pixel_painted_twice(guide_pieces(overlay))

                # Zero offset puts the tall pair's markers at the middle, on the middle line (screen y 397):
                # their lines merge into it and each tick gives up the pixel the line crosses.
                overlay.setProperty("horizontalGapHeaderOffset", 0.0)
                assert live_drag(canvas, card, moving_id, 50.0, -200.0) == (50.0, -200.0)
                assert marker_rows() == [], guide_pieces(overlay)
                assert guide_pieces(overlay, "gapTick")[:2] == [(450.0, 394.0, 1.0, 3.0), (450.0, 398.0, 1.0, 3.0)], (
                    guide_pieces(overlay, "gapTick")
                )
                assert (236.0, 397.0, 718.0, 1.0) in guide_pieces(overlay, "line"), guide_pieces(overlay, "line")
                assert_no_pixel_painted_twice(guide_pieces(overlay))
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_crossing_and_coinciding_guides_never_paint_a_pixel_twice(self) -> None:
        self._run_canvas_probe(
            "smart-guides-disjoint-pieces",
            """
            scene, shell = new_scene()
            # A column (A, B, then the dragged node, 76 apart, left edges aligned) and C to the right, level
            # with the dragged node's final place.
            scene.add_node_from_type(CONSTANT, 0.0, -300.0)
            scene.add_node_from_type(CONSTANT, 0.0, -150.0)
            scene.add_node_from_type(CONSTANT, 400.0, 0.0)
            moving_id = scene.add_node_from_type(CONSTANT, 0.0, 200.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                overlay = guide_overlay(canvas)
                assert live_drag(canvas, card, moving_id, 0.0, -200.0) == (0.0, -200.0)
                lines = sorted((line["axis"], line["value"]) for line in guide_lines(guides))
                assert lines == [("x", 0.0), ("x", 105.0), ("x", 210.0), ("y", 0.0), ("y", 37.0), ("y", 74.0)], lines
                # The vertical gaps (A-B and B-dragged, 76 each) run down the middle, x 105: the centre line.
                gaps = sorted((gap["axis"], gap["start"], gap["end"], gap["cross"]) for gap in guide_gaps(guides))
                assert gaps == [("y", -226.0, -150.0, 105.0), ("y", -76.0, 0.0, 105.0)], gaps

                pieces = guide_pieces(overlay)
                assert_no_pixel_painted_twice(pieces)
                # Nor is a pixel lost: the pieces paint exactly what the lines, gap lines and ticks cover.
                expected = set()

                def cover(x0, x1, y0, y1):
                    expected.update((x, y) for x in range(x0, x1) for y in range(y0, y1))

                for column in (640, 745, 850):  # x 0, 105, 210 from A's top (screen 60) to the dragged bottom (434)
                    cover(column, column + 1, 56, 438)
                for row in (360, 397, 434):  # y 0, 37, 74 from the dragged left (640) to C's right (1250)
                    cover(636, 1254, row, row + 1)
                for first, last in ((134, 209), (284, 359)):  # each gap's first and last pixel row
                    cover(742, 749, first, first + 1)  # 7 px ticks centred on x 745
                    cover(742, 749, last, last + 1)
                    cover(745, 746, first + 1, last)  # the gap line between them
                assert set(painted_pixels(pieces)) == expected
                # The gap lines lie on the centre line and merge into it; the horizontal lines and the ticks
                # give up the pixels where a vertical line crosses them.
                assert len(guide_pieces(overlay, "line")) == 3 + 3 * 4
                assert len(guide_pieces(overlay, "gapTick")) == 4 * 2
                assert guide_pieces(overlay, "gapLine") == []
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_default_colours_follow_the_canvas_fill(self) -> None:
        self._run_canvas_probe(
            "smart-guides-colours",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            moving_id = scene.add_node_from_type(CONSTANT, 100.0, 100.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                overlay = guide_overlay(canvas)

                def colours():
                    return tuple(
                        argb(overlay.property(name))
                        for name in ("backgroundFillColor", "guideColor", "pillFillColor", "labelTextColor")
                    )

                # The probe theme's canvas is dark (#151821): the lighter orange at 45% (alpha 0x73).
                assert colours() == ("#FF151821", "#73FF7A3D", "#FFFF7A3D", "#FF1B1D22"), colours()
                # The canvas colour is its own preference, whatever the shell theme: light and white canvases
                # take #E8590C at 60% (0x99), the dark canvas the lighter orange again.
                for variant, fill, guide, pill in (
                    ("white", "#FFFFFFFF", "#99E8590C", "#FFE8590C"),
                    ("light", "#FFF3F5F8", "#99E8590C", "#FFE8590C"),
                    ("dark", "#FF1D1F24", "#73FF7A3D", "#FFFF7A3D"),
                ):
                    set_canvas_background(canvas, shell, variant)
                    assert colours() == (fill, guide, pill, "#FF1B1D22"), (variant, colours())

                # The pieces draw in that colour, alpha included, and follow a canvas colour change mid-drag.
                def piece_colours():
                    shown = [item for item in named_child_items(overlay, "graphCanvasSmartGuidePiece") if item.isVisible()]
                    assert len(shown) == 3, len(shown)
                    return {argb(item.property("color")) for item in shown}

                set_canvas_background(canvas, shell, "white")
                assert live_drag(canvas, card, moving_id, -403.0, 7.0) == (-407.0, 7.0)
                assert piece_colours() == {"#99E8590C"}, piece_colours()
                set_canvas_background(canvas, shell, "dark")
                assert piece_colours() == {"#73FF7A3D"}, piece_colours()
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_gap_labels_are_off_by_default_and_readable_when_shown(self) -> None:
        self._run_canvas_probe(
            "smart-guides-gap-labels",
            """
            scene, shell = new_scene()
            # 80 units each side of the dragged node's final place: wide enough for a label (it needs its
            # own width plus a tick length on either side).
            scene.add_node_from_type(CONSTANT, -440.0, 0.0)
            scene.add_node_from_type(CONSTANT, 140.0, 0.0)
            moving_id = scene.add_node_from_type(CONSTANT, -200.0, 200.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                overlay = guide_overlay(canvas)
                assert live_drag(canvas, card, moving_id, 50.0, -200.0) == (50.0, -200.0)
                assert int(overlay.property("visibleGapCount")) == 2
                assert not bool(overlay.property("showGapLabels"))
                assert not any(item.isVisible() for item in label_items(overlay))

                # Shown, a label reads the gap size on a pill of the opaque guide hue, centred on its marker
                # (x 450 and 740, y 376.5). That orange is bright, so the text is dark.
                overlay.setProperty("showGapLabels", True)
                settle_events(2)
                shown = sorted((item for item in label_items(overlay) if item.isVisible()), key=lambda item: item.x())
                assert len(shown) == 2, [(item.isVisible(), item.width(), item.x()) for item in label_items(overlay)]
                for item, centre_x in zip(shown, (450.0, 740.0)):
                    text = named_item(item, "graphCanvasSmartGuideGapLabelText")
                    assert str(text.property("text")) == "80", text.property("text")
                    assert argb(item.property("color")) == "#FFFF7A3D", argb(item.property("color"))
                    assert argb(text.property("color")) == "#FF1B1D22", argb(text.property("color"))
                    assert abs(item.x() + item.width() / 2.0 - centre_x) <= 0.5, (item.x(), item.width())
                    assert abs(item.y() + item.height() / 2.0 - 376.5) <= 0.5, (item.y(), item.height())

                # A dark pill gets white text.
                overlay.setProperty("pillFillColor", QColor("#1F3A60"))
                settle_events(2)
                assert argb(overlay.property("labelTextColor")) == "#FFFFFFFF", argb(overlay.property("labelTextColor"))
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_controller_republishes_when_only_the_shared_span_changes(self) -> None:
        self._run_canvas_probe(
            "smart-guides-republish-span",
            """
            scene, shell = new_scene()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                guides = smart_guides(canvas)
                overlay = guide_overlay(canvas)

                def publish(gaps):
                    QMetaObject.invokeMethod(
                        guides,
                        "_publish",
                        Qt.ConnectionType.DirectConnection,
                        Q_ARG("QVariant", []),
                        Q_ARG("QVariant", gaps),
                    )
                    settle_events(2)
                    return [(gap["crossStart"], gap["cross"], gap["crossEnd"]) for gap in guide_gaps(guides)]

                def gap(cross_start, cross_end):
                    return {"axis": "x", "start": -190.0, "end": -150.0, "cross": 37.0, "crossStart": cross_start,
                            "crossEnd": cross_end, "size": 40.0}

                def revision():
                    return int(guides.property("guideRevision"))

                start = revision()
                assert publish([gap(0.0, 74.0)]) == [(0.0, 37.0, 74.0)]
                assert guide_pieces(overlay, "gapLine") == [(451.0, 376.0, 38.0, 1.0)], guide_pieces(overlay)
                assert revision() == start + 1
                # The same guides again publish nothing.
                assert publish([gap(0.0, 74.0)]) == [(0.0, 37.0, 74.0)]
                assert revision() == start + 1
                # Only the span changes (its middle stays 37): republished, so the marker follows the new top.
                assert publish([gap(10.0, 64.0)]) == [(10.0, 37.0, 64.0)]
                assert guide_pieces(overlay, "gapLine") == [(451.0, 386.0, 38.0, 1.0)], guide_pieces(overlay)
                assert revision() == start + 2

                # The overlay takes the controller's lines and gaps together when the revision moves, so a
                # publish that changes both lays the pieces out once. A bare write of the gaps shows nothing
                # until the revision moves.
                guides.setProperty("gaps", [])
                settle_events(2)
                assert guide_pieces(overlay, "gapLine") == [(451.0, 386.0, 38.0, 1.0)], guide_pieces(overlay)
                guides.setProperty("guideRevision", revision() + 1)
                settle_events(2)
                assert guide_pieces(overlay) == [], guide_pieces(overlay)
                assert publish([]) == []
                assert not bool(overlay.property("visible"))
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_overlay_maps_guides_through_an_off_origin_view_centre(self) -> None:
        self._run_canvas_probe(
            "smart-guides-view-centre",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -400.0, 0.0)
            scene.add_node_from_type(CONSTANT, 100.0, 0.0)
            moving_id = scene.add_node_from_type(CONSTANT, -200.0, 200.0)
            scene.clear_selection()
            canvas, view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                overlay = guide_overlay(canvas)
                # Centred on scene (100, -50), a scene point (x, y) sits at screen (540 + x, 410 + y): every
                # piece of the equal-spacing test shifts 100 left and 50 down.
                view.set_view_state(1.0, 100.0, -50.0)
                app.processEvents()
                assert live_drag(canvas, card, moving_id, 47.0, -198.0) == (50.0, -200.0)
                assert guide_pieces(overlay, "line") == [
                    (136.0, 410.0, 718.0, 1.0), (136.0, 447.0, 718.0, 1.0), (136.0, 484.0, 718.0, 1.0)
                ], guide_pieces(overlay, "line")
                assert guide_pieces(overlay, "gapTick") == [
                    (350.0, 423.0, 1.0, 7.0), (389.0, 423.0, 1.0, 7.0), (600.0, 423.0, 1.0, 7.0), (639.0, 423.0, 1.0, 7.0)
                ], guide_pieces(overlay, "gapTick")
                assert guide_pieces(overlay, "gapLine") == [(351.0, 426.0, 38.0, 1.0), (601.0, 426.0, 38.0, 1.0)], (
                    guide_pieces(overlay, "gapLine")
                )
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_overlay_pieces_cover_whole_device_pixels_at_other_pixel_ratios(self) -> None:
        self._run_canvas_probe(
            "smart-guides-pixel-ratio",
            """
            scene, shell = new_scene()
            # The first test's neighbour and the equal-spacing test's pair; neither drag below comes near
            # the other's nodes.
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            scene.add_node_from_type(CONSTANT, -400.0, 0.0)
            scene.add_node_from_type(CONSTANT, 100.0, 0.0)
            moving_id = scene.add_node_from_type(CONSTANT, 100.0, 100.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                overlay = guide_overlay(canvas)
                # The probe screen is 1:1; the overlay takes its ratio from a plain property.
                assert float(overlay.property("devicePixelRatio")) == 1.0

                def device_pieces(ratio, part=None):
                    # Every piece in device pixels, which must be whole.
                    scaled = []
                    for piece in guide_pieces(overlay, part):
                        values = tuple(value * ratio for value in piece)
                        assert all(abs(value - round(value)) < 1e-6 for value in values), (ratio, piece)
                        scaled.append(tuple(float(round(value)) for value in values))
                    return scaled

                # The three alignment lines of the first test (screen x 333, 438 and 543, y 156..545). At 150%
                # a hairline is two device pixels (4/3 logical px) on the 4/3 px grid; at 200% it is two
                # device pixels (1 logical px) again.
                for ratio, expected in (
                    (1.5, [(498.0, 234.0, 2.0, 584.0), (656.0, 234.0, 2.0, 584.0), (814.0, 234.0, 2.0, 584.0)]),
                    (2.0, [(666.0, 312.0, 2.0, 778.0), (876.0, 312.0, 2.0, 778.0), (1086.0, 312.0, 2.0, 778.0)]),
                ):
                    overlay.setProperty("devicePixelRatio", ratio)
                    assert abs(float(overlay.property("hairline")) - 2.0 / ratio) < 1e-9
                    assert live_drag(canvas, card, moving_id, -403.0, 7.0) == (-407.0, 7.0)
                    assert device_pieces(ratio) == expected, (ratio, device_pieces(ratio))
                    card.dragCanceled.emit(moving_id)
                    app.processEvents()

                # Equal spacing at 150%: ticks, gap lines and lines all stay two device pixels thick, and no
                # device pixel is painted twice. The gap line runs 16 below the pair's top (screen y 376, the
                # 4/3 px cell from device row 564).
                overlay.setProperty("devicePixelRatio", 1.5)
                assert live_drag(canvas, card, moving_id, -253.0, -98.0) == (-250.0, -100.0)
                pieces = device_pieces(1.5)
                assert all(min(width, height) == 2.0 for _x, _y, width, height in pieces), pieces
                assert {y for _x, y, _w, _h in device_pieces(1.5, "gapLine")} == {564.0}, device_pieces(1.5, "gapLine")
                assert len(device_pieces(1.5, "gapTick")) == 4, device_pieces(1.5, "gapTick")
                assert_no_pixel_painted_twice(pieces)
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_piece_pool_splits_as_many_crossings_as_it_has_room_for(self) -> None:
        self._run_canvas_probe(
            "smart-guides-piece-pool",
            """
            scene, shell = new_scene()
            canvas, _view, window = open_canvas(scene, shell)
            try:
                guides = smart_guides(canvas)
                overlay = guide_overlay(canvas)
                # Six lines and twelve gap markers, three pieces each, twice over for splits.
                assert int(overlay.property("pieceCapacity")) == 84
                assert len(named_child_items(overlay, "graphCanvasSmartGuidePiece")) == 84

                # Twelve gaps stacked down x = 0 (scene y -330 + 55k, 40 tall): each draws a gap line down
                # screen column 640 and two ticks at its first and last rows, 601 px long (columns 340..940).
                overlay.setProperty("gapTickLengthPx", 601.0)
                gaps = [
                    {"axis": "y", "start": -330.0 + 55.0 * k, "end": -290.0 + 55.0 * k, "cross": 0.0,
                     "crossStart": -20.0, "crossEnd": 20.0, "size": 40.0}
                    for k in range(12)
                ]
                tick_rows = [row for k in range(12) for row in (30 + 55 * k, 69 + 55 * k)]

                def publish(line_xs):
                    lines = [{"axis": "x", "value": x, "start": -350.0, "end": 350.0} for x in line_xs]
                    QMetaObject.invokeMethod(
                        guides,
                        "_publish",
                        Qt.ConnectionType.DirectConnection,
                        Q_ARG("QVariant", lines),
                        Q_ARG("QVariant", gaps),
                    )
                    settle_events(2)
                    # What the guides cover: each line down its column (rows 6..713 with the overshoot), each
                    # tick across its row, each gap line between its ticks.
                    columns = [640 + int(x) for x in line_xs]
                    covered = {(column, row) for column in columns for row in range(6, 714)}
                    covered |= {(column, row) for row in tick_rows for column in range(340, 941)}
                    covered |= {(640, row) for k in range(12) for row in range(31 + 55 * k, 69 + 55 * k)}
                    pieces = guide_pieces(overlay)
                    painted = painted_pixels(pieces)
                    assert set(painted) == covered, (len(set(painted) - covered), len(covered - set(painted)))
                    counts = {}
                    for pixel in painted:
                        counts[pixel] = counts.get(pixel, 0) + 1
                    twice = sorted(pixel for pixel, count in counts.items() if count > 1)
                    assert all(column in columns and row in tick_rows for column, row in twice), twice
                    return len(pieces), len(twice)

                # Lines at screen x 340 and 940 meet every tick in its end cell, which only shortens the tick;
                # the one at 740 splits it. 39 pieces plus 24 splits fit: nothing is painted twice.
                assert publish([-300.0, 100.0, 300.0]) == (63, 0)

                # Two more lines inside the ticks: 41 pieces plus 72 splits would need 113. The pool fills up
                # with 43 splits, and only the 29 crossings left over are painted twice.
                assert publish([-300.0, -100.0, 100.0, 200.0, 300.0]) == (84, 29)
                QMetaObject.invokeMethod(
                    guides, "_publish", Qt.ConnectionType.DirectConnection, Q_ARG("QVariant", []), Q_ARG("QVariant", [])
                )
                settle_events(2)
                assert guide_pieces(overlay) == []
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_unmoved_release_inside_a_live_session_neither_snaps_nor_keeps_the_session(self) -> None:
        self._run_canvas_probe(
            "smart-guides-unmoved-release-in-session",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            # 4 px right of the neighbour's left edge: a guide snap at the commit would pull it to -307.
            moving_id = scene.add_node_from_type(CONSTANT, -303.0, 100.0)
            scene.clear_selection()
            history = bind_history(scene)
            canvas, _view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                # A live frame starts the anchor's move session ...
                assert live_drag(canvas, card, moving_id, 40.0, 0.0) == (40.0, 0.0)
                assert bool(guides.property("active"))
                before = guide_counts(guides)
                # ... then the gesture reports an unmoved release at the node's own position.
                card.dragFinished.emit(moving_id, -303.0, 100.0, False, "", False)
                app.processEvents()
                assert position(scene, moving_id) == (-303.0, 100.0), position(scene, moving_id)
                assert guide_counts(guides) == before
                assert not bool(guides.property("active"))
                assert guide_lines(guides) == [] and guide_gaps(guides) == []
                assert live_offset(canvas) == (0.0, 0.0)
                assert history.undo_depth(scene.workspace_id) == 0
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_right_press_mid_drag_cancels_the_drag_before_the_context_menu(self) -> None:
        self._run_canvas_probe(
            "smart-guides-right-press-mid-drag",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            moving_id = scene.add_node_from_type(CONSTANT, -303.0, 100.0)
            scene.clear_selection()
            history = bind_history(scene)
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            events = []
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                card.dragOffsetChanged.connect(lambda *args: events.append("offset"))
                card.dragFinished.connect(lambda *args: events.append("finished"))
                card.dragCanceled.connect(lambda *args: events.append("canceled"))
                card.nodeContextRequested.connect(lambda *args: events.append("context"))
                card.nodeClicked.connect(lambda *args: events.append("clicked"))

                def send(kind, button, buttons, point):
                    event = QMouseEvent(
                        kind, QPointF(point), QPointF(window.mapToGlobal(point)), button, buttons,
                        Qt.KeyboardModifier.NoModifier,
                    )
                    QCoreApplication.sendEvent(window, event)
                    settle_events(2)

                def menu_point():
                    return float(canvas.property("contextMenuX")), float(canvas.property("contextMenuY"))

                # A plain right-click, with no drag, only opens the context menu, at the pointer.
                start = hover_host_local_point(window, card, 100.0, 45.0)
                send(QEvent.Type.MouseButtonPress, Qt.MouseButton.RightButton, Qt.MouseButton.RightButton, start)
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.RightButton, Qt.MouseButton.NoButton, start)
                assert events == ["context"], events
                assert bool(canvas.property("nodeContextVisible"))
                assert menu_point() == (start.x(), start.y()), (menu_point(), start)
                canvas._closeContextMenus()
                settle_events(2)
                events.clear()

                # A live drag 40 px right and 20 down; its first frame starts the guide session.
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                far = QPoint(start.x() + 40, start.y() + 20)
                move_with(window, far)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                assert live_offset(canvas) == (40.0, 20.0), live_offset(canvas)
                assert bool(guides.property("active"))
                assert set(events) == {"offset"}, events
                events.clear()

                # A right press mid-drag cancels the drag, then opens the context menu: no live offset or
                # guide session lingers under the menu. The cancel moves the node back, yet the menu opens
                # under the pointer, not where the drag grabbed the node.
                both = Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
                send(QEvent.Type.MouseButtonPress, Qt.MouseButton.RightButton, both, far)
                assert events == ["canceled", "context"], events
                assert live_offset(canvas) == (0.0, 0.0), live_offset(canvas)
                assert not bool(guides.property("active"))
                assert guide_lines(guides) == [] and guide_gaps(guides) == []
                assert bool(canvas.property("nodeContextVisible"))
                assert menu_point() == (far.x(), far.y()), (menu_point(), far)
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.RightButton, Qt.MouseButton.LeftButton, far)

                # The rest of that left press is inert: moving on restarts no drag, and the release neither
                # commits a move nor clicks.
                further = QPoint(start.x() + 90, start.y())
                move_with(window, further)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, further)
                assert events == ["canceled", "context"], events
                assert live_offset(canvas) == (0.0, 0.0)
                assert not bool(guides.property("active"))
                assert position(scene, moving_id) == (-303.0, 100.0), position(scene, moving_id)
                assert history.undo_depth(scene.workspace_id) == 0
                assert selected_ids(canvas) == []

                # That release ended the inert state: the next plain click selects the node ...
                canvas._closeContextMenus()
                settle_events(2)
                events.clear()
                click_card(window, card)
                assert "clicked" in events, events
                assert selected_ids(canvas) == [moving_id]

                # ... and the next drag moves it and commits (60 px right: no guide within reach).
                scene.clear_selection()
                app.processEvents()
                events.clear()
                QTest.qWait(int(app.styleHints().mouseDoubleClickInterval()) + 50)
                start = hover_host_local_point(window, card, 100.0, 45.0)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                end = QPoint(start.x() + 60, start.y())
                move_with(window, end)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                assert live_offset(canvas) == (60.0, 0.0), live_offset(canvas)
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, end)
                assert events[-1] == "finished" and "canceled" not in events, events
                assert position(scene, moving_id) == (-243.0, 100.0), position(scene, moving_id)
                assert history.undo_depth(scene.workspace_id) == 1
                assert live_offset(canvas) == (0.0, 0.0)
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_right_press_before_the_drag_threshold_leaves_the_rest_of_the_press_inert(self) -> None:
        self._run_canvas_probe(
            "smart-guides-right-press-before-threshold",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            moving_id = scene.add_node_from_type(CONSTANT, -303.0, 100.0)
            scene.clear_selection()
            history = bind_history(scene)
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            events = []
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                card.dragOffsetChanged.connect(lambda *args: events.append("offset"))
                card.dragFinished.connect(lambda *args: events.append("finished"))
                card.dragCanceled.connect(lambda *args: events.append("canceled"))
                card.nodeContextRequested.connect(lambda *args: events.append("context"))
                card.nodeClicked.connect(lambda *args: events.append("clicked"))
                both = Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton

                def send(kind, button, buttons, point):
                    event = QMouseEvent(
                        kind, QPointF(point), QPointF(window.mapToGlobal(point)), button, buttons,
                        Qt.KeyboardModifier.NoModifier,
                    )
                    QCoreApplication.sendEvent(window, event)
                    settle_events(2)

                def assert_untouched():
                    assert live_offset(canvas) == (0.0, 0.0), live_offset(canvas)
                    assert not bool(guides.property("active"))
                    assert position(scene, moving_id) == (-303.0, 100.0), position(scene, moving_id)
                    assert history.undo_depth(scene.workspace_id) == 0
                    assert selected_ids(canvas) == []

                # The left button goes down, the pointer moves 2 px (under the 4 px drag threshold) and the
                # right button goes down: no drag is live, so nothing is canceled, and the menu opens.
                start = hover_host_local_point(window, card, 100.0, 45.0)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                near = QPoint(start.x() + 2, start.y())
                move_with(window, near)
                send(QEvent.Type.MouseButtonPress, Qt.MouseButton.RightButton, both, near)
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.RightButton, Qt.MouseButton.LeftButton, near)
                assert events == ["context"], events
                assert bool(canvas.property("nodeContextVisible"))

                # The rest of that left press is inert: moving well past the threshold starts no drag and
                # no guides under the open menu, and the release neither commits nor clicks the menu shut.
                far = QPoint(start.x() + 60, start.y() + 3)
                move_with(window, far)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                assert_untouched()
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, far)
                assert events == ["context"], events
                assert bool(canvas.property("nodeContextVisible"))
                assert_untouched()

                # The same without moving: the left release neither selects nor closes the menu.
                canvas._closeContextMenus()
                settle_events(2)
                events.clear()
                QTest.qWait(int(app.styleHints().mouseDoubleClickInterval()) + 50)
                start = hover_host_local_point(window, card, 100.0, 45.0)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                send(QEvent.Type.MouseButtonPress, Qt.MouseButton.RightButton, both, start)
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.RightButton, Qt.MouseButton.LeftButton, start)
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, start)
                assert events == ["context"], events
                assert bool(canvas.property("nodeContextVisible"))
                assert_untouched()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_right_press_mid_group_drag_over_a_wire_opens_the_wire_menu(self) -> None:
        self._run_canvas_probe(
            "smart-guides-right-press-group-over-wire",
            """
            scene, shell = new_scene()
            group_id = add_group(scene, -300.0, -150.0, 600.0, 400.0)
            # A wire between two nodes outside the Group runs across it.
            source_id = scene.add_node_from_type(CONSTANT, -760.0, 10.0)
            target_id = scene.add_node_from_type("core.logger", 480.0, 10.0)
            edge_id = scene.add_edge(source_id, "value", target_id, "message")
            scene.clear_selection()
            history = bind_history(scene)
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            events = []
            try:
                settle_events(6)
                card = card_for(canvas, group_id, "graphGroupBackdropInputCard")
                card.dragOffsetChanged.connect(lambda *args: events.append("offset"))
                card.dragFinished.connect(lambda *args: events.append("finished"))
                card.dragCanceled.connect(lambda *args: events.append("canceled"))
                card.nodeContextRequested.connect(lambda *args: events.append("context"))
                edge_layer = canvas.findChild(QObject, "graphCanvasEdgeLayer")
                geometry = variant_value(variant_value(edge_layer._visibleEdgeSnapshot(edge_id)).get("geometry"))
                anchor = variant_value(edge_layer._edgeAnchor(geometry, 0.5))
                on_wire = QPoint(
                    round(float(edge_layer.sceneToScreenX(float(anchor["x"])))),
                    round(float(edge_layer.sceneToScreenY(float(anchor["y"])))),
                )
                assert str(edge_layer.edgeAtScreen(on_wire.x(), on_wire.y())) == edge_id
                start = QPoint(on_wire.x(), on_wire.y() + 60)
                assert str(edge_layer.edgeAtScreen(start.x(), start.y())) == ""

                def send(kind, button, buttons, point):
                    event = QMouseEvent(
                        kind, QPointF(point), QPointF(window.mapToGlobal(point)), button, buttons,
                        Qt.KeyboardModifier.NoModifier,
                    )
                    QCoreApplication.sendEvent(window, event)
                    settle_events(2)

                # Grab the Group off the wire and drag it up until the pointer sits on the wire.
                QTest.mouseMove(window, start)
                settle_events(3)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                move_with(window, QPoint(start.x(), start.y() - 30))
                move_with(window, on_wire)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                assert live_offset(canvas)[1] < -50.0, live_offset(canvas)

                # The right press cancels the drag, which moves the Group back, yet it lands where the
                # pointer is: on the wire, so the wire menu opens rather than the Group's.
                both = Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
                send(QEvent.Type.MouseButtonPress, Qt.MouseButton.RightButton, both, on_wire)
                assert "canceled" in events and "context" not in events, events
                assert live_offset(canvas) == (0.0, 0.0), live_offset(canvas)
                assert bool(canvas.property("edgeContextVisible"))
                assert not bool(canvas.property("nodeContextVisible"))
                assert str(canvas.property("edgeContextEdgeId")) == edge_id
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.RightButton, Qt.MouseButton.LeftButton, on_wire)

                # The rest of the left press stays inert.
                events.clear()
                last = QPoint(on_wire.x() + 40, on_wire.y() - 40)
                move_with(window, last)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                send(QEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, last)
                assert events == [], events
                assert position(scene, group_id) == (-300.0, -150.0), position(scene, group_id)
                assert history.undo_depth(scene.workspace_id) == 0
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_resize_handle_snaps_moving_edges_after_the_pointer_moves(self) -> None:
        self._run_canvas_probe(
            "smart-guides-resize-handle",
            """
            scene, shell = new_scene()
            # Flowchart processes are 224 x 84. Right edges at 327 (3 px from the resized node's) and 364.
            scene.add_node_from_type(PROCESS, 103.0, -200.0)
            scene.add_node_from_type(PROCESS, 140.0, -400.0)
            node_id = scene.add_node_from_type(PROCESS, 100.0, 100.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            try:
                card = card_for(canvas, node_id)
                guides = smart_guides(canvas)
                handle = [
                    item
                    for item in named_child_items(card, "graphNodeResizeHandle")
                    if str(item.property("cornerRole")) == "bottomRight"
                ][0]
                hover_host_local_point(window, card, 60.0, 40.0)
                start = item_scene_point(handle, 0.75, 0.75)
                QTest.mouseMove(window, start)
                settle_events(3)

                def at(dx, dy):
                    return QPoint(start.x() + dx, start.y() + dy)

                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                assert bool(guides.property("active"))
                # The press-time preview must not jump to the edge 3 px away.
                assert_rect(card, (100.0, 100.0, 224.0, 84.0))
                assert guide_lines(guides) == []

                move_with(window, at(1, 0))
                assert_rect(card, (100.0, 100.0, 227.0, 84.0))
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", 327.0)]
                assert int(guide_overlay(canvas).property("visibleLineCount")) == 1

                # 10 px from the 364 edge: no snap.
                move_with(window, at(30, 0))
                assert_rect(card, (100.0, 100.0, 254.0, 84.0))
                assert guide_lines(guides) == []

                move_with(window, at(37, 0))
                assert_rect(card, (100.0, 100.0, 264.0, 84.0))
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", 364.0)]

                # Alt skips the guides.
                move_with(window, at(37, 0), Qt.KeyboardModifier.AltModifier)
                assert_rect(card, (100.0, 100.0, 261.0, 84.0))
                assert guide_lines(guides) == []

                # Shift keeps the press aspect ratio: the snapped width drives the height.
                move_with(window, at(37, 6), Qt.KeyboardModifier.ShiftModifier)
                assert_rect(card, (100.0, 100.0, 264.0, 99.0))
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", 364.0)]

                # The preference turned off mid-resize: the next move neither snaps nor shows a guide.
                set_smart_guides_preference(canvas, shell, False)
                assert not bool(guides.property("enabled"))
                move_with(window, at(37, 0))
                assert_rect(card, (100.0, 100.0, 261.0, 84.0))
                assert guide_lines(guides) == []
                set_smart_guides_preference(canvas, shell, True)

                move_with(window, at(37, 0))
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at(37, 0))
                settle_events(3)
                payload = payload_of(scene, node_id)
                assert (payload["x"], payload["y"], payload["width"], payload["height"]) == (100.0, 100.0, 264.0, 84.0), payload
                assert guide_lines(guides) == []
                assert not bool(guides.property("active"))
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_click_never_runs_guides_or_records_a_move(self) -> None:
        self._run_canvas_probe(
            "smart-guides-click",
            """
            scene, shell = new_scene()
            neighbour_id = scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            # 4 px right of the neighbour's left edge: a guide snap would pull it to -307.
            near_id = scene.add_node_from_type(CONSTANT, -303.0, 100.0)
            partner_id = scene.add_node_from_type(CONSTANT, -250.0, 250.0)
            scene.clear_selection()
            history = bind_history(scene)
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            try:
                card = card_for(canvas, near_id)
                guides = smart_guides(canvas)

                def assert_unmoved():
                    assert position(scene, near_id) == (-303.0, 100.0), position(scene, near_id)
                    assert position(scene, partner_id) == (-250.0, 250.0), position(scene, partner_id)
                    assert history.undo_depth(scene.workspace_id) == 0
                    assert guide_counts(guides) == (0, 0)
                    assert not bool(guides.property("active"))

                # A plain click selects the node without a guide session, snapshot or move.
                click_card(window, card)
                assert_unmoved()
                assert selected_ids(canvas) == [near_id]

                # A click inside a multi-selection whose union is near-aligned moves nothing either.
                scene.select_node(near_id, False)
                scene.select_node(partner_id, True)
                app.processEvents()
                click_card(window, card)
                assert_unmoved()

                # Ctrl+click adds to the selection: no commit reselects the node before the click toggles it.
                scene.select_node(neighbour_id, False)
                app.processEvents()
                click_card(window, card, Qt.KeyboardModifier.ControlModifier)
                assert_unmoved()
                assert selected_ids(canvas) == sorted([neighbour_id, near_id])

                # With grid snap on, a click keeps its pre-existing grid commit and never meets the guide.
                shell.snap_to_grid_enabled = True
                scene.clear_selection()
                scene.move_node(near_id, -303.0, 107.0)
                app.processEvents()
                click_card(window, card)
                assert position(scene, near_id) == (-300.0, 100.0), position(scene, near_id)
                assert guide_counts(guides) == (0, 0)
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_real_pointer_drag_lands_exactly_aligned(self) -> None:
        self._run_canvas_probe(
            "smart-guides-pointer-drag",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            moving_id = scene.add_node_from_type(CONSTANT, 100.0, 100.0)
            scene.clear_selection()
            history = bind_history(scene)
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                start = hover_host_local_point(window, card, 100.0, 45.0)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                move_with(window, QPoint(start.x() - 200, start.y()))
                # 4 px right of the neighbour's left edge.
                end = QPoint(start.x() - 403, start.y() + 7)
                move_with(window, end)
                canvas.property("frameSchedulerRef").flushPendingRedraws()
                app.processEvents()
                assert live_offset(canvas) == (-407.0, 7.0), live_offset(canvas)
                assert ("x", -307.0) in [(line["axis"], line["value"]) for line in guide_lines(guides)]

                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
                settle_events(3)
                assert position(scene, moving_id) == (-307.0, 107.0), position(scene, moving_id)
                assert history.undo_depth(scene.workspace_id) == 1
                assert live_offset(canvas) == (0.0, 0.0)
                assert guide_lines(guides) == []
                assert not bool(guides.property("active"))
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_zoom_change_mid_drag_rebuilds_the_snapshot_and_rescales_the_threshold(self) -> None:
        self._run_canvas_probe(
            "smart-guides-zoom-mid-drag",
            """
            scene, shell = new_scene()
            scene.add_node_from_type(CONSTANT, -307.0, -200.0)
            moving_id = scene.add_node_from_type(CONSTANT, 100.0, 100.0)
            scene.clear_selection()
            canvas, view, window = open_canvas(scene, shell)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                overlay = guide_overlay(canvas)
                # Zoom 1: 4 scene units are 4 px, inside the 6 px threshold.
                assert live_drag(canvas, card, moving_id, -403.0, 7.0) == (-407.0, 7.0)
                assert int(guides.property("profileSnapshotCount")) == 1

                view.set_view_state(2.0, 0.0, 0.0)
                app.processEvents()
                # Zoom 2: the same 4 units are 8 px, outside the threshold; the view change re-snapshots.
                assert live_drag(canvas, card, moving_id, -403.0, 7.0) == (-403.0, 7.0)
                assert int(guides.property("profileSnapshotCount")) == 2
                # 2 units (4 px) still snap, on the same snapshot.
                assert live_drag(canvas, card, moving_id, -405.0, 7.0) == (-407.0, 7.0)
                assert int(guides.property("profileSnapshotCount")) == 2
                # Screen space follows the zoom: scene x -307 sits at 640 + (-307 * 2) = 26.
                shown = guide_pieces(overlay, "line")
                assert min(piece[0] for piece in shown) == 26.0, shown
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_a_long_drag_past_a_trimmed_snapshot_retakes_it_near_the_destination(self) -> None:
        self._run_canvas_probe(
            "smart-guides-trimmed-long-drag",
            """
            def build(filler_rows):
                # At zoom 0.25 the 1280 x 720 view shows scene x -2560..2560 and y -1440..1440. Fillers sit in
                # rows of 13 at the top left; the moving node starts below their first column and the target
                # sits alone at the bottom right.
                scene, shell = new_scene()
                for row in range(filler_rows):
                    for column in range(13):
                        scene.add_node_from_type(CONSTANT, -2400.0 + 250.0 * column, -1300.0 + 120.0 * row)
                target_id = scene.add_node_from_type(CONSTANT, 2000.0, 1000.0)
                moving_id = scene.add_node_from_type(CONSTANT, -2400.0, 0.0)
                scene.clear_selection()
                canvas, view, window = open_canvas(scene, shell)
                view.set_view_state(0.25, 0.0, 0.0)
                app.processEvents()
                return scene, canvas, window, target_id, moving_id

            def long_drag(canvas, card, moving_id):
                # Ten frames to 10 right of the target's left edge (x 2010, 4410 from the start) and 226 above
                # it; the snapshot count after each. The threshold is 24 scene units at zoom 0.25.
                counts = []
                for step in range(1, 11):
                    offset = live_drag(canvas, card, moving_id, 441.0 * step, 70.0 * step)
                    counts.append(guide_counts(smart_guides(canvas))[0])
                return offset, counts

            # 131 candidates: 130 fillers and the target, 3 more than the cap.
            scene, canvas, window, target_id, moving_id = build(10)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                # The drop-gap rule alone: no retake interval, whatever the frames' pace.
                guides.setProperty("retakeMinIntervalMs", 0)
                bridge = canvas.property("canvasStateBridge")
                first = variant_value(bridge.smart_guide_snapshot([moving_id], {}, {"offset_x": 441.0, "offset_y": 70.0}))
                assert len(first["candidates"]) == 128 and first["trimmed"], first["trimmed"]
                # Ranked at frame 1, the snapshot leaves out the target and the two fillers farthest up and
                # right. Their nearest along x is 2349 away (the far column of fillers), along y 856 (the
                # target), so no frame retakes it until one has moved 2349 less the threshold along x.
                assert target_id not in {rect["node_id"] for rect in first["candidates"]}
                assert (first["dropGapX"], first["dropGapY"]) == (2349.0, 856.0), first
                offset, counts = long_drag(canvas, card, moving_id)
                # Frame 7 is the first 2325 or more along x from frame 1 (2646): it retakes, ranked beside
                # the target's column, and frame 10 snaps to the target's left edge.
                assert counts == [1, 1, 1, 1, 1, 1, 2, 2, 2, 2], counts
                assert offset == (4400.0, 700.0), offset
                assert guide_counts(guides) == (2, 10), guide_counts(guides)
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [
                    ("x", 2000.0), ("x", 2105.0), ("x", 2210.0)
                ], guide_lines(guides)
                card.dragCanceled.emit(moving_id)
                app.processEvents()

                # Without the re-snapshot the only snapshot is the one ranked at frame 1: no target.
                guides.setProperty("resnapshotFloorPx", 1.0e9)
                before = guide_counts(guides)
                offset, counts = long_drag(canvas, card, moving_id)
                assert offset == (4410.0, 700.0), offset
                assert guide_counts(guides)[0] - before[0] == 1
                assert guide_lines(guides) == []
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)

            # One row of fillers: 14 candidates, all in the one snapshot, which the drag keeps however far.
            scene, canvas, window, target_id, moving_id = build(1)
            try:
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                assert long_drag(canvas, card, moving_id)[0] == (4400.0, 700.0), live_offset(canvas)
                assert guide_counts(guides) == (1, 10), guide_counts(guides)
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_a_trimmed_snapshot_is_retaken_before_a_left_out_candidate_can_draw_a_gap(self) -> None:
        # Zoom 0.12: threshold 50 scene units, re-snapshot floor 333. 126 fillers in the moving node's column
        # band, tall Groups A and B beside its rows and a short Group H between them lower down make 129
        # candidates, so the snapshot ranked at the first frame keeps A and B and leaves H out. At the end of
        # the drag the moving node is in H's rows, where a snapshot without H measures the A-B gap straight
        # through H and snaps X from 1208 to 1200 one A-B gap past B.
        self._run_canvas_probe(
            "smart-guides-trimmed-spurious-gap",
            """
            scene, shell = new_scene()
            moving_id = scene.add_node_from_type(CONSTANT, 0.0, 0.0)
            for k in range(126):
                scene.add_node_from_type(CONSTANT, -150.0 + 75.0 * (k % 5), -400.0 - 80.0 * (k // 5))
            a_id = add_group(scene, 300.0, 110.0, 260.0, 2400.0)
            h_id = add_group(scene, 550.0, 1000.0, 260.0, 180.0)
            b_id = add_group(scene, 750.0, 110.0, 260.0, 2400.0)
            scene.clear_selection()
            canvas, view, window = open_canvas(scene, shell)
            try:
                view.set_view_state(0.12, 500.0, 0.0)
                app.processEvents()
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                # The drop-gap rule alone: no retake interval, whatever the frames' pace.
                guides.setProperty("retakeMinIntervalMs", 0)
                bridge = canvas.property("canvasStateBridge")
                first = variant_value(bridge.smart_guide_snapshot([moving_id], {}, {"offset_x": 2.0, "offset_y": 2.0}))
                kept = {rect["node_id"] for rect in first["candidates"]}
                assert first["trimmed"] and a_id in kept and b_id in kept and h_id not in kept, first["trimmed"]
                path = [(2.0, 2.0)] + [(1208.0 * step / 6.0, 1020.0 * step / 6.0) for step in range(1, 7)]
                counts = []
                for dx, dy in path:
                    live = live_drag(canvas, card, moving_id, dx, dy)
                    counts.append(guide_counts(guides)[0])
                hx, hy, hw, hh = (float(payload_of(scene, h_id)[key]) for key in ("x", "y", "width", "height"))
                across_h = [
                    gap for gap in guide_gaps(guides)
                    if gap["start"] < hx + hw and gap["end"] > hx and gap["crossStart"] < hy + hh and gap["crossEnd"] > hy
                ]
                # H is 338 from the moving node along x: the frame at x 403 (401 from the first frame) retakes
                # the snapshot, with H in it, before H can join a band. At the end, as with every candidate,
                # nothing guides X and Y meets H's top edge 20 up.
                assert counts[:3] == [1, 1, 2], counts
                assert across_h == [], (across_h, guide_gaps(guides))
                assert live == (1208.0, 1000.0), live
                assert ("y", 1000.0) in [(line["axis"], line["value"]) for line in guide_lines(guides)], guide_lines(guides)
                assert [line for line in guide_lines(guides) if line["axis"] == "x"] == [], guide_lines(guides)
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_a_trimmed_snapshot_is_retaken_only_once_a_left_out_candidate_could_join_a_band(self) -> None:
        self._run_canvas_probe(
            "smart-guides-drop-gap-rule",
            _STUB_GUIDES_HARNESS
            + """
            try:
                # The drop-gap rule alone: no retake interval.
                guides.setProperty("retakeMinIntervalMs", 0)
                # Untrimmed: one snapshot however far the drag goes.
                stub.setProperty("trimmed", False)
                assert drag([(40.0 * step, 25.0 * step) for step in range(60)]) == [(0.0, 0.0)]

                # Trimmed, the nearest left-out candidate 300 away along x and 900 along y. A snap moves the
                # settled rect up to the 6-unit threshold further, so x retakes at 294 of travel, not 293.
                stub.setProperty("trimmed", True)
                stub.setProperty("dropGapX", 300.0)
                stub.setProperty("dropGapY", 900.0)
                assert drag([(0.0, 0.0), (293.0, 0.0), (294.0, 0.0), (500.0, 0.0)]) == [(0.0, 0.0), (294.0, 0.0)]
                assert drag([(0.0, 0.0), (0.0, -893.0), (0.0, -894.0)]) == [(0.0, 0.0), (0.0, -894.0)]
                # Travel counts from where the last snapshot was ranked.
                assert drag([(0.0, 0.0), (294.0, 0.0), (587.0, 0.0), (588.0, 0.0)]) == [
                    (0.0, 0.0), (294.0, 0.0), (588.0, 0.0)
                ]

                # A left-out candidate beside the moving rect (both gaps 0): only the floor holds retakes back,
                # one per 40 units of travel, straight-line.
                stub.setProperty("dropGapX", 0.0)
                stub.setProperty("dropGapY", 0.0)
                assert drag([(10.0 * step, 0.0) for step in range(13)]) == [
                    (0.0, 0.0), (40.0, 0.0), (80.0, 0.0), (120.0, 0.0)
                ]
                assert drag([(0.0, 0.0), (28.0, 28.0), (29.0, 29.0)]) == [(0.0, 0.0), (29.0, 29.0)]
                # A trimmed snapshot without drop gaps counts them as 0.
                stub.setProperty("reportGaps", False)
                stub.setProperty("dropGapX", 300.0)
                stub.setProperty("dropGapY", 900.0)
                assert drag([(10.0 * step, 0.0) for step in range(9)]) == [(0.0, 0.0), (40.0, 0.0), (80.0, 0.0)]
                stub.setProperty("reportGaps", True)
                stub.setProperty("dropGapX", 0.0)
                stub.setProperty("dropGapY", 0.0)

                # Zoom 0.25: the 40 px floor is 160 scene units and the 6 px threshold 24.
                view.setProperty("zoom_value", 0.25)
                assert drag([(40.0 * step, 0.0) for step in range(9)]) == [(0.0, 0.0), (160.0, 0.0), (320.0, 0.0)]
                stub.setProperty("dropGapX", 300.0)
                stub.setProperty("dropGapY", 900.0)
                assert drag([(0.0, 0.0), (275.0, 0.0), (276.0, 0.0)]) == [(0.0, 0.0), (276.0, 0.0)]
            finally:
                stage.deleteLater()
                app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_a_resize_past_a_trimmed_snapshot_retakes_it_around_the_moving_corner(self) -> None:
        self._run_canvas_probe(
            "smart-guides-trimmed-resize",
            _STUB_GUIDES_HARNESS
            + """
            try:
                # The drop-gap rule alone: no retake interval.
                guides.setProperty("retakeMinIntervalMs", 0)
                # Bottom-right corner, drop gaps 150 along both axes. The stored rect is x 100..300, y 100..200;
                # the first snapshot is ranked at it and holds the "near" edge 303.
                guides.beginResize("resized")
                assert resize((100.0, 100.0, 301.0, 200.0)) == (100.0, 100.0, 303.0, 200.0)
                # The corner 205 right and 260 down, past both drop gaps: a new snapshot ranked there.
                assert resize((100.0, 100.0, 505.0, 460.0)) == (100.0, 100.0, 505.0, 460.0)
                # Far out the new snapshot is ranked beside the target, whose right edge (1300) is 3 away.
                assert resize((100.0, 100.0, 1297.0, 200.0)) == (100.0, 100.0, 1300.0, 200.0)
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", 1300.0)]
                assert offsets() == [(0.0, 0.0), (205.0, 260.0), (997.0, 0.0)], offsets()
                # A move of 7 along x and 50 along y stays on the current snapshot.
                assert resize((100.0, 100.0, 1290.0, 150.0)) == (100.0, 100.0, 1290.0, 150.0)
                assert len(offsets()) == 3
                guides.endResize()

                # The top-left corner ranks by its own moving edges: 250 left and 30 up.
                stub.setProperty("offsets", [])
                guides.beginResize("resized")
                resize((95.0, 95.0, 300.0, 200.0), moving_left=True, moving_top=True)
                resize((-150.0, 70.0, 300.0, 200.0), moving_left=True, moving_top=True)
                assert offsets() == [(0.0, 0.0), (-250.0, -30.0)], offsets()
                guides.endResize()

                # Untrimmed, the snapshot holds every candidate: one serves the whole resize.
                stub.setProperty("trimmed", False)
                stub.setProperty("offsets", [])
                guides.beginResize("resized")
                assert resize((100.0, 100.0, 301.0, 200.0)) == (100.0, 100.0, 303.0, 200.0)
                assert resize((100.0, 100.0, 1297.0, 200.0)) == (100.0, 100.0, 1297.0, 200.0)
                assert offsets() == [(0.0, 0.0)], offsets()
                guides.endResize()
            finally:
                stage.deleteLater()
                app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_a_scene_change_mid_resize_ranks_the_new_snapshot_at_the_moving_corner(self) -> None:
        self._run_canvas_probe(
            "smart-guides-resize-invalidate-rank",
            _STUB_GUIDES_HARNESS
            + """
            try:
                # The drop-gap rule alone: no retake interval.
                guides.setProperty("retakeMinIntervalMs", 0)
                guides.beginResize("resized")
                resize((100.0, 100.0, 301.0, 200.0))
                assert resize((100.0, 100.0, 1297.0, 200.0)) == (100.0, 100.0, 1300.0, 200.0)
                assert offsets() == [(0.0, 0.0), (997.0, 0.0)], offsets()
                # The scene changes under the resize: the next frame takes a new snapshot, still ranked at the
                # corner 997 right of the stored rect, so it holds the target and snaps at once. The frame
                # after it keeps that snapshot.
                guides.invalidateSnapshot()
                assert guide_lines(guides) == []
                assert resize((100.0, 100.0, 1297.0, 200.0)) == (100.0, 100.0, 1300.0, 200.0)
                assert offsets() == [(0.0, 0.0), (997.0, 0.0), (997.0, 0.0)], offsets()
                assert resize((100.0, 100.0, 1297.0, 200.0)) == (100.0, 100.0, 1300.0, 200.0)
                assert len(offsets()) == 3, offsets()

                # A new session, even one begun over a session that never ended, ranks its first snapshot at the
                # stored rect again, and the next frame, 997 from it, retakes it at the corner.
                stub.setProperty("offsets", [])
                guides.beginResize("resized")
                resize((100.0, 100.0, 1297.0, 200.0))
                resize((100.0, 100.0, 1297.0, 200.0))
                assert offsets() == [(0.0, 0.0), (997.0, 0.0)], offsets()
                guides.endResize()
            finally:
                stage.deleteLater()
                app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_within_the_retake_interval_the_drop_gap_rule_does_not_retake(self) -> None:
        self._run_canvas_probe(
            "smart-guides-retake-interval-holds",
            _STUB_GUIDES_HARNESS
            + """
            try:
                # The default interval, 80 ms. With both drop gaps 0 every frame 40 or more from where the
                # snapshot was ranked is due; 10, 40 and 79 ms after the first snapshot none retakes.
                assert int(guides.property("retakeMinIntervalMs")) == 80
                stub.setProperty("dropGapX", 0.0)
                stub.setProperty("dropGapY", 0.0)
                assert drag_at([(1000, 0, 0), (1010, 50, 0), (1040, 100, 0), (1079, 150, 0)]) == [(0.0, 0.0)]

                # A frame held back resolves on the snapshot it kept: with drop gaps 150 the frame 997 right is
                # due, but only a snapshot ranked past x 600 holds the target, whose right edge (1300) is 3 away.
                stub.setProperty("dropGapX", 150.0)
                stub.setProperty("dropGapY", 150.0)
                stub.setProperty("offsets", [])
                guides.beginMove(["resized"])
                resolve_dx(1000, 0.0, 0.0)
                assert resolve_dx(1010, 997.0, 0.0) == 997.0
                assert offsets() == [(0.0, 0.0)], offsets()
                guides.endMove()
            finally:
                stage.deleteLater()
                app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_after_the_retake_interval_the_next_due_frame_retakes(self) -> None:
        self._run_canvas_probe(
            "smart-guides-retake-interval-passes",
            _STUB_GUIDES_HARNESS
            + """
            try:
                stub.setProperty("dropGapX", 0.0)
                stub.setProperty("dropGapY", 0.0)
                # A due frame 79 ms after the first snapshot waits, the one at 80 ms retakes, and the interval
                # runs again from that retake.
                assert drag_at([(1000, 0, 0), (1079, 50, 0), (1080, 100, 0), (1159, 200, 0), (1160, 250, 0)]) == [
                    (0.0, 0.0), (100.0, 0.0), (250.0, 0.0)
                ]
                # Time alone never retakes: long after the interval a frame short of the floor keeps the
                # snapshot, and the next frame, due, retakes it.
                assert drag_at([(1000, 0, 0), (5000, 39, 0), (5001, 40, 0)]) == [(0.0, 0.0), (40.0, 0.0)]
                # A clock that went back (a system time change) does not hold a due retake back.
                assert drag_at([(1000, 0, 0), (400, 50, 0)]) == [(0.0, 0.0), (50.0, 0.0)]

                # With drop gaps 150, the frame 997 right held back at 1010 misses the target; at 1080 the same
                # frame retakes, ranked there, and snaps to the target's right edge (1300).
                stub.setProperty("dropGapX", 150.0)
                stub.setProperty("dropGapY", 150.0)
                stub.setProperty("offsets", [])
                guides.beginMove(["resized"])
                resolve_dx(1000, 0.0, 0.0)
                assert resolve_dx(1010, 997.0, 0.0) == 997.0
                assert resolve_dx(1080, 997.0, 0.0) == 1000.0
                assert offsets() == [(0.0, 0.0), (997.0, 0.0)], offsets()
                guides.endMove()
            finally:
                stage.deleteLater()
                app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_the_first_snapshot_and_view_or_scene_changes_never_wait_for_the_retake_interval(self) -> None:
        self._run_canvas_probe(
            "smart-guides-retake-interval-exempt",
            _STUB_GUIDES_HARNESS
            + """
            try:
                stub.setProperty("dropGapX", 0.0)
                stub.setProperty("dropGapY", 0.0)
                # One session's snapshot at 1000 ms, then the next session's first 10 ms later.
                assert drag_at([(1000, 0, 0)]) == [(0.0, 0.0)]
                stub.setProperty("offsets", [])
                guides.beginMove(["resized"])
                resolve_dx(1010, 3.0, 0.0)
                # Every 10 ms after it, a scene change (invalidateSnapshot), a zoom change and a view-centre
                # change: the next frame rebuilds the snapshot at once each time.
                guides.invalidateSnapshot()
                resolve_dx(1020, 3.0, 0.0)
                view.setProperty("zoom_value", 0.5)
                resolve_dx(1030, 3.0, 0.0)
                view.setProperty("center_x", 10.0)
                resolve_dx(1040, 3.0, 0.0)
                assert offsets() == [(3.0, 0.0)] * 4, offsets()
                # The interval runs from the last of them. At zoom 0.5 the floor is 80 scene units: a due
                # frame at 1119 waits, and at 1120 it retakes.
                resolve_dx(1119, 103.0, 0.0)
                assert len(offsets()) == 4, offsets()
                resolve_dx(1120, 103.0, 0.0)
                assert offsets()[4:] == [(103.0, 0.0)], offsets()
                guides.endMove()
            finally:
                stage.deleteLater()
                app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_a_resize_follows_the_same_retake_interval(self) -> None:
        self._run_canvas_probe(
            "smart-guides-retake-interval-resize",
            _STUB_GUIDES_HARNESS
            + """
            try:
                # Bottom-right corner, drop gaps 150. The corner 997 right of the stored rect is due, but up to
                # 79 ms after the first snapshot the frames keep it and miss the target's right edge (1300);
                # at 80 ms the snapshot is retaken, ranked at the corner, and the edge snaps.
                guides.beginResize("resized")
                at(1000)
                assert resize((100.0, 100.0, 301.0, 200.0)) == (100.0, 100.0, 303.0, 200.0)
                at(1010)
                assert resize((100.0, 100.0, 1297.0, 200.0)) == (100.0, 100.0, 1297.0, 200.0)
                at(1079)
                assert resize((100.0, 100.0, 1297.0, 200.0)) == (100.0, 100.0, 1297.0, 200.0)
                assert offsets() == [(0.0, 0.0)], offsets()
                at(1080)
                assert resize((100.0, 100.0, 1297.0, 200.0)) == (100.0, 100.0, 1300.0, 200.0)
                assert offsets() == [(0.0, 0.0), (997.0, 0.0)], offsets()
                guides.endResize()
            finally:
                stage.deleteLater()
                app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_a_release_keeps_the_snapshot_whose_retake_the_interval_held_back(self) -> None:
        self._run_canvas_probe(
            "smart-guides-retake-interval-release",
            _STUB_GUIDES_HARNESS
            + """
            try:
                # Drop gaps 150. 10 ms after the first snapshot the frame 997 right is due but held back, so it
                # misses the target's right edge (1300). A release there 490 ms later, the pointer still, lands
                # where that frame showed the node: it keeps the snapshot rather than retake one with the target.
                guides.beginMove(["resized"])
                resolve_dx(1000, 0.0, 0.0)
                assert resolve_dx(1010, 997.0, 0.0) == 997.0
                assert resolve_dx(1500, 997.0, 0.0, commit=True) == 997.0
                assert offsets() == [(0.0, 0.0)], offsets()
                # A frame past the interval retakes it, ranked at 997, and shows the snap.
                assert resolve_dx(1600, 997.0, 0.0) == 1000.0
                # Nothing is held back on this snapshot, so a release past its drop gap follows the frames'
                # rule: within the interval it keeps the snapshot, after it the release retakes.
                resolve_dx(1610, 1400.0, 0.0, commit=True)
                assert offsets() == [(0.0, 0.0), (997.0, 0.0)], offsets()
                resolve_dx(1680, 1400.0, 0.0, commit=True)
                assert offsets() == [(0.0, 0.0), (997.0, 0.0), (1400.0, 0.0)], offsets()
                guides.endMove()

                # A retake held back on one snapshot is not held on the next: after a view-centre change
                # retakes it, a release past the drop gap retakes again once the interval has passed.
                stub.setProperty("offsets", [])
                guides.beginMove(["resized"])
                resolve_dx(3000, 0.0, 0.0)
                resolve_dx(3010, 997.0, 0.0)
                view.setProperty("center_x", 5.0)
                resolve_dx(3020, 997.0, 0.0)
                resolve_dx(3200, 1400.0, 0.0, commit=True)
                assert offsets() == [(0.0, 0.0), (997.0, 0.0), (1400.0, 0.0)], offsets()
                guides.endMove()
            finally:
                stage.deleteLater()
                app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_the_canvas_retakes_at_most_once_per_retake_interval_of_wall_clock(self) -> None:
        self._run_canvas_probe(
            "smart-guides-retake-interval-wall-clock",
            """
            import time

            scene, shell = new_scene()
            moving_id = scene.add_node_from_type(CONSTANT, 0.0, 0.0)
            # 135 fillers in the moving node's column: its column band holds more than the cap, so a trimmed
            # snapshot always leaves out a candidate overlapping the moving rect along x (drop gap x 0), and
            # at zoom 0.25 every frame 160 scene units (the 40 px floor) from where it was ranked is due.
            for k in range(135):
                scene.add_node_from_type(CONSTANT, 0.0, -1400.0 + 20.0 * k)
            scene.clear_selection()
            canvas, view, window = open_canvas(scene, shell)
            try:
                view.set_view_state(0.25, 0.0, 0.0)
                app.processEvents()
                card = card_for(canvas, moving_id)
                guides = smart_guides(canvas)
                bridge = canvas.property("canvasStateBridge")
                first = variant_value(bridge.smart_guide_snapshot([moving_id], {}, {"offset_x": 0.0, "offset_y": 2.0}))
                assert first["trimmed"] and first["dropGapX"] == 0.0, (first["trimmed"], first.get("dropGapX"))
                assert int(guides.property("retakeMinIntervalMs")) == 80

                def frames(start, count):
                    # Frames 200 scene units apart down the column; the snapshots taken so far.
                    for step in range(start, start + count):
                        live_drag(canvas, card, moving_id, 0.0, 2.0 + 200.0 * step)
                    return guide_counts(guides)[0]

                # A burst of 12 due frames retakes at most once per 80 ms of it after the first snapshot
                # (Date.now() may tick coarser than perf_counter, hence 32 ms of slack).
                started = time.perf_counter()
                snapshots = frames(0, 12)
                burst_ms = (time.perf_counter() - started) * 1000.0
                assert 1 <= snapshots <= 1 + (burst_ms + 32.0) / 80.0, (snapshots, burst_ms)
                # Well past the interval the next due frame retakes.
                QTest.qWait(150)
                assert frames(12, 1) == snapshots + 1, guide_counts(guides)
                # With no interval every due frame retakes.
                guides.setProperty("retakeMinIntervalMs", 0)
                assert frames(13, 3) == snapshots + 4, guide_counts(guides)
                card.dragCanceled.emit(moving_id)
                app.processEvents()
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_collapsed_group_drags_by_its_pill_bounds(self) -> None:
        self._run_canvas_probe(
            "smart-guides-collapsed-group",
            """
            scene, shell = new_scene()
            group_id = add_group(scene, -400.0, -300.0, 700.0, 500.0)
            member_id = scene.add_node_from_type(CONSTANT, -396.0, -100.0)
            assert payload_of(scene, member_id)["owner_backdrop_id"] == group_id
            assert scene.set_node_collapsed(group_id, True)
            # Below the expanded Group; its left edge is 4 px right of the collapsed pill's right edge (-270).
            candidate_id = scene.add_node_from_type(CONSTANT, -266.0, 250.0)
            scene.clear_selection()
            assert payload_of(scene, candidate_id)["owner_backdrop_id"] == ""
            pill = payload_of(scene, group_id)
            assert (pill["x"], pill["y"], pill["width"], pill["height"]) == (-400.0, -300.0, 130.0, 36.0), pill
            canvas, _view, window = open_canvas(scene, shell)
            try:
                group_card = card_for(canvas, group_id, "graphGroupBackdropInputCard")
                # The pill's right edge lands on the candidate's left edge; the expanded bounds (right
                # edge 300) would have nothing within reach.
                assert live_drag(canvas, group_card, group_id, 1.0, 0.0) == (4.0, 0.0)
                assert set(variant_value(canvas.property("liveDragNodeLookup"))) == {group_id, member_id}
                assert [(line["axis"], line["value"]) for line in guide_lines(smart_guides(canvas))] == [("x", -266.0)]
                group_card.dragFinished.emit(group_id, -399.0, -300.0, True, "", False)
                app.processEvents()
                assert position(scene, group_id) == (-396.0, -300.0)
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_top_left_resize_snaps_the_left_and_top_edges(self) -> None:
        self._run_canvas_probe(
            "smart-guides-top-left-resize",
            """
            scene, shell = new_scene()
            # A left edge at 60 and a top edge at 50, each 3 px past where the drag puts the corner.
            scene.add_node_from_type(PROCESS, 60.0, -300.0)
            scene.add_node_from_type(PROCESS, 600.0, 50.0)
            node_id = scene.add_node_from_type(PROCESS, 100.0, 100.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            try:
                card = card_for(canvas, node_id)
                guides = smart_guides(canvas)
                handle = corner_handle(card, "topLeft")
                hover_host_local_point(window, card, 60.0, 40.0)
                start = item_scene_point(handle, 0.25, 0.25)
                QTest.mouseMove(window, start)
                settle_events(3)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                end = QPoint(start.x() - 37, start.y() - 47)
                move_with(window, end)
                # The right and bottom edges stay at 324 and 184.
                assert_rect(card, (60.0, 50.0, 264.0, 134.0))
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", 60.0), ("y", 50.0)]
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
                settle_events(3)
                payload = payload_of(scene, node_id)
                assert (payload["x"], payload["y"], payload["width"], payload["height"]) == (60.0, 50.0, 264.0, 134.0), payload
                assert not bool(guides.property("active"))
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_resize_session_ends_when_its_node_goes_away_or_the_canvas_resets(self) -> None:
        self._run_canvas_probe(
            "smart-guides-resize-teardown",
            """
            scene, shell = new_scene()
            # Right edges at 327 and -73, 3 px past the resized nodes' right edges (324 and -76).
            scene.add_node_from_type(PROCESS, 103.0, -200.0)
            scene.add_node_from_type(PROCESS, -297.0, -200.0)
            node_id = scene.add_node_from_type(PROCESS, 100.0, 100.0)
            other_id = scene.add_node_from_type(PROCESS, -300.0, 200.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            try:
                guides = smart_guides(canvas)
                overlay = guide_overlay(canvas)

                def press_and_snap(card, guide_value):
                    # Grab the bottom-right grip and move 1 px: the right edge snaps 3 px out.
                    handle = corner_handle(card, "bottomRight")
                    hover_host_local_point(window, card, 60.0, 40.0)
                    start = item_scene_point(handle, 0.75, 0.75)
                    QTest.mouseMove(window, start)
                    settle_events(3)
                    QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                    settle_events(2)
                    moved = QPoint(start.x() + 1, start.y())
                    move_with(window, moved)
                    assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", guide_value)], (
                        guide_value, guide_lines(guides), host_rect(card)
                    )
                    assert bool(overlay.property("visible"))
                    return moved

                # The node is deleted mid-resize, so its handle goes away without a release.
                point = press_and_snap(card_for(canvas, node_id), 327.0)
                scene.remove_node(node_id)
                settle_events(5)
                assert not bool(guides.property("active"))
                assert guide_lines(guides) == []
                assert not bool(overlay.property("visible"))
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
                settle_events(3)
                assert not bool(guides.property("active"))

                # A canvas reset mid-resize ends the session too; the rest of that gesture stays unguided.
                point = press_and_snap(card_for(canvas, other_id), -73.0)
                canvas._resetCanvasSceneState()
                settle_events(2)
                assert not bool(guides.property("active"))
                assert guide_lines(guides) == []
                move_with(window, point)
                assert guide_lines(guides) == []
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
                settle_events(3)
                assert not bool(guides.property("active"))
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_scene_change_mid_resize_retakes_the_snapshot_and_keeps_the_session(self) -> None:
        self._run_canvas_probe(
            "smart-guides-resize-scene-change",
            """
            scene, shell = new_scene()
            # A right edge at 327, 3 px past the resized node's right edge (324).
            neighbour_id = scene.add_node_from_type(PROCESS, 103.0, -200.0)
            node_id = scene.add_node_from_type(PROCESS, 100.0, 100.0)
            scene.clear_selection()
            canvas, _view, window = open_canvas(scene, shell, with_window=True)
            try:
                card = card_for(canvas, node_id)
                guides = smart_guides(canvas)
                handle = corner_handle(card, "bottomRight")
                hover_host_local_point(window, card, 60.0, 40.0)
                start = item_scene_point(handle, 0.75, 0.75)
                QTest.mouseMove(window, start)
                settle_events(3)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                move_with(window, QPoint(start.x() + 1, start.y()))
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", 327.0)]
                snapshots = guide_counts(guides)[0]

                # The neighbour moves (an undo, say) while the handle is held: its right edge is now 334.
                # The session stays, and the guides drawn from the old snapshot go at once.
                scene.move_node(neighbour_id, 110.0, -200.0)
                settle_events(3)
                assert bool(guides.property("active"))
                assert guide_lines(guides) == []
                assert guide_counts(guides)[0] == snapshots

                # 332 is 5 from the old edge and 2 from the new one: only a new snapshot knows where it is.
                move_with(window, QPoint(start.x() + 8, start.y()))
                assert guide_counts(guides)[0] == snapshots + 1
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", 334.0)], guide_lines(guides)
                assert_rect(card, (100.0, 100.0, 234.0, 84.0))
                QTest.mouseRelease(
                    window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(start.x() + 8, start.y())
                )
                settle_events(3)
                payload = payload_of(scene, node_id)
                assert (payload["x"], payload["width"]) == (100.0, 234.0), payload
                assert not bool(guides.property("active"))
            finally:
                close_canvas(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_content_height_floor_drops_the_guide_it_pushes_an_edge_off(self) -> None:
        # A bare handle on a stand-in host: its surface is content-sized (narrower than 240 it needs 120
        # of height) and counts its measurements; the snapshot comes from a stub state bridge.
        self._run_canvas_probe(
            "smart-guides-content-height-floor",
            """
            harness_qml = '''
            import QtQuick 2.15
            import "../graph_canvas" as GraphCanvasComponents

            Item {
                id: stage
                width: 800
                height: 600

                QtObject {
                    id: stateBridge
                    objectName: "contentFloorStateBridge"
                    property bool guideLeft: false
                    function smart_guide_snapshot(nodeIds, sceneRect) {
                        return {
                            "moving": [],
                            "candidates": [
                                {"node_id": "column", "x": guideLeft ? 122.0 : 114.0, "y": -300.0, "width": 224.0, "height": 50.0},
                                {"node_id": "shelf", "x": 600.0, "y": 140.0, "width": 100.0, "height": 50.0}
                            ]
                        };
                    }
                }

                QtObject {
                    id: viewStub
                    property real zoom_value: 1.0
                    property real center_x: 0.0
                    property real center_y: 0.0
                }

                QtObject {
                    id: canvasStub
                    property var visibleSceneRectPayload: ({"x": -1000.0, "y": -1000.0, "width": 3000.0, "height": 3000.0})
                }

                GraphCanvasComponents.GraphCanvasSmartGuides {
                    id: guidesObject
                    canvasItem: canvasStub
                    canvasStateBridge: stateBridge
                    viewBridge: viewStub
                }

                Item {
                    id: fakeHost
                    objectName: "fakeResizeHost"
                    property var nodeData: ({"node_id": "resized", "x": 100.0, "y": 100.0})
                    property var smartGuides: guidesObject
                    property bool _liveGeometryActive: false
                    property real _liveX: 0.0
                    property real _liveY: 0.0
                    property real _liveWidth: 0.0
                    property real _liveHeight: 0.0
                    readonly property real _minNodeWidth: 60.0
                    readonly property real _minNodeHeight: 40.0
                    property var loadedSurfaceItem: QtObject {
                        objectName: "fakeContentSurface"
                        property int measureCount: 0
                        property bool aspectRatioLocked: false
                        function minimumNodeHeightForWidth(width) {
                            measureCount += 1;
                            return width < 240.0 ? 120.0 : 0.0;
                        }
                    }
                    readonly property real _resizeHandleSize: 16.0
                    readonly property real _resizeHandleHitSize: 20.0
                    readonly property bool _resizeHandlesVisible: true
                    readonly property bool surfaceInteractionLocked: false
                    readonly property bool isBareTextAnnotationSurface: false
                    readonly property color outlineColor: "#888888"
                    signal resizePreviewChanged(string nodeId, real newX, real newY, real newWidth, real newHeight, bool active)
                    signal resizeFinished(string nodeId, real newX, real newY, real newWidth, real newHeight)
                    function currentViewportZoom() { return 1.0; }
                    x: _liveGeometryActive ? _liveX : Number(nodeData.x)
                    y: _liveGeometryActive ? _liveY : Number(nodeData.y)
                    width: _liveGeometryActive ? _liveWidth : 260.0
                    height: _liveGeometryActive ? _liveHeight : 84.0

                    Repeater {
                        model: ["bottomRight", "topRight", "bottomLeft", "topLeft"]
                        GraphNodeResizeHandle {
                            host: fakeHost
                            cornerRole: modelData
                        }
                    }
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(
                harness_qml.encode("utf-8"),
                QUrl.fromLocalFile(str(components_dir / "graph" / "SmartGuideResizeHarness.qml")),
            )
            assert component.status() == QQmlComponent.Status.Ready, [error.toString() for error in component.errors()]
            stage = component.create()
            assert stage is not None
            window = attach_host_to_window(stage, 800, 600)
            try:
                host = stage.findChild(QObject, "fakeResizeHost")
                surface = stage.findChild(QObject, "fakeContentSurface")
                guides = stage.findChild(QObject, "graphCanvasSmartGuides")
                assert host is not None and surface is not None and guides is not None

                def live_rect():
                    return tuple(float(host.property(name)) for name in ("_liveX", "_liveY", "_liveWidth", "_liveHeight"))

                def measures():
                    return int(surface.property("measureCount"))

                handles = {str(item.property("cornerRole")): item
                           for item in named_child_items(stage, "graphNodeResizeHandle")}
                start = item_scene_point(handles["bottomRight"], 0.75, 0.75)
                QTest.mouseMove(window, start)
                settle_events(3)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
                settle_events(2)
                assert live_rect() == (100.0, 100.0, 260.0, 84.0), live_rect()

                # The right edge (341) snaps to 338 and the bottom edge (187) to 190, but 238 wide the
                # surface needs 120 of height: the floor pushes the bottom to 220, so only the x guide holds.
                before = measures()
                move_with(window, QPoint(start.x() - 19, start.y() + 3))
                assert live_rect() == (100.0, 100.0, 238.0, 120.0), live_rect()
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("x", 338.0)]
                assert measures() - before == 2

                # A guide that leaves the width alone keeps the one measurement and its y guide.
                before = measures()
                move_with(window, QPoint(start.x() + 3, start.y() + 3))
                assert live_rect() == (100.0, 100.0, 263.0, 90.0), live_rect()
                assert [(line["axis"], line["value"]) for line in guide_lines(guides)] == [("y", 190.0)]
                assert measures() - before == 1

                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                                   QPoint(start.x() + 3, start.y() + 3))
                settle_events(2)
                assert not bool(guides.property("active"))
                assert guide_lines(guides) == []

                # A guide that narrows a proportional resize across the same wrap boundary must be
                # rejected, not stretch only the height. Exercise every fixed opposite corner, both
                # Shift and a surface-owned lock, and the released geometry as well as the preview.
                finishes = []
                host.resizeFinished.connect(
                    lambda _id, x, y, width, height: finishes.append((x, y, width, height))
                )
                for lock_kind in ("shift", "surface"):
                    surface.setProperty("aspectRatioLocked", lock_kind == "surface")
                    modifiers = (Qt.KeyboardModifier.ShiftModifier if lock_kind == "shift"
                                 else Qt.KeyboardModifier.NoModifier)
                    for corner in ("bottomRight", "topRight", "bottomLeft", "topLeft"):
                        moving_left = corner.endswith("Left")
                        moving_top = corner.startswith("top")
                        handle = handles[corner]
                        # The candidate's edge is 3 units beyond the raw moving edge: either right
                        # 338 or left 122, both leaving 238 width, below the 240 wrap threshold.
                        state = stage.findChild(QObject, "contentFloorStateBridge")
                        state.setProperty("guideLeft", moving_left)
                        QTest.qWait(int(app.styleHints().mouseDoubleClickInterval()) + 20)
                        start = item_scene_point(handle, 0.25 if moving_left else 0.75,
                                                 0.25 if moving_top else 0.75)
                        QTest.mouseMove(window, start)
                        settle_events(2)
                        QTest.mousePress(window, Qt.MouseButton.LeftButton, modifiers, start)
                        settle_events(2)
                        assert bool(handle.property("dragActive")), (lock_kind, corner)
                        end = QPoint(start.x() + (19 if moving_left else -19), start.y())
                        move_with(window, end, modifiers)
                        height = 241.0 * 84.0 / 260.0
                        expected = (119.0 if moving_left else 100.0,
                                    184.0 - height if moving_top else 100.0, 241.0, height)
                        actual = live_rect()
                        assert all(abs(a - b) < 0.01 for a, b in zip(actual, expected)), (lock_kind, corner, actual)
                        assert guide_lines(guides) == [], (lock_kind, corner, guide_lines(guides))
                        count = len(finishes)
                        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, modifiers, end)
                        settle_events(2)
                        assert len(finishes) == count + 1, (lock_kind, corner, finishes)
                        assert all(abs(a - b) < 0.01 for a, b in zip(finishes[-1], expected)), finishes[-1]
                        assert not bool(guides.property("active"))
            finally:
                dispose_host_window(stage, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_host_alt_drag_marks_offsets_and_release_as_snap_bypass(self) -> None:
        self._run_qml_probe(
            "alt-drag-snap-bypass",
            """
            from PyQt6.QtCore import QCoreApplication
            from PyQt6.QtGui import QMouseEvent

            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            gesture_layer = host.findChild(QObject, "graphNodeHostGestureLayer")
            assert gesture_layer is not None
            offsets = []
            finishes = []
            host.dragOffsetChanged.connect(
                lambda node_id, dx, dy, axis_lock, snap_bypass: offsets.append(
                    (float(dx), float(dy), str(axis_lock), bool(snap_bypass))
                )
            )
            host.dragFinished.connect(
                lambda node_id, final_x, final_y, moved, axis_lock, snap_bypass: finishes.append(
                    (float(final_x), float(final_y), bool(moved), str(axis_lock), bool(snap_bypass))
                )
            )
            window = attach_host_to_window(host)
            alt = Qt.KeyboardModifier.AltModifier
            shift = Qt.KeyboardModifier.ShiftModifier
            plain = Qt.KeyboardModifier.NoModifier

            def move_with(point, modifiers):
                # QTest.mouseMove always sends NoModifier in Qt 6.
                event = QMouseEvent(
                    QEvent.Type.MouseMove,
                    QPointF(point),
                    QPointF(window.mapToGlobal(point)),
                    Qt.MouseButton.NoButton,
                    Qt.MouseButton.LeftButton,
                    modifiers,
                )
                QCoreApplication.sendEvent(window, event)
                settle_events(2)

            def drag(steps, release_modifiers):
                offsets.clear()
                finishes.clear()
                start = host_scene_point(host, 40.0, 44.0)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, plain, start)
                settle_events(2)
                for (dx, dy), modifiers in steps:
                    move_with(QPoint(start.x() + dx, start.y() + dy), modifiers)
                last = steps[-1][0]
                QTest.mouseRelease(
                    window, Qt.MouseButton.LeftButton, release_modifiers, QPoint(start.x() + last[0], start.y() + last[1])
                )
                settle_events(2)

            # Alt is read on every move: pressing it mid-drag bypasses from that event on. (The release
            # re-emits its offset, and QTest may add a move of its own, so only the order is pinned.)
            drag((((20, 10), plain), ((30, 12), alt)), alt)
            assert len(offsets) >= 3 and offsets[0][3] is False, offsets
            assert all(entry[3] for entry in offsets[1:]), offsets
            assert finishes == [(150.0, 132.0, True, "", True)], finishes
            assert not bool(gesture_layer.property("dragSnapBypass"))

            # Releasing Alt before the button restores snapping for the release.
            drag((((20, 10), alt), ((30, 12), plain)), plain)
            assert len(offsets) >= 3 and offsets[0][3] is True, offsets
            assert not any(entry[3] for entry in offsets[1:]), offsets
            assert finishes == [(150.0, 132.0, True, "", False)], finishes

            # Shift and Alt combine: axis lock plus bypass.
            drag((((30, 8), shift | alt),), shift | alt)
            assert offsets[-1] == (30.0, 0.0, "horizontal", True), offsets
            assert finishes == [(150.0, 120.0, True, "horizontal", True)], finishes

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )


if __name__ == "__main__":
    unittest.main()
