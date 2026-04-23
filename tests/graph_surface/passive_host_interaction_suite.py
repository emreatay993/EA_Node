from __future__ import annotations

from tests.graph_surface.environment import *  # noqa: F403

class PassiveGraphSurfaceHostTests(PassiveGraphSurfaceHostTestBase):
    def test_standard_host_keeps_port_labels_tied_to_port_handles(self) -> None:
        self._run_qml_probe(
            "port-label-geometry-host",
            """
            payload = node_payload()
            payload["width"] = 320.0
            payload["surface_metrics"]["default_width"] = 320.0
            payload["ports"][0]["label"] = "in"
            payload["ports"][1]["label"] = "out"

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]

            gap = float(host.property("_portLabelGap"))
            max_width = float(host.property("_portLabelMaxWidth"))
            output_implicit_width = float(output_label.property("implicitWidth"))
            input_label_left = input_label.mapToItem(host, QPointF(0.0, 0.0)).x()
            output_label_right = output_label.mapToItem(host, QPointF(float(output_label.width()), 0.0)).x()

            assert abs(input_label_left - (input_dot.x() + input_dot.width() + gap)) < 0.5
            assert abs(output_label_right - (output_dot.x() - gap)) < 0.5
            assert output_label.width() < max_width
            assert abs(output_label.width() - output_implicit_width) < 0.5
            """,
        )

    def test_standard_host_replaces_default_exec_port_labels_with_arrows(self) -> None:
        self._run_qml_probe(
            "exec-port-arrow-labels-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]
            input_mouse = named_child_items(host, "graphNodeInputPortMouseArea")[0]
            output_mouse = named_child_items(host, "graphNodeOutputPortMouseArea")[0]

            assert input_label.property("text") == "\u27A1"
            assert output_label.property("text") == "\u27A1"
            assert input_mouse.property("portLabelTooltipText") == "Exec In"
            assert output_mouse.property("portLabelTooltipText") == "Exec Out"
            """,
        )

    def test_graph_typography_host_chrome_shared_roles_apply_without_overriding_passive_title_authority(self) -> None:
        self._run_qml_probe(
            "graph-typography-host-chrome-passive-authority",
            """
            def configured_payload(*, passive=False, font_size=None, font_weight=None):
                payload = node_payload()
                payload["can_enter_scope"] = True
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
                    },
                    {
                        "key": "exec_out",
                        "label": "Exec Out",
                        "direction": "out",
                        "kind": "exec",
                        "data_type": "exec",
                        "connected": False,
                    },
                ]
                if passive:
                    payload["runtime_behavior"] = "passive"
                    payload["visual_style"] = {}
                    if font_size is not None:
                        payload["visual_style"]["font_size"] = font_size
                    if font_weight is not None:
                        payload["visual_style"]["font_weight"] = font_weight
                return payload

            active_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": configured_payload(),
                    "graphLabelPixelSize": 16,
                },
            )
            active_typography = active_host.findChild(QObject, "graphSharedTypography")
            active_title = active_host.findChild(QObject, "graphNodeTitle")
            active_open_badge = active_host.findChild(QObject, "graphNodeOpenBadgeText")
            active_input_labels = named_child_items(active_host, "graphNodeInputPortLabel")
            active_output_labels = named_child_items(active_host, "graphNodeOutputPortLabel")
            active_data_label = [item for item in active_input_labels if item.property("text") == "Message"][0]
            active_exec_input = [item for item in active_input_labels if item.property("text") == "\u27A1"][0]
            active_exec_output = [item for item in active_output_labels if item.property("text") == "\u27A1"][0]

            assert active_typography is not None
            assert active_title is not None
            assert active_open_badge is not None
            assert active_title.property("font").pixelSize() == int(active_typography.property("nodeTitlePixelSize"))
            assert active_title.property("font").weight() == int(active_typography.property("nodeTitleFontWeight"))
            assert active_open_badge.property("font").pixelSize() == int(active_typography.property("badgePixelSize"))
            assert active_open_badge.property("font").weight() == int(active_typography.property("badgeFontWeight"))
            assert active_data_label.property("font").pixelSize() == int(active_typography.property("portLabelPixelSize"))
            assert active_data_label.property("font").weight() == int(active_typography.property("portLabelFontWeight"))
            assert active_exec_input.property("font").pixelSize() == int(active_typography.property("execArrowPortPixelSize"))
            assert active_exec_input.property("font").weight() == int(active_typography.property("execArrowPortFontWeight"))
            assert active_exec_output.property("font").pixelSize() == int(active_typography.property("execArrowPortPixelSize"))
            assert active_exec_output.property("font").weight() == int(active_typography.property("execArrowPortFontWeight"))

            passive_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": configured_payload(passive=True, font_size=17, font_weight="normal"),
                    "graphLabelPixelSize": 16,
                },
            )
            passive_typography = passive_host.findChild(QObject, "graphSharedTypography")
            passive_title = passive_host.findChild(QObject, "graphNodeTitle")
            passive_open_badge = passive_host.findChild(QObject, "graphNodeOpenBadgeText")
            passive_input_labels = named_child_items(passive_host, "graphNodeInputPortLabel")
            passive_data_label = [item for item in passive_input_labels if item.property("text") == "Message"][0]

            assert passive_typography is not None
            assert passive_title is not None
            assert passive_open_badge is not None
            assert passive_title.property("font").pixelSize() == 17
            assert passive_title.property("font").weight() == 400
            assert passive_title.property("font").pixelSize() != int(passive_typography.property("nodeTitlePixelSize"))
            assert passive_title.property("font").weight() != int(passive_typography.property("nodeTitleFontWeight"))
            assert passive_open_badge.property("font").pixelSize() == int(passive_typography.property("badgePixelSize"))
            assert passive_open_badge.property("font").weight() == int(passive_typography.property("badgeFontWeight"))
            assert passive_data_label.property("font").pixelSize() == int(passive_typography.property("portLabelPixelSize"))
            assert passive_data_label.property("font").weight() == int(passive_typography.property("portLabelFontWeight"))
            """,
        )

    def test_graph_typography_inline_edge_inline_roles_apply_without_overriding_passive_title_authority(self) -> None:
        self._run_qml_probe(
            "graph-typography-inline-edge-passive-authority",
            """
            def configured_payload(*, passive=False):
                payload = node_payload()
                payload["inline_properties"] = [
                    {
                        "key": "source_path",
                        "label": "Source",
                        "inline_editor": "text",
                        "value": "/fixtures/original.txt",
                        "status_chip_text": "Stored",
                        "status_chip_variant": "stored",
                        "overridden_by_input": False,
                        "input_port_label": "source_path",
                    }
                ]
                if passive:
                    payload["runtime_behavior"] = "passive"
                    payload["visual_style"] = {
                        "font_size": 17,
                        "font_weight": "normal",
                    }
                return payload

            def inline_item(host, object_name, property_key):
                return next(
                    item for item in named_child_items(host, object_name)
                    if str(item.property("propertyKey") or "") == property_key
                )

            active_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": configured_payload(),
                    "graphLabelPixelSize": 16,
                },
            )
            active_typography = active_host.findChild(QObject, "graphSharedTypography")
            active_inline_label = inline_item(active_host, "graphNodeInlinePropertyLabel", "source_path")
            active_status_chip = inline_item(active_host, "graphNodeInlineStatusChipLabel", "source_path")

            assert active_typography is not None
            assert active_inline_label.property("font").pixelSize() == int(active_typography.property("inlinePropertyPixelSize"))
            assert active_inline_label.property("font").weight() == int(active_typography.property("inlinePropertyFontWeight"))
            assert active_status_chip.property("font").pixelSize() == int(active_typography.property("badgePixelSize"))
            assert active_status_chip.property("font").weight() == int(active_typography.property("badgeFontWeight"))

            passive_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": configured_payload(passive=True),
                    "graphLabelPixelSize": 16,
                },
            )
            passive_typography = passive_host.findChild(QObject, "graphSharedTypography")
            passive_title = passive_host.findChild(QObject, "graphNodeTitle")
            passive_inline_label = inline_item(passive_host, "graphNodeInlinePropertyLabel", "source_path")
            passive_status_chip = inline_item(passive_host, "graphNodeInlineStatusChipLabel", "source_path")

            assert passive_typography is not None
            assert passive_title is not None
            assert passive_title.property("font").pixelSize() == 17
            assert passive_title.property("font").weight() == 400
            assert passive_title.property("font").pixelSize() != int(passive_typography.property("nodeTitlePixelSize"))
            assert passive_title.property("font").weight() != int(passive_typography.property("nodeTitleFontWeight"))
            assert passive_inline_label.property("font").pixelSize() == int(passive_typography.property("inlinePropertyPixelSize"))
            assert passive_inline_label.property("font").weight() == int(passive_typography.property("inlinePropertyFontWeight"))
            assert passive_status_chip.property("font").pixelSize() == int(passive_typography.property("badgePixelSize"))
            assert passive_status_chip.property("font").weight() == int(passive_typography.property("badgeFontWeight"))
            """,
        )

    def test_title_icon_renders_for_non_passive_titles_and_uses_centered_reserve(self) -> None:
        self._run_qml_probe(
            "title-icon-non-passive-host",
            """
            from pathlib import Path

            def normalized_source(value):
                if hasattr(value, "toString"):
                    return str(value.toString())
                return str(value or "")

            icon_source = (Path.cwd() / "ea_node_editor" / "assets" / "app_icon" / "corex_app_minimal.svg").as_uri()

            active_canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": {
                        "graphics_graph_label_pixel_size": 16,
                        "graphics_graph_node_icon_pixel_size_override": 12,
                        "graphics_node_title_icon_pixel_size": 12,
                    },
                },
            )

            active_payload = node_payload()
            active_payload["title"] = "Archive Session"
            active_payload["surface_metrics"]["title_centered"] = True
            active_payload["icon_source"] = icon_source

            active_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": active_payload,
                    "canvasItem": active_canvas,
                },
            )
            active_typography = active_host.findChild(QObject, "graphSharedTypography")
            active_display = active_host.findChild(QObject, "graphNodeTitleDisplay")
            active_title = active_host.findChild(QObject, "graphNodeTitle")
            active_icon = active_host.findChild(QObject, "graphNodeTitleIcon")
            active_comment_icon = active_host.findChild(QObject, "graphNodeCommentTitleIcon")

            assert active_typography is not None
            assert active_display is not None
            assert active_title is not None
            assert active_icon is not None
            assert active_comment_icon is not None
            assert int(active_host.property("effectiveNodeTitleIconPixelSize")) == 12
            assert int(active_typography.property("nodeTitleIconPixelSize")) == 12
            assert bool(active_icon.property("visible"))
            assert not bool(active_comment_icon.property("visible"))
            assert normalized_source(active_icon.property("source")) == icon_source
            assert int(active_icon.property("width")) == 12
            assert int(active_icon.property("height")) == 12
            assert bool(active_icon.property("smooth"))
            assert bool(active_icon.property("mipmap"))
            assert float(active_title.x()) > 0.0
            assert float(active_title.width()) < float(active_display.width())

            passive_canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": {
                        "graphics_graph_label_pixel_size": 16,
                        "graphics_graph_node_icon_pixel_size_override": 12,
                        "graphics_node_title_icon_pixel_size": 12,
                    },
                },
            )

            passive_payload = node_payload()
            passive_payload["runtime_behavior"] = "passive"
            passive_payload["surface_metrics"]["title_centered"] = True
            passive_payload["icon_source"] = icon_source

            passive_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": passive_payload,
                    "canvasItem": passive_canvas,
                },
            )
            passive_title = passive_host.findChild(QObject, "graphNodeTitle")
            passive_icon = passive_host.findChild(QObject, "graphNodeTitleIcon")

            assert passive_title is not None
            assert passive_icon is not None
            assert not bool(passive_icon.property("visible"))
            assert abs(float(passive_title.x()) - 0.0) < 0.5
            """,
        )

    def test_title_icon_filtering_follows_canvas_render_quality(self) -> None:
        self._run_qml_probe(
            "title-icon-filtering-follows-canvas-render-quality",
            """
            from pathlib import Path

            def normalized_source(value):
                if hasattr(value, "toString"):
                    return str(value.toString())
                return str(value or "")

            icon_source = (Path.cwd() / "ea_node_editor" / "assets" / "app_icon" / "corex_app_minimal.svg").as_uri()

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": {
                        "graphics_graph_label_pixel_size": 16,
                        "graphics_graph_node_icon_pixel_size_override": 12,
                        "graphics_node_title_icon_pixel_size": 12,
                    },
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            payload = node_payload()
            payload["title"] = "Archive Session"
            payload["surface_metrics"]["title_centered"] = True
            payload["icon_source"] = icon_source

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "canvasItem": canvas,
                },
            )
            title_icon = host.findChild(QObject, "graphNodeTitleIcon")

            assert title_icon is not None
            assert normalized_source(title_icon.property("source")) == icon_source
            assert bool(canvas.property("highQualityRendering"))
            assert bool(host.property("highQualityRendering"))
            assert bool(title_icon.property("smooth"))
            assert bool(title_icon.property("mipmap"))

            canvas.beginViewportInteraction()
            canvas.finishViewportInteractionSoon()
            app.processEvents()

            assert bool(canvas.property("interactionActive"))
            assert not bool(canvas.property("highQualityRendering"))
            assert not bool(host.property("highQualityRendering"))
            assert not bool(title_icon.property("smooth"))
            assert not bool(title_icon.property("mipmap"))
            """,
        )

    def test_title_icon_large_override_expands_title_row_and_stays_within_bounds(self) -> None:
        self._run_qml_probe(
            "title-icon-large-override-header-bounds",
            """
            from pathlib import Path

            icon_source = (Path.cwd() / "ea_node_editor" / "assets" / "app_icon" / "corex_app_minimal.svg").as_uri()

            canvas_item = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": {
                        "graphics_graph_label_pixel_size": 16,
                        "graphics_graph_node_icon_pixel_size_override": 50,
                        "graphics_node_title_icon_pixel_size": 50,
                    },
                },
            )

            payload = node_payload()
            payload["title"] = "Archive Session"
            payload["height"] = 80.0
            payload["surface_metrics"]["default_height"] = 80.0
            payload["surface_metrics"]["header_height"] = 54.0
            payload["surface_metrics"]["title_height"] = 54.0
            payload["surface_metrics"]["body_top"] = 60.0
            payload["surface_metrics"]["port_top"] = 60.0
            payload["surface_metrics"]["title_centered"] = True
            payload["icon_source"] = icon_source

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "canvasItem": canvas_item,
                },
            )
            title_display = host.findChild(QObject, "graphNodeTitleDisplay")
            title_icon = host.findChild(QObject, "graphNodeTitleIcon")

            assert title_display is not None
            assert title_icon is not None
            assert int(host.property("effectiveNodeTitleIconPixelSize")) == 50
            assert bool(title_icon.property("visible"))
            assert float(title_display.property("height")) > 24.0
            assert float(host.property("height")) > 50.0
            assert float(title_icon.property("width")) == 50.0
            assert float(title_icon.property("height")) <= float(title_display.property("height"))
            assert float(title_icon.property("y")) >= 0.0
            assert float(title_icon.property("y")) + float(title_icon.property("height")) <= float(title_display.property("height")) + 0.5
            assert float(title_icon.property("height")) == float(host.property("effectiveNodeTitleIconPixelSize"))
            """,
        )

    def test_standard_host_consumes_metric_backed_label_columns_without_overlap(self) -> None:
        self._run_qml_probe(
            "port-label-width-contract-host",
            """
            payload = node_payload()
            payload["ports"][0]["label"] = "Primary Input Payload"
            payload["ports"][1]["label"] = "Dispatch Result Token"
            payload["width"] = 360.0
            payload["surface_metrics"]["default_width"] = 360.0

            measurement_host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            measurement_input = named_child_items(measurement_host, "graphNodeInputPortLabel")[0]
            measurement_output = named_child_items(measurement_host, "graphNodeOutputPortLabel")[0]
            left_width = float(measurement_input.property("implicitWidth"))
            right_width = float(measurement_output.property("implicitWidth"))
            measurement_host.deleteLater()
            app.processEvents()

            port_gutter = 21.5
            center_gap = 24.0
            min_width = left_width + right_width + (port_gutter * 2.0) + center_gap
            payload["width"] = min_width
            payload["surface_metrics"]["default_width"] = min_width
            payload["surface_metrics"]["min_width"] = min_width
            payload["surface_metrics"]["standard_left_label_width"] = left_width
            payload["surface_metrics"]["standard_right_label_width"] = right_width
            payload["surface_metrics"]["standard_port_gutter"] = port_gutter
            payload["surface_metrics"]["standard_center_gap"] = center_gap
            payload["surface_metrics"]["standard_port_label_min_width"] = min_width

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]

            assert bool(host.property("_usesStandardPortLabelColumns"))
            assert abs(float(input_label.width()) - left_width) < 0.75
            assert abs(float(output_label.width()) - right_width) < 0.75

            gap = float(host.property("_portLabelGap"))
            input_left = input_label.mapToItem(host, QPointF(0.0, 0.0)).x()
            input_right = input_label.mapToItem(host, QPointF(float(input_label.width()), 0.0)).x()
            output_left = output_label.mapToItem(host, QPointF(0.0, 0.0)).x()
            output_right = output_label.mapToItem(host, QPointF(float(output_label.width()), 0.0)).x()

            assert abs(input_left - (input_dot.x() + input_dot.width() + gap)) < 0.5
            assert abs(output_right - (output_dot.x() - gap)) < 0.5
            assert output_left - input_right >= center_gap - 0.5
            """,
        )

    def test_standard_host_uses_extra_width_to_expand_metric_backed_label_columns(self) -> None:
        self._run_qml_probe(
            "port-label-extra-width-host",
            """
            payload = node_payload()
            payload["ports"][0]["label"] = "Primary Input Payload"
            payload["ports"][1]["label"] = "Dispatch Result Token"
            payload["width"] = 360.0
            payload["surface_metrics"]["default_width"] = 360.0

            measurement_host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            measurement_input = named_child_items(measurement_host, "graphNodeInputPortLabel")[0]
            measurement_output = named_child_items(measurement_host, "graphNodeOutputPortLabel")[0]
            left_width = float(measurement_input.property("implicitWidth"))
            right_width = float(measurement_output.property("implicitWidth"))
            measurement_host.deleteLater()
            app.processEvents()

            metric_left_width = max(20.0, left_width - 12.0)
            metric_right_width = max(20.0, right_width - 12.0)
            port_gutter = 21.5
            center_gap = 24.0
            min_width = metric_left_width + metric_right_width + (port_gutter * 2.0) + center_gap
            payload["width"] = min_width + 24.0
            payload["surface_metrics"]["default_width"] = payload["width"]
            payload["surface_metrics"]["min_width"] = min_width
            payload["surface_metrics"]["standard_left_label_width"] = metric_left_width
            payload["surface_metrics"]["standard_right_label_width"] = metric_right_width
            payload["surface_metrics"]["standard_port_gutter"] = port_gutter
            payload["surface_metrics"]["standard_center_gap"] = center_gap
            payload["surface_metrics"]["standard_port_label_min_width"] = min_width

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]

            assert bool(host.property("_usesStandardPortLabelColumns"))
            assert float(input_label.width()) > metric_left_width + 10.0
            assert float(output_label.width()) > metric_right_width + 10.0
            assert abs(float(input_label.width()) - left_width) < 0.75
            assert abs(float(output_label.width()) - right_width) < 0.75
            """,
        )

    def test_standard_host_uses_tooltip_only_port_labels_when_preference_disabled(self) -> None:
        self._run_qml_probe(
            "tooltip-only-port-labels-host",
            """
            payload = node_payload()
            payload["ports"][0]["label"] = "Primary Input Payload"
            payload["ports"][1]["label"] = "Dispatch Result Token"

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": payload,
                    "showPortLabelsPreference": False,
                },
            )
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]
            input_mouse = named_child_items(host, "graphNodeInputPortMouseArea")[0]
            output_mouse = named_child_items(host, "graphNodeOutputPortMouseArea")[0]

            assert bool(host.property("_tooltipOnlyPortLabelsActive"))
            assert not bool(host.property("_portLabelsVisible"))
            assert not bool(input_label.property("visible"))
            assert not bool(output_label.property("visible"))
            assert bool(input_mouse.property("tooltipOnlyPortLabelActive"))
            assert bool(output_mouse.property("tooltipOnlyPortLabelActive"))
            assert input_mouse.property("portLabelTooltipText") == "Primary Input Payload"
            assert output_mouse.property("portLabelTooltipText") == "Dispatch Result Token"

            window = attach_host_to_window(host)
            try:
                QTest.mouseMove(window, item_scene_point(input_mouse))
                settle_events(5)
                assert bool(input_mouse.property("containsMouse"))
                assert bool(input_mouse.property("tooltipVisible"))
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_standard_host_marks_inactive_input_ports_with_muted_label_and_reason_tooltip(self) -> None:
        self._run_qml_probe(
            "inactive-input-port-ux-host",
            """
            payload = node_payload()
            payload["ports"][0]["key"] = "path"
            payload["ports"][0]["label"] = "path"
            payload["ports"][0]["kind"] = "data"
            payload["ports"][0]["data_type"] = "path"
            payload["ports"][0]["inactive"] = True
            payload["ports"][0]["inactive_source_key"] = "result_file"
            payload["ports"][0]["inactive_reason"] = "Driven by result_file"

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            inactive_slash = named_child_items(host, "graphNodeInputPortInactiveSlash")[0]
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            input_mouse = named_child_items(host, "graphNodeInputPortMouseArea")[0]

            assert abs(float(input_dot.property("opacity")) - 0.46) < 0.01
            assert abs(float(input_label.property("opacity")) - 0.52) < 0.01
            assert bool(inactive_slash.property("visible"))
            assert input_mouse.property("inactiveTooltipText") == "Driven by result_file"
            assert input_mouse.property("cursorShape") == Qt.CursorShape.ForbiddenCursor
            """,
        )

    def test_flowchart_host_does_not_replace_surface_suppressed_labels_with_tooltips(self) -> None:
        self._run_qml_probe(
            "flowchart-no-tooltip-port-labels-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": flowchart_payload("decision"),
                    "showPortLabelsPreference": False,
                },
            )

            assert not bool(host.property("_portLabelsVisible"))
            assert not bool(host.property("_tooltipOnlyPortLabelsActive"))
            assert not bool(host.property("_usesStandardPortLabelColumns"))
            """,
        )

    def test_standard_exec_ports_remain_visible_without_hover(self) -> None:
        self._run_qml_probe(
            "standard-exec-port-visible-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]

            assert float(input_dot.property("opacity")) > 0.99
            assert float(output_dot.property("opacity")) > 0.99
            """,
        )

    def test_flow_edge_ports_reveal_on_hover_and_pending_connection_only(self) -> None:
        self._run_qml_probe(
            "flow-edge-port-reveal-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": flowchart_payload("decision")},
            )
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]

            assert float(input_dot.property("opacity")) < 0.01
            assert float(output_dot.property("opacity")) < 0.01

            host.setProperty("pendingPort", {
                "node_id": "node_surface_host_test",
                "port_key": "top",
                "direction": "neutral",
            })
            app.processEvents()

            assert float(input_dot.property("opacity")) > 0.99
            assert float(output_dot.property("opacity")) < 0.01

            host.setProperty("pendingPort", None)
            app.processEvents()

            assert float(input_dot.property("opacity")) < 0.01
            assert float(output_dot.property("opacity")) < 0.01

            window = attach_host_to_window(host)
            try:
                hover_host_local_point(window, host, float(host.width()) * 0.5, float(host.height()) * 0.5)
                assert bool(host.property("hoverActive"))
                assert float(input_dot.property("opacity")) > 0.99
                assert float(output_dot.property("opacity")) > 0.99
            finally:
                dispose_host_window(host, window)
            """,
        )

    def test_graph_node_host_shadow_cache_key_ignores_viewport_cache_flags_but_tracks_geometry_and_shadow_preferences(self) -> None:
        self._run_qml_probe(
            "host-shadow-cache-key",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": node_payload(),
                    "showShadow": True,
                },
            )
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            shadow_item = host.findChild(QObject, "graphNodeShadow")
            chrome_item = host.findChild(QObject, "graphNodeChrome")

            assert background_layer is not None
            assert shadow_item is not None
            assert chrome_item is not None
            assert bool(background_layer.property("cacheActive"))
            assert bool(background_layer.property("chromeCacheActive"))
            assert bool(background_layer.property("shadowCacheActive"))
            assert bool(chrome_item.property("visible"))
            assert bool(shadow_item.property("cached"))

            baseline_key = str(background_layer.property("cacheKey") or "")
            assert baseline_key

            host.setProperty("viewportInteractionCacheActive", True)
            app.processEvents()
            assert str(background_layer.property("cacheKey") or "") == baseline_key

            host.setProperty("snapshotReuseActive", True)
            app.processEvents()
            assert str(background_layer.property("cacheKey") or "") == baseline_key

            host.setProperty("_liveWidth", 244.0)
            host.setProperty("_liveHeight", 96.0)
            host.setProperty("_liveGeometryActive", True)
            app.processEvents()
            geometry_key = str(background_layer.property("cacheKey") or "")
            assert geometry_key != baseline_key

            host.setProperty("_liveGeometryActive", False)
            host.setProperty("shadowStrength", 55)
            app.processEvents()
            shadow_preference_key = str(background_layer.property("cacheKey") or "")
            assert shadow_preference_key != baseline_key
            assert shadow_preference_key != geometry_key
            """,
        )

    def test_graph_node_host_node_execution_visualization_states_drive_timer_priority_and_cache_keys(self) -> None:
        self._run_qml_probe(
            "host-node-execution-visualization",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSignal
            from PyQt6.QtTest import QTest
            import time

            class ExecutionSceneBridge(QObject):
                selected_node_lookup_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._selected_node_lookup = {}

                @pyqtProperty("QVariantMap", notify=selected_node_lookup_changed)
                def selected_node_lookup(self):
                    return dict(self._selected_node_lookup)

            class ExecutionCanvasItem(QQuickItem):
                failed_node_lookup_changed = pyqtSignal()
                failed_node_revision_changed = pyqtSignal()
                running_node_lookup_changed = pyqtSignal()
                completed_node_lookup_changed = pyqtSignal()
                running_node_started_at_ms_lookup_changed = pyqtSignal()
                node_elapsed_ms_lookup_changed = pyqtSignal()
                node_execution_revision_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._scene_bridge = ExecutionSceneBridge()
                    self._failed_node_lookup = {}
                    self._failed_node_revision = 0
                    self._running_node_lookup = {}
                    self._completed_node_lookup = {}
                    self._running_node_started_at_ms_lookup = {}
                    self._node_elapsed_ms_lookup = {}
                    self._node_execution_revision = 0

                @pyqtProperty(QObject, constant=True)
                def sceneBridge(self):
                    return self._scene_bridge

                @pyqtProperty("QVariantMap", notify=failed_node_lookup_changed)
                def failedNodeLookup(self):
                    return dict(self._failed_node_lookup)

                @pyqtProperty(int, notify=failed_node_revision_changed)
                def failedNodeRevision(self):
                    return int(self._failed_node_revision)

                @pyqtProperty("QVariantMap", notify=running_node_lookup_changed)
                def runningNodeLookup(self):
                    return dict(self._running_node_lookup)

                @pyqtProperty("QVariantMap", notify=completed_node_lookup_changed)
                def completedNodeLookup(self):
                    return dict(self._completed_node_lookup)

                @pyqtProperty("QVariantMap", notify=running_node_started_at_ms_lookup_changed)
                def runningNodeStartedAtMsLookup(self):
                    return dict(self._running_node_started_at_ms_lookup)

                @pyqtProperty("QVariantMap", notify=node_elapsed_ms_lookup_changed)
                def nodeElapsedMsLookup(self):
                    return dict(self._node_elapsed_ms_lookup)

                @pyqtProperty(int, notify=node_execution_revision_changed)
                def nodeExecutionRevision(self):
                    return int(self._node_execution_revision)

                def set_running(self, node_id, started_at_ms):
                    self._running_node_lookup = {str(node_id): True}
                    self._completed_node_lookup = {}
                    self._running_node_started_at_ms_lookup = {str(node_id): float(started_at_ms)}
                    self._node_execution_revision += 1
                    self.running_node_lookup_changed.emit()
                    self.completed_node_lookup_changed.emit()
                    self.running_node_started_at_ms_lookup_changed.emit()
                    self.node_execution_revision_changed.emit()

                def set_completed(self, node_id, elapsed_ms):
                    self._running_node_lookup = {}
                    self._completed_node_lookup = {str(node_id): True}
                    self._running_node_started_at_ms_lookup = {}
                    self._node_elapsed_ms_lookup = {str(node_id): float(elapsed_ms)}
                    self._node_execution_revision += 1
                    self.running_node_lookup_changed.emit()
                    self.completed_node_lookup_changed.emit()
                    self.running_node_started_at_ms_lookup_changed.emit()
                    self.node_elapsed_ms_lookup_changed.emit()
                    self.node_execution_revision_changed.emit()

                def clear_cached_elapsed(self):
                    self._node_elapsed_ms_lookup = {}
                    self._node_execution_revision += 1
                    self.node_elapsed_ms_lookup_changed.emit()
                    self.node_execution_revision_changed.emit()

                def set_failed(self, node_id):
                    self._failed_node_lookup = {str(node_id): True}
                    self._failed_node_revision += 1
                    self.failed_node_lookup_changed.emit()
                    self.failed_node_revision_changed.emit()

            canvas_item = ExecutionCanvasItem()
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": node_payload(),
                    "canvasItem": canvas_item,
                    "showShadow": True,
                },
            )
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            running_halo = host.findChild(QObject, "graphNodeRunningHalo")
            running_pulse_halo = host.findChild(QObject, "graphNodeRunningPulseHalo")
            completed_flash_halo = host.findChild(QObject, "graphNodeCompletedFlashHalo")
            elapsed_timer = host.findChild(QObject, "graphNodeElapsedTimer")

            assert background_layer is not None
            assert running_halo is not None
            assert running_pulse_halo is not None
            assert completed_flash_halo is not None
            assert elapsed_timer is not None

            started_at_ms = (time.time() * 1000.0) - 1800.0
            completed_elapsed_ms = 3487.0
            canvas_item.set_running("node_surface_host_test", started_at_ms)
            app.processEvents()
            assert bool(host.property("isRunningNode"))
            assert not bool(host.property("isCompletedNode"))
            assert bool(host.property("renderActive"))
            assert int(host.property("z")) == 31
            assert str(background_layer.property("effectiveBorderState")) == "running"
            assert bool(running_halo.property("visible"))
            assert bool(running_pulse_halo.property("visible"))
            assert bool(elapsed_timer.property("visible"))
            assert bool(elapsed_timer.property("liveElapsedActive"))
            assert abs(float(elapsed_timer.property("startedAtMs")) - started_at_ms) < 16.0
            running_key = str(background_layer.property("cacheKey") or "")
            assert "|running|" in running_key

            QTest.qWait(80)
            app.processEvents()
            assert float(elapsed_timer.property("elapsedMilliseconds")) >= 1400.0

            canvas_item.set_completed("node_surface_host_test", completed_elapsed_ms)
            app.processEvents()
            QTest.qWait(80)
            app.processEvents()

            assert not bool(host.property("isRunningNode"))
            assert bool(host.property("isCompletedNode"))
            assert bool(host.property("renderActive"))
            assert int(host.property("z")) == 29
            assert str(background_layer.property("effectiveBorderState")) == "completed"
            assert not bool(running_halo.property("visible"))
            assert not bool(running_pulse_halo.property("visible"))
            assert bool(elapsed_timer.property("visible"))
            assert not bool(elapsed_timer.property("liveElapsedActive"))
            assert bool(elapsed_timer.property("cachedElapsedActive"))
            assert abs(float(elapsed_timer.property("cachedElapsedMilliseconds")) - completed_elapsed_ms) < 0.01
            assert str(elapsed_timer.property("text") or "") == "3.5s"
            assert float(elapsed_timer.property("opacity")) == float(host.property("completedElapsedFooterOpacity"))
            assert float(background_layer.property("completedFlashProgress")) > 0.0
            completed_key = str(background_layer.property("cacheKey") or "")
            assert completed_key != running_key
            assert "|completed|" in completed_key

            canvas_item.clear_cached_elapsed()
            app.processEvents()

            assert not bool(elapsed_timer.property("visible"))
            assert not bool(elapsed_timer.property("cachedElapsedActive"))

            canvas_item.set_failed("node_surface_host_test")
            app.processEvents()

            assert bool(host.property("isFailedNode"))
            assert str(background_layer.property("effectiveBorderState")) == "failed"
            assert not bool(running_halo.property("visible"))
            assert not bool(running_pulse_halo.property("visible"))
            assert not bool(completed_flash_halo.property("visible"))
            assert "|failed|" in str(background_layer.property("cacheKey") or "")
            """,
        )

    def test_persistent_node_elapsed_footer_graph_node_host_reuses_canvas_timing_and_clears_on_invalidation(self) -> None:
        self.test_graph_node_host_node_execution_visualization_states_drive_timer_priority_and_cache_keys()

    def test_flowchart_host_shadow_visibility_follows_global_shadow_preference(self) -> None:
        self._run_qml_probe(
            "flowchart-host-shadow-visibility",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": flowchart_payload("decision"),
                    "showShadow": True,
                },
            )
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            shadow_item = host.findChild(QObject, "graphNodeShadow")
            flowchart_shadow = host.findChild(QObject, "graphNodeFlowchartShadow")
            chrome_item = host.findChild(QObject, "graphNodeChrome")
            flowchart_surface = host.findChild(QObject, "graphNodeFlowchartSurface")

            assert bool(host.property("isFlowchartSurface"))
            assert not bool(host.property("_useHostChrome"))
            assert background_layer is not None
            assert shadow_item is not None
            assert flowchart_shadow is not None
            assert chrome_item is not None
            assert flowchart_surface is not None
            assert not bool(background_layer.property("cacheActive"))
            assert not bool(background_layer.property("chromeCacheActive"))
            assert not bool(background_layer.property("shadowCacheActive"))
            assert not bool(chrome_item.property("visible"))
            assert not bool(shadow_item.property("visible"))
            assert bool(flowchart_surface.property("shapeShadowVisible"))
            assert bool(flowchart_surface.property("shapeShadowCacheActive"))
            assert bool(flowchart_shadow.property("visible"))
            assert bool(flowchart_shadow.property("cacheActive"))

            host.setProperty("showShadow", False)
            app.processEvents()

            assert not bool(background_layer.property("cacheActive"))
            assert not bool(background_layer.property("shadowCacheActive"))
            assert not bool(shadow_item.property("visible"))
            assert not bool(flowchart_surface.property("shapeShadowVisible"))
            assert not bool(flowchart_surface.property("shapeShadowCacheActive"))
            assert not bool(flowchart_shadow.property("visible"))
            """,
        )

    def test_flowchart_host_shadow_cache_key_tracks_shadow_preferences_without_host_chrome(self) -> None:
        self._run_qml_probe(
            "flowchart-host-shadow-cache-key",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": flowchart_payload("decision"),
                    "showShadow": True,
                },
            )
            background_layer = host.findChild(QObject, "graphNodeChromeBackgroundLayer")
            shadow_item = host.findChild(QObject, "graphNodeShadow")
            flowchart_shadow = host.findChild(QObject, "graphNodeFlowchartShadow")
            chrome_item = host.findChild(QObject, "graphNodeChrome")
            flowchart_surface = host.findChild(QObject, "graphNodeFlowchartSurface")

            assert background_layer is not None
            assert shadow_item is not None
            assert flowchart_shadow is not None
            assert chrome_item is not None
            assert flowchart_surface is not None
            assert not bool(background_layer.property("cacheActive"))
            assert not bool(background_layer.property("chromeCacheActive"))
            assert not bool(background_layer.property("shadowCacheActive"))
            assert not bool(chrome_item.property("visible"))
            assert not bool(shadow_item.property("visible"))
            assert bool(flowchart_shadow.property("cacheActive"))

            baseline_key = str(flowchart_shadow.property("cacheKey") or "")
            assert baseline_key

            host.setProperty("viewportInteractionCacheActive", True)
            app.processEvents()
            assert str(flowchart_shadow.property("cacheKey") or "") == baseline_key

            host.setProperty("snapshotReuseActive", True)
            app.processEvents()
            assert str(flowchart_shadow.property("cacheKey") or "") == baseline_key

            host.setProperty("_liveWidth", 248.0)
            host.setProperty("_liveHeight", 132.0)
            host.setProperty("_liveGeometryActive", True)
            app.processEvents()
            geometry_key = str(flowchart_shadow.property("cacheKey") or "")
            assert geometry_key != baseline_key

            host.setProperty("_liveGeometryActive", False)
            host.setProperty("shadowSoftness", 41)
            app.processEvents()
            shadow_preference_key = str(flowchart_shadow.property("cacheKey") or "")
            assert shadow_preference_key != baseline_key
            assert shadow_preference_key != geometry_key

            host.setProperty("showShadow", False)
            app.processEvents()
            disabled_shadow_key = str(flowchart_shadow.property("cacheKey") or "")
            assert disabled_shadow_key != shadow_preference_key
            assert not bool(background_layer.property("cacheActive"))
            assert not bool(flowchart_shadow.property("cacheActive"))
            """,
        )

    def test_graph_node_host_shows_four_resize_handles_only_on_hover_for_expanded_nodes(self) -> None:
        self._run_qml_probe(
            "host-hover-only-resize-handles",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            resize_handles = named_child_items(host, "graphNodeResizeHandle")
            assert len(resize_handles) == 4
            assert all(not bool(handle.property("visible")) for handle in resize_handles)

            window = attach_host_to_window(host)
            hover_host_local_point(window, host, 84.0, 40.0)

            assert bool(host.property("hoverActive"))
            assert all(bool(handle.property("visible")) for handle in resize_handles)

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_keeps_resize_handles_hidden_for_collapsed_nodes(self) -> None:
        self._run_qml_probe(
            "host-collapsed-resize-handles-hidden",
            """
            payload = node_payload()
            payload["collapsed"] = True
            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            resize_handles = named_child_items(host, "graphNodeResizeHandle")
            assert len(resize_handles) == 4

            window = attach_host_to_window(host)
            hover_host_local_point(window, host, 24.0, 18.0)

            assert all(not bool(handle.property("visible")) for handle in resize_handles)

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_top_left_resize_handle_previews_anchored_geometry(self) -> None:
        self._run_qml_probe(
            "host-top-left-resize-preview",
            """
            from PyQt6.QtCore import QPoint
            from PyQt6.QtTest import QTest

            payload = node_payload()
            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            preview_events = []
            finish_events = []
            host.resizePreviewChanged.connect(
                lambda node_id, x, y, width, height, active: preview_events.append(
                    (node_id, x, y, width, height, active)
                )
            )
            host.resizeFinished.connect(
                lambda node_id, x, y, width, height: finish_events.append((node_id, x, y, width, height))
            )

            window = attach_host_to_window(host)
            hover_host_local_point(window, host, 40.0, 24.0)

            top_left_handle = [
                handle
                for handle in named_child_items(host, "graphNodeResizeHandle")
                if str(handle.property("cornerRole")) == "topLeft"
            ][0]
            start_point = item_scene_point(top_left_handle, 0.25, 0.25)
            end_point = QPoint(start_point.x() - 30, start_point.y() - 20)

            QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start_point)
            settle_events(2)
            QTest.mouseMove(window, end_point)
            settle_events(2)

            assert bool(host.property("_liveGeometryActive"))
            assert abs(float(host.x()) - 90.0) < 0.75
            assert abs(float(host.y()) - 100.0) < 0.75
            assert abs(float(host.width()) - 240.0) < 0.75
            assert abs(float(host.height()) - 108.0) < 0.75
            assert any(
                entry[0] == "node_surface_host_test"
                and abs(float(entry[1]) - 90.0) < 0.75
                and abs(float(entry[2]) - 100.0) < 0.75
                and abs(float(entry[3]) - 240.0) < 0.75
                and abs(float(entry[4]) - 108.0) < 0.75
                and bool(entry[5])
                for entry in preview_events
            )

            QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end_point)
            settle_events(2)

            assert finish_events == [("node_surface_host_test", 90.0, 100.0, 240.0, 108.0)]
            assert not bool(host.property("_liveGeometryActive"))

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_routes_body_click_open_and_context_from_below_surface_layer(self) -> None:
        self._run_qml_probe(
            "host-body-interactions-below-surface",
            """
            from PyQt6.QtQml import QQmlProperty

            payload = node_payload()
            payload["inline_properties"] = []
            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            gesture_layer = host.findChild(QObject, "graphNodeHostGestureLayer")
            drag_area = host.findChild(QObject, "graphNodeDragArea")

            assert loader is not None
            assert gesture_layer is not None
            assert drag_area is not None
            assert drag_area.parentItem().objectName() == "graphNodeHostGestureLayer"

            surface_layer = loader.parentItem()
            assert surface_layer is not None
            assert float(surface_layer.property("z")) > float(drag_area.property("z"))
            assert abs(float(drag_area.property("width")) - float(host.property("width"))) < 0.5
            assert abs(float(drag_area.property("height")) - float(host.property("height"))) < 0.5

            drag_target = QQmlProperty.read(drag_area, "drag.target")
            assert drag_target is not None
            assert drag_target.property("objectName") == "graphNodeCard"
            assert drag_target.property("nodeData")["node_id"] == "node_surface_host_test"

            window = attach_host_to_window(host)
            body_point = host_scene_point(host, 105.0, 44.0)
            events = host_pointer_events(host)

            mouse_click(window, body_point)
            assert events["clicked"] == [("node_surface_host_test", False)]

            mouse_double_click(window, body_point)
            assert events["opened"] == ["node_surface_host_test"]

            mouse_click(window, body_point, Qt.MouseButton.RightButton)
            assert len(events["contexts"]) == 1
            assert events["contexts"][0][0] == "node_surface_host_test"
            assert abs(float(events["contexts"][0][1]) - 105.0) < 0.5
            assert abs(float(events["contexts"][0][2]) - 44.0) < 0.5

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_render_activation_reloads_offscreen_surface_for_hover_drag_and_resize(self) -> None:
        self._run_qml_probe(
            "host-render-activation-force-active-states",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": node_payload(),
                    "renderActivationSceneRectPayload": {
                        "x": -400.0,
                        "y": -300.0,
                        "width": 60.0,
                        "height": 40.0,
                    },
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            settle_events(2)
            assert not bool(host.property("renderActive"))
            assert not bool(loader.property("renderActive"))
            assert not bool(loader.property("surfaceLoaded"))

            host.setProperty("liveDragDx", 18.0)
            settle_events(2)

            assert bool(host.property("renderActive"))
            assert bool(loader.property("renderActive"))
            assert bool(loader.property("surfaceLoaded"))

            host.setProperty("liveDragDx", 0.0)
            settle_events(2)

            assert not bool(host.property("renderActive"))
            assert not bool(loader.property("renderActive"))
            assert not bool(loader.property("surfaceLoaded"))

            host.setProperty("_liveX", 90.0)
            host.setProperty("_liveY", 100.0)
            host.setProperty("_liveWidth", 240.0)
            host.setProperty("_liveHeight", 108.0)
            host.setProperty("_liveGeometryActive", True)
            settle_events(2)

            assert bool(host.property("renderActive"))
            assert bool(loader.property("renderActive"))
            assert bool(loader.property("surfaceLoaded"))

            host.setProperty("_liveGeometryActive", False)
            settle_events(2)

            assert not bool(host.property("renderActive"))
            assert not bool(loader.property("renderActive"))
            assert not bool(loader.property("surfaceLoaded"))

            window = attach_host_to_window(host)
            hover_host_local_point(window, host, 84.0, 40.0)

            assert bool(host.property("hoverActive"))
            assert bool(host.property("renderActive"))
            assert bool(loader.property("renderActive"))
            assert bool(loader.property("surfaceLoaded"))

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_keeps_live_drag_preview_continuous_when_snap_to_grid_is_enabled(self) -> None:
        self._run_qml_probe(
            "graph-canvas-snap-live-preview",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSignal

            class MainWindowBridge(QObject):
                snap_to_grid_changed = pyqtSignal()
                graphics_preferences_changed = pyqtSignal()

                @pyqtProperty(bool, notify=snap_to_grid_changed)
                def snap_to_grid_enabled(self):
                    return True

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_minimap_expanded(self):
                    return True

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)
            node_id = scene.nodes_model[0]["node_id"]

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)
            main_window_bridge = MainWindowBridge()

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": main_window_bridge,
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]

            assert canvas.snapToGridEnabled() is True
            node_card.dragOffsetChanged.emit(node_id, 11.0, 9.0)
            app.processEvents()
            assert canvas.liveDragDxForNode(node_id) == 11.0
            assert canvas.liveDragDyForNode(node_id) == 9.0

            node_card.dragFinished.emit(node_id, 131.0, 149.0, True)
            app.processEvents()
            assert canvas.liveDragDxForNode(node_id) == 0.0
            assert canvas.liveDragDyForNode(node_id) == 0.0
            assert scene.nodes_model[0]["x"] == 140.0
            assert scene.nodes_model[0]["y"] == 140.0

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_routes_live_resize_geometry_through_edge_layer_and_scene_commit(self) -> None:
        self._run_qml_probe(
            "graph-canvas-live-resize-geometry",
            """
            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            source_node_id = scene.add_node_from_type("core.start", 40.0, 140.0)
            target_node_id = scene.add_node_from_type("core.logger", 220.0, 140.0)
            scene.add_edge(source_node_id, "exec_out", target_node_id, "exec_in")

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
            target_card = [
                card
                for card in node_cards
                if card.property("nodeData")["node_id"] == target_node_id
            ][0]
            edge_layer = canvas.findChild(QObject, "graphCanvasEdgeLayer")
            assert edge_layer is not None

            target_card.resizePreviewChanged.emit(target_node_id, 190.0, 120.0, 260.0, 120.0, True)
            app.processEvents()

            canvas_live_geometry = variant_value(canvas.property("liveNodeGeometry"))
            edge_live_geometry = variant_value(edge_layer.property("liveNodeGeometry"))
            assert canvas_live_geometry[target_node_id] == {
                "x": 190.0,
                "y": 120.0,
                "width": 260.0,
                "height": 120.0,
            }
            assert edge_live_geometry[target_node_id] == canvas_live_geometry[target_node_id]

            target_card.resizeFinished.emit(target_node_id, 190.0, 120.0, 260.0, 120.0)
            app.processEvents()

            assert variant_value(canvas.property("liveNodeGeometry")) == {}
            updated_target = [node for node in scene.nodes_model if node["node_id"] == target_node_id][0]
            assert updated_target["x"] == 190.0
            assert updated_target["y"] == 120.0
            assert updated_target["width"] == 260.0
            assert updated_target["height"] == 120.0

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_drag_moves_all_selected_nodes_together(self) -> None:
        self._run_qml_probe(
            "graph-canvas-multi-drag-selection",
            """
            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            first_node_id = scene.add_node_from_type("core.logger", 120.0, 140.0)
            second_node_id = scene.add_node_from_type("core.start", 320.0, 180.0)
            scene.select_node(first_node_id, False)
            scene.select_node(second_node_id, True)

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
            node_cards = {
                card.property("nodeData")["node_id"]: card
                for card in named_child_items(canvas, "graphNodeCard")
            }
            assert set(scene.selected_node_lookup) == {first_node_id, second_node_id}
            drag_node_ids = canvas.dragNodeIdsForAnchor(second_node_id)
            if hasattr(drag_node_ids, "toVariant"):
                drag_node_ids = drag_node_ids.toVariant()
            assert list(drag_node_ids) == [second_node_id, first_node_id]

            before = {item["node_id"]: (item["x"], item["y"]) for item in scene.nodes_model}
            node_cards[second_node_id].dragOffsetChanged.emit(second_node_id, 25.0, 15.0)
            app.processEvents()
            assert canvas.liveDragDxForNode(first_node_id) == 25.0
            assert canvas.liveDragDyForNode(first_node_id) == 15.0
            assert canvas.liveDragDxForNode(second_node_id) == 25.0
            assert canvas.liveDragDyForNode(second_node_id) == 15.0

            node_cards[second_node_id].dragFinished.emit(second_node_id, 345.0, 195.0, True)
            app.processEvents()
            after = {item["node_id"]: (item["x"], item["y"]) for item in scene.nodes_model}

            assert canvas.liveDragDxForNode(first_node_id) == 0.0
            assert canvas.liveDragDyForNode(first_node_id) == 0.0
            assert canvas.liveDragDxForNode(second_node_id) == 0.0
            assert canvas.liveDragDyForNode(second_node_id) == 0.0
            assert after[first_node_id] == (before[first_node_id][0] + 25.0, before[first_node_id][1] + 15.0)
            assert after[second_node_id] == (before[second_node_id][0] + 25.0, before[second_node_id][1] + 15.0)

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_keeps_node_shadow_visible_during_wheel_zoom(self) -> None:
        self._run_qml_probe_with_retry(
            "graph-canvas-shadow-quality",
            """
            from tests.qt_wait import wait_for_condition_or_raise

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
            assert len(node_cards) == 1
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None
            assert not bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert bool(shadow_item.property("visible"))
            assert not bool(canvas.property("interactionActive"))
            assert bool(canvas.property("highQualityRendering"))

            applied = canvas.applyWheelZoom(
                {"x": 640.0, "y": 360.0, "angleDelta": {"y": 120}, "inverted": False}
            )
            assert applied is True
            app.processEvents()
            assert bool(canvas.property("interactionActive"))
            assert bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert not bool(canvas.property("highQualityRendering"))
            assert bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))

            wait_for_condition_or_raise(
                lambda: (
                    not bool(canvas.property("interactionActive"))
                    and bool(canvas.property("highQualityRendering"))
                    and bool(shadow_item.property("visible"))
                ),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for wheel-zoom interaction state to recover.",
            )
            assert not bool(canvas.property("interactionActive"))
            assert not bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_max_performance_degrades_grid_and_minimap_but_preserves_shadows_during_wheel_zoom(self) -> None:
        self._run_qml_probe(
            "graph-canvas-max-performance-wheel-zoom",
            """
            from tests.qt_wait import wait_for_condition_or_raise

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
                    "mainWindowBridge": {
                        "graphics_show_grid": True,
                        "graphics_show_minimap": True,
                        "graphics_minimap_expanded": True,
                        "graphics_node_shadow": True,
                        "graphics_shadow_strength": 70,
                        "graphics_shadow_softness": 50,
                        "graphics_shadow_offset": 4,
                        "graphics_performance_mode": "max_performance",
                        "snap_to_grid_enabled": False,
                        "snap_grid_size": 20.0,
                    },
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            background = canvas.findChild(QObject, "graphCanvasBackground")
            minimap_overlay = canvas.findChild(QObject, "graphCanvasMinimapOverlay")
            minimap_viewport = canvas.findChild(QObject, "graphCanvasMinimapViewport")
            assert shadow_item is not None
            assert background is not None
            assert minimap_overlay is not None
            assert minimap_viewport is not None
            assert canvas.property("resolvedGraphicsPerformanceMode") == "max_performance"
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert bool(shadow_item.property("visible"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(background.property("effectiveShowGrid"))
            assert bool(minimap_overlay.property("minimapContentVisible"))
            assert bool(minimap_viewport.property("visible"))

            applied = canvas.applyWheelZoom(
                {"x": 640.0, "y": 360.0, "angleDelta": {"y": 120}, "inverted": False}
            )
            assert applied is True
            app.processEvents()
            assert bool(canvas.property("interactionActive"))
            assert bool(canvas.property("transientDegradedWindowActive"))
            assert not bool(canvas.property("highQualityRendering"))
            assert bool(canvas.property("gridSimplificationActive"))
            assert bool(canvas.property("minimapSimplificationActive"))
            assert not bool(canvas.property("shadowSimplificationActive"))
            assert bool(canvas.property("snapshotProxyReuseActive"))
            assert bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))
            assert not bool(background.property("effectiveShowGrid"))
            assert not bool(minimap_overlay.property("minimapContentVisible"))
            assert not bool(minimap_viewport.property("visible"))

            wait_for_condition_or_raise(
                lambda: (
                    not bool(canvas.property("interactionActive"))
                    and not bool(canvas.property("transientDegradedWindowActive"))
                    and bool(canvas.property("highQualityRendering"))
                    and bool(shadow_item.property("visible"))
                    and bool(background.property("effectiveShowGrid"))
                    and bool(minimap_overlay.property("minimapContentVisible"))
                ),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for max-performance wheel-zoom recovery.",
            )
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))
            assert bool(background.property("effectiveShowGrid"))
            assert bool(minimap_overlay.property("minimapContentVisible"))
            assert bool(minimap_viewport.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_minimap_keeps_node_geometry_static_when_center_changes(self) -> None:
        self._run_qml_probe(
            "graph-canvas-minimap-center-stability",
            """
            from tests.qt_wait import wait_for_condition_or_raise

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)
            scene.add_node_from_type("core.logger", 460.0, 280.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": {
                        "graphics_show_grid": True,
                        "graphics_show_minimap": True,
                        "graphics_minimap_expanded": True,
                        "graphics_node_shadow": True,
                        "graphics_shadow_strength": 70,
                        "graphics_shadow_softness": 50,
                        "graphics_shadow_offset": 4,
                        "graphics_performance_mode": "full_fidelity",
                        "snap_to_grid_enabled": False,
                        "snap_grid_size": 20.0,
                    },
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            minimap_viewport = canvas.findChild(QObject, "graphCanvasMinimapViewport")
            minimap_viewport_rect = canvas.findChild(QObject, "graphCanvasMinimapViewportRect")
            minimap_node_content = canvas.findChild(QObject, "graphCanvasMinimapNodeContent")
            assert minimap_viewport is not None
            assert minimap_viewport_rect is not None
            assert minimap_node_content is not None

            wait_for_condition_or_raise(
                lambda: int(minimap_viewport.property("_nodeDelegateCreationCount")) == 2,
                timeout_ms=120,
                app=app,
                timeout_message="Timed out waiting for minimap node delegates to settle.",
            )

            baseline_node_key = str(minimap_viewport.property("nodeGeometryCacheKey"))
            baseline_creation_count = int(minimap_viewport.property("_nodeDelegateCreationCount"))
            baseline_node_x = float(minimap_node_content.property("x"))
            baseline_node_y = float(minimap_node_content.property("y"))
            baseline_node_scale = float(minimap_node_content.property("scale"))
            baseline_rect_key = str(minimap_viewport_rect.property("geometryKey"))
            baseline_rect_updates = int(minimap_viewport_rect.property("_geometryUpdateCount"))

            view.centerOn(160.0, 80.0)
            app.processEvents()
            view.centerOn(260.0, 210.0)
            app.processEvents()

            assert str(minimap_viewport.property("nodeGeometryCacheKey")) == baseline_node_key
            assert int(minimap_viewport.property("_nodeDelegateCreationCount")) == baseline_creation_count
            assert abs(float(minimap_node_content.property("x")) - baseline_node_x) < 0.001
            assert abs(float(minimap_node_content.property("y")) - baseline_node_y) < 0.001
            assert abs(float(minimap_node_content.property("scale")) - baseline_node_scale) < 1e-6
            assert str(minimap_viewport_rect.property("geometryKey")) != baseline_rect_key
            assert int(minimap_viewport_rect.property("_geometryUpdateCount")) > baseline_rect_updates

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_media_performance_mode_uses_proxy_surface_during_wheel_zoom_and_recovers(self) -> None:
        self._run_qml_probe(
            "graph-canvas-media-max-performance-wheel-cache",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage
            from tests.qt_wait import wait_for_condition_or_raise

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "canvas-proxy-image.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                model = GraphModel()
                registry = build_default_registry()
                workspace_id = model.active_workspace.workspace_id
                scene = GraphSceneBridge()
                scene.set_workspace(model, registry, workspace_id)
                node_id = scene.add_node_from_type("passive.media.image_panel", 120.0, 140.0)
                scene.set_node_property(node_id, "source_path", str(image_path))
                scene.set_node_property(node_id, "caption", "Proxy preview")
                scene.set_node_property(node_id, "fit_mode", "contain")

                view = ViewportBridge()
                view.set_viewport_size(1280.0, 720.0)

                canvas = create_component(
                    graph_canvas_qml_path,
                    {
                        "mainWindowBridge": {
                            "graphics_show_grid": True,
                            "graphics_show_minimap": True,
                            "graphics_minimap_expanded": True,
                            "graphics_node_shadow": True,
                            "graphics_shadow_strength": 70,
                            "graphics_shadow_softness": 50,
                            "graphics_shadow_offset": 4,
                            "graphics_performance_mode": "max_performance",
                            "snap_to_grid_enabled": False,
                            "snap_grid_size": 20.0,
                        },
                        "sceneBridge": scene,
                        "viewBridge": view,
                        "width": 1280.0,
                        "height": 720.0,
                    },
                )
                node_cards = [
                    card for card in named_child_items(canvas, "graphNodeCard")
                    if str(card.property("surfaceFamily")) == "media"
                ]
                assert len(node_cards) == 1

                node_card = node_cards[0]
                loader = node_card.findChild(QObject, "graphNodeSurfaceLoader")
                surface = node_card.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = node_card.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = node_card.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None

                wait_for_condition_or_raise(
                    lambda: str(surface.property("previewState")) == "ready",
                    timeout_ms=600,
                    app=app,
                    timeout_message="Timed out waiting for media preview to reach ready state.",
                )
                assert node_card.property("resolvedQualityTier") == "full"
                assert not bool(node_card.property("proxySurfaceRequested"))
                assert not bool(surface.property("proxySurfaceActive"))
                assert not bool(loader.property("proxySurfaceActive"))
                assert not bool(proxy_preview.property("visible"))
                assert bool(applied_viewport.property("visible"))

                applied = canvas.applyWheelZoom(
                    {"x": 640.0, "y": 360.0, "angleDelta": {"y": 120}, "inverted": False}
                )
                assert applied is True

                wait_for_condition_or_raise(
                    lambda: (
                        bool(canvas.property("transientDegradedWindowActive"))
                        and bool(node_card.property("viewportInteractionCacheActive"))
                        and not bool(node_card.property("snapshotReuseActive"))
                        and node_card.property("resolvedQualityTier") == "proxy"
                        and bool(node_card.property("proxySurfaceRequested"))
                        and bool(surface.property("proxySurfaceActive"))
                        and bool(loader.property("proxySurfaceActive"))
                        and bool(proxy_preview.property("visible"))
                        and not bool(applied_viewport.property("visible"))
                    ),
                    timeout_ms=240,
                    app=app,
                    timeout_message="Timed out waiting for media viewport proxy activation.",
                )

                wait_for_condition_or_raise(
                    lambda: (
                        not bool(canvas.property("interactionActive"))
                        and not bool(canvas.property("transientDegradedWindowActive"))
                        and not bool(node_card.property("viewportInteractionCacheActive"))
                        and node_card.property("resolvedQualityTier") == "full"
                        and not bool(node_card.property("proxySurfaceRequested"))
                        and not bool(surface.property("proxySurfaceActive"))
                        and not bool(loader.property("proxySurfaceActive"))
                        and not bool(proxy_preview.property("visible"))
                        and bool(applied_viewport.property("visible"))
                    ),
                    timeout_ms=400,
                    app=app,
                    timeout_message="Timed out waiting for media viewport proxy recovery.",
                )

                canvas.deleteLater()
                app.processEvents()
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_canvas_media_performance_mode_uses_proxy_surface_during_mutation_burst_and_recovers(self) -> None:
        self._run_qml_probe(
            "graph-canvas-media-max-performance-mutation-proxy",
            """
            import tempfile

            from PyQt6.QtGui import QColor, QImage
            from tests.qt_wait import wait_for_condition_or_raise

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "canvas-mutation-proxy-image.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                model = GraphModel()
                registry = build_default_registry()
                workspace_id = model.active_workspace.workspace_id
                scene = GraphSceneBridge()
                scene.set_workspace(model, registry, workspace_id)
                node_id = scene.add_node_from_type("passive.media.image_panel", 120.0, 140.0)
                scene.set_node_property(node_id, "source_path", str(image_path))
                scene.set_node_property(node_id, "caption", "Mutation proxy preview")
                scene.set_node_property(node_id, "fit_mode", "contain")

                view = ViewportBridge()
                view.set_viewport_size(1280.0, 720.0)

                canvas = create_component(
                    graph_canvas_qml_path,
                    {
                        "mainWindowBridge": {
                            "graphics_show_grid": True,
                            "graphics_show_minimap": True,
                            "graphics_minimap_expanded": True,
                            "graphics_node_shadow": True,
                            "graphics_shadow_strength": 70,
                            "graphics_shadow_softness": 50,
                            "graphics_shadow_offset": 4,
                            "graphics_performance_mode": "max_performance",
                            "snap_to_grid_enabled": False,
                            "snap_grid_size": 20.0,
                        },
                        "sceneBridge": scene,
                        "viewBridge": view,
                        "width": 1280.0,
                        "height": 720.0,
                    },
                )
                node_cards = [
                    card for card in named_child_items(canvas, "graphNodeCard")
                    if str(card.property("surfaceFamily")) == "media"
                ]
                assert len(node_cards) == 1

                node_card = node_cards[0]
                loader = node_card.findChild(QObject, "graphNodeSurfaceLoader")
                surface = node_card.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = node_card.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = node_card.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None

                wait_for_condition_or_raise(
                    lambda: str(surface.property("previewState")) == "ready",
                    timeout_ms=600,
                    app=app,
                    timeout_message="Timed out waiting for media preview to reach ready state.",
                )
                assert node_card.property("resolvedQualityTier") == "full"
                assert not bool(node_card.property("proxySurfaceRequested"))
                assert not bool(surface.property("proxySurfaceActive"))
                assert not bool(loader.property("proxySurfaceActive"))
                assert not bool(proxy_preview.property("visible"))
                assert bool(applied_viewport.property("visible"))

                scene.add_node_from_type("core.logger", 360.0, 210.0)
                app.processEvents()

                node_cards = [
                    card for card in named_child_items(canvas, "graphNodeCard")
                    if str(card.property("surfaceFamily")) == "media"
                ]
                assert len(node_cards) == 1
                node_card = node_cards[0]
                loader = node_card.findChild(QObject, "graphNodeSurfaceLoader")
                surface = node_card.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = node_card.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = node_card.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None

                wait_for_condition_or_raise(
                    lambda: (
                        bool(canvas.property("mutationBurstActive"))
                        and bool(canvas.property("transientDegradedWindowActive"))
                        and not bool(node_card.property("viewportInteractionCacheActive"))
                        and bool(node_card.property("snapshotReuseActive"))
                        and node_card.property("resolvedQualityTier") == "proxy"
                        and bool(node_card.property("proxySurfaceRequested"))
                        and bool(surface.property("proxySurfaceActive"))
                        and bool(loader.property("proxySurfaceActive"))
                        and bool(proxy_preview.property("visible"))
                        and not bool(applied_viewport.property("visible"))
                    ),
                    timeout_ms=240,
                    app=app,
                    timeout_message="Timed out waiting for media mutation proxy activation.",
                )

                wait_for_condition_or_raise(
                    lambda: (
                        not bool(canvas.property("mutationBurstActive"))
                        and not bool(canvas.property("transientDegradedWindowActive"))
                        and not bool(node_card.property("snapshotReuseActive"))
                        and node_card.property("resolvedQualityTier") == "full"
                        and not bool(node_card.property("proxySurfaceRequested"))
                        and not bool(surface.property("proxySurfaceActive"))
                        and not bool(loader.property("proxySurfaceActive"))
                        and not bool(proxy_preview.property("visible"))
                        and bool(applied_viewport.property("visible"))
                    ),
                    timeout_ms=400,
                    app=app,
                    timeout_message="Timed out waiting for media mutation proxy recovery.",
                )

                canvas.deleteLater()
                app.processEvents()
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_canvas_mutation_burst_performance_policy_tracks_scene_changes_and_recovers(self) -> None:
        self._run_qml_probe(
            "graph-canvas-mutation-burst-policy",
            """
            from tests.qt_wait import wait_for_condition_or_raise

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
            policy = canvas.findChild(QObject, "graphCanvasPerformancePolicy")
            node_cards = {
                card.property("nodeData")["node_id"]: card
                for card in named_child_items(canvas, "graphNodeCard")
            }
            assert policy is not None
            assert len(node_cards) == 1
            tracked_node_id = next(iter(node_cards))
            shadow_item = node_cards[tracked_node_id].findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None

            assert canvas.property("resolvedGraphicsPerformanceMode") == "full_fidelity"
            assert not bool(canvas.property("mutationBurstActive"))
            assert not bool(canvas.property("transientPerformanceActivityActive"))
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(canvas.property("shadowSimplificationActive"))
            assert bool(shadow_item.property("visible"))

            scene.add_node_from_type("core.logger", 360.0, 210.0)
            app.processEvents()
            node_cards = {
                card.property("nodeData")["node_id"]: card
                for card in named_child_items(canvas, "graphNodeCard")
            }
            shadow_item = node_cards[tracked_node_id].findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None

            assert bool(policy.property("mutationBurstActive"))
            assert bool(canvas.property("mutationBurstActive"))
            assert bool(canvas.property("transientPerformanceActivityActive"))
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(canvas.property("shadowSimplificationActive"))
            assert bool(shadow_item.property("visible"))

            wait_for_condition_or_raise(
                lambda: not bool(canvas.property("mutationBurstActive")) and bool(shadow_item.property("visible")),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for scene mutation burst policy to settle.",
            )
            assert not bool(canvas.property("transientPerformanceActivityActive"))
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(canvas.property("shadowSimplificationActive"))
            assert bool(shadow_item.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_max_performance_mutation_burst_uses_snapshot_reuse_and_recovers(self) -> None:
        self._run_qml_probe(
            "graph-canvas-max-performance-mutation-burst",
            """
            from tests.qt_wait import wait_for_condition_or_raise

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
                    "mainWindowBridge": {
                        "graphics_show_grid": True,
                        "graphics_show_minimap": True,
                        "graphics_minimap_expanded": True,
                        "graphics_node_shadow": True,
                        "graphics_shadow_strength": 70,
                        "graphics_shadow_softness": 50,
                        "graphics_shadow_offset": 4,
                        "graphics_performance_mode": "max_performance",
                        "snap_to_grid_enabled": False,
                        "snap_grid_size": 20.0,
                    },
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            background = canvas.findChild(QObject, "graphCanvasBackground")
            minimap_overlay = canvas.findChild(QObject, "graphCanvasMinimapOverlay")
            minimap_viewport = canvas.findChild(QObject, "graphCanvasMinimapViewport")
            assert shadow_item is not None
            assert background is not None
            assert minimap_overlay is not None
            assert minimap_viewport is not None

            assert canvas.property("resolvedGraphicsPerformanceMode") == "max_performance"
            assert not bool(canvas.property("mutationBurstActive"))
            assert not bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))

            scene.add_node_from_type("core.logger", 360.0, 210.0)
            app.processEvents()

            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 2
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None
            assert bool(canvas.property("mutationBurstActive"))
            assert bool(canvas.property("transientPerformanceActivityActive"))
            assert bool(canvas.property("transientDegradedWindowActive"))
            assert not bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert bool(node_card.property("snapshotReuseActive"))
            assert bool(node_card.property("effectiveTextureCacheActive"))
            assert not bool(shadow_item.property("visible"))
            assert not bool(background.property("effectiveShowGrid"))
            assert not bool(minimap_overlay.property("minimapContentVisible"))
            assert not bool(minimap_viewport.property("visible"))

            wait_for_condition_or_raise(
                lambda: (
                    not bool(canvas.property("mutationBurstActive"))
                    and not bool(canvas.property("transientDegradedWindowActive"))
                    and bool(canvas.property("highQualityRendering"))
                    and bool(shadow_item.property("visible"))
                    and bool(background.property("effectiveShowGrid"))
                    and bool(minimap_overlay.property("minimapContentVisible"))
                ),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for max-performance mutation burst recovery.",
            )
            assert not bool(node_card.property("viewportInteractionCacheActive"))
            assert not bool(node_card.property("snapshotReuseActive"))
            assert not bool(node_card.property("effectiveTextureCacheActive"))
            assert bool(shadow_item.property("visible"))
            assert bool(background.property("effectiveShowGrid"))
            assert bool(minimap_overlay.property("minimapContentVisible"))
            assert bool(minimap_viewport.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_viewport_interaction_cache_remains_viewport_only_not_port_drag(self) -> None:
        self._run_qml_probe(
            "graph-canvas-cache-scope",
            """
            from PyQt6.QtCore import QPointF

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
            assert len(node_cards) == 1
            node_card = node_cards[0]
            node_payload = node_card.property("nodeData")
            output_dot = named_child_items(node_card, "graphNodeOutputPortDot")[0]
            dot_center = output_dot.mapToItem(
                canvas,
                QPointF(output_dot.width() * 0.5, output_dot.height() * 0.5),
            )
            scene_x = canvas.screenToSceneX(dot_center.x())
            scene_y = canvas.screenToSceneY(dot_center.y())

            assert not bool(canvas.property("interactionActive"))
            assert not bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))

            canvas.beginPortWireDrag(
                str(node_payload["node_id"]),
                "exec_out",
                "out",
                scene_x,
                scene_y,
                dot_center.x(),
                dot_center.y(),
            )
            app.processEvents()

            assert canvas.property("wireDragState") is not None
            assert not bool(canvas.property("interactionActive"))
            assert not bool(canvas.property("viewportInteractionWorldCacheActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert not bool(node_card.property("viewportInteractionCacheActive"))

            assert canvas.cancelWireDrag() is True
            app.processEvents()
            assert canvas.property("wireDragState") is None

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )
