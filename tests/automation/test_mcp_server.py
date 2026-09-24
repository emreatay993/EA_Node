# Purpose: Drive corex-mcp through a real in-memory MCP session against a fake CorexClient; pin tools == catalog, resources, prompts, errors, images, CLI wiring.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_mcp_server.py
from __future__ import annotations

import asyncio
import copy
import json
import subprocess
import sys
import textwrap
import unittest
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

from ea_node_editor.automation import guidance, mcp_server, op_catalog
from ea_node_editor.automation.errors import APP_SHUTTING_DOWN, AutomationOpError, ERROR_CODES, NOT_FOUND

try:
    from mcp import types as mcp_types
    from mcp.shared.exceptions import McpError
    from mcp.shared.memory import create_connected_server_and_client_session
    from pydantic import AnyUrl
except ImportError:  # pragma: no cover - the [mcp] extra is optional
    MCP_AVAILABLE = False
else:
    MCP_AVAILABLE = True

REPO_ROOT = Path(__file__).resolve().parents[2]
# 1x1 transparent PNG.
TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
NODE_ADD_RESULT = {"node_id": "node_1", "node": {"node_id": "node_1", "type_id": "passive.flowchart.process", "title": "Mesh"}}
CAPTURE_RESULT = {
    "mode": "views",
    "fidelity": "offscreen_layout",
    "images": [
        {"path": "C:/tmp/view.png", "width": 1, "height": 1, "view_id": "view_1", "view_name": "Main", "png_base64": TINY_PNG_BASE64},
        {"path": "C:/tmp/no_inline.png", "width": 1, "height": 1, "view_id": "view_2", "view_name": "Other"},
    ],
}


class FakeCorexClient:
    """Records ``call`` invocations and answers with canned results or a designated error."""

    def __init__(
        self,
        *,
        results: Mapping[str, Mapping[str, Any]] | None = None,
        errors: Mapping[str, AutomationOpError] | None = None,
        handle: Any = None,
    ) -> None:
        self.calls: list[tuple[str, dict[str, Any], float]] = []
        self.results = {key: dict(value) for key, value in (results or {}).items()}
        self.errors = dict(errors or {})
        self.handle = handle
        self.closed_with: list[bool] = []

    def call(self, op: str, params: Mapping[str, Any] | None = None, *, timeout_s: float = 30.0) -> dict[str, Any]:
        self.calls.append((op, dict(params or {}), float(timeout_s)))
        if op in self.errors:
            raise self.errors[op]
        return copy.deepcopy(self.results.get(op, {"ok": True, "op": op}))

    def close(self, *, quit_owned_instance: bool = True) -> None:
        self.closed_with.append(bool(quit_owned_instance))


def _default_client() -> FakeCorexClient:
    return FakeCorexClient(
        results={"node.add": NODE_ADD_RESULT, "capture.screenshot": CAPTURE_RESULT},
        errors={"node.update": AutomationOpError(NOT_FOUND, "Node 'node_9' was not found.", details={"id": "node_9"})},
    )


def _run(server: Any, action: Callable[[Any], Awaitable[Any]]) -> Any:
    async def runner() -> Any:
        async with create_connected_server_and_client_session(server) as session:
            return await action(session)

    return asyncio.run(runner())


def _run_expecting_mcp_error(server: Any, action: Callable[[Any], Awaitable[Any]]) -> Any:
    """Return the ``McpError`` the request raised (caught in-session so the SDK task group never wraps it)."""

    async def guarded(session: Any) -> Any:
        try:
            await action(session)
        except McpError as exc:
            return exc
        return None

    return _run(server, guarded)


def _text_blocks(result: Any) -> list[str]:
    return [block.text for block in result.content if isinstance(block, mcp_types.TextContent)]


def _image_blocks(result: Any) -> list[Any]:
    return [block for block in result.content if isinstance(block, mcp_types.ImageContent)]


@unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed")
class McpSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _default_client()
        self.server = mcp_server.build_server(self.client)

    def test_server_name_and_instructions(self) -> None:
        self.assertEqual(self.server.name, mcp_server.SERVER_NAME)
        self.assertTrue(self.server.instructions)
        self.assertIn("corex_status", self.server.instructions)
        options = self.server.create_initialization_options()
        self.assertEqual(options.instructions, guidance.server_instructions())
        self.assertIsNotNone(options.capabilities.tools)
        self.assertIsNotNone(options.capabilities.resources)
        self.assertIsNotNone(options.capabilities.prompts)

    def test_list_tools_matches_catalog_exactly(self) -> None:
        result = _run(self.server, lambda session: session.list_tools())
        expected = [op.mcp_tool for op in op_catalog.mcp_tool_ops()]
        self.assertEqual(len(expected), 48)
        self.assertEqual([tool.name for tool in result.tools], expected)
        self.assertEqual(sorted(tool.name for tool in result.tools), sorted(expected))
        by_name = {tool.name: tool for tool in result.tools}
        for op in op_catalog.mcp_tool_ops():
            with self.subTest(tool=op.mcp_tool):
                tool = by_name[op.mcp_tool]
                self.assertEqual(tool.inputSchema, op.params)
                self.assertIn(op.summary.strip(), tool.description or "")
                if op.examples:
                    self.assertIn("Example:", tool.description or "")

    def test_call_tool_forwards_arguments_and_returns_json(self) -> None:
        arguments = {"type_id": "passive.flowchart.process", "x": 320, "y": 0, "title": "Mesh"}
        result = _run(self.server, lambda session: session.call_tool("node_add", arguments))
        self.assertFalse(result.isError)
        self.assertEqual(self.client.calls, [("node.add", arguments, mcp_server.DEFAULT_TOOL_TIMEOUT_S)])
        texts = _text_blocks(result)
        self.assertEqual(len(texts), 1)
        self.assertEqual(json.loads(texts[0]), NODE_ADD_RESULT)
        self.assertEqual(_image_blocks(result), [])

    def test_call_tool_adds_margin_to_op_timeout(self) -> None:
        _run(self.server, lambda session: session.call_tool("run_status", {"wait": True, "timeout_s": 5}))
        op, params, timeout = self.client.calls[-1]
        self.assertEqual(op, "run.status")
        self.assertEqual(params, {"wait": True, "timeout_s": 5})
        self.assertEqual(timeout, 5 + mcp_server.TOOL_TIMEOUT_MARGIN_S)

    def test_capture_screenshot_returns_image_content_and_slim_json(self) -> None:
        result = _run(self.server, lambda session: session.call_tool("capture_screenshot", {}))
        self.assertFalse(result.isError)
        images = _image_blocks(result)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].data, TINY_PNG_BASE64)
        self.assertEqual(images[0].mimeType, "image/png")
        texts = _text_blocks(result)
        self.assertEqual(len(texts), 1)
        self.assertNotIn(TINY_PNG_BASE64, texts[0])
        payload = json.loads(texts[0])
        self.assertEqual(payload["fidelity"], "offscreen_layout")
        self.assertNotIn("png_base64", payload["images"][0])
        self.assertTrue(payload["images"][0]["image_attached"])
        self.assertEqual(payload["images"][0]["path"], "C:/tmp/view.png")
        self.assertNotIn("image_attached", payload["images"][1])
        # The client's own result object is untouched.
        self.assertEqual(self.client.results["capture.screenshot"]["images"][0]["png_base64"], TINY_PNG_BASE64)

    def test_automation_error_becomes_is_error_json_envelope(self) -> None:
        result = _run(self.server, lambda session: session.call_tool("node_update", {"node_id": "node_9", "title": "x"}))
        self.assertTrue(result.isError)
        payload = json.loads(_text_blocks(result)[0])
        self.assertEqual(payload["code"], NOT_FOUND)
        self.assertIn("node_9", payload["message"])
        self.assertTrue(payload["hint"])
        self.assertEqual(payload["details"], {"id": "node_9"})
        self.assertFalse(payload["retryable"])

    def test_unknown_tool_is_an_error_result_without_a_client_call(self) -> None:
        result = _run(self.server, lambda session: session.call_tool("node_ad", {}))
        self.assertTrue(result.isError)
        payload = json.loads(_text_blocks(result)[0])
        self.assertEqual(payload["code"], "UNKNOWN_OP")
        self.assertIn("node_add", payload["details"]["suggestions"])
        self.assertEqual(self.client.calls, [])

    def test_list_resources_and_read_ops_resource(self) -> None:
        async def action(session: Any) -> tuple[Any, Any]:
            listed = await session.list_resources()
            ops = await session.read_resource(AnyUrl("corex://ops"))
            return listed, ops

        listed, ops = _run(self.server, action)
        uris = sorted(str(resource.uri).rstrip("/") for resource in listed.resources)
        self.assertEqual(uris, sorted(guidance.RESOURCE_URIS))
        self.assertTrue(all(resource.mimeType == "text/markdown" for resource in listed.resources))
        self.assertTrue(all(resource.name and resource.description for resource in listed.resources))
        self.assertEqual(len(ops.contents), 1)
        self.assertEqual(ops.contents[0].mimeType, "text/markdown")
        text = ops.contents[0].text
        for op in op_catalog.mcp_tool_ops():
            with self.subTest(tool=op.mcp_tool):
                self.assertIn(f"`{op.mcp_tool}` -> `{op.name}`", text)

    def test_read_guide_mentions_graph_apply_and_status(self) -> None:
        result = _run(self.server, lambda session: session.read_resource(AnyUrl("corex://guide")))
        text = result.contents[0].text
        self.assertIn("graph_apply", text)
        self.assertIn("corex_status", text)
        for code in ERROR_CODES:
            self.assertIn(f"`{code}`", text)

    def test_unknown_resource_raises_mcp_error(self) -> None:
        error = _run_expecting_mcp_error(self.server, lambda session: session.read_resource(AnyUrl("corex://nope")))
        self.assertIsInstance(error, McpError)
        self.assertIn("corex://guide", str(error))

    def test_prompts_are_listed_and_rendered_as_user_messages(self) -> None:
        async def action(session: Any) -> tuple[Any, Any, Any]:
            listed = await session.list_prompts()
            flowchart = await session.get_prompt("build_flowchart", {"description": "Mesh a bracket"})
            board = await session.get_prompt("annotate_board", {"topic": "Load cases"})
            return listed, flowchart, board

        listed, flowchart, board = _run(self.server, action)
        self.assertEqual([prompt.name for prompt in listed.prompts], list(guidance.prompt_names()))
        self.assertEqual(listed.prompts[0].arguments[0].name, "description")
        self.assertTrue(listed.prompts[0].arguments[0].required)
        self.assertEqual(len(flowchart.messages), 1)
        self.assertEqual(flowchart.messages[0].role, "user")
        self.assertIn("Mesh a bracket", flowchart.messages[0].content.text)
        self.assertIn("graph_apply", flowchart.messages[0].content.text)
        self.assertEqual(board.messages[0].role, "user")
        self.assertIn("Load cases", board.messages[0].content.text)
        self.assertIn("node_add_text", board.messages[0].content.text)

    def test_unknown_prompt_raises_mcp_error(self) -> None:
        error = _run_expecting_mcp_error(self.server, lambda session: session.get_prompt("nope", {}))
        self.assertIsInstance(error, McpError)
        self.assertIn("build_flowchart", str(error))


