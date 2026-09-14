# Purpose: Measure cold and warm execution, GUI edit return and accepted-image frames.
# Map: feature_routes/run_controller_selected_workspace_state.md
# Tests: tests/test_signal_plot_scientific_integration.py, tests/test_shell_run_controller.py
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import statistics
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def percentiles(values):
    values = sorted(values)
    return (
        {
            "count": len(values),
            "p50": statistics.median(values),
            "p95": values[min(len(values) - 1, math.ceil(len(values) * 0.95) - 1)],
            "max": max(values),
        }
        if values
        else {}
    )


def fixture(registry, folder, kind, unrelated):
    from ea_node_editor.graph.model import GraphModel

    model = GraphModel()
    mutations = model.validated_mutations(model.active_workspace.workspace_id, registry)
    if kind == "plot":
        path = folder / "source.csv"
        path.write_text(
            "sample,sine\n" + "".join(f"{i},{math.sin(i)}\n" for i in range(1, 20)),
            encoding="utf-8",
        )
        source = mutations.add_node(
            type_id="tabular.input",
            title="Source",
            x=0,
            y=0,
            properties={"path": str(path), "cache_policy": "source_direct"},
        )
        edited = mutations.add_node(
            type_id="plot.signal",
            title="Plot",
            x=400,
            y=0,
            properties={"marker_shapes": [1], "marker_sizes": [20]},
        )
        output = mutations.add_node(type_id="media.panel", title="Output", x=780, y=0)
        mutations.add_edge(
            source_node_id=source.node_id,
            source_port_key="table_data",
            target_node_id=edited.node_id,
            target_port_key="values",
        )
        mutations.add_edge(
            source_node_id=edited.node_id,
            source_port_key="image",
            target_node_id=output.node_id,
            target_port_key="source",
        )
        output_key = "_surface_source"
    else:
        source = edited = mutations.add_node(
            type_id="data.number_slider",
            title="Source",
            x=0,
            y=0,
            properties={"value": 1.0},
        )
        middle = mutations.add_node(type_id="data.panel", title="Display", x=400, y=0)
        output = mutations.add_node(type_id="data.panel", title="Output", x=780, y=0)
        mutations.add_edge(
            source_node_id=source.node_id,
            source_port_key="value",
            target_node_id=middle.node_id,
            target_port_key="input",
        )
        mutations.add_edge(
            source_node_id=middle.node_id,
            source_port_key="output",
            target_node_id=output.node_id,
            target_port_key="input",
        )
        output_key = "output"
    for index in range(unrelated):
        mutations.add_node(
            type_id="data.number_slider",
            title=f"Unrelated {index}",
            x=1500,
            y=index * 150,
        )
    return model, edited.node_id, output.node_id, output_key


def change(kind, index):
    return (
        (
            {"marker_sizes": [21 + index % 30]}
            if index % 2 == 0
            else {"x_axis_label": f"Sample {index}"}
        )
        if kind == "plot"
        else {"value": float(index % 8 + 2)}
    )


def verify(value, kind, changes):
    if kind == "plot":
        from ea_node_editor.runtime_contracts import PlotValue

        assert isinstance(value, PlotValue)
        assert all(signal.y.shape == (19,) for signal in value.signals)
        for key, expected in changes.items():
            actual = getattr(value.settings, key)
            assert actual == (
                tuple(expected) if isinstance(expected, list) else expected
            ), (key, actual, expected)
        return value.preview.sha256
    assert float(value) == changes.get("value", 1.0), (value, changes)
    return str(value)


def output_digest(value, kind):
    if value is None:
        return ""
    return value.preview.sha256 if kind == "plot" else str(value)


def backend_identity(runtime):
    client = runtime._client._process_client
    process = client._process
    return {
        "backend_id": "process_isolated",
        "worker_pid": process.pid if process is not None else None,
        "runtime_generation": client._physical_generation_token,
        "registry_contract_fingerprint": runtime._registry.contract_fingerprint(),
    }


