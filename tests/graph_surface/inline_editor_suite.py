from __future__ import annotations

from tests.graph_surface.environment import *  # noqa: F403

class PassiveGraphSurfaceInlineEditorTests(PassiveGraphSurfaceHostTestBase):
    def test_expanded_flowchart_body_text_replaces_visible_header_title_and_double_click_enters_inline_edit(self) -> None:
        self._run_qml_probe(
            "flowchart-body-text-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": flowchart_payload("decision")})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                title_item = host.findChild(QObject, "graphNodeTitle")
                title_editor = host.findChild(QObject, "graphNodeTitleEditor")
                body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
                body_editor = host.findChild(QObject, "graphNodeFlowchartBodyEditor")
                body_field = host.findChild(QObject, "graphNodeFlowchartBodyEditorField")
                assert title_item is not None
                assert title_editor is not None
                assert body_text is not None
                assert body_editor is not None
                assert body_field is not None

                events = host_pointer_events(host)
                interactions = []
                host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
                body_point = item_scene_point(body_text)

                assert not bool(title_item.property("visible"))
                assert not bool(title_editor.property("visible"))
                assert str(body_text.property("text") or "") == "Review the decision criteria and route accordingly."
                assert bool(body_text.property("visible"))
                assert not bool(body_editor.property("visible"))

                mouse_click(window, body_point)
                assert events["clicked"] == [("node_surface_host_test", False)]
                assert events["opened"] == []
                assert not bool(body_editor.property("visible"))

                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_double_click(window, body_point)
                settle_events(5)

                assert not bool(title_editor.property("visible"))
                assert not bool(body_text.property("visible"))
                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))
                assert str(body_field.property("text") or "") == "Review the decision criteria and route accordingly."
                assert int(body_field.property("cursorPosition")) == len(str(body_field.property("text") or ""))
                assert len(interactions) >= 1
                assert all(node_id == "node_surface_host_test" for node_id in interactions)
                assert events["opened"] == []
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_expanded_flowchart_body_text_uses_fallback_chain_and_passive_style_hooks(self) -> None:
        self._run_qml_probe(
            "flowchart-body-fallback-style-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": flowchart_payload(
                        "decision",
                        title="Archive",
                        properties={"title": "Archive", "body": "   "},
                        visual_style={
                            "text_color": "#204060",
                            "font_size": 17,
                            "font_weight": "bold",
                        },
                    ),
                },
            )
            title_item = host.findChild(QObject, "graphNodeTitle")
            body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
            assert title_item is not None
            assert body_text is not None
            assert not bool(title_item.property("visible"))
            assert bool(body_text.property("visible"))
            assert str(body_text.property("text") or "") == "Archive"
            body_font = body_text.property("font")
            assert body_font.pixelSize() == 17
            assert body_font.bold()
            assert body_text.property("color").name().lower() == "#204060"
            """,
        )

    def test_expanded_flowchart_body_editor_commits_from_external_click_path(self) -> None:
        self._run_qml_probe(
            "flowchart-body-external-click-commit-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": flowchart_payload("decision")})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
                body_editor = host.findChild(QObject, "graphNodeFlowchartBodyEditor")
                body_field = host.findChild(QObject, "graphNodeFlowchartBodyEditorField")
                assert body_text is not None
                assert body_editor is not None
                assert body_field is not None

                events = host_pointer_events(host)
                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(body_text))
                settle_events(5)
                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))

                body_field.setProperty("text", "Approve request\\nNotify requester")
                app.processEvents()

                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_click(window, host_scene_point(host, 24.0, 6.0))
                settle_events(5)

                assert committed == [("node_surface_host_test", "body", "Approve request\\nNotify requester")]
                assert events["clicked"] == [("node_surface_host_test", False)]
                assert events["opened"] == []
                assert events["contexts"] == []
                assert bool(body_text.property("visible"))
                assert not bool(body_editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_expanded_flowchart_body_editor_cancels_and_closes_on_escape(self) -> None:
        self._run_qml_probe(
            "flowchart-body-escape-cancel-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": flowchart_payload("decision")})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
                body_editor = host.findChild(QObject, "graphNodeFlowchartBodyEditor")
                body_field = host.findChild(QObject, "graphNodeFlowchartBodyEditorField")
                assert body_text is not None
                assert body_editor is not None
                assert body_field is not None

                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(body_text))
                settle_events(5)
                assert bool(body_editor.property("visible"))

                body_field.setProperty("text", "Discard this draft")
                app.processEvents()
                app.sendEvent(
                    body_field,
                    QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                )
                app.sendEvent(
                    body_field,
                    QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                )
                settle_events(5)

                assert committed == []
                assert bool(body_text.property("visible"))
                assert not bool(body_editor.property("visible"))
                assert str(body_field.property("text") or "") == "Review the decision criteria and route accordingly."
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_passive_planning_body_text_double_click_commits_and_cancels_inline_edits(self) -> None:
        self._run_qml_probe(
            "planning-inline-body-edit-host",
            """
            payload = node_payload(surface_family="planning", surface_variant="decision_card")
            payload["runtime_behavior"] = "passive"
            payload["type_id"] = "passive.planning.decision_card"
            payload["properties"] = {
                "body": "Review the decision criteria and route accordingly.",
                "state": "open",
                "status": "open",
                "outcome": "",
            }

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_text = host.findChild(QObject, "graphNodePlanningBodyText")
                body_editor = host.findChild(QObject, "graphNodePlanningBodyEditor")
                body_field = host.findChild(QObject, "graphNodePlanningBodyEditorField")
                assert body_text is not None
                assert body_editor is not None
                assert body_field is not None

                events = host_pointer_events(host)
                interactions = []
                committed = []
                host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                body_point = item_scene_point(body_text)
                mouse_double_click(window, body_point)
                settle_events(5)

                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))
                assert str(body_field.property("text") or "") == "Review the decision criteria and route accordingly."
                assert len(interactions) >= 1
                assert all(node_id == "node_surface_host_test" for node_id in interactions)
                assert events["opened"] == []

                body_field.setProperty("text", "Approve path A\\nNotify the team")
                app.processEvents()
                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_click(window, host_scene_point(host, 24.0, 8.0))
                settle_events(5)

                assert committed == [("node_surface_host_test", "body", "Approve path A\\nNotify the team")]
                assert events["opened"] == []
                assert not bool(body_editor.property("visible"))
                assert bool(body_text.property("visible"))

                committed.clear()
                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_double_click(window, body_point)
                settle_events(5)
                assert bool(body_editor.property("visible"))

                body_field.setProperty("text", "Discard this draft")
                app.processEvents()
                app.sendEvent(
                    body_field,
                    QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                )
                app.sendEvent(
                    body_field,
                    QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                )
                settle_events(5)

                assert committed == []
                assert not bool(body_editor.property("visible"))
                assert bool(body_text.property("visible"))
                assert events["opened"] == []
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_passive_annotation_body_text_double_click_edits_body_and_subtitle_inline(self) -> None:
        self._run_qml_probe(
            "annotation-inline-edit-host",
            """
            def run_annotation_case(
                label,
                payload,
                text_object_name,
                editor_object_name,
                field_object_name,
                key,
                *,
                commit_via_keyboard=False,
            ):
                host = create_component(graph_node_host_qml_path, {"nodeData": payload})
                window = attach_host_to_window(host, width=640, height=480)
                try:
                    text_item = host.findChild(QObject, text_object_name)
                    editor = host.findChild(QObject, editor_object_name)
                    field = host.findChild(QObject, field_object_name)
                    assert text_item is not None, label
                    assert editor is not None, label
                    assert field is not None, label

                    events = host_pointer_events(host)
                    interactions = []
                    committed = []
                    host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
                    host.inlinePropertyCommitted.connect(
                        lambda node_id, committed_key, value: committed.append((node_id, committed_key, variant_value(value)))
                    )

                    text_point = item_scene_point(text_item)
                    mouse_double_click(window, text_point)
                    settle_events(10 if commit_via_keyboard else 5)

                    assert bool(editor.property("visible")), label
                    assert bool(field.property("activeFocus")), label
                    assert len(interactions) >= 1, label
                    assert all(node_id == "node_surface_host_test" for node_id in interactions), label
                    assert events["opened"] == [], label

                    field.setProperty("text", f"Edited {label}")
                    app.processEvents()
                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()

                    if commit_via_keyboard:
                        app.sendEvent(
                            field,
                            QKeyEvent(
                                QEvent.Type.KeyPress,
                                Qt.Key.Key_Enter,
                                Qt.KeyboardModifier.ControlModifier,
                            ),
                        )
                        app.sendEvent(
                            field,
                            QKeyEvent(
                                QEvent.Type.KeyRelease,
                                Qt.Key.Key_Enter,
                                Qt.KeyboardModifier.ControlModifier,
                            ),
                        )
                    else:
                        mouse_click(window, host_scene_point(host, 24.0, 8.0))
                    settle_events(10 if commit_via_keyboard else 5)

                    assert committed == [("node_surface_host_test", key, f"Edited {label}")], label
                    assert not bool(editor.property("visible")), label
                    assert events["opened"] == [], label
                finally:
                    dispose_host_window(host, window)

            sticky_payload = node_payload(surface_family="annotation", surface_variant="sticky_note")
            sticky_payload["runtime_behavior"] = "passive"
            sticky_payload["type_id"] = "passive.annotation.sticky_note"
            sticky_payload["properties"] = {"body": "Sticky note body"}
            run_annotation_case(
                "sticky-note-body",
                sticky_payload,
                "graphNodeAnnotationBodyText",
                "graphNodeAnnotationBodyEditor",
                "graphNodeAnnotationBodyEditorField",
                "body",
            )

            section_payload = node_payload(surface_family="annotation", surface_variant="section_header")
            section_payload["runtime_behavior"] = "passive"
            section_payload["type_id"] = "passive.annotation.section_header"
            section_payload["properties"] = {"subtitle": "Section subtitle"}
            run_annotation_case(
                "section-header-subtitle",
                section_payload,
                "graphNodeAnnotationSubtitleText",
                "graphNodeAnnotationBodyEditor",
                "graphNodeAnnotationSubtitleEditorField",
                "subtitle",
                commit_via_keyboard=True,
            )
            """,
        )

    def test_passive_planning_empty_body_area_double_click_enters_edit_and_blur_closes_without_commit(self) -> None:
        self._run_qml_probe(
            "planning-empty-body-inline-edit-host",
            """
            payload = node_payload(surface_family="planning", surface_variant="decision_card")
            payload["runtime_behavior"] = "passive"
            payload["type_id"] = "passive.planning.decision_card"
            payload["properties"] = {
                "body": "",
                "state": "open",
                "status": "open",
                "outcome": "",
            }

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_editor = host.findChild(QObject, "graphNodePlanningBodyEditor")
                body_field = host.findChild(QObject, "graphNodePlanningBodyEditorField")
                assert body_editor is not None
                assert body_field is not None

                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(body_editor))
                settle_events(5)

                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))
                assert str(body_field.property("text") or "") == ""

                mouse_click(window, host_scene_point(host, 24.0, 8.0))
                settle_events(5)

                assert committed == []
                assert not bool(body_editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_passive_annotation_empty_body_area_double_click_enters_edit_and_blur_closes_without_commit(self) -> None:
        self._run_qml_probe(
            "annotation-empty-body-inline-edit-host",
            """
            payload = node_payload(surface_family="annotation", surface_variant="sticky_note")
            payload["runtime_behavior"] = "passive"
            payload["type_id"] = "passive.annotation.sticky_note"
            payload["properties"] = {"body": ""}

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                body_editor = host.findChild(QObject, "graphNodeAnnotationBodyEditor")
                body_field = host.findChild(QObject, "graphNodeAnnotationBodyEditorField")
                assert body_editor is not None
                assert body_field is not None

                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(body_editor))
                settle_events(5)

                assert bool(body_editor.property("visible"))
                assert bool(body_field.property("activeFocus"))
                assert str(body_field.property("text") or "") == ""

                mouse_click(window, host_scene_point(host, 24.0, 8.0))
                settle_events(5)

                assert committed == []
                assert not bool(body_editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_collapsed_flowchart_keeps_compact_header_title_behavior(self) -> None:
        self._run_qml_probe(
            "flowchart-collapsed-title-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": flowchart_payload("decision", title="Archive", collapsed=True)},
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            title_item = host.findChild(QObject, "graphNodeTitle")
            editor = host.findChild(QObject, "graphNodeTitleEditor")
            body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
            assert loader is not None
            assert title_item is not None
            assert editor is not None
            assert body_text is None
            assert not bool(loader.property("surfaceLoaded"))
            assert bool(title_item.property("visible"))
            assert str(title_item.property("text") or "") == "Archive"
            assert not bool(editor.property("visible"))
            """,
        )

    def test_non_scoped_standard_and_passive_titles_use_shared_header_editor_without_pointer_leaks(self) -> None:
        self._run_qml_probe(
            "shared-header-title-rollout-host",
            """
            def passive_standard_payload():
                payload = node_payload()
                payload["runtime_behavior"] = "passive"
                payload["type_id"] = "passive.standard.note"
                payload["title"] = "Passive Note"
                payload["properties"] = {"title": "Passive Note"}
                payload["visual_style"] = {
                    "fill_color": "#f3f8fd",
                    "border_color": "#6f88a3",
                    "text_color": "#173247",
                    "header_color": "#deebf7",
                }
                return payload

            scenarios = [
                ("standard", node_payload(), "Approved"),
                ("passive", passive_standard_payload(), "Reviewed"),
            ]

            for label, payload, committed_title in scenarios:
                def scenario_check(condition, step):
                    assert condition, f"{label}: {step}"

                host = create_component(graph_node_host_qml_path, {"nodeData": payload})
                window = attach_host_to_window(host, width=640, height=480)
                try:
                    title_item = host.findChild(QObject, "graphNodeTitle")
                    editor = host.findChild(QObject, "graphNodeTitleEditor")
                    scenario_check(title_item is not None, "title item missing")
                    scenario_check(editor is not None, "title editor missing")
                    scenario_check(
                        bool(host.property("sharedHeaderTitleEditable")),
                        "shared header title editing disabled",
                    )

                    events = host_pointer_events(host)
                    interactions = []
                    committed = []
                    host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
                    host.inlinePropertyCommitted.connect(
                        lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                    )

                    title_point = item_scene_point(title_item)
                    body_point = host_scene_point(
                        host,
                        24.0,
                        44.0,
                    )

                    mouse_click(window, title_point)
                    scenario_check(
                        events["clicked"] == [(payload["node_id"], False)],
                        f"single-click title routed unexpectedly: clicked={events['clicked']!r}",
                    )
                    scenario_check(
                        events["opened"] == [],
                        f"single-click title unexpectedly opened node: opened={events['opened']!r}",
                    )
                    scenario_check(
                        not bool(editor.property("visible")),
                        "single-click title unexpectedly opened editor",
                    )

                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()

                    mouse_double_click(window, title_point)
                    settle_events(5)
                    scenario_check(bool(editor.property("visible")), "double-click title did not open editor")
                    scenario_check(
                        str(editor.property("selectedText") or "") == "",
                        f"editor selected unexpected title text: {editor.property('selectedText')!r}",
                    )
                    scenario_check(
                        int(editor.property("cursorPosition")) == len(str(payload["title"])),
                        f"cursor positioned incorrectly: cursor={editor.property('cursorPosition')!r}",
                    )
                    scenario_check(
                        interactions == [payload["node_id"]],
                        f"title edit interaction event mismatch: {interactions!r}",
                    )
                    scenario_check(
                        events["opened"] == [],
                        f"double-click title unexpectedly opened node: opened={events['opened']!r}",
                    )

                    editor.setProperty("text", f" {committed_title} ")
                    app.processEvents()
                    app.sendEvent(
                        editor,
                        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
                    )
                    app.sendEvent(
                        editor,
                        QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
                    )
                    settle_events(5)
                    scenario_check(
                        committed == [(payload["node_id"], "title", committed_title)],
                        f"title commit mismatch: {committed!r}",
                    )
                    scenario_check(not bool(editor.property("visible")), "editor stayed visible after commit")

                    committed.clear()
                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()

                    mouse_double_click(window, title_point)
                    settle_events(5)
                    scenario_check(bool(editor.property("visible")), "second title double-click did not reopen editor")

                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()
                    editor_point = item_scene_point(editor)
                    mouse_click(window, editor_point)
                    mouse_double_click(window, editor_point)
                    mouse_click(window, editor_point, Qt.MouseButton.RightButton)
                    settle_events(5)
                    scenario_check(
                        events["clicked"] == [],
                        f"editor click leaked node clicks: {events['clicked']!r}",
                    )
                    scenario_check(
                        events["opened"] == [],
                        f"editor click leaked node opens: {events['opened']!r}",
                    )
                    scenario_check(
                        events["contexts"] == [],
                        f"editor click leaked node context menu: {events['contexts']!r}",
                    )

                    app.sendEvent(
                        editor,
                        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                    )
                    app.sendEvent(
                        editor,
                        QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
                    )
                    settle_events(5)
                    scenario_check(committed == [], f"escape unexpectedly committed title: {committed!r}")
                    scenario_check(not bool(editor.property("visible")), "editor stayed visible after escape")

                    events["clicked"].clear()
                    events["opened"].clear()
                    events["contexts"].clear()
                    mouse_double_click(window, body_point)
                    settle_events(5)
                    scenario_check(
                        events["opened"] == [payload["node_id"]],
                        f"body double-click did not open node: {events['opened']!r}",
                    )
                finally:
                    dispose_host_window(host, window)
            """,
        )

    def test_collapsed_nodes_use_shared_header_editor_for_title_commits(self) -> None:
        self._run_qml_probe(
            "shared-header-title-rollout-collapsed-host",
            """
            payload = node_payload()
            payload["collapsed"] = True

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                title_item = host.findChild(QObject, "graphNodeTitle")
                editor = host.findChild(QObject, "graphNodeTitleEditor")
                assert title_item is not None
                assert editor is not None
                assert bool(host.property("sharedHeaderTitleEditable"))

                committed = []
                events = host_pointer_events(host)
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                mouse_double_click(window, item_scene_point(title_item))
                settle_events(5)
                assert bool(editor.property("visible"))
                assert events["opened"] == []

                editor.setProperty("text", " Collapsed Logger ")
                app.processEvents()
                app.sendEvent(
                    editor,
                    QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
                )
                app.sendEvent(
                    editor,
                    QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
                )
                settle_events(5)

                assert committed == [("node_surface_host_test", "title", "Collapsed Logger")]
                assert not bool(editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

class GraphSurfaceInlineEditorContractTests(GraphSurfaceInputContractTestBase):
    def test_graph_canvas_routes_surface_control_edits_by_explicit_node_id(self) -> None:
        self._run_qml_probe(
            "graph-canvas-surface-control-bridge",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

            class SceneBridgeStub(QObject):
                nodes_changed = pyqtSignal()
                edges_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_property_calls = []
                    self._nodes_model = [node_payload()]
                    self._selected_node_lookup = {}

                @pyqtProperty("QVariantList", notify=nodes_changed)
                def nodes_model(self):
                    return self._nodes_model

                @pyqtProperty("QVariantList", notify=edges_changed)
                def edges_model(self):
                    return []

                @pyqtProperty("QVariantMap", notify=nodes_changed)
                def selected_node_lookup(self):
                    return self._selected_node_lookup

                @pyqtSlot(str)
                @pyqtSlot(str, bool)
                def select_node(self, node_id, additive=False):
                    normalized_node_id = str(node_id or "")
                    self.select_calls.append((normalized_node_id, bool(additive)))
                    self._selected_node_lookup = {normalized_node_id: True} if normalized_node_id else {}
                    self.nodes_changed.emit()

                @pyqtSlot(str, str, "QVariant")
                def set_node_property(self, node_id, key, value):
                    self.set_node_property_calls.append((str(node_id or ""), str(key or ""), variant_value(value)))

                @pyqtSlot(str, str, str)
                def set_node_port_label(self, node_id, port_key, label):
                    pass

                @pyqtSlot(str, str, result=bool)
                def are_port_kinds_compatible(self, _source_kind, _target_kind):
                    return True

                @pyqtSlot(str, str, result=bool)
                def are_data_types_compatible(self, _source_type, _target_type):
                    return True

            class MainWindowBridgeStub(QObject):
                @pyqtProperty(bool, constant=True)
                def graphics_minimap_expanded(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, constant=True)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, constant=True)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, constant=True)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                def __init__(self):
                    super().__init__()
                    self.set_selected_node_property_calls = []

                @pyqtSlot(str, "QVariant")
                def set_selected_node_property(self, key, value):
                    self.set_selected_node_property_calls.append((str(key or ""), variant_value(value)))

            scene_bridge = SceneBridgeStub()
            window_bridge = MainWindowBridgeStub()
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=window_bridge,
                scene_bridge=scene_bridge,
            )
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                },
            )
            def walk_items(item):
                yield item
                for child in item.childItems():
                    yield from walk_items(child)

            node_card = next((item for item in walk_items(canvas) if item.objectName() == "graphNodeCard"), None)
            assert node_card is not None

            canvas.setProperty(
                "pendingConnectionPort",
                {
                    "node_id": "pending-node",
                    "port_key": "exec_out",
                    "direction": "out",
                    "allow_multiple_connections": False,
                    "scene_x": 10.0,
                    "scene_y": 12.0,
                },
            )
            canvas.setProperty(
                "wireDragState",
                {
                    "node_id": "pending-node",
                    "port_key": "exec_out",
                    "source_direction": "out",
                    "start_x": 10.0,
                    "start_y": 12.0,
                    "cursor_x": 20.0,
                    "cursor_y": 30.0,
                    "press_screen_x": 40.0,
                    "press_screen_y": 50.0,
                    "active": True,
                },
            )
            canvas.setProperty(
                "wireDropCandidate",
                {
                    "node_id": "candidate-node",
                    "port_key": "exec_in",
                    "direction": "in",
                    "scene_x": 20.0,
                    "scene_y": 30.0,
                    "valid_drop": True,
                },
            )
            canvas.setProperty("edgeContextVisible", True)
            canvas.setProperty("nodeContextVisible", True)
            canvas.setProperty("selectedEdgeIds", ["edge-1"])
            app.processEvents()

            node_card.surfaceControlInteractionStarted.emit("node_surface_contract_test")
            app.processEvents()

            assert scene_bridge.select_calls == [("node_surface_contract_test", False)]
            assert canvas.property("pendingConnectionPort") is None
            assert canvas.property("wireDragState") is None
            assert canvas.property("wireDropCandidate") is None
            assert not bool(canvas.property("edgeContextVisible"))
            assert not bool(canvas.property("nodeContextVisible"))
            assert variant_list(canvas.property("selectedEdgeIds")) == []

            node_card.inlinePropertyCommitted.emit(
                "node_surface_contract_test",
                "message",
                "updated from graph surface",
            )
            app.processEvents()

            assert scene_bridge.set_node_property_calls == [
                ("node_surface_contract_test", "message", "updated from graph surface")
            ]
            assert window_bridge.set_selected_node_property_calls == []
            assert scene_bridge.select_calls == [
                ("node_surface_contract_test", False),
                ("node_surface_contract_test", False),
            ]

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_routes_non_scoped_shared_header_title_edits_without_body_pointer_regressions(self) -> None:
        self._run_qml_probe(
            "graph-canvas-shared-header-title-editor",
            """
            from PyQt6.QtCore import QObject, QPointF, pyqtProperty, pyqtSignal, pyqtSlot

            class SceneBridgeStub(QObject):
                nodes_changed = pyqtSignal()
                edges_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_property_calls = []
                    self._nodes_model = [node_payload()]
                    self._selected_node_lookup = {}

                @pyqtProperty("QVariantList", notify=nodes_changed)
                def nodes_model(self):
                    return self._nodes_model

                @pyqtProperty("QVariantList", notify=edges_changed)
                def edges_model(self):
                    return []

                @pyqtProperty("QVariantMap", notify=nodes_changed)
                def selected_node_lookup(self):
                    return self._selected_node_lookup

                @pyqtSlot(str)
                @pyqtSlot(str, bool)
                def select_node(self, node_id, additive=False):
                    normalized_node_id = str(node_id or "")
                    self.select_calls.append((normalized_node_id, bool(additive)))
                    self._selected_node_lookup = {normalized_node_id: True} if normalized_node_id else {}
                    self.nodes_changed.emit()

                @pyqtSlot(str, str, "QVariant")
                def set_node_property(self, node_id, key, value):
                    self.set_node_property_calls.append((str(node_id or ""), str(key or ""), variant_value(value)))

                @pyqtSlot(str, str, str)
                def set_node_port_label(self, node_id, port_key, label):
                    pass

                @pyqtSlot(str, str, result=bool)
                def are_port_kinds_compatible(self, _source_kind, _target_kind):
                    return True

                @pyqtSlot(str, str, result=bool)
                def are_data_types_compatible(self, _source_type, _target_type):
                    return True

            class MainWindowBridgeStub(QObject):
                @pyqtProperty(bool, constant=True)
                def graphics_minimap_expanded(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, constant=True)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, constant=True)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, constant=True)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

            scene_bridge = SceneBridgeStub()
            window_bridge = MainWindowBridgeStub()
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=window_bridge,
                scene_bridge=scene_bridge,
            )
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )
            try:
                node_card = next((item for item in walk_items(canvas) if item.objectName() == "graphNodeCard"), None)
                assert node_card is not None
                title_item = node_card.findChild(QObject, "graphNodeTitle")
                editor = node_card.findChild(QObject, "graphNodeTitleEditor")
                assert title_item is not None
                assert editor is not None
                assert bool(node_card.property("sharedHeaderTitleEditable"))

                open_requests = []
                node_card.nodeOpenRequested.connect(lambda node_id: open_requests.append(node_id))

                title_point = title_item.mapToItem(
                    node_card,
                    QPointF(float(title_item.width()) * 0.5, float(title_item.height()) * 0.5),
                )
                body_local_x = float(node_card.property("width")) * 0.5
                body_local_y = float(node_card.property("height")) * 0.78

                assert not node_card.requestInlineTitleEditAt(body_local_x, body_local_y)
                assert not bool(editor.property("visible"))
                assert node_card.requestInlineTitleEditAt(title_point.x(), title_point.y())
                settle_events(5)
                assert bool(editor.property("visible"))
                assert open_requests == []
                assert scene_bridge.select_calls == [("node_surface_contract_test", False)]

                assert not node_card.commitInlineTitleEditAt(title_point.x(), title_point.y())
                assert bool(editor.property("visible"))

                scene_bridge.select_calls.clear()
                scene_bridge.set_node_property_calls.clear()
                editor.setProperty("text", " Updated Logger ")
                app.processEvents()
                assert node_card.commitInlineTitleEditAt(body_local_x, body_local_y)
                settle_events(5)

                assert scene_bridge.set_node_property_calls == [
                    ("node_surface_contract_test", "title", "Updated Logger")
                ]
                assert scene_bridge.select_calls == [("node_surface_contract_test", False)]
                assert not bool(editor.property("visible"))
                assert open_requests == []
            finally:
                canvas.deleteLater()
                app.processEvents()
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_canvas_supports_surface_control_edits_via_split_canvas_bridges(self) -> None:
        self._run_qml_probe(
            "graph-canvas-split-bridge-surface-control",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

            class CanvasStateBridgeStub(QObject):
                graphics_preferences_changed = pyqtSignal()
                snap_to_grid_changed = pyqtSignal()
                scene_nodes_changed = pyqtSignal()
                scene_edges_changed = pyqtSignal()
                scene_selection_changed = pyqtSignal()
                view_state_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_property_calls = []
                    self._nodes_model = [node_payload()]
                    self._selected_node_lookup = {}
                    self._width = 640.0
                    self._height = 480.0

                @pyqtProperty(bool, constant=True)
                def graphics_minimap_expanded(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, constant=True)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, constant=True)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, constant=True)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtProperty(float, constant=True)
                def center_x(self):
                    return 0.0

                @pyqtProperty(float, constant=True)
                def center_y(self):
                    return 0.0

                @pyqtProperty(float, constant=True)
                def zoom_value(self):
                    return 1.0

                @pyqtProperty("QVariantMap", notify=view_state_changed)
                def visible_scene_rect_payload(self):
                    return {
                        "x": -(self._width * 0.5),
                        "y": -(self._height * 0.5),
                        "width": self._width,
                        "height": self._height,
                    }

                @pyqtProperty("QVariantList", notify=scene_nodes_changed)
                def nodes_model(self):
                    return self._nodes_model

                @pyqtProperty("QVariantList", notify=scene_nodes_changed)
                def minimap_nodes_model(self):
                    return self._nodes_model

                @pyqtProperty("QVariantMap", notify=scene_nodes_changed)
                def workspace_scene_bounds_payload(self):
                    return {
                        "x": 0.0,
                        "y": 0.0,
                        "width": 640.0,
                        "height": 480.0,
                    }

                @pyqtProperty("QVariantList", notify=scene_edges_changed)
                def edges_model(self):
                    return []

                @pyqtProperty("QVariantMap", notify=scene_selection_changed)
                def selected_node_lookup(self):
                    return self._selected_node_lookup

                @pyqtSlot(str, str, result=bool)
                def are_port_kinds_compatible(self, _source_kind, _target_kind):
                    return True

                @pyqtSlot(str, str, result=bool)
                def are_data_types_compatible(self, _source_type, _target_type):
                    return True

            class CanvasCommandBridgeStub(QObject):
                def __init__(self, state_bridge):
                    super().__init__()
                    self._state_bridge = state_bridge

                @pyqtSlot(float, float)
                def set_viewport_size(self, width, height):
                    self._state_bridge._width = float(width)
                    self._state_bridge._height = float(height)
                    self._state_bridge.view_state_changed.emit()

                @pyqtSlot(str)
                @pyqtSlot(str, bool)
                def select_node(self, node_id, additive=False):
                    normalized_node_id = str(node_id or "")
                    self._state_bridge.select_calls.append((normalized_node_id, bool(additive)))
                    self._state_bridge._selected_node_lookup = (
                        {normalized_node_id: True} if normalized_node_id else {}
                    )
                    self._state_bridge.scene_selection_changed.emit()

                @pyqtSlot(str, str, "QVariant")
                def set_node_property(self, node_id, key, value):
                    self._state_bridge.set_node_property_calls.append(
                        (str(node_id or ""), str(key or ""), variant_value(value))
                    )

                @pyqtSlot(str, str, str)
                def set_node_port_label(self, node_id, port_key, label):
                    pass

            canvas_state_bridge = CanvasStateBridgeStub()
            canvas_command_bridge = CanvasCommandBridgeStub(canvas_state_bridge)
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )

            def walk_items(item):
                yield item
                for child in item.childItems():
                    yield from walk_items(child)

            node_card = next((item for item in walk_items(canvas) if item.objectName() == "graphNodeCard"), None)
            assert node_card is not None

            node_card.surfaceControlInteractionStarted.emit("node_surface_contract_test")
            app.processEvents()
            node_card.inlinePropertyCommitted.emit(
                "node_surface_contract_test",
                "message",
                "updated through split bridges",
            )
            app.processEvents()

            assert canvas_state_bridge.select_calls == [
                ("node_surface_contract_test", False),
                ("node_surface_contract_test", False),
            ]
            assert canvas_state_bridge.set_node_property_calls == [
                ("node_surface_contract_test", "message", "updated through split bridges")
            ]

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )
