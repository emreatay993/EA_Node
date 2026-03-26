from __future__ import annotations

from tests.workspace_library_controller_unit.support import *  # noqa: F401,F403


class WorkspaceLibraryControllerCoreOpsTests(WorkspaceLibraryControllerUnitTestBase):
    def test_request_connect_ports_delegates_and_wraps_result(self) -> None:
        host = _WorkspaceHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]

        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.workspace_graph_edit_controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]

        result = controller.request_connect_ports("node_a", "out", "node_b", "in")

        self.assertTrue(result.ok)
        self.assertTrue(result.payload)
        self.assertTrue(refreshed["value"])
        self.assertEqual(host._graph_interactions.calls, [("node_a", "out", "node_b", "in")])

    def test_undo_delegates_to_runtime_history_and_refreshes_scene(self) -> None:
        host = _UndoRedoHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.workspace_graph_edit_controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]

        undone = controller.undo()

        workspace_id = host.workspace_manager.active_workspace_id()
        self.assertTrue(undone)
        self.assertEqual(host.runtime_history.undo_calls, [workspace_id])
        self.assertEqual(host.scene.refreshed_workspaces, [workspace_id])
        self.assertTrue(refreshed["value"])

    def test_redo_returns_false_when_runtime_history_has_no_entry(self) -> None:
        host = _UndoRedoHostStub()
        host.runtime_history.redo_return = None
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.workspace_graph_edit_controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]

        redone = controller.redo()

        workspace_id = host.workspace_manager.active_workspace_id()
        self.assertFalse(redone)
        self.assertEqual(host.runtime_history.redo_calls, [workspace_id])
        self.assertEqual(host.scene.refreshed_workspaces, [])
        self.assertFalse(refreshed["value"])

    def test_cut_selected_nodes_routes_through_delete_selected_path(self) -> None:
        host = _ClipboardHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        delete_calls: list[list[object]] = []

        controller.workspace_graph_edit_controller.copy_selected_nodes_to_clipboard = lambda: True  # type: ignore[method-assign]

        def _delete_selected(edge_ids: list[object]) -> ControllerResult[bool]:
            delete_calls.append(list(edge_ids))
            return ControllerResult(True, payload=True)

        controller.workspace_graph_edit_controller.request_delete_selected_graph_items = _delete_selected  # type: ignore[method-assign]

        cut = controller.cut_selected_nodes_to_clipboard()

        self.assertTrue(cut)
        self.assertEqual(delete_calls, [[]])

    def test_paste_nodes_from_clipboard_offsets_from_original_position_and_refreshes(self) -> None:
        host = _ClipboardHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.workspace_graph_edit_controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]
        payload = self._valid_fragment_payload()
        controller.workspace_graph_edit_controller._read_graph_fragment_from_clipboard = lambda: payload  # type: ignore[method-assign]

        pasted = controller.paste_nodes_from_clipboard()

        self.assertTrue(pasted)
        self.assertEqual(host.scene.paste_calls, [(payload, 140.0, 240.0)])
        self.assertEqual(host.selected_node_changed.calls, 1)
        self.assertTrue(refreshed["value"])

    def test_paste_nodes_from_clipboard_offsets_consecutive_pastes(self) -> None:
        host = _ClipboardHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        payload = self._valid_fragment_payload()
        controller.workspace_graph_edit_controller._read_graph_fragment_from_clipboard = lambda: payload  # type: ignore[method-assign]
        controller.workspace_graph_edit_controller.refresh_workspace_tabs = lambda: None  # type: ignore[method-assign]

        first = controller.paste_nodes_from_clipboard()
        second = controller.paste_nodes_from_clipboard()

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertEqual(host.scene.paste_calls[0], (payload, 140.0, 240.0))
        self.assertEqual(host.scene.paste_calls[1], (payload, 180.0, 280.0))

    def test_paste_nodes_from_clipboard_is_noop_when_clipboard_is_missing(self) -> None:
        host = _ClipboardHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.workspace_graph_edit_controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]
        controller.workspace_graph_edit_controller._read_graph_fragment_from_clipboard = lambda: None  # type: ignore[method-assign]

        pasted = controller.paste_nodes_from_clipboard()

        self.assertFalse(pasted)
        self.assertEqual(host.scene.paste_calls, [])
        self.assertEqual(host.selected_node_changed.calls, 0)
        self.assertFalse(refreshed["value"])

    def test_jump_to_graph_node_opens_scope_before_focus(self) -> None:
        host = _ScopeFocusHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        workspace_id = host.workspace_manager.active_workspace_id()
        node_id = host.model.add_node(
            workspace_id,
            type_id="core.logger",
            title="Target",
            x=20.0,
            y=10.0,
        ).node_id

        controller.workspace_navigation_controller.reveal_parent_chain = lambda _workspace_id, _node_id: []  # type: ignore[method-assign]
        controller.workspace_navigation_controller.center_on_selection = lambda: True  # type: ignore[method-assign]

        jumped = controller.jump_to_graph_node(workspace_id, node_id)

        self.assertTrue(jumped)
        self.assertEqual(host.scene.open_scope_calls, [node_id])
        self.assertEqual(host.scene.focus_calls, [node_id])

    def test_focus_failed_node_opens_scope_for_each_focus_candidate(self) -> None:
        host = _ScopeFocusHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        workspace_id = host.workspace_manager.active_workspace_id()

        controller.workspace_navigation_controller.reveal_parent_chain = lambda _workspace_id, _node_id: ["ancestor_a"]  # type: ignore[method-assign]
        focused: list[str] = []
        controller.workspace_navigation_controller.center_on_node = lambda node_id: focused.append(node_id) or True  # type: ignore[method-assign]
        host.scene.focus_results = {
            "node_target": _PointStub(5.0, 7.0),
            "ancestor_a": _PointStub(9.0, 3.0),
        }

        controller.focus_failed_node(workspace_id, "node_target", "")

        self.assertEqual(host.scene.open_scope_calls, ["node_target"])
        self.assertEqual(host.scene.focus_calls, ["node_target"])
        self.assertEqual(focused, ["node_target"])

    def test_on_node_property_changed_refreshes_shell_payload_for_direct_child_pin(self) -> None:
        host = _PinPropertyHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.workspace_graph_edit_controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]
        workspace_id = host.workspace_manager.active_workspace_id()
        shell_node = host.model.add_node(
            workspace_id,
            type_id="core.subnode",
            title="Subnode",
            x=40.0,
            y=50.0,
        )
        pin_node = host.model.add_node(
            workspace_id,
            type_id="core.subnode_input",
            title="Subnode Input",
            x=80.0,
            y=120.0,
        )
        pin_node.parent_node_id = shell_node.node_id

        controller.on_node_property_changed(pin_node.node_id, "label", "Data In")

        self.assertEqual(host.scene.property_calls, [(pin_node.node_id, "label", "Data In")])
        self.assertEqual(host.scene.refreshed_workspaces, [workspace_id])
        self.assertEqual(host.selected_node_changed.calls, 1)
        self.assertTrue(refreshed["value"])

    def test_on_node_property_changed_skips_shell_refresh_for_non_pin_nodes(self) -> None:
        host = _PinPropertyHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        controller.workspace_graph_edit_controller.refresh_workspace_tabs = lambda: None  # type: ignore[method-assign]
        workspace_id = host.workspace_manager.active_workspace_id()
        logger_node = host.model.add_node(
            workspace_id,
            type_id="core.logger",
            title="Logger",
            x=20.0,
            y=20.0,
        )

        controller.on_node_property_changed(logger_node.node_id, "message", "hello")

        self.assertEqual(host.scene.property_calls, [(logger_node.node_id, "message", "hello")])
        self.assertEqual(host.scene.refreshed_workspaces, [])