def runtime_probe(args, registry, model, edited, output, output_key):
    from ea_node_editor.execution.runtime import CorexRuntime
    from ea_node_editor.execution.runtime_requests import ExecutionRequest
    from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
    from scripts.benchmark_signal_plot import settled_item, wait_for_runtime_idle

    runtime = CorexRuntime(registry=registry)
    records = []
    wid = model.active_workspace.workspace_id
    readiness_ms = None
    try:
        if args.warmup_worker:
            started = time.perf_counter()
            assert runtime.warm_up_builtin_generation().result(60).available
            readiness_ms = (time.perf_counter() - started) * 1000
        for index in range(-1, args.warmups + args.edits):
            changes = {} if index < 0 else change(args.graph, index)
            start = time.perf_counter()
            if changes:
                model.validated_mutations(wid, registry).set_node_properties(
                    edited, changes
                )
            snapshot = build_runtime_snapshot(
                model.project, workspace_id=wid, registry=registry
            )
            captured = time.perf_counter()
            if changes:
                runtime.invalidate_solution(
                    snapshot.project_id, wid, snapshot, (edited,), "property_changed"
                )
            invalidated = time.perf_counter()
            result = runtime.run(
                ExecutionRequest(
                    workspace_id=wid,
                    runtime_snapshot=snapshot,
                    target_node_ids=(edited, output) if changes else (),
                ),
                timeout=60,
            )
            finished = time.perf_counter()
            assert result.status == "completed", (result.error, result.traceback)
            settlements = {
                event["node_id"]: event
                for event in result.events
                if event.get("type") == "node_settled"
            }
            digest = verify(
                settled_item(settlements[output], output_key, registry.data_types),
                args.graph,
                changes,
            )
            records.append(
                {
                    "iteration": index,
                    "cold": index < 0,
                    "measured": index >= args.warmups,
                    "capture_ms": (captured - start) * 1000,
                    "invalidate_ms": (invalidated - captured) * 1000,
                    "total_ms": (finished - start) * 1000,
                    "output_digest": digest,
                    "nodes": [
                        {
                            key: event.get(key)
                            for key in (
                                "node_id",
                                "elapsed_ms",
                                "disposition",
                                "decision_reason",
                            )
                        }
                        for event in settlements.values()
                    ],
                }
            )
            wait_for_runtime_idle(runtime)
        identity = backend_identity(runtime)
    finally:
        runtime.shutdown()
    return {
        "records": records,
        "backend_identity": identity,
        "readiness_ms": readiness_ms,
    }


