from __future__ import annotations

from tests.graph_surface.environment import *  # noqa: F403

class PassiveGraphSurfaceHostBoundaryTests(PassiveGraphSurfaceHostTestBase):
    def test_graph_node_host_routes_theme_and_layout_derivations_through_split_helpers(self) -> None:
        host_text = (_REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml").read_text(encoding="utf-8")
        theme_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml"
        ).read_text(encoding="utf-8")
        layout_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostLayout.qml"
        ).read_text(encoding="utf-8")
        render_quality_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostRenderQuality.qml"
        ).read_text(encoding="utf-8")
        scene_access_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostSceneAccess.qml"
        ).read_text(encoding="utf-8")
        interaction_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph/GraphNodeHostInteractionState.qml"
        ).read_text(encoding="utf-8")

        self.assertIn("GraphNodeHostTheme {", host_text)
        self.assertIn("GraphNodeHostLayout {", host_text)
        self.assertIn("GraphNodeHostRenderQuality {", host_text)
        self.assertIn("GraphNodeHostSceneAccess {", host_text)
        self.assertIn("GraphNodeHostInteractionState {", host_text)
        self.assertIn("readonly property color surfaceColor: themeState.surfaceColor", host_text)
        self.assertIn("readonly property bool _useHostChrome: chromeLayout.useHostChrome", host_text)
        self.assertIn("readonly property var renderQuality: renderQualityState.renderQuality", host_text)
        self.assertIn("return sceneAccess.localPortPoint(direction, rowIndex);", host_text)
        self.assertIn("return interactionState.requestInlineTitleEditAt(localX, localY);", host_text)
        self.assertIn("readonly property color surfaceColor:", theme_text)
        self.assertIn("readonly property bool useHostChrome:", layout_text)
        self.assertIn("readonly property string chromeShadowCacheKey:", layout_text)
        self.assertIn('readonly property string resolvedQualityTier:', render_quality_text)
        self.assertIn("function localPortPoint(direction, rowIndex) {", scene_access_text)
        self.assertIn("function pointInEmbeddedInteractiveRect(localX, localY) {", interaction_text)

    def test_graph_node_host_loads_standard_surface_for_standard_nodes(self) -> None:
        self._run_qml_probe(
            "standard-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            assert host.objectName() == "graphNodeCard"
            assert host.property("surfaceFamily") == "standard"
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "standard"
            assert host.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_node_host_falls_back_to_standard_surface_for_unknown_family(self) -> None:
        self._run_qml_probe(
            "fallback-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": node_payload(surface_family="mystery", surface_variant="sticky_note")},
            )
            assert host.property("surfaceFamily") == "mystery"
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "standard"
            assert host.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_node_host_uses_curve_rendering_for_node_text(self) -> None:
        self._run_qml_probe(
            "curve-rendering-host",
            """
            standard_host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            expected_render_type = standard_host.property("nodeTextRenderType")
            title_item = standard_host.findChild(QObject, "graphNodeTitle")
            input_labels = named_child_items(standard_host, "graphNodeInputPortLabel")
            assert title_item is not None
            assert len(input_labels) >= 1
            assert title_item.property("effectiveRenderType") == expected_render_type
            assert input_labels[0].property("effectiveRenderType") == expected_render_type

            annotation_payload = node_payload(surface_family="annotation", surface_variant="sticky_note")
            annotation_payload["runtime_behavior"] = "passive"
            annotation_payload["properties"] = {"body": "Sticky note"}
            annotation_host = create_component(graph_node_host_qml_path, {"nodeData": annotation_payload})
            annotation_text = annotation_host.findChild(QObject, "graphNodeAnnotationBodyText")
            assert annotation_text is not None
            assert annotation_text.property("effectiveRenderType") == annotation_host.property("nodeTextRenderType")

            planning_payload = node_payload(surface_family="planning", surface_variant="task_card")
            planning_payload["runtime_behavior"] = "passive"
            planning_payload["properties"] = {
                "body": "Follow up with render pass",
                "status": "in progress",
                "owner": "Alex",
                "due_date": "Tomorrow",
            }
            planning_host = create_component(graph_node_host_qml_path, {"nodeData": planning_payload})
            planning_text = planning_host.findChild(QObject, "graphNodePlanningBodyText")
            assert planning_text is not None
            assert planning_text.property("effectiveRenderType") == planning_host.property("nodeTextRenderType")

            media_payload = node_payload(surface_family="media", surface_variant="image_panel")
            media_payload["runtime_behavior"] = "passive"
            media_payload["properties"] = {"caption": "Preview caption"}
            media_host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
            caption_text = media_host.findChild(QObject, "graphNodeMediaCaption")
            assert caption_text is not None
            assert caption_text.property("effectiveRenderType") == media_host.property("nodeTextRenderType")
            """,
        )

    def test_graph_node_host_exposes_split_helper_layers_with_stable_stacking(self) -> None:
        self._run_qml_probe(
            "host-split-helper-layers",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            header_layer = host.findChild(QObject, "graphNodeHeaderLayer")
            gesture_layer = host.findChild(QObject, "graphNodeHostGestureLayer")
            ports_layer = host.findChild(QObject, "graphNodePortsLayer")
            resize_handles = named_child_items(host, "graphNodeResizeHandle")
            drag_area = host.findChild(QObject, "graphNodeDragArea")
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")

            assert background_layer is not None
            assert header_layer is not None
            assert gesture_layer is not None
            assert ports_layer is not None
            assert len(resize_handles) == 4
            assert {str(handle.property("cornerRole")) for handle in resize_handles} == {
                "topLeft",
                "topRight",
                "bottomLeft",
                "bottomRight",
            }
            assert loader is not None
            assert drag_area is not None
            assert drag_area.parentItem().objectName() == "graphNodeHostGestureLayer"

            surface_layer = loader.parentItem()
            assert surface_layer is not None
            assert float(background_layer.property("z")) < float(surface_layer.property("z"))
            assert float(gesture_layer.property("z")) < float(surface_layer.property("z"))
            assert float(header_layer.property("z")) > float(surface_layer.property("z"))
            assert float(ports_layer.property("z")) > float(header_layer.property("z"))
            assert all(float(handle.property("z")) > float(ports_layer.property("z")) for handle in resize_handles)
            """,
        )

    def test_graph_node_host_keeps_bottom_corner_resize_targets_clear_of_nearby_ports(self) -> None:
        self._run_qml_probe(
            "host-bottom-corner-resize-clearance",
            """
            payload = node_payload()
            payload["ports"] = [
                {
                    "key": "exec_in",
                    "label": "Exec In",
                    "direction": "in",
                    "kind": "exec",
                    "data_type": "exec",
                    "connected": False,
                },
                {
                    "key": "message",
                    "label": "Message",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "str",
                    "connected": False,
                    "allow_multiple_connections": False,
                },
                {
                    "key": "exec_out",
                    "label": "Exec Out",
                    "direction": "out",
                    "kind": "exec",
                    "data_type": "exec",
                    "connected": False,
                },
                {
                    "key": "result",
                    "label": "Result",
                    "direction": "out",
                    "kind": "data",
                    "data_type": "str",
                    "connected": False,
                    "allow_multiple_connections": False,
                },
            ]
            payload["inline_properties"] = [
                {
                    "key": "message",
                    "label": "Message",
                    "inline_editor": "text",
                    "value": "log message",
                    "overridden_by_input": False,
                    "input_port_label": "message",
                }
            ]

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            handles = named_child_items(host, "graphNodeResizeHandle")
            assert len(handles) == 4
            bottom_left_handle = next(handle for handle in handles if str(handle.property("cornerRole")) == "bottomLeft")
            bottom_right_handle = next(
                handle for handle in handles if str(handle.property("cornerRole")) == "bottomRight"
            )
            bottom_left_area = bottom_left_handle.findChild(QObject, "graphNodeResizeDragArea")
            bottom_right_area = bottom_right_handle.findChild(QObject, "graphNodeResizeDragArea")
            input_mouse = named_item(host, "graphNodeInputPortMouseArea", "message")
            output_mouse = max(
                named_child_items(host, "graphNodeOutputPortMouseArea"),
                key=lambda item: item.mapToScene(QPointF(item.width() * 0.5, item.height() * 0.5)).y(),
            )

            assert bottom_left_area is not None
            assert bottom_right_area is not None
            assert float(bottom_left_area.width()) < float(bottom_left_handle.width())
            assert float(bottom_right_area.width()) < float(bottom_right_handle.width())

            window = attach_host_to_window(host, 520, 320)
            hover_host_local_point(window, host, host.width() * 0.5, host.height() * 0.5)

            assert bool(bottom_left_handle.property("visible")) is True
            assert bool(bottom_right_handle.property("visible")) is True

            input_center_in_host = input_mouse.mapToItem(
                host,
                QPointF(input_mouse.width() * 0.5, input_mouse.height() * 0.5),
            )
            output_center_in_host = output_mouse.mapToItem(
                host,
                QPointF(output_mouse.width() * 0.5, output_mouse.height() * 0.5),
            )

            assert host._isResizeHandlePoint(float(input_center_in_host.x()), float(input_center_in_host.y())) is False
            assert host._isResizeHandlePoint(float(output_center_in_host.x()), float(output_center_in_host.y())) is False
            assert host._isResizeHandlePoint(1.0, float(host.height()) - 1.0) is True
            assert host._isResizeHandlePoint(float(host.width()) - 1.0, float(host.height()) - 1.0) is True
            assert host._isResizeHandlePoint(8.0, float(host.height()) - 9.0) is False
            assert host._isResizeHandlePoint(float(host.width()) - 8.0, float(host.height()) - 9.0) is False

            clicked_ports = []
            preview_events = []
            host.portClicked.connect(
                lambda node_id, port_key, direction, scene_x, scene_y: clicked_ports.append((port_key, direction))
            )
            host.resizePreviewChanged.connect(
                lambda node_id, x, y, width, height, active: preview_events.append(active)
            )

            mouse_click(window, item_scene_point(input_mouse))
            mouse_click(window, item_scene_point(output_mouse))

            assert ("message", "in") in clicked_ports
            assert ("result", "out") in clicked_ports
            assert preview_events == []
            """,
        )

    def test_node_card_wrapper_preserves_standard_host_contract(self) -> None:
        self._run_qml_probe(
            "node-card-wrapper",
            """
            node_card = create_component(
                node_card_qml_path,
                {"nodeData": node_payload(surface_family="annotation", surface_variant="sticky_note")},
            )
            assert node_card.objectName() == "graphNodeCard"
            assert node_card.property("surfaceFamily") == "standard"
            assert node_card.findChild(QObject, "graphNodeSurfaceLoader") is not None
            assert node_card.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_canvas_keeps_graph_node_card_discoverability_through_host_delegate(self) -> None:
        self._run_qml_probe(
            "graph-canvas-host",
            """
            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) >= 1
            assert node_cards[0].findChild(QObject, "graphNodeStandardSurface") is not None
            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

class GraphSurfaceBoundaryContractTests(GraphSurfaceInputContractTestBase):
    def test_passive_graph_surface_host_entrypoint_stays_packetized_and_under_200_lines(self) -> None:
        entrypoint_path = _REPO_ROOT / "tests" / "test_passive_graph_surface_host.py"
        entrypoint_text = entrypoint_path.read_text(encoding="utf-8")
        entrypoint_lines = entrypoint_text.splitlines()

        self.assertLessEqual(len(entrypoint_lines), 200)
        self.assertIn("from tests.graph_surface import (", entrypoint_text)
        self.assertIn("PassiveGraphSurfaceHostBoundaryTests", entrypoint_text)
        self.assertIn("PassiveGraphSurfaceHostTests", entrypoint_text)
        self.assertIn("PassiveGraphSurfaceInlineEditorTests", entrypoint_text)
        self.assertIn("PassiveGraphSurfaceMediaAndScopeTests", entrypoint_text)
        self.assertNotIn("def _run_qml_probe(", entrypoint_text)

    def test_graph_surface_input_contract_entrypoint_stays_packetized_and_under_200_lines(self) -> None:
        entrypoint_path = _REPO_ROOT / "tests" / "test_graph_surface_input_contract.py"
        entrypoint_text = entrypoint_path.read_text(encoding="utf-8")
        entrypoint_lines = entrypoint_text.splitlines()

        self.assertLessEqual(len(entrypoint_lines), 200)
        self.assertIn("from tests.graph_surface import (", entrypoint_text)
        self.assertIn("GraphSurfaceBoundaryContractTests", entrypoint_text)
        self.assertIn("GraphSurfaceInputContractTests", entrypoint_text)
        self.assertIn("GraphSurfaceInlineEditorContractTests", entrypoint_text)
        self.assertIn("GraphSurfaceMediaAndScopeContractTests", entrypoint_text)
        self.assertNotIn("def _run_qml_probe(", entrypoint_text)

    def test_graph_canvas_root_packetization_keeps_helper_split_and_stable_public_contract(self) -> None:
        graph_canvas_path = _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "GraphCanvas.qml"
        root_bindings_path = graph_canvas_path.parent / "graph_canvas" / "GraphCanvasRootBindings.qml"
        root_layers_path = graph_canvas_path.parent / "graph_canvas" / "GraphCanvasRootLayers.qml"
        root_api_path = graph_canvas_path.parent / "graph_canvas" / "GraphCanvasRootApi.js"

        graph_canvas_lines = graph_canvas_path.read_text(encoding="utf-8").splitlines()
        graph_canvas_text = "\n".join(graph_canvas_lines)
        root_layers_text = root_layers_path.read_text(encoding="utf-8")
        root_api_text = root_api_path.read_text(encoding="utf-8")

        self.assertLessEqual(len(graph_canvas_lines), 700)
        self.assertTrue(root_bindings_path.exists())
        self.assertTrue(root_layers_path.exists())
        self.assertTrue(root_api_path.exists())

        for snippet in (
            'import "graph_canvas/GraphCanvasRootApi.js" as GraphCanvasRootApi',
            "GraphCanvasComponents.GraphCanvasRootBindings {",
            "GraphCanvasComponents.GraphCanvasRootLayers {",
            "function toggleMinimapExpanded() {",
            "function clearLibraryDropPreview() {",
            "function updateLibraryDropPreview(screenX, screenY, payload) {",
            "function isPointInCanvas(screenX, screenY) {",
            "function performLibraryDrop(screenX, screenY, payload) {",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, graph_canvas_text)

        for snippet in (
            "GraphCanvasBackground {",
            "GraphComponents.EdgeLayer {",
            "GraphCanvasMinimapOverlay {",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, root_layers_text)

        for snippet in (
            "function invoke(target, methodName, args, fallbackValue) {",
            "function snapToGridValue(canvasStateBridge, value) {",
            "function clampMenuPosition(canvasItem, x, y, menuWidth, menuHeight) {",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, root_api_text)

    def test_graph_scene_payload_builder_publishes_normalized_render_quality_metadata(self) -> None:
        registry: NodeRegistry = build_default_registry()
        spec = NodeTypeSpec(
            type_id="tests.render_quality_payload",
            display_name="Render Quality Payload",
            category_path=("Tests",),
            icon="",
            ports=(),
            properties=(),
            render_quality={
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            },  # type: ignore[arg-type]
        )
        registry.register(lambda: _RenderQualityPayloadPlugin(spec))

        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(
            workspace_id,
            spec.type_id,
            spec.display_name,
            80.0,
            120.0,
        )

        builder = GraphScenePayloadBuilder()
        nodes_payload, _minimap_payload, _edges_payload = builder.rebuild_models(
            model=model,
            registry=registry,
            workspace_id=workspace_id,
            scope_path=(),
            graph_theme_bridge=None,
        )

        payload = next(item for item in nodes_payload if item["type_id"] == spec.type_id)
        self.assertEqual(
            payload["render_quality"],
            {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            },
        )

    def test_graph_scene_payload_builder_orders_exec_ports_first_within_each_side(self) -> None:
        registry: NodeRegistry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(
            workspace_id,
            "io.excel_read",
            "Excel Read",
            80.0,
            120.0,
        )
        model.add_node(
            workspace_id,
            "io.excel_write",
            "Excel Write",
            280.0,
            120.0,
        )

        builder = GraphScenePayloadBuilder()
        nodes_payload, _minimap_payload, _edges_payload = builder.rebuild_models(
            model=model,
            registry=registry,
            workspace_id=workspace_id,
            scope_path=(),
            graph_theme_bridge=None,
        )

        payloads_by_type = {str(item["type_id"]): item for item in nodes_payload}

        excel_read_ports = payloads_by_type["io.excel_read"]["ports"]
        excel_read_output_keys = [
            str(port["key"])
            for port in excel_read_ports
            if str(port["direction"]) == "out"
        ]
        self.assertEqual(excel_read_output_keys, ["exec_out", "rows"])

        excel_write_ports = payloads_by_type["io.excel_write"]["ports"]
        excel_write_input_keys = [
            str(port["key"])
            for port in excel_write_ports
            if str(port["direction"]) == "in"
        ]
        excel_write_output_keys = [
            str(port["key"])
            for port in excel_write_ports
            if str(port["direction"]) == "out"
        ]
        self.assertEqual(excel_write_input_keys, ["exec_in", "rows", "path"])
        self.assertEqual(excel_write_output_keys, ["exec_out", "written_path"])

    def test_graph_scene_payload_builder_projects_locked_and_optional_ports_and_applies_active_view_filters(self) -> None:
        registry: NodeRegistry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        workspace = model.project.workspaces[workspace_id]
        logger = model.validated_mutations(workspace_id, registry).add_node(
            type_id="core.logger",
            title="Logger",
            x=80.0,
            y=120.0,
        )

        builder = GraphScenePayloadBuilder()

        def _logger_ports() -> list[dict[str, object]]:
            nodes_payload, _minimap_payload, _edges_payload = builder.rebuild_models(
                model=model,
                registry=registry,
                workspace_id=workspace_id,
                scope_path=(),
                graph_theme_bridge=None,
            )
            payload = next(item for item in nodes_payload if item["node_id"] == logger.node_id)
            return payload["ports"]

        ports_by_key = {str(port["key"]): port for port in _logger_ports()}
        self.assertTrue(bool(ports_by_key["message"]["locked"]))
        self.assertTrue(bool(ports_by_key["message"]["lockable"]))
        self.assertTrue(bool(ports_by_key["message"]["optional"]))
        self.assertFalse(bool(ports_by_key["exec_in"]["locked"]))
        self.assertFalse(bool(ports_by_key["exec_in"]["lockable"]))
        self.assertFalse(bool(ports_by_key["exec_in"]["optional"]))

        active_view = workspace.views[workspace.active_view_id]
        active_view.hide_locked_ports = True
        hidden_locked_keys = {str(port["key"]) for port in _logger_ports()}
        self.assertEqual(hidden_locked_keys, {"exec_in", "exec_out"})

        active_view.hide_locked_ports = False
        active_view.hide_optional_ports = True
        hidden_optional_keys = [str(port["key"]) for port in _logger_ports()]
        self.assertEqual(hidden_optional_keys, ["exec_in"])

    def test_graph_node_host_render_quality_contract_exposes_reduced_quality_tier(self) -> None:
        self._run_qml_probe(
            "host-render-quality-contract",
            """
            payload = node_payload()
            payload["render_quality"] = {
                "weight_class": "heavy",
                "max_performance_strategy": "generic_fallback",
                "supported_quality_tiers": ["full", "reduced"],
            }

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                    "shadowSimplificationActive": True,
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeStandardSurface")
            assert loader is not None
            assert surface is not None

            render_quality = variant_value(host.property("renderQuality"))
            loader_render_quality = variant_value(loader.property("renderQuality"))
            context = variant_value(host.property("surfaceQualityContext"))
            loader_context = variant_value(loader.property("surfaceQualityContext"))

            assert render_quality == {
                "weight_class": "heavy",
                "max_performance_strategy": "generic_fallback",
                "supported_quality_tiers": ["full", "reduced"],
            }
            assert loader_render_quality == render_quality
            assert host.property("requestedQualityTier") == "reduced"
            assert host.property("resolvedQualityTier") == "reduced"
            assert not bool(host.property("proxySurfaceRequested"))
            assert loader.property("requestedQualityTier") == "reduced"
            assert loader.property("resolvedQualityTier") == "reduced"
            assert not bool(loader.property("proxySurfaceRequested"))
            assert not bool(loader.property("proxySurfaceActive"))
            assert context["requested_quality_tier"] == "reduced"
            assert context["resolved_quality_tier"] == "reduced"
            assert not bool(context["proxy_surface_requested"])
            assert loader_context["resolved_quality_tier"] == "reduced"
            assert surface.property("host").property("resolvedQualityTier") == "reduced"
            """,
        )

    def test_graph_scene_bridge_exposes_set_node_property_as_qml_slot(self) -> None:
        from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

        bridge = GraphSceneBridge()
        meta_object = bridge.metaObject()
        for signature in (
            b"set_node_property(QString,QString,QVariant)",
            b"set_port_locked(QString,QString,bool)",
            b"set_hide_locked_ports(bool)",
            b"set_hide_optional_ports(bool)",
        ):
            with self.subTest(signature=signature):
                self.assertGreaterEqual(meta_object.indexOfMethod(signature), 0)
