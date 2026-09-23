# Purpose: corex-mcp stdio server: catalog-generated tools over CorexClient, inline screenshot images, corex:// guidance resources.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_mcp_server.py
"""MCP server for COREX automation.

Built on the low-level ``mcp.server.lowlevel.Server`` (``mcp>=1.10,<2``; pinned
because 2.x renames FastMCP -> MCPServer). Tools are generated from
``op_catalog.mcp_tool_ops()``: name = ``op.mcp_tool``, inputSchema = ``op.params``,
description = ``op.summary`` + ``op.description`` + first example. Tool calls run
``client.call(op.name, arguments)`` on a worker thread so the stdio loop stays
responsive; results come back as pretty JSON text and, for
``capture_screenshot``, one ``ImageContent`` per inline PNG (the base64 is
removed from the JSON copy). ``AutomationOpError`` becomes an ``isError`` result
whose text is the frozen ``{code, message, hint, details, retryable}`` envelope.
Input validation is left to COREX (``validate_input=False``) so agents always see
the catalog's ``INVALID_PARAMS`` problems and hints instead of the SDK's terse
jsonschema message.

CLI::

    corex-mcp --mode auto|attach|private [--headless/--no-headless] [--instance-id ID]
    python -m ea_node_editor.automation.mcp_server --mode auto

COREX is contacted lazily: ``main`` answers the MCP handshake immediately and the
first tool call attaches to (or spawns) the instance, so a 10-20 s private launch never
trips an MCP client's startup timeout. A lost connection (``APP_SHUTTING_DOWN``) drops
the client and the next tool call reconnects.

``mcp`` (and ``anyio``) are imported lazily inside ``build_server`` / ``main`` so
importing this module never requires the optional extra; a missing SDK raises a
``RuntimeError`` naming ``pip install -e ".[mcp]"``.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ea_node_editor import __version__
from ea_node_editor.automation import op_catalog
from ea_node_editor.automation.client import CorexClient
from ea_node_editor.automation.errors import APP_SHUTTING_DOWN, INTERNAL, UNKNOWN_OP, AutomationOpError
from ea_node_editor.automation.guidance import (
    PROMPTS,
    RESOURCE_MIME_TYPE,
    RESOURCE_URIS,
    prompt_description,
    prompt_text,
    resource_description,
    resource_name,
    resource_text,
    resource_title,
    server_instructions,
)
from ea_node_editor.automation.op_model import OpSpec

SERVER_NAME = "corex"
DEFAULT_TOOL_TIMEOUT_S = 120.0
TOOL_TIMEOUT_MARGIN_S = 30.0
SCREENSHOT_OP = "capture.screenshot"
PNG_MIME_TYPE = "image/png"
INLINE_IMAGE_KEY = "png_base64"
MCP_INSTALL_HINT = (
    "corex-mcp needs the optional MCP SDK (mcp>=1.10,<2). Install it into the COREX environment with "
    '`pip install -e ".[mcp]"` (or `pip install "mcp>=1.10,<2"`) and retry.'
)


@dataclass(slots=True)
class ToolOutcome:
    """SDK-free result of one tool call: JSON text, inline PNG payloads, error flag."""

    text: str
    images: list[str] = field(default_factory=list)
    is_error: bool = False


@dataclass(slots=True)
class _McpSdk:
    types: Any
    server_class: Any
    read_resource_contents: Any
    anyio: Any


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="corex-mcp", description="COREX automation MCP server (stdio).")
    parser.add_argument("--mode", choices=("auto", "attach", "private"), default="auto")
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--headless", dest="headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    return parser.parse_args(list(argv) if argv is not None else None)


# ------------------------------------------------------------------ tool plumbing


def tool_description(op: OpSpec) -> str:
    parts = [op.summary.strip()]
    if op.description.strip():
        parts.append(op.description.strip())
    if op.examples:
        parts.append("Example: " + json.dumps(op.examples[0], ensure_ascii=False, separators=(",", ":")))
    return "\n\n".join(parts)


def tool_timeout_s(arguments: Mapping[str, Any] | None) -> float:
    """Client-side wait: the op's own ``timeout_s`` plus a margin, else the default."""
    value = (arguments or {}).get("timeout_s")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return float(value) + TOOL_TIMEOUT_MARGIN_S
    return DEFAULT_TOOL_TIMEOUT_S


def split_inline_images(result: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Copy a capture result without its base64 payloads, returning them separately."""
    payload = copy.deepcopy(dict(result))
    images: list[str] = []
    rows = payload.get("images")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            data = row.get(INLINE_IMAGE_KEY)
            if isinstance(data, str) and data:
                images.append(data)
                del row[INLINE_IMAGE_KEY]
                row["image_attached"] = True
    return payload, images


def execute_tool(client: Any, name: str, arguments: Mapping[str, Any] | None) -> ToolOutcome:
    """Run one MCP tool through ``client.call``; never raises for automation errors."""
    op = op_catalog.op_for_mcp_tool(name)
    if op is None:
        names = [spec.mcp_tool for spec in op_catalog.mcp_tool_ops() if spec.mcp_tool]
        error = AutomationOpError(
            UNKNOWN_OP,
            f"Unknown MCP tool '{name}'.",
            hint="Use one of the listed tools (tools/list) or read corex://ops for the tool names.",
            details={"tool": str(name), "suggestions": difflib.get_close_matches(str(name), names, n=5, cutoff=0.4)},
            retryable=False,
        )
        return _error_outcome(error)
    params = dict(arguments or {})
    try:
        result = client.call(op.name, params, timeout_s=tool_timeout_s(params))
    except AutomationOpError as exc:
        return _error_outcome(exc)
    except Exception as exc:  # noqa: BLE001 - keep the MCP error envelope uniform for agents
        return _error_outcome(
            AutomationOpError(
                INTERNAL,
                f"{op.name} failed inside the MCP bridge: {exc}",
                hint="Check that the COREX instance is still running; restart corex-mcp if the connection is gone.",
                details={"op": op.name, "exception": type(exc).__name__},
                retryable=False,
            )
        )
    images: list[str] = []
    payload: Mapping[str, Any] = result
    if op.name == SCREENSHOT_OP:
        payload, images = split_inline_images(result)
    return ToolOutcome(text=_json_text(payload), images=images)


def _error_outcome(error: AutomationOpError) -> ToolOutcome:
    return ToolOutcome(text=_json_text(error.to_dict()), is_error=True)


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def should_quit_owned_instance(client: Any) -> bool:
    """Quit only private instances this process launched; visible/attached instances belong to the user."""
    handle = client.handle
    return bool(handle is not None and handle.owned and handle.private)


class LazyCorexClient:
    """Connects on the first tool call instead of before the MCP handshake.

    ``factory`` returns a connected ``CorexClient`` (attach / auto / private). Factory
    failures surface as ordinary tool errors (e.g. ``NOT_FOUND`` with a hint) so the MCP
    session stays up and the agent can retry. A lost connection (``APP_SHUTTING_DOWN``,
    not retryable) discards the client; the next call reconnects.
    """

    def __init__(self, factory: Callable[[], Any]) -> None:
        self._factory = factory
        self._client: Any = None
        self._lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._client is not None

    @property
    def handle(self) -> Any:
        client = self._client
        return client.handle if client is not None else None

    def _ensure(self) -> Any:
        with self._lock:
            if self._client is None:
                self._client = self._factory()
            return self._client

    def call(self, op: str, params: Mapping[str, Any] | None = None, *, timeout_s: float = DEFAULT_TOOL_TIMEOUT_S) -> dict[str, Any]:
        client = self._ensure()
        try:
            return client.call(op, params, timeout_s=timeout_s)
        except AutomationOpError as exc:
            if exc.code == APP_SHUTTING_DOWN and not exc.retryable:
                self._discard(client)
            raise

    def _discard(self, client: Any) -> None:
        with self._lock:
            if self._client is client:
                self._client = None
        try:
            client.close(quit_owned_instance=should_quit_owned_instance(client))
        except Exception:  # noqa: BLE001 - the connection is already gone
            pass

    def close(self, *, quit_owned_instance: bool = True) -> None:
        with self._lock:
            client, self._client = self._client, None
        if client is not None:
            client.close(quit_owned_instance=bool(quit_owned_instance) and should_quit_owned_instance(client))


# ------------------------------------------------------------------------ server


def _load_mcp() -> _McpSdk:
    try:
        import anyio
        import mcp.types as types
        from mcp.server.lowlevel import Server
        from mcp.server.lowlevel.helper_types import ReadResourceContents
    except ImportError as exc:
        raise RuntimeError(MCP_INSTALL_HINT) from exc
    return _McpSdk(types=types, server_class=Server, read_resource_contents=ReadResourceContents, anyio=anyio)


def build_server(client: Any) -> Any:
    """Return a low-level MCP ``Server`` whose tools/resources/prompts are backed by ``client``."""
    sdk = _load_mcp()
    types = sdk.types
    server = sdk.server_class(SERVER_NAME, version=__version__, instructions=server_instructions())

    @server.list_tools()
    async def _list_tools() -> list[Any]:
        return [
            types.Tool(name=op.mcp_tool, description=tool_description(op), inputSchema=copy.deepcopy(op.params))
            for op in op_catalog.mcp_tool_ops()
        ]

    @server.call_tool(validate_input=False)
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> Any:
        outcome = await sdk.anyio.to_thread.run_sync(execute_tool, client, name, arguments)
        content: list[Any] = [types.TextContent(type="text", text=outcome.text)]
        content.extend(types.ImageContent(type="image", data=data, mimeType=PNG_MIME_TYPE) for data in outcome.images)
        return types.CallToolResult(content=content, isError=outcome.is_error)

    @server.list_resources()
    async def _list_resources() -> list[Any]:
        return [
            types.Resource(
                uri=uri,
                name=resource_name(uri),
                title=resource_title(uri),
                description=resource_description(uri),
                mimeType=RESOURCE_MIME_TYPE,
            )
            for uri in RESOURCE_URIS
        ]

    @server.read_resource()
    async def _read_resource(uri: Any) -> list[Any]:
        return [sdk.read_resource_contents(content=resource_text(str(uri)), mime_type=RESOURCE_MIME_TYPE)]

    @server.list_prompts()
    async def _list_prompts() -> list[Any]:
        return [
            types.Prompt(
                name=prompt["name"],
                description=prompt["description"],
                arguments=[types.PromptArgument(**dict(argument)) for argument in prompt["arguments"]],
            )
            for prompt in PROMPTS
        ]

    @server.get_prompt()
    async def _get_prompt(name: str, arguments: dict[str, str] | None) -> Any:
        return types.GetPromptResult(
            description=prompt_description(name),
            messages=[types.PromptMessage(role="user", content=types.TextContent(type="text", text=prompt_text(name, arguments)))],
        )

    return server


async def _serve(server: Any) -> None:
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def create_client(args: argparse.Namespace) -> CorexClient:
    if args.mode == "attach":
        return CorexClient.connect(instance_id=args.instance_id)
    return CorexClient.launch(args.mode, headless=bool(args.headless), instance_id=args.instance_id)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        sdk = _load_mcp()  # fail before spawning COREX when the SDK is missing
    except RuntimeError as exc:
        print(f"corex-mcp: {exc}", file=sys.stderr)
        return 2
    client = LazyCorexClient(lambda: create_client(args))
    exit_code = 0
    try:
        server = build_server(client)
        sdk.anyio.run(_serve, server)
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        # Only private instances this server launched are quit; attached or auto-spawned
        # visible instances belong to the user and stay open.
        client.close(quit_owned_instance=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = [
    "DEFAULT_TOOL_TIMEOUT_S",
    "LazyCorexClient",
    "MCP_INSTALL_HINT",
    "SERVER_NAME",
    "TOOL_TIMEOUT_MARGIN_S",
    "ToolOutcome",
    "build_server",
    "create_client",
    "execute_tool",
    "main",
    "parse_args",
    "should_quit_owned_instance",
    "split_inline_images",
    "tool_description",
    "tool_timeout_s",
]
