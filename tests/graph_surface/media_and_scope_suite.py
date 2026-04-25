from __future__ import annotations

from tests.graph_surface.environment import *  # noqa: F403

class PassiveGraphSurfaceMediaAndScopeTests(PassiveGraphSurfaceHostTestBase):
    def test_scope_capable_nodes_publish_open_badge_hit_region_and_keep_title_double_click_for_editing(self) -> None:
        self._run_qml_probe(
            "shared-header-title-rollout-scope-open-badge",
            """
            payload = node_payload()
            payload["can_enter_scope"] = True

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            window = attach_host_to_window(host, width=640, height=480)
            try:
                header = host.findChild(QObject, "graphNodeHeaderLayer")
                title_item = host.findChild(QObject, "graphNodeTitle")
                editor = host.findChild(QObject, "graphNodeTitleEditor")
                open_badge = host.findChild(QObject, "graphNodeOpenBadge")
                assert header is not None
                assert title_item is not None
                assert editor is not None
                assert open_badge is not None
                assert bool(host.property("sharedHeaderTitleEditable"))

                embedded_rects = variant_list(header.property("embeddedInteractiveRects"))
                assert len(embedded_rects) == 1
                badge_rect = embedded_rects[0]
                badge_local_point = open_badge.mapToItem(
                    host,
                    QPointF(float(open_badge.width()) * 0.5, float(open_badge.height()) * 0.5),
                )
                badge_local_x = float(badge_local_point.x())
                badge_local_y = float(badge_local_point.y())
                assert rect_field(badge_rect, "x") <= badge_local_x <= (
                    rect_field(badge_rect, "x") + rect_field(badge_rect, "width")
                )
                assert rect_field(badge_rect, "y") <= badge_local_y <= (
                    rect_field(badge_rect, "y") + rect_field(badge_rect, "height")
                )

                committed = []
                events = host_pointer_events(host)
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )
                mouse_double_click(window, item_scene_point(title_item))
                settle_events(5)

                assert bool(editor.property("visible"))
                assert events["opened"] == []

                editor.setProperty("text", " Scoped Logger ")
                app.processEvents()
                events["clicked"].clear()
                events["opened"].clear()
                events["contexts"].clear()

                mouse_click(window, item_scene_point(open_badge))
                settle_events(5)

                assert committed == [("node_surface_host_test", "title", "Scoped Logger")]
                assert events["clicked"] == []
                assert events["opened"] == ["node_surface_host_test"]
                assert events["contexts"] == []
                assert not bool(editor.property("visible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_media_host_proxy_surface_activates_when_ready_image_enters_proxy_quality_tier(self) -> None:
        self._run_qml_probe(
            "media-render-quality-proxy-surface",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage

            media_payload = node_payload(surface_family="media", surface_variant="image_panel")
            media_payload["runtime_behavior"] = "passive"
            media_payload["type_id"] = "passive.media.image_panel"
            media_payload["title"] = "Image Panel"
            media_payload["width"] = 296.0
            media_payload["height"] = 236.0
            media_payload["surface_metrics"] = {
                "body_height": 180.0,
            }
            media_payload["ports"] = []
            media_payload["inline_properties"] = []
            media_payload["render_quality"] = {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            }

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "proxy-image.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "Proxy seam",
                    "fit_mode": "contain",
                }

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": media_payload,
                        "snapshotReuseActive": True,
                        "shadowSimplificationActive": True,
                    },
                )
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = host.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = host.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None

                for _index in range(50):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break

                render_quality = variant_value(host.property("renderQuality"))
                context = variant_value(host.property("surfaceQualityContext"))

                assert surface.property("previewState") == "ready"
                assert render_quality == {
                    "weight_class": "heavy",
                    "max_performance_strategy": "proxy_surface",
                    "supported_quality_tiers": ["full", "proxy"],
                }
                assert host.property("requestedQualityTier") == "reduced"
                assert host.property("resolvedQualityTier") == "proxy"
                assert bool(host.property("proxySurfaceRequested"))
                assert loader.property("requestedQualityTier") == "reduced"
                assert loader.property("resolvedQualityTier") == "proxy"
                assert bool(loader.property("proxySurfaceRequested"))
                assert bool(loader.property("proxySurfaceActive"))
                assert bool(proxy_preview.property("visible"))
                assert not bool(applied_viewport.property("visible"))
                assert context["resolved_quality_tier"] == "proxy"
                assert bool(context["proxy_surface_requested"])
                assert bool(surface.property("proxySurfaceActive"))
                assert surface.property("host").property("resolvedQualityTier") == "proxy"
                assert loader.property("loadedSurfaceKey") == "media"
            """,
        )

    def test_media_crop_mode_locks_host_drag_resize_and_ports(self) -> None:
        self._run_qml_probe(
            "media-host-lock",
            """
            import tempfile
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-lock.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                assert surface is not None
                assert loader is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break

                surface.setProperty("cropModeActive", True)
                app.processEvents()

                drag_area = host.findChild(QObject, "graphNodeDragArea")
                resize_area = host.findChild(QObject, "graphNodeResizeDragArea")
                input_areas = named_child_items(host, "graphNodeInputPortMouseArea")
                output_areas = named_child_items(host, "graphNodeOutputPortMouseArea")
                embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))

                assert bool(host.property("surfaceInteractionLocked"))
                assert bool(loader.property("blocksHostInteraction"))
                assert host.findChild(QObject, "graphNodeSurfaceHoverActionButton") is None
                assert len(embedded_rects) == 10
                assert drag_area is not None
                assert resize_area is not None
                assert not bool(drag_area.property("enabled"))
                assert not bool(resize_area.property("enabled"))
                assert len(input_areas) >= 1
                assert len(output_areas) >= 1
                assert not bool(input_areas[0].property("enabled"))
                assert not bool(output_areas[0].property("enabled"))

                handle_areas = named_child_items(host, "graphNodeMediaCropHandleMouseArea")
                handle_lookup = {
                    str(item.property("handleId")): item
                    for item in handle_areas
                }
                assert len(handle_lookup) == 8
                assert float(handle_lookup["top_left"].property("width")) > 12.0
                assert float(handle_lookup["top_left"].property("height")) > 12.0
                assert handle_lookup["top_left"].property("cursorShape") == Qt.CursorShape.SizeFDiagCursor
                assert handle_lookup["top_right"].property("cursorShape") == Qt.CursorShape.SizeBDiagCursor
                assert handle_lookup["top"].property("cursorShape") == Qt.CursorShape.SizeVerCursor
                assert handle_lookup["left"].property("cursorShape") == Qt.CursorShape.SizeHorCursor
            """,
        )

    def test_media_surface_publishes_crop_and_fullscreen_actions_without_inline_buttons(self) -> None:
        self._run_qml_probe(
            "media-surface-actions-crop-fullscreen",
            """
            import tempfile
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-hover-action.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                assert surface is not None
                assert loader is not None
                assert host.findChild(QObject, "graphNodeMediaCropButton") is None
                assert host.findChild(QObject, "graphNodeMediaFullscreenButton") is None
                assert host.findChild(QObject, "graphNodeMediaRepairButton") is None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                window = attach_host_to_window(host)

                hover_host_local_point(window, host, 80.0, 44.0)

                embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))

                assert host.findChild(QObject, "graphNodeSurfaceHoverActionButton") is None
                assert loader.metaObject().indexOfProperty("hoverActionHitRect") == -1
                assert surface.metaObject().indexOfProperty("hoverActionHitRect") == -1
                assert embedded_rects == []

                surface_actions = variant_list(surface.property("surfaceActions"))
                action_ids = [action["id"] for action in surface_actions]
                assert action_ids == ["crop", "fullscreen", "repair"]
                crop_action = next(action for action in surface_actions if action["id"] == "crop")
                fullscreen_action = next(action for action in surface_actions if action["id"] == "fullscreen")
                repair_action = next(action for action in surface_actions if action["id"] == "repair")
                assert bool(crop_action["enabled"])
                assert not bool(fullscreen_action["enabled"])
                assert not bool(repair_action["enabled"])

                loader_actions = variant_list(loader.property("surfaceActions"))
                assert [action["id"] for action in loader_actions] == ["crop", "fullscreen", "repair"]

                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_media_surface_fullscreen_action_routes_bridge_without_crop_mode(self) -> None:
        self._run_qml_probe(
            "media-surface-fullscreen-action",
            """
            import tempfile
            from PyQt6.QtCore import Q_ARG
            from PyQt6.QtGui import QColor, QImage

            class ContentFullscreenBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.toggle_calls = []

                @pyqtSlot(str, result=bool)
                def request_toggle_for_node(self, node_id):
                    self.toggle_calls.append(str(node_id or ""))
                    return True

            bridge = ContentFullscreenBridgeStub()
            engine.rootContext().setContextProperty("contentFullscreenBridge", bridge)

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-fullscreen.png"
                image = QImage(32, 20, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                assert surface is not None
                assert loader is not None
                assert host.findChild(QObject, "graphNodeMediaFullscreenButton") is None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                window = attach_host_to_window(host)
                hover_host_local_point(window, host, 80.0, 44.0)

                def fullscreen_action():
                    return next(
                        action
                        for action in variant_list(surface.property("surfaceActions"))
                        if action["id"] == "fullscreen"
                    )

                assert bool(fullscreen_action()["enabled"])

                QMetaObject.invokeMethod(
                    surface,
                    "dispatchSurfaceAction",
                    Q_ARG("QVariant", "fullscreen"),
                )
                app.processEvents()
                assert bridge.toggle_calls == ["node_surface_host_test"]

                surface.setProperty("cropModeActive", True)
                app.processEvents()
                assert not bool(fullscreen_action()["enabled"])

                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_media_surface_routes_crop_actions_through_canvas_contract(self) -> None:
        self._run_qml_probe(
            "media-canvas-contract",
            """
            import tempfile
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-contract.png"
                image = QImage(40, 20, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                canvas_item = create_surface_canvas_item()
                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": media_payload,
                        "canvasItem": canvas_item,
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                apply_button = host.findChild(QObject, "graphNodeMediaCropApplyButton")
                assert surface is not None
                assert apply_button is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                QMetaObject.invokeMethod(surface, "triggerHoverAction")
                app.processEvents()

                assert canvas_item.requested_crop_node_id == "node_surface_host_test"
                assert bool(surface.property("cropModeActive"))

                surface.setProperty("draftCropX", 0.1)
                surface.setProperty("draftCropY", 0.2)
                surface.setProperty("draftCropW", 0.5)
                surface.setProperty("draftCropH", 0.6)
                app.processEvents()

                QMetaObject.invokeMethod(apply_button, "click")
                app.processEvents()

                assert canvas_item.last_committed_node_id == "node_surface_host_test"
                assert abs(float(canvas_item.last_committed_properties["crop_x"]) - 0.1) < 1e-6
                assert abs(float(canvas_item.last_committed_properties["crop_y"]) - 0.2) < 1e-6
                assert abs(float(canvas_item.last_committed_properties["crop_w"]) - 0.5) < 1e-6
                assert abs(float(canvas_item.last_committed_properties["crop_h"]) - 0.6) < 1e-6
                assert not bool(surface.property("cropModeActive"))
            """,
        )

    def test_media_surface_repair_action_relinks_missing_source_through_canvas_contract(self) -> None:
        self._run_qml_probe(
            "media-repair-contract",
            """
            import tempfile

            from PyQt6.QtCore import Q_ARG
            from PyQt6.QtGui import QColor, QImage
            from PyQt6.QtQuick import QQuickItem

            class RepairCanvasItem(QQuickItem):
                def __init__(self, repaired_path):
                    super().__init__()
                    self.repaired_path = str(repaired_path)
                    self.last_browse_args = None

                @pyqtSlot(str, str, str, result=str)
                def browseNodePropertyPath(self, node_id, key, current_path):
                    self.last_browse_args = (
                        str(node_id),
                        str(key),
                        str(current_path),
                    )
                    return self.repaired_path

            with tempfile.TemporaryDirectory() as temp_dir:
                missing_path = Path(temp_dir) / "missing.png"
                repaired_path = Path(temp_dir) / "repaired.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(repaired_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(missing_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                canvas_item = RepairCanvasItem(repaired_path)
                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": media_payload,
                        "canvasItem": canvas_item,
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                issue_badge = host.findChild(QObject, "graphNodeMediaIssueBadge")
                assert surface is not None
                assert issue_badge is not None
                assert host.findChild(QObject, "graphNodeMediaRepairButton") is None

                committed = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: committed.append((node_id, key, variant_value(value)))
                )

                assert str(surface.property("previewState")) == "error"
                assert bool(issue_badge.property("visible"))

                repair_action = next(
                    action
                    for action in variant_list(surface.property("surfaceActions"))
                    if action["id"] == "repair"
                )
                assert bool(repair_action["enabled"])

                QMetaObject.invokeMethod(
                    surface,
                    "dispatchSurfaceAction",
                    Q_ARG("QVariant", "repair"),
                )
                app.processEvents()

                assert canvas_item.last_browse_args is not None
                assert canvas_item.last_browse_args[0] == "node_surface_host_test"
                assert canvas_item.last_browse_args[1] == "source_path"
                assert canvas_item.last_browse_args[2].startswith("ea-file-repair:")
                assert committed == [("node_surface_host_test", "source_path", str(repaired_path))]
            """,
        )

    def test_media_surface_accepts_managed_source_refs_in_qml_preview_binding(self) -> None:
        self._run_qml_probe(
            "media-managed-source",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage

            from ea_node_editor.persistence.artifact_refs import format_managed_artifact_ref
            from ea_node_editor.ui.media_preview_provider import set_media_preview_project_context_provider

            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir) / "artifact_demo.sfe"
                managed_image_path = project_path.with_name("artifact_demo.data") / "assets" / "media" / "managed.png"
                managed_image_path.parent.mkdir(parents=True, exist_ok=True)
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(managed_image_path))

                set_media_preview_project_context_provider(
                    lambda: (
                        project_path,
                        {
                            "artifact_store": {
                                "artifacts": {
                                    "managed_image": {"relative_path": "assets/media/managed.png"},
                                }
                            }
                        },
                    )
                )

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": format_managed_artifact_ref("managed_image"),
                    "caption": "",
                    "fit_mode": "contain",
                }
                host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                assert surface is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break

                assert str(surface.property("previewState")) == "ready"
                assert not bool(surface.property("sourceRejected"))
                assert str(surface.property("previewSourceUrl")).startswith("image://local-media-preview/")
                assert "artifact%3A%2F%2Fmanaged_image" in str(surface.property("previewSourceUrl"))
                assert float(surface.property("sourcePixelWidth")) == 24.0
                assert float(surface.property("sourcePixelHeight")) == 18.0
            """,
        )

class GraphSurfaceMediaAndScopeContractTests(GraphSurfaceInputContractTestBase):
    def test_graph_node_host_accepts_viewer_surface_family_without_canvas_special_cases(self) -> None:
        self._run_qml_probe(
            "viewer-surface-family-contract",
            """
            payload = node_payload(surface_family="viewer")
            payload["type_id"] = "tests.viewer_surface_contract"
            payload["title"] = "Viewer Contract"
            payload["width"] = 296.0
            payload["height"] = 236.0
            payload["ports"] = [
                {
                    "key": "fields",
                    "label": "Fields",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "dpf_field",
                    "connected": False,
                },
                {
                    "key": "session",
                    "label": "Session",
                    "direction": "out",
                    "kind": "data",
                    "data_type": "dpf_view_session",
                    "connected": False,
                },
            ]
            payload["inline_properties"] = []
            payload["render_quality"] = {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            }
            payload["surface_metrics"] = {
                "default_width": 296.0,
                "default_height": 236.0,
                "min_width": 220.0,
                "min_height": 208.0,
                "collapsed_width": 130.0,
                "collapsed_height": 36.0,
                "header_height": 24.0,
                "header_top_margin": 4.0,
                "body_left_margin": 14.0,
                "body_right_margin": 14.0,
                "body_top": 30.0,
                "body_height": 176.0,
                "body_bottom_margin": 12.0,
                "port_top": 206.0,
                "port_height": 18.0,
                "port_center_offset": 6.0,
                "port_side_margin": 8.0,
                "port_dot_radius": 3.5,
                "resize_handle_size": 16.0,
                "title_top": 4.0,
                "title_height": 24.0,
                "title_left_margin": 10.0,
                "title_right_margin": 42.0,
                "title_centered": False,
                "show_header_background": True,
                "show_accent_bar": True,
                "use_host_chrome": True,
                "standard_title_full_width": 0.0,
                "standard_left_label_width": 0.0,
                "standard_right_label_width": 0.0,
                "standard_port_gutter": 21.5,
                "standard_center_gap": 24.0,
                "standard_port_label_min_width": 0.0,
            }
            payload["viewer_surface"] = {
                "body_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "proxy_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "live_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "overlay_target": "body",
                "proxy_surface_supported": True,
                "live_surface_supported": True,
            }

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "snapshotReuseActive": True,
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            assert loader is not None
            assert surface is not None

            assert host.property("surfaceFamily") == "viewer"
            assert loader.property("loadedSurfaceKey") == "viewer"
            assert host.property("requestedQualityTier") == "reduced"
            assert host.property("resolvedQualityTier") == "proxy"
            assert bool(surface.property("proxySurfaceActive"))

            contract = variant_value(loader.property("viewerSurfaceContract"))
            assert contract["overlay_target"] == "body"

            live_rect = loader.property("viewerLiveSurfaceRect")
            assert rect_field(live_rect, "x") == float(contract["live_rect"]["x"])
            assert rect_field(live_rect, "y") == float(contract["live_rect"]["y"])
            assert rect_field(live_rect, "width") == float(contract["live_rect"]["width"])
            assert rect_field(live_rect, "height") == float(contract["live_rect"]["height"])
            """,
        )

    def test_viewer_surface_control_rects_flow_through_host_contract(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-contract",
            """
            from PyQt6.QtCore import pyqtSignal, pyqtSlot

            class ViewerSessionBridgeStub(QObject):
                sessions_changed = pyqtSignal()

                @staticmethod
                def _session_projection():
                    return {
                        "workspace_id": "ws_main",
                        "node_id": "node_surface_contract_test",
                        "session_id": "session::viewer-surface-pointer",
                        "phase": "open",
                        "request_id": "req::viewer-pointer",
                        "last_command": "open",
                        "last_error": "",
                        "live_mode": "proxy",
                        "playback_state": "paused",
                        "step_index": 1,
                        "live_policy": "focus_only",
                        "keep_live": False,
                        "cache_state": "proxy_ready",
                        "invalidated_reason": "",
                        "close_reason": "",
                        "data_refs": {},
                        "summary": {
                            "result_name": "Displacement",
                            "set_label": "Set 1",
                            "cache_state": "proxy_ready",
                        },
                        "options": {
                            "live_mode": "proxy",
                            "playback_state": "paused",
                            "step_index": 1,
                            "live_policy": "focus_only",
                            "keep_live": False,
                        },
                    }

                @pyqtProperty("QVariantList", notify=sessions_changed)
                def sessions_model(self):
                    return [self._session_projection()]

                @pyqtSlot(str, result="QVariantMap")
                def session_state(self, node_id):
                    if str(node_id or "") != "node_surface_contract_test":
                        return {}
                    return self._session_projection()

                @pyqtProperty(str, constant=True)
                def last_error(self):
                    return ""

            bridge = ViewerSessionBridgeStub()
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            payload = node_payload(surface_family="viewer")
            payload["type_id"] = "tests.viewer_surface_contract"
            payload["title"] = "Viewer Contract"
            payload["width"] = 296.0
            payload["height"] = 236.0
            payload["ports"] = [
                {
                    "key": "fields",
                    "label": "Fields",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "dpf_field",
                    "connected": False,
                },
                {
                    "key": "session",
                    "label": "Session",
                    "direction": "out",
                    "kind": "data",
                    "data_type": "dpf_view_session",
                    "connected": False,
                },
            ]
            payload["inline_properties"] = []
            payload["render_quality"] = {
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy"],
            }
            payload["surface_metrics"] = {
                "default_width": 296.0,
                "default_height": 236.0,
                "min_width": 220.0,
                "min_height": 208.0,
                "collapsed_width": 130.0,
                "collapsed_height": 36.0,
                "header_height": 24.0,
                "header_top_margin": 4.0,
                "body_left_margin": 14.0,
                "body_right_margin": 14.0,
                "body_top": 30.0,
                "body_height": 176.0,
                "body_bottom_margin": 12.0,
                "port_top": 206.0,
                "port_height": 18.0,
                "port_center_offset": 6.0,
                "port_side_margin": 8.0,
                "port_dot_radius": 3.5,
                "resize_handle_size": 16.0,
                "title_top": 4.0,
                "title_height": 24.0,
                "title_left_margin": 10.0,
                "title_right_margin": 42.0,
                "title_centered": False,
                "show_header_background": True,
                "show_accent_bar": True,
                "use_host_chrome": True,
                "standard_title_full_width": 0.0,
                "standard_left_label_width": 0.0,
                "standard_right_label_width": 0.0,
                "standard_port_gutter": 21.5,
                "standard_center_gap": 24.0,
                "standard_port_label_min_width": 0.0,
            }
            payload["viewer_surface"] = {
                "body_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "proxy_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "live_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "overlay_target": "body",
                "proxy_surface_supported": True,
                "live_surface_supported": True,
            }

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            assert loader is not None
            assert surface is not None

            bridge_binding = variant_value(host.property("viewerBridgeBinding"))
            contract = variant_value(host.property("viewerSurfaceContract"))
            control_rects = variant_list(host.property("viewerInteractiveRects"))
            surface_actions = variant_list(loader.property("surfaceActions"))
            assert bridge_binding["phase"] == "open", bridge_binding
            assert bridge_binding["live_mode"] == "proxy", bridge_binding
            assert contract["bridge_binding"]["phase"] == "open", contract
            assert control_rects == [], control_rects
            assert variant_list(loader.property("embeddedInteractiveRects")) == [], variant_list(loader.property("embeddedInteractiveRects"))
            assert contract["interactive_rects"] == [], contract
            assert [action["id"] for action in surface_actions] == ["openSession", "playPause", "step", "keepLive", "fullscreen"], surface_actions
            assert rect_field(host.property("viewerBodyRect"), "x") == float(contract["body_rect"]["x"]), variant_value(host.property("viewerBodyRect"))
            assert rect_field(host.property("viewerLiveSurfaceRect"), "width") == float(contract["live_rect"]["width"]), variant_value(host.property("viewerLiveSurfaceRect"))
            assert rect_field(host.property("viewerLiveSurfaceRect"), "height") == float(contract["live_rect"]["height"]), variant_value(host.property("viewerLiveSurfaceRect"))
            """,
        )

    def test_graph_canvas_routes_scoped_open_badge_through_request_open_subnode_scope(self) -> None:
        self._run_qml_probe(
            "graph-canvas-scoped-open-badge-route",
            """
            from PyQt6.QtCore import QObject, QPointF, pyqtProperty, pyqtSignal, pyqtSlot

            scoped_payload = node_payload()
            scoped_payload["can_enter_scope"] = True

            class SceneBridgeStub(QObject):
                nodes_changed = pyqtSignal()
                edges_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_property_calls = []
                    self._nodes_model = [scoped_payload]
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
                    self.scope_open_calls = []

                @pyqtSlot(str, result=bool)
                def request_open_subnode_scope(self, node_id):
                    self.scope_open_calls.append(str(node_id or ""))
                    return True

            class GraphActionBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.actions = []

                @pyqtSlot(str, "QVariantMap", result=bool)
                def trigger_graph_action(self, action_id, payload):
                    self.actions.append((str(action_id or ""), dict(payload or {})))
                    return True

            scene_bridge = SceneBridgeStub()
            window_bridge = MainWindowBridgeStub()
            graph_action_bridge = GraphActionBridgeStub()
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=window_bridge,
                scene_bridge=scene_bridge,
            )
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "graphActionBridge": graph_action_bridge,
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
                open_badge = node_card.findChild(QObject, "graphNodeOpenBadge")
                assert title_item is not None
                assert editor is not None
                assert open_badge is not None
                assert bool(node_card.property("sharedHeaderTitleEditable"))

                title_point = title_item.mapToItem(
                    node_card,
                    QPointF(float(title_item.width()) * 0.5, float(title_item.height()) * 0.5),
                )
                open_point = open_badge.mapToItem(
                    node_card,
                    QPointF(float(open_badge.width()) * 0.5, float(open_badge.height()) * 0.5),
                )

                assert not node_card.requestScopeOpenAt(title_point.x(), title_point.y())
                assert node_card.requestInlineTitleEditAt(title_point.x(), title_point.y())
                settle_events(5)

                assert bool(editor.property("visible"))
                assert scene_bridge.select_calls == [("node_surface_contract_test", False)]

                editor.setProperty("text", " Scoped Logger ")
                app.processEvents()
                assert node_card.requestScopeOpenAt(open_point.x(), open_point.y())
                settle_events(5)

                assert scene_bridge.set_node_property_calls == [
                    ("node_surface_contract_test", "title", "Scoped Logger")
                ]
                assert scene_bridge.select_calls == [
                    ("node_surface_contract_test", False),
                    ("node_surface_contract_test", False),
                ]
                assert graph_action_bridge.actions == [
                    ("enterScope", {"node_id": "node_surface_contract_test"})
                ]
                assert window_bridge.scope_open_calls == []
                assert not bool(editor.property("visible"))
            finally:
                canvas.deleteLater()
                app.processEvents()
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_media_whole_surface_lock_remains_independent_from_local_interactive_rects(self) -> None:
        self._run_qml_probe(
            "media-whole-surface-lock",
            """
            import tempfile
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-contract.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                drag_area = host.findChild(QObject, "graphNodeDragArea")
                assert surface is not None
                assert loader is not None
                assert drag_area is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                window = attach_host_to_window(host)
                hover_host_local_point(window, host, 80.0, 44.0)

                assert variant_list(loader.property("embeddedInteractiveRects")) == []
                assert not bool(loader.property("blocksHostInteraction"))
                assert bool(drag_area.property("enabled"))

                surface.setProperty("cropModeActive", True)
                app.processEvents()

                assert len(variant_list(loader.property("embeddedInteractiveRects"))) == 10
                assert bool(loader.property("blocksHostInteraction"))
                assert not bool(drag_area.property("enabled"))

                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_shell_window_browse_node_property_path_uses_explicit_node_id(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        test_env = ShellTestEnvironment()
        test_env.start()
        window = ShellWindow()
        try:
            window.app_preferences_controller.set_source_import_mode("external_link")
            image_node_id = window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
            logger_node_id = window.scene.add_node_from_type("core.logger", x=360.0, y=80.0)
            self.assertTrue(image_node_id)
            self.assertTrue(logger_node_id)
            app.processEvents()

            picked_path = str(_REPO_ROOT / "tests" / "fixtures" / "graph-surface-picked-path.png")
            with patch(
                "ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName",
                return_value=(picked_path, ""),
            ) as dialog_mock:
                self.assertEqual(window.browse_selected_node_property_path("source_path", ""), "")
                self.assertEqual(
                    window.browse_node_property_path(image_node_id, "source_path", ""),
                    picked_path,
                )
                self.assertEqual(dialog_mock.call_count, 1)

            self.assertEqual(window.browse_node_property_path(logger_node_id, "message", ""), "")
            self.assertNotIn("artifact_store", window.model.project.metadata)
        finally:
            _destroy_shell_window(window, app)
            test_env.stop()
            _flush_qt_events(app)

    def test_shell_window_browse_node_property_path_stages_managed_copy_and_reuses_artifact_id(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        test_env = ShellTestEnvironment()
        temp_root = test_env.start()
        window = ShellWindow()
        try:
            seed_fixture = _REPO_ROOT / "tests" / "fixtures" / "passive_nodes" / "reference_preview.png"
            replacement_fixture = temp_root / "replacement.png"
            replacement_fixture.write_bytes(b"replacement-image-bytes")
            project_path = temp_root / "managed-seed-demo.sfe"
            managed_image_path = project_path.with_name("managed-seed-demo.data") / "assets" / "media" / "seed.png"
            managed_image_path.parent.mkdir(parents=True, exist_ok=True)
            managed_image_path.write_bytes(seed_fixture.read_bytes())
            managed_ref = format_managed_artifact_ref("managed_image")

            window.project_path = str(project_path)
            window.model.project.metadata = {
                "artifact_store": {
                    "artifacts": {
                        "managed_image": {"relative_path": "assets/media/seed.png"},
                    }
                }
            }

            image_node_id = window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
            self.assertTrue(image_node_id)
            window.scene.set_node_property(image_node_id, "source_path", managed_ref)
            app.processEvents()

            with patch(
                "ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName",
                return_value=(str(replacement_fixture), ""),
            ) as dialog_mock:
                staged_ref = window.browse_node_property_path(image_node_id, "source_path", managed_ref)
                self.assertEqual(staged_ref, "artifact-stage://managed_image")
                self.assertEqual(dialog_mock.call_count, 1)
                self.assertEqual(dialog_mock.call_args.args[2], str(managed_image_path))

            store = ProjectArtifactStore.from_project_metadata(
                project_path=window.project_path,
                project_metadata=window.model.project.metadata,
            )
            staged_path = store.resolve_staged_path(staged_ref)
            self.assertIsNotNone(staged_path)
            assert staged_path is not None
            self.assertTrue(staged_path.exists())
            self.assertEqual(staged_path.read_bytes(), replacement_fixture.read_bytes())

            with patch(
                "ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName",
                return_value=(str(seed_fixture), ""),
            ) as dialog_mock:
                replacement_ref = window.browse_node_property_path(image_node_id, "source_path", staged_ref)
                self.assertEqual(replacement_ref, staged_ref)
                self.assertEqual(dialog_mock.call_count, 1)
                self.assertEqual(dialog_mock.call_args.args[2], str(staged_path))

            store = ProjectArtifactStore.from_project_metadata(
                project_path=window.project_path,
                project_metadata=window.model.project.metadata,
            )
            replacement_path = store.resolve_staged_path(staged_ref)
            self.assertIsNotNone(replacement_path)
            assert replacement_path is not None
            self.assertEqual(replacement_path, staged_path)
            self.assertTrue(replacement_path.exists())
            self.assertEqual(replacement_path.read_bytes(), seed_fixture.read_bytes())
            self.assertEqual(
                window.model.project.metadata["artifact_store"]["staged"],
                {
                    "managed_image": {
                        "relative_path": ".staging/assets/media/managed_image.png",
                    }
                },
            )
        finally:
            _destroy_shell_window(window, app)
            test_env.stop()
            _flush_qt_events(app)

    def test_shell_window_selected_node_property_items_publish_file_issue_payload(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        test_env = ShellTestEnvironment()
        temp_root = test_env.start()
        window = ShellWindow()
        try:
            missing_path = str(temp_root / "missing-input.txt")
            node_id = window.scene.add_node_from_type("io.file_read", x=120.0, y=80.0)
            self.assertTrue(node_id)
            window.scene.set_node_property(node_id, "path", missing_path)
            window.scene.select_node(node_id, False)
            app.processEvents()

            path_item = next(item for item in window.selected_node_property_items if item["key"] == "path")
            self.assertTrue(path_item["file_issue_active"])
            self.assertEqual(path_item["file_issue_kind"], "external_missing")
            self.assertTrue(path_item["file_issue_supports_external_repair"])
            self.assertFalse(path_item["file_issue_supports_managed_repair"])
            self.assertEqual(
                path_item["file_issue_request"],
                encode_file_repair_request(missing_path),
            )
        finally:
            _destroy_shell_window(window, app)
            test_env.stop()
            _flush_qt_events(app)