def shell_probe(args, registry, model, edited, output, output_key, launched):
    print("Creating native shell", flush=True)
    from ea_node_editor.app import (
        prepare_qt_application_attributes,
        _register_bundled_application_fonts,
    )

    prepare_qt_application_attributes()
    from PyQt6.QtCore import QTimer, QEventLoop, QThread, Qt
    from PyQt6.QtWidgets import QApplication
    from ea_node_editor.app_preferences import default_app_preferences_document
    from ea_node_editor.persistence.serializer import JsonProjectSerializer
    from ea_node_editor.ui.shell.composition import create_shell_window
    from ea_node_editor.ui.support.solution_output_cache import current_output_value

    app = QApplication(["execution-responsiveness-probe"])
    _register_bundled_application_fonts()
    preferences = default_app_preferences_document()
    preferences["solution"] = {"default_mode": "manual"}
    window = create_shell_window(registry=registry, preferences_document=preferences)
    startup_warmup = getattr(window, "startup_worker_warmup", None)
    if startup_warmup is not None:
        startup_warmup.enabled = False
    window.resize(1500, 900)
    frames = []
    content_frames = []
    content_reader = [lambda: ""]
    frame_content = [""]
    observer_errors = []

    def synchronize_frame_content():
        # The reference QQuickWidget uses the GUI thread for render control.
        # Read the presentation immediately before its scene is synchronized,
        # then retain only a plain string for the render-completion callback.
        if QThread.currentThread() != app.thread():
            observer_errors.append("The content probe requires the QQuickWidget GUI render loop")
            return
        frame_content[0] = content_reader[0]()

    def record_frame():
        now = time.perf_counter()
        frames.append(now)
        content_frames.append((now, frame_content[0]))

    # QQuickWidget renders through QQuickRenderControl: afterRendering is the
    # render completion signal; QWidget painting then presents that texture.
    window.qml_host.quick_window().beforeSynchronizing.connect(
        synchronize_frame_content, Qt.ConnectionType.DirectConnection
    )
    window.qml_host.quick_window().afterRendering.connect(
        record_frame, Qt.ConnectionType.DirectConnection
    )
    window.show()
    window.raise_()
    window.activateWindow()
    print("Native shell shown", flush=True)
    wid = model.active_workspace.workspace_id
    beats = []
    previous = [time.perf_counter()]
    run_starts = []
    preparation_intervals = []
    measured_intervals = []
    readiness_interval = None
    route_event = window.run_event_controller._route_execution_event

    def record_run_start(event):
        if event.get("type") == "run_started":
            run_starts.append(time.perf_counter())
        route_event(event)

    window.run_event_controller._route_execution_event = record_run_start

    def heartbeat():
        now = time.perf_counter()
        beats.append(
            (previous[0] + 0.010, now, max(0, (now - previous[0]) * 1000 - 10))
        )
        previous[0] = now

    def heartbeat_for(intervals):
        return percentiles(
            [
                late
                for expected, observed, late in beats
                if any(expected < end and observed >= start for start, end in intervals)
            ]
        )

    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(heartbeat)
    timer.start()

    def spin(predicate, timeout=60):
        if predicate():
            return
        loop = QEventLoop()
        check = QTimer()
        check.setInterval(1)
        deadline = QTimer()
        deadline.setSingleShot(True)
        errors = []

        def poll():
            try:
                if observer_errors:
                    raise RuntimeError(observer_errors[0])
                if predicate():
                    loop.quit()
            except Exception as exc:
                errors.append(exc)
                loop.quit()

        check.timeout.connect(poll)
        deadline.timeout.connect(loop.quit)
        check.start()
        deadline.start(int(timeout * 1000))
        loop.exec()
        check.stop()
        deadline.stop()
        if errors:
            raise errors[0]
        if not predicate():
            raise TimeoutError(f"GUI probe timeout: {window.console_panel.errors_text}")

    def current():
        tree = current_output_value(window.run_state, wid, output, output_key)
        return (
            next((item for _, items in tree.branches for item in items), None)
            if tree is not None
            else None
        )

    def idle():
        return not window.run_state.active_run_id and not getattr(
            window.run_state, "active_submission_id", ""
        )

    def visual_items(item):
        yield item
        for child in item.childItems():
            yield from visual_items(child)

    output_card = [None]

    def find_output_card(item):
        if item.objectName() == "graphNodeCard":
            return item if str(item.property("nodeId")) == output else None
        for child in item.childItems():
            found = find_output_card(child)
            if found is not None:
                return found
        return None

    def resolve_output_card():
        if output_card[0] is None:
            output_card[0] = find_output_card(window.qml_host.root_object())
            if output_card[0] is not None:
                output_card[0].destroyed.connect(
                    lambda: output_card.__setitem__(0, None)
                )
        return output_card[0] is not None

    content_item = [None]

    def visible_content_key():
        if not resolve_output_card():
            return ""
        if content_item[0] is None:
            object_name = (
                "graphNodeMediaImageRenderer" if args.graph == "plot"
                else "graphPanelItemValue"
            )
            item = next((item for item in visual_items(output_card[0])
                         if item.objectName() == object_name and item.isVisible()), None)
            if item is None:
                return ""
            content_item[0] = item
            item.destroyed.connect(
                lambda *_args, observed=item: content_item.__setitem__(0, None)
                if content_item[0] is observed else None
            )
        item = content_item[0]
        if not item.isVisible():
            content_item[0] = None
            return ""
        if args.graph == "plot":
            return (
                str(item.property("previewSourceUrl") or "")
                if item.property("previewState") == "ready" else ""
            )
        try:
            return str(float(item.property("text")))
        except (TypeError, ValueError):
            return ""

    content_reader[0] = visible_content_key
    records = []
    readiness_ms = None
    try:
        spin(lambda: bool(frames))
        print("Native first frame", flush=True)
        launch_ms = (frames[0] - launched) * 1000
        path = args.output.parent / "fixture.cxproj"
        JsonProjectSerializer(registry).save(str(path), model.project)
        assert window.project_session_controller.open_project_path(
            path, show_errors=False
        )
        window.view.set_view_state(0.65, 550, 160)
        if args.expand_settings and args.graph == "plot":
            for group in registry.get_spec("plot.signal").settings_groups:
                window.scene.set_node_settings_group_expanded(
                    edited, group.group_id, True
                )
        spin(resolve_output_card)
        setup_frame_count = len(frames)
        window.quick_widget.update()
        spin(lambda: len(frames) > setup_frame_count)
        if args.warmup_worker:
            readiness_started = time.perf_counter()
            readiness = window.execution_client.warm_up_builtin_generation()
            spin(readiness.done)
            assert readiness.result().available
            readiness_ms = (time.perf_counter() - readiness_started) * 1000
            readiness_interval = readiness_started, time.perf_counter()
        for index in range(-1, args.warmups + args.edits):
            changes = {} if index < 0 else change(args.graph, index)
            old_digest = output_digest(current(), args.graph)
            first_start_index = len(run_starts)
            gui_profile = None
            if args.profile_gui and index >= args.warmups:
                import cProfile

                gui_profile = cProfile.Profile()
                gui_profile.enable()
            start = time.perf_counter()
            if index < 0:
                window.run_controller.run_workflow()
            else:
                if args.profile_handler and index >= args.warmups:
                    import cProfile
                    import pstats

                    profile = cProfile.Profile()
                    profile.enable()
                    assert window.scene.set_node_properties(edited, changes)
                    profile.disable()
                    profile_path = args.output.with_suffix(f".handler_{index}.pstats")
                    profile.dump_stats(str(profile_path))
                    with profile_path.with_suffix(".txt").open(
                        "w", encoding="utf-8"
                    ) as stream:
                        pstats.Stats(profile, stream=stream).sort_stats(
                            "cumulative"
                        ).print_stats(70)
                else:
                    assert window.scene.set_node_properties(edited, changes)
            returned = time.perf_counter()
            spin(
                lambda: (
                    idle()
                    and current() is not None
                    and output_digest(current(), args.graph) != old_digest
                )
            )
            accepted = time.perf_counter()
            print(f"Native accepted iteration {index}", flush=True)
            value = current()
            digest = verify(value, args.graph, changes)
            def accepted_frame():
                return next(
                    ((stamp, key) for stamp, key in content_frames if stamp >= start
                     and (digest in key if args.graph == "plot" else key == str(float(value)))),
                    None,
                )

            # The first matching frame may already have rendered while later
            # run events were being projected. Do not force an extra frame
            # and count its latency as the first appearance of this result.
            window.qml_host.quick_window().update()
            spin(lambda: accepted_frame() is not None)
            presented_at, presented_key = accepted_frame()
            app.processEvents()
            records.append(
                {
                    "iteration": index,
                    "cold": index < 0,
                    "measured": index >= args.warmups,
                    "handler_ms": (returned - start) * 1000,
                    "idle_observed_ms": (accepted - start) * 1000,
                    "total_ms": (presented_at - start) * 1000,
                    "output_digest": digest,
                    "image_url": presented_key if args.graph == "plot" else "",
                }
            )
            preparation_end = (
                run_starts[first_start_index]
                if len(run_starts) > first_start_index
                else accepted
            )
            records[-1]["preparation_to_start_ms"] = (preparation_end - start) * 1000
            preparation_intervals.append((start, preparation_end))
            if index >= args.warmups:
                measured_intervals.append((start, presented_at))
            if gui_profile is not None:
                import pstats

                gui_profile.disable()
                profile_path = args.output.with_suffix(f".gui_{index}.pstats")
                gui_profile.dump_stats(str(profile_path))
                with profile_path.with_suffix(".txt").open(
                    "w", encoding="utf-8"
                ) as stream:
                    pstats.Stats(gui_profile, stream=stream).sort_stats(
                        "cumulative"
                    ).print_stats(80)
            print(
                f"Native iteration {index}: {records[-1]['total_ms']:.1f} ms",
                flush=True,
            )
            if index == -1:
                window.run_controller.set_auto_run_enabled(True)
                spin(idle)
        captured_frame = ""
        if args.capture_frame:
            capture_path = args.output.with_suffix(".png")
            if not window.grab().save(str(capture_path), "PNG"):
                raise RuntimeError("Could not capture the final native shell frame")
            captured_frame = str(capture_path)
        return {
            "records": records,
            "launch_to_shell_ms": launch_ms,
            "readiness_ms": readiness_ms,
            "backend_identity": backend_identity(window.execution_client),
            "heartbeat_ms": heartbeat_for(measured_intervals),
            "preparation_heartbeat_ms": heartbeat_for(preparation_intervals),
            "readiness_heartbeat_ms": heartbeat_for(
                [readiness_interval] if readiness_interval else []
            ),
            "frame_evidence": "Content sampled before synchronization; earliest afterRendering with image URL/text matching the accepted output",
            "frame_probe_revision": 5,
            "heartbeat_probe_revision": 2,
            "qt_backend": window.qtquick_backend_debug_payload(),
            "window_active": window.isActiveWindow(),
            "platform": app.platformName(),
            "qml_host": window.qml_host.host_kind,
            "captured_frame": captured_frame,
        }
    finally:
        timer.stop()
        window.close()
        app.processEvents()