class ToolPlumbingTests(unittest.TestCase):
    def test_tool_timeout_uses_margin_or_default(self) -> None:
        self.assertEqual(mcp_server.tool_timeout_s(None), mcp_server.DEFAULT_TOOL_TIMEOUT_S)
        self.assertEqual(mcp_server.tool_timeout_s({}), mcp_server.DEFAULT_TOOL_TIMEOUT_S)
        self.assertEqual(mcp_server.tool_timeout_s({"timeout_s": 10}), 10 + mcp_server.TOOL_TIMEOUT_MARGIN_S)
        self.assertEqual(mcp_server.tool_timeout_s({"timeout_s": 0}), mcp_server.TOOL_TIMEOUT_MARGIN_S)
        self.assertEqual(mcp_server.tool_timeout_s({"timeout_s": True}), mcp_server.DEFAULT_TOOL_TIMEOUT_S)
        self.assertEqual(mcp_server.tool_timeout_s({"timeout_s": "5"}), mcp_server.DEFAULT_TOOL_TIMEOUT_S)

    def test_execute_tool_wraps_unexpected_exceptions_as_internal(self) -> None:
        class Broken:
            def call(self, op: str, params: Any, *, timeout_s: float) -> dict[str, Any]:
                raise RuntimeError("socket exploded")

        outcome = mcp_server.execute_tool(Broken(), "corex_status", {})
        self.assertTrue(outcome.is_error)
        payload = json.loads(outcome.text)
        self.assertEqual(payload["code"], "INTERNAL")
        self.assertIn("socket exploded", payload["message"])
        self.assertFalse(payload["retryable"])

    def test_execute_tool_passes_empty_params_for_missing_arguments(self) -> None:
        client = FakeCorexClient()
        outcome = mcp_server.execute_tool(client, "corex_status", None)
        self.assertFalse(outcome.is_error)
        self.assertEqual(client.calls, [("app.status", {}, mcp_server.DEFAULT_TOOL_TIMEOUT_S)])

    def test_tool_description_combines_summary_description_and_example(self) -> None:
        op = op_catalog.op_by_name("node.add")
        text = mcp_server.tool_description(op)
        self.assertTrue(text.startswith(op.summary))
        self.assertIn(op.description, text)
        self.assertIn('"passive.flowchart.process"', text)
        status = mcp_server.tool_description(op_catalog.op_by_name("workspace.list"))
        self.assertNotIn("Example:", status)

    def test_should_quit_only_owned_private_instances(self) -> None:
        cases = (
            (None, False),
            (SimpleNamespace(owned=False, private=False), False),
            (SimpleNamespace(owned=True, private=False), False),
            (SimpleNamespace(owned=False, private=True), False),
            (SimpleNamespace(owned=True, private=True), True),
        )
        for handle, expected in cases:
            with self.subTest(handle=handle):
                self.assertIs(mcp_server.should_quit_owned_instance(FakeCorexClient(handle=handle)), expected)


