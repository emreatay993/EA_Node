# Purpose: Deterministic production-node fixture and control-render measurement support.
# Map: feature_routes/performance_harness_graph_stress
# Tests: tests/test_node_visual_quality_tooling.py
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable

WORKSPACE_ID = "ws_visual_quality"
TARGET_IDS = {
    "slider": "vq_slider",
    "switch": "vq_switch",
    "switch_off": "vq_switch_off",
    "collapsed": "vq_collapsed",
    "general": "vq_general",
    "signal": "vq_signal",
    "resize": "vq_panel",
}


def capture_viewport_size(available_width: int, available_height: int) -> tuple[int, int]:
    """Fit a 16:9 capture inside available logical screen space before creating Qt roots."""
    width_budget = available_width - 64
    height_budget = available_height - 64
    if width_budget < 320 or height_budget < 180:
        raise ValueError("Available screen space is too small for capture with safe frame margins")
    scale = min(1.0, width_budget / 1280, height_budget / 720)
    return int(1280 * scale), int(720 * scale)


def is_graphics_device_failure(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in (
        "device loss", "device lost", "device removed", "device hung",
        "failed to create readback", "0x887a0005", "0x887a0006", "0x887a0007",
    ))


def validate_capture_frame(frame: Any, diagnostics: list[str]) -> dict[str, Any]:
    """Analyze pixels and graphics diagnostics without modifying the captured artifact."""
    from PyQt6.QtGui import QImage

    failures = [message for message in diagnostics if is_graphics_device_failure(message)]
    if failures:
        raise RuntimeError(f"Graphics device failure invalidates capture: {failures[0]}")
    if frame.isNull() or frame.width() < 1 or frame.height() < 1:
        raise RuntimeError("Empty capture frame is not visual evidence")
    analysis_image = frame.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = analysis_image.constBits().asstring(analysis_image.sizeInBytes())
    if pixels == pixels[:4] * (len(pixels) // 4):
        raise RuntimeError(f"Uniform capture frame {tuple(pixels[:4])} is not visual evidence")
    if not any(pixels[3::4]):
        raise RuntimeError("Fully transparent capture frame is not visual evidence")
    return {"nonuniform_pixels": True, "nonempty_alpha": True,
            "pixel_count": frame.width() * frame.height(), "graphics_device_failures": 0}


def build_visual_quality_project(*, node_count: int = 9):
    """Use built-in production specs, stable IDs, and no runtime/plugin fixtures."""
    from ea_node_editor.graph.project_state import ProjectData
    from ea_node_editor.graph.records import EdgeInstance, NodeInstance
    from ea_node_editor.graph.workspace_state import ViewState, WorkspaceData

    project = ProjectData(project_id="proj_visual_quality", name="Visual quality")
    workspace = WorkspaceData(workspace_id=WORKSPACE_ID, name="Visual quality")
    workspace.views["view_visual_quality"] = ViewState(
        view_id="view_visual_quality", name="V1", zoom=1.0, pan_x=0.0, pan_y=0.0
    )
    workspace.active_view_id = "view_visual_quality"
    nodes = [
        NodeInstance("vq_backdrop", "passive.annotation.group_backdrop", "Contrast backdrop",
                     -35, -35, custom_width=1300, custom_height=1380,
                     visual_style={"fill_color": "#455F8F"}),
        NodeInstance("vq_slider", "data.number_slider", "Number Slider", 25, 35,
                     properties={"value": 5.0}, custom_width=410),
        NodeInstance("vq_switch", "data.boolean_toggle", "Boolean Toggle", 470, 35,
                     properties={"value": True}),
        NodeInstance("vq_switch_off", "data.boolean_toggle", "Boolean Toggle", 780, 35,
                     properties={"value": False}),
        NodeInstance("vq_collapsed", "plot.signal", "Signal Plot", 25, 160,
                     custom_width=310),
        NodeInstance("vq_general", "plot.signal", "General options", 420, 160,
                     expanded_settings_group_ids=("general_options",), custom_width=370),
        NodeInstance("vq_signal", "plot.signal", "Signal plot options", 855, 160,
                     expanded_settings_group_ids=("signal_plot_options",), custom_width=370),
        NodeInstance("vq_connected", "plot.signal", "Connected input", 25, 475,
                     expanded_settings_group_ids=("general_options",), custom_width=310),
        NodeInstance("vq_panel", "passive.annotation.sticky_note", "Resizable card", 25, 1080,
                     custom_width=310, custom_height=180),
    ]
    for index in range(max(0, node_count - len(nodes))):
        nodes.append(NodeInstance(
            f"vq_extra_{index:04d}", "plot.signal", f"Expanded controls {index + 1}",
            (index % 12) * 430, 1550 + (index // 12) * 700,
            expanded_settings_group_ids=("general_options",), custom_width=370,
        ))
    workspace.nodes = {node.node_id: node for node in nodes}
    workspace.edges["vq_edge_values"] = EdgeInstance(
        "vq_edge_values", "vq_slider", "value", "vq_connected", "values"
    )
    workspace.edges["vq_edge_legend"] = EdgeInstance(
        "vq_edge_legend", "vq_switch_off", "boolean", "vq_connected", "show_legend"
    )
    project.workspaces[WORKSPACE_ID] = workspace
    project.active_workspace_id = WORKSPACE_ID
    project.metadata["workspace_order"] = [WORKSPACE_ID]
    return project


def source_runtime_metadata() -> dict[str, Any]:
    from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, qVersion
    import ea_node_editor

    root = Path(__file__).resolve().parents[3]
    def git(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    changed = git("diff", "--name-only", "HEAD").splitlines()
    return {
        "source_root": str(root), "import_root": str(Path(ea_node_editor.__file__).resolve()),
        "cwd": str(Path.cwd()), "source_head": git("rev-parse", "HEAD"),
        "tracked_dirty_sha256": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in changed if (root / name).is_file()
        },
        "untracked_source_sha256": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in git("ls-files", "--others", "--exclude-standard").splitlines()
            if name.endswith((".py", ".qml", ".js")) and (root / name).is_file()
        },
        "python_executable": sys.executable, "python_version": sys.version,
        "pyqt_version": PYQT_VERSION_STR, "qt_build_version": QT_VERSION_STR,
        "qt_runtime_version": qVersion(),
        "qt_quick_controls_style_requested": os.environ.get("QT_QUICK_CONTROLS_STYLE", ""),
        "qt_scale_factor": os.environ.get("QT_SCALE_FACTOR", ""),
    }


def wait_for_changed_render(
    host: Any, *, changed: Callable[[], bool], started: float, timeout_ms: int = 3000,
    observer: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Require state change, then a strictly later rendered frame; never grab pixels."""
    observed_frame: int | None = None
    deadline = time.perf_counter() + timeout_ms / 1000.0
    while time.perf_counter() < deadline:
        host.app.processEvents()
        if observer is not None:
            observer()
        if changed():
            current = host.frame_render_timestamp_index()
            if observed_frame is None:
                observed_frame = current
                host.window.update()
                if host.widget is not None:
                    host.widget.update()
            elif current > observed_frame:
                completion = host._frame_render_timestamps[current - 1]
                return {"elapsed_ms": (completion - started) * 1000.0,
                        "state_observed_frame": observed_frame, "completion_frame": current}
        else:
            observed_frame = None
        time.sleep(0.001)
    raise RuntimeError("Control state did not change and reach a later afterRendering frame")


class SettingsAnimationEvidence:
    """Observe production animation state independently of assumed wall-clock duration."""
    def __init__(self, started: float):
        self.started = started
        self.running_at: float | None = None
        self.completed_at: float | None = None
        self.samples: list[dict[str, Any]] = []

    def observe(self, *, running: bool, remaining: float, width: float, height: float,
                timestamp: float, frame_index: int) -> None:
        if not math.isfinite(remaining):
            raise RuntimeError("Settings animation has non-finite progress")
        if running and self.completed_at is None:
            if self.running_at is None:
                self.running_at = timestamp
            sample = {"elapsed_ms": (timestamp-self.started)*1000, "remaining": remaining,
                      "width": width, "height": height, "frame_index": frame_index}
            if not self.samples or any(sample[key] != self.samples[-1][key]
                                       for key in ("remaining", "width", "height", "frame_index")):
                self.samples.append(sample)
        elif not running and self.running_at is not None and self.completed_at is None:
            if abs(remaining) > 1e-6:
                raise RuntimeError("Settings animation stopped before reaching its final progress")
            self.completed_at = timestamp

    def result(self, frame_timestamps: list[float]) -> dict[str, Any]:
        if self.running_at is None:
            raise RuntimeError("Settings animation was absent or disabled; not acceptance evidence")
        if self.completed_at is None:
            raise RuntimeError("Settings animation did not complete; not acceptance evidence")
        if len({item["remaining"] for item in self.samples}) < 2:
            raise RuntimeError("Settings animation progress was not observed; not acceptance evidence")
        if len({(item["width"], item["height"]) for item in self.samples}) < 2:
            raise RuntimeError("Settings animation geometry did not progress; not acceptance evidence")
        active_frames = [stamp for stamp in frame_timestamps
                         if self.running_at <= stamp <= self.completed_at]
        if len(active_frames) < 2:
            raise RuntimeError("Settings animation has fewer than two active rendered frames; not acceptance evidence")
        return {
            "observed_running": True, "observed_completion": True,
            "completion_duration_ms": (self.completed_at-self.started)*1000,
            "active_duration_ms": (self.completed_at-self.running_at)*1000,
            "raw_frame_count": len(frame_timestamps), "active_frame_count": len(active_frames),
            "progress_samples": self.samples,
            "frame_intervals_ms": [(right-left)*1000 for left, right in zip(active_frames, active_frames[1:])],
        }


class SettingsAnimationMonitor:
    """Retain transitions emitted inside a single GUI event-drain call."""
    def __init__(self, card: Any, host: Any):
        self.card = card
        self.host = host
        self.evidence: SettingsAnimationEvidence | None = None
        self.error: Exception | None = None
        self.signals = (
            card.settingsGroupAnimationRunningChanged,
            card._settingsGroupAnimationRemainingChanged,
        )
        for signal in self.signals:
            signal.connect(self.observe)

    def start(self, started: float) -> SettingsAnimationEvidence:
        self.evidence = SettingsAnimationEvidence(started)
        return self.evidence

    def observe(self) -> None:
        if self.evidence is None:
            return
        try:
            self.evidence.observe(
                running=bool(self.card.property("settingsGroupAnimationRunning")),
                remaining=float(self.card.property("_settingsGroupAnimationRemaining")),
                width=float(self.card.width()), height=float(self.card.height()),
                timestamp=time.perf_counter(), frame_index=self.host.frame_render_timestamp_index(),
            )
        except Exception as error:
            # Exceptions must leave through the measurement loop, not a Qt signal callback.
            self.error = error

    def poll(self) -> None:
        self.observe()
        if self.error is not None:
            raise RuntimeError(f"Settings animation observation failed: {self.error}") from self.error

    def close(self) -> None:
        for signal in self.signals:
            signal.disconnect(self.observe)


def validate_control_renderer(renderer: dict[str, Any]) -> None:
    if (renderer.get("qt_qpa_platform") != "windows"
            or renderer.get("graphics_api") != "Direct3D11Rhi"
            or renderer.get("software_fallback_active", False)):
        raise RuntimeError("Control timing requires display-attached Windows/Direct3D 11; not acceptance evidence")


def benchmark_control_interactions(*, app, doc, workspace_id, samples=40, warmup_samples=3):
    """Opt-in pointer interactions on the canonical GraphCanvas benchmark host."""
    if samples < 1 or warmup_samples < 0:
        raise ValueError("Control measurements require positive samples and nonnegative warmups")
    from PyQt6.QtCore import QPoint, QPointF, Qt
    from PyQt6.QtTest import QTest
    import psutil
    from .performance_harness import (
        _GraphCanvasBenchmarkHost, _iter_quick_item_tree, _metric_summary_ms,
    )

    reports = {}
    with _GraphCanvasBenchmarkHost(app=app, doc=doc, workspace_id=workspace_id) as host:
        if host.widget is None:
            raise ValueError("Control interaction evidence requires the production QQuickWidget host")
        validate_control_renderer(host.renderer_diagnostics())
        host.widget.raise_()
        host.widget.activateWindow()
        workspace = host.model.project.workspaces[workspace_id]
        missing = set(TARGET_IDS.values()).difference(workspace.nodes)
        if missing:
            raise ValueError(f"--control-interactions requires the visual-quality fixture: {sorted(missing)}")

        def settle(milliseconds=220):
            deadline = time.perf_counter() + milliseconds / 1000
            while time.perf_counter() < deadline:
                app.processEvents()
                time.sleep(0.001)

        def card(node_id):
            return next(item for item in host.node_cards()
                        if (item.property("nodeData") or {}).get("node_id") == node_id)

        def find(node_id, name, **properties):
            return next(item for item in _iter_quick_item_tree(card(node_id))
                        if item.objectName() == name
                        and all(item.property(key) == value for key, value in properties.items()))

        def point(item, x=None, y=None):
            mapped = item.mapToScene(QPointF(item.width()/2 if x is None else x,
                                            item.height()/2 if y is None else y))
            result = mapped.toPoint()
            if not host.widget.rect().contains(result):
                raise RuntimeError(f"Control target outside viewport: {item.objectName()} {result}")
            return result

        def frame_item(node_id, item):
            local = item.mapToItem(card(node_id), QPointF(item.width()/2, item.height()/2))
            node = workspace.nodes[node_id]
            host.view.centerOn(node.x + local.x(), node.y + local.y())
            settle(40)
            host.render_frame()  # untimed setup only

        def drag(start, end):
            QTest.mousePress(host.widget, Qt.MouseButton.LeftButton, pos=start, delay=0)
            app.processEvents()
            QTest.mouseMove(host.widget, end, delay=1)
            app.processEvents()
            QTest.mouseRelease(host.widget, Qt.MouseButton.LeftButton, pos=end, delay=0)

        for zoom in (1.0, 2.0, 5.0):
            host.view.set_zoom(zoom)
            for operation in ("slider_drag", "switch_click", "settings_expand", "settings_collapse", "geometry_resize"):
                node_id = TARGET_IDS["slider" if operation == "slider_drag" else
                                     "switch" if operation == "switch_click" else
                                     "resize" if operation == "geometry_resize" else "collapsed"]
                node = workspace.nodes[node_id]
                host.view.centerOn(node.x + 120, node.y + 80)
                settle(60)
                host._force_visible_node_cards_current()
                sample_records = []
                for iteration in range(warmup_samples + samples):
                    if operation == "slider_drag":
                        control = find(node_id, "graphNumberSliderControl")
                        frame_item(node_id, control)
                        before = float(control.property("value"))
                        handle = control.property("handle")
                        start = point(handle)
                        target_x = control.width() * (0.75 if before < 5 else 0.25)
                        end = point(control, target_x, float(control.property("topPadding")) + float(control.property("availableHeight"))/2)
                        changed = lambda: abs(float(workspace.nodes[node_id].properties["value"]) - before) > 0.01
                        dispatch = lambda: drag(start, end)
                    elif operation == "switch_click":
                        control = find(node_id, "graphBooleanToggleControl")
                        frame_item(node_id, control)
                        before = bool(workspace.nodes[node_id].properties["value"])
                        click = point(control, 15, control.height()/2)
                        changed = lambda: bool(workspace.nodes[node_id].properties["value"]) != before
                        dispatch = lambda: QTest.mouseClick(host.widget, Qt.MouseButton.LeftButton, pos=click, delay=0)
                    elif operation.startswith("settings_"):
                        expanded = operation == "settings_expand"
                        host.scene.set_node_settings_group_expanded(node_id, "general_options", not expanded)
                        settle()
                        header = find(node_id, "graphNodeSettingsGroupHeader", groupId="general_options")
                        frame_item(node_id, header)
                        click = point(header)
                        changed = lambda: ("general_options" in workspace.nodes[node_id].expanded_settings_group_ids) == expanded
                        dispatch = lambda: QTest.mouseClick(host.widget, Qt.MouseButton.LeftButton, pos=click, delay=0)
                    else:
                        control = find(node_id, "graphNodeResizeHandle", cornerRole="topRight")
                        frame_item(node_id, control)
                        resize_card = card(node_id)
                        before = float(resize_card.width())
                        # Stay inside the rounded corner as well as its triangular hit area.
                        start = point(control, control.width()-3, 3)
                        QTest.mouseMove(host.widget, point(card(node_id), card(node_id).width()-30, 25), delay=0)
                        settle(25)
                        QTest.mouseMove(host.widget, start, delay=0)
                        settle(25)
                        end = start + QPoint(round((11.5 if iteration % 2 == 0 else -11.5) * zoom), 0)
                        changed = lambda: abs(float(resize_card.width()) - before) > 1
                        dispatch = lambda: drag(start, end)
                    animated_card = None
                    if operation.startswith("settings_"):
                        animated_card = card(node_id)
                        if not bool(animated_card.property("settingsGroupAnimationsEnabled")):
                            raise RuntimeError("Settings animation is disabled; not acceptance evidence")
                    monitor = SettingsAnimationMonitor(animated_card, host) if animated_card is not None else None
                    started = time.perf_counter()
                    frame_start = host.frame_render_timestamp_index()
                    animation = None
                    observe_animation = None
                    if monitor is not None:
                        animation = monitor.start(started)
                        observe_animation = monitor.poll
                    try:
                        dispatch()
                        if observe_animation is not None:
                            observe_animation()
                        result = wait_for_changed_render(host, changed=changed, started=started,
                                                        observer=observe_animation)
                        if animation is not None:
                            try:
                                completed_render = wait_for_changed_render(
                                    host, changed=lambda: animation.completed_at is not None,
                                    started=started, observer=observe_animation,
                                )
                            except RuntimeError:
                                animation.result(host._frame_render_timestamps[frame_start:])
                                raise
                            result["animation"] = animation.result(host._frame_render_timestamps[frame_start:])
                            result["animation"]["completion_render_ms"] = completed_render["elapsed_ms"]
                            result["animation"]["completion_render_frame"] = completed_render["completion_frame"]
                    except RuntimeError as error:
                        raise RuntimeError(f"{operation} at {zoom=}, {iteration=}: {error}; "
                                           f"changed={changed()}, node={workspace.nodes[node_id]}, "
                                           f"frames={host.frame_render_timestamp_index()}") from error
                    finally:
                        if monitor is not None:
                            monitor.close()
                    result["iteration"] = iteration - warmup_samples
                    if animation is None:
                        settle()  # switch/hover transitions are outside the first-render measurement
                    if iteration >= warmup_samples:
                        sample_records.append(result)
                timings = [item["elapsed_ms"] for item in sample_records]
                reports[f"{operation}.zoom{round(100*zoom)}"] = {
                    "samples": timings, "summary": _metric_summary_ms(timings), "evidence": sample_records,
                }
                if operation.startswith("settings_"):
                    intervals = [value for item in sample_records for value in item["animation"]["frame_intervals_ms"]]
                    reports[f"{operation}.zoom{round(100*zoom)}"]["animation_frame_intervals_ms"] = {
                        "samples": intervals, "summary": _metric_summary_ms(intervals),
                    }
                    completion = [item["animation"]["completion_render_ms"] for item in sample_records]
                    reports[f"{operation}.zoom{round(100*zoom)}"]["animation_completion_ms"] = {
                        "samples": completion, "summary": _metric_summary_ms(completion),
                    }
        settle(300)
        before_frames = host.frame_render_timestamp_index()
        before_profile = host.collect_targeted_profiling_snapshot()
        process = psutil.Process()
        before_cpu = sum(process.cpu_times()[:2])
        before_rss = process.memory_info().rss
        idle_started = time.perf_counter()
        settle(1000)
        idle = {"wall_seconds": time.perf_counter()-idle_started,
                "cpu_seconds": sum(process.cpu_times()[:2])-before_cpu,
                "rss_before": before_rss, "rss_after": process.memory_info().rss,
                "rendered_frames": host.frame_render_timestamp_index()-before_frames,
                "profile_before": before_profile, "profile_after": host.collect_targeted_profiling_snapshot()}
        renderer = {**host.renderer_diagnostics(), "grab_window_readback_included": False}
    return {"kind": "production_canvas_pointer_controls", "metrics": reports, "idle": idle,
            "renderer": renderer, "sample_budget": samples, "warmups_per_metric": warmup_samples,
            "measurement_contract": {"state_change_required": True, "later_afterRendering_required": True,
                "grab_window_readback_included": False,
                "animation_sampling": "afterRendering intervals strictly inside observed settingsGroupAnimationRunning; geometry/progress and completion are required",
                "completion": "committed control state or resize geometry observed, then a strictly later afterRendering callback",
                "limitation": "Qt render completion, not physical monitor presentation; settings animation completion is a separate timing metric"}}