def main():
    import faulthandler

    faulthandler.dump_traceback_later(120, repeat=True)
    launched = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("runtime", "shell"), default="runtime")
    parser.add_argument("--graph", choices=("plot", "scalar"), default="plot")
    parser.add_argument("--edits", type=int, default=50)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--unrelated", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-handler", action="store_true")
    parser.add_argument("--profile-gui", action="store_true")
    parser.add_argument("--expand-settings", action="store_true")
    parser.add_argument("--warmup-worker", action="store_true")
    parser.add_argument("--capture-frame", action="store_true")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    os.environ["APPDATA"] = str(args.output.parent / "profile")
    if args.mode == "shell":
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
        print("Preloading native table runtime", flush=True)
        from ea_node_editor.addons.tabular_data.loader_cache_service import (
            _preload_native_tabular_runtime,
        )

        _preload_native_tabular_runtime()
    from ea_node_editor.nodes.bootstrap import build_default_registry

    registry = build_default_registry(include_public_plugins=False)
    print("Registry ready", flush=True)
    model, edited, output, key = fixture(
        registry, args.output.parent, args.graph, args.unrelated
    )
    import psutil

    process = psutil.Process()
    stop = threading.Event()
    peak = [0]

    def sample():
        while not stop.wait(0.01):
            total = 0
            for child in [process, *process.children(recursive=True)]:
                try:
                    total += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            peak[0] = max(peak[0], total)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        report = (
            runtime_probe(args, registry, model, edited, output, key)
            if args.mode == "runtime"
            else shell_probe(args, registry, model, edited, output, key, launched)
        )
    finally:
        stop.set()
        sampler.join()
    report.update(
        mode=args.mode,
        profiled=args.profile_handler or args.profile_gui,
        expanded_settings=args.expand_settings,
        warmup_worker=args.warmup_worker,
        graph=args.graph,
        unrelated=args.unrelated,
        python=sys.executable,
        peak_combined_rss=peak[0],
        process_id=os.getpid(),
        warm_ms=percentiles(
            [record["total_ms"] for record in report["records"] if record["measured"]]
        ),
    )
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    faulthandler.cancel_dump_traceback_later()
    print(
        json.dumps({key: value for key, value in report.items() if key != "records"}),
        flush=True,
    )


if __name__ == "__main__":
    main()