class GuidanceTests(unittest.TestCase):
    def test_instructions_are_short_and_mention_the_essentials(self) -> None:
        text = guidance.server_instructions()
        self.assertLessEqual(len(text.splitlines()), 40)
        for needle in ("corex_status", "corex://guide", "graph_apply", "top|right|bottom|left", "capture_screenshot", "corex_history", "corex_quit"):
            self.assertIn(needle, text)

    def test_resource_text_rejects_unknown_uri_and_normalizes_known_ones(self) -> None:
        with self.assertRaises(ValueError):
            guidance.resource_text("corex://nope")
        self.assertEqual(guidance.resource_text("corex://guide/"), guidance.resource_text("corex://guide"))
        for uri in guidance.RESOURCE_URIS:
            with self.subTest(uri=uri):
                self.assertTrue(guidance.resource_text(uri).startswith("# COREX"))
                self.assertTrue(guidance.resource_name(uri))
                self.assertTrue(guidance.resource_title(uri))
                self.assertTrue(guidance.resource_description(uri))

    def test_ops_resource_renders_params_flags_and_results_from_the_catalog(self) -> None:
        text = guidance.ops_text()
        self.assertIn("`graph_apply` -> `graph.apply`", text)
        self.assertIn("`type_id`: string, min length 1", text)
        self.assertIn("`runtime_behavior`: string, one of any|active|passive, default \"any\"", text)
        self.assertIn("$ref fields: `source_node_id`, `target_node_id`", text)
        self.assertIn("- flags: mutates graph, apply", text)
        self.assertIn("- flags: read-only, deferred", text)
        self.assertIn("result keys: `node_id`, `node`", text)
        self.assertIn("(keys: fill_color", text)

    def test_styles_resource_lists_keys_enums_and_aliases(self) -> None:
        text = guidance.styles_text()
        for needle in (
            "`gradient_color`",
            "`fill_color_end` -> `gradient_color`",
            "`stroke_color`",
            "`color` -> `stroke_color`",
            "`label_background` -> `label_background_color`",
            "`label_text_color`",
            "`color` -> `text_color`",
            "solid|dashed|dotted",
            "north|east|south|west|radial",
            "markdown|plain",
            "left|center|right|justify",
        ):
            self.assertIn(needle, text)
        for key in guidance.NODE_STYLE_KEYS:
            self.assertIn(f"`{key}`", text)
        self.assertNotIn("header_color", text)

    def test_node_types_resource_covers_builtin_passive_type_ids(self) -> None:
        from ea_node_editor.nodes.builtins import passive_annotation, passive_flowchart
        from ea_node_editor.nodes.builtins.media_panel import MEDIA_PANEL_TYPE_ID
        from ea_node_editor.nodes.builtins.web_viewer import WEB_PAGE_VIEWER_DISPLAY_MODES, WEB_PAGE_VIEWER_TYPE_ID

        text = guidance.node_types_text()
        builtin_ids = {
            getattr(module, name)
            for module in (passive_flowchart, passive_annotation)
            for name in dir(module)
            if name.endswith("_TYPE_ID")
        }
        self.assertEqual(builtin_ids, set(guidance.FLOWCHART_TYPE_IDS) | set(guidance.ANNOTATION_TYPE_IDS))
        for type_id in sorted(builtin_ids | {MEDIA_PANEL_TYPE_ID, WEB_PAGE_VIEWER_TYPE_ID, "io.path_pointer", "data.panel"}):
            with self.subTest(type_id=type_id):
                self.assertIn(f"`{type_id}`", text)
        self.assertIn("|".join(WEB_PAGE_VIEWER_DISPLAY_MODES), text)
        self.assertIn("top|right|bottom|left", text)
        self.assertIn("catalog_list_node_types", text)
        self.assertIn("content key `text`", text)

    def test_prompt_text_uses_arguments_and_rejects_unknown_names(self) -> None:
        self.assertIn("Mesh a bracket", guidance.prompt_text("build_flowchart", {"description": "Mesh a bracket"}))
        self.assertIn("the process the user describes", guidance.prompt_text("build_flowchart", None))
        self.assertIn("Load cases", guidance.prompt_text("annotate_board", {"topic": "Load cases"}))
        with self.assertRaises(ValueError):
            guidance.prompt_text("nope")
        self.assertEqual(guidance.prompt_names(), ("build_flowchart", "annotate_board"))


class CliTests(unittest.TestCase):
    def test_parse_args_defaults_and_overrides(self) -> None:
        args = mcp_server.parse_args([])
        self.assertEqual(args.mode, "auto")
        self.assertTrue(args.headless)
        self.assertIsNone(args.instance_id)
        self.assertFalse(mcp_server.parse_args(["--no-headless"]).headless)
        private = mcp_server.parse_args(["--mode", "private", "--instance-id", "abc"])
        self.assertEqual((private.mode, private.instance_id, private.headless), ("private", "abc", True))
        with self.assertRaises(SystemExit):
            mcp_server.parse_args(["--mode", "bogus"])

    @unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed")
    def test_main_private_launch_is_lazy_and_quits_owned_instance(self) -> None:
        client = FakeCorexClient(handle=SimpleNamespace(owned=True, private=True))
        launch = mock.Mock(return_value=client)
        connect = mock.Mock()
        seen: dict[str, Any] = {}

        async def fake_serve(server: Any) -> None:
            seen["name"] = server.name
            seen["launched_before_first_call"] = launch.called  # the MCP handshake never waits for COREX
            seen["outcome"] = mcp_server.execute_tool(_lazy_client_of(server), "corex_status", {})

        with mock.patch.object(mcp_server.CorexClient, "launch", launch), mock.patch.object(
            mcp_server.CorexClient, "connect", connect
        ), mock.patch.object(mcp_server, "_serve", fake_serve), mock.patch.object(
            mcp_server, "build_server", _capturing_build_server
        ):
            self.assertEqual(mcp_server.main(["--mode", "private", "--no-headless"]), 0)
        self.assertEqual(seen["name"], mcp_server.SERVER_NAME)
        self.assertFalse(seen["launched_before_first_call"])
        self.assertFalse(seen["outcome"].is_error)
        launch.assert_called_once_with("private", headless=False, instance_id=None)
        connect.assert_not_called()
        self.assertEqual(client.closed_with, [True])

    @unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed")
    def test_main_attach_never_quits_the_users_instance(self) -> None:
        client = FakeCorexClient(handle=None)
        connect = mock.Mock(return_value=client)

        async def fake_serve(server: Any) -> None:
            mcp_server.execute_tool(_lazy_client_of(server), "corex_status", {})

        with mock.patch.object(mcp_server.CorexClient, "connect", connect), mock.patch.object(
            mcp_server, "_serve", fake_serve
        ), mock.patch.object(mcp_server, "build_server", _capturing_build_server):
            self.assertEqual(mcp_server.main(["--mode", "attach", "--instance-id", "abc"]), 0)
        connect.assert_called_once_with(instance_id="abc")
        self.assertEqual(client.closed_with, [False])

    @unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed")
    def test_main_auto_attached_or_visible_instance_is_left_running(self) -> None:
        client = FakeCorexClient(handle=SimpleNamespace(owned=True, private=False))
        launch = mock.Mock(return_value=client)

        async def fake_serve(server: Any) -> None:
            mcp_server.execute_tool(_lazy_client_of(server), "corex_status", {})

        with mock.patch.object(mcp_server.CorexClient, "launch", launch), mock.patch.object(
            mcp_server, "_serve", fake_serve
        ), mock.patch.object(mcp_server, "build_server", _capturing_build_server):
            self.assertEqual(mcp_server.main([]), 0)
        launch.assert_called_once_with("auto", headless=True, instance_id=None)
        self.assertEqual(client.closed_with, [False])

    @unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed")
    def test_main_without_tool_calls_never_contacts_corex(self) -> None:
        launch = mock.Mock()
        connect = mock.Mock()

        async def fake_serve(server: Any) -> None:
            return None

        with mock.patch.object(mcp_server.CorexClient, "launch", launch), mock.patch.object(
            mcp_server.CorexClient, "connect", connect
        ), mock.patch.object(mcp_server, "_serve", fake_serve):
            self.assertEqual(mcp_server.main(["--mode", "private"]), 0)
        launch.assert_not_called()
        connect.assert_not_called()

    def test_lazy_client_reports_connect_failures_as_tool_errors(self) -> None:
        error = AutomationOpError(NOT_FOUND, "No live COREX automation instance was found.")
        lazy = mcp_server.LazyCorexClient(mock.Mock(side_effect=error))
        outcome = mcp_server.execute_tool(lazy, "corex_status", {})
        self.assertTrue(outcome.is_error)
        self.assertEqual(json.loads(outcome.text)["code"], NOT_FOUND)
        self.assertFalse(lazy.connected)

    def test_lazy_client_reconnects_after_a_lost_connection(self) -> None:
        lost = AutomationOpError(APP_SHUTTING_DOWN, "Connection lost.", retryable=False)
        first = FakeCorexClient(errors={"app.status": lost}, handle=SimpleNamespace(owned=True, private=True))
        second = FakeCorexClient()
        factory = mock.Mock(side_effect=[first, second])
        lazy = mcp_server.LazyCorexClient(factory)
        self.assertTrue(mcp_server.execute_tool(lazy, "corex_status", {}).is_error)
        self.assertEqual(first.closed_with, [True])
        self.assertFalse(lazy.connected)
        self.assertFalse(mcp_server.execute_tool(lazy, "corex_status", {}).is_error)
        self.assertEqual(factory.call_count, 2)
        lazy.close()
        self.assertEqual(second.closed_with, [False])


_REAL_BUILD_SERVER = mcp_server.build_server


def _capturing_build_server(client: Any) -> Any:
    server = _REAL_BUILD_SERVER(client)
    server._corex_test_client = client  # test hook: lets fake _serve drive tools through the lazy client
    return server


def _lazy_client_of(server: Any) -> Any:
    return server._corex_test_client


class OptionalDependencyGuardTests(unittest.TestCase):
    def test_module_imports_without_mcp_and_build_server_names_the_extra(self) -> None:
        code = textwrap.dedent(
            """
            import sys
            sys.modules["mcp"] = None
            import ea_node_editor.automation.mcp_server as mcp_server
            import ea_node_editor.automation.guidance as guidance
            assert guidance.server_instructions()
            assert guidance.resource_text("corex://ops")
            assert "mcp" not in {name.split(".")[0] for name in sys.modules if sys.modules[name] is not None}
            try:
                mcp_server.build_server(object())
            except RuntimeError as exc:
                print("RUNTIME_ERROR:" + str(exc))
            else:
                print("NO_ERROR")
            """
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("RUNTIME_ERROR:", completed.stdout)
        self.assertIn('.[mcp]', completed.stdout)
        self.assertNotIn("NO_ERROR", completed.stdout)


if __name__ == "__main__":
    unittest.main()
