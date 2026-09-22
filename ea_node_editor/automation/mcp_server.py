# Purpose: corex-mcp stdio server: catalog-generated tools over CorexClient, inline screenshot images, corex:// guidance resources.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""MCP server (T10 owner: implement; T00 fixes the shape).

Built on the low-level ``mcp.server.Server`` (``mcp>=1.10,<2``; pinned because
2.x renames FastMCP -> MCPServer). Tools are generated from
``op_catalog.mcp_tool_ops()``: name = ``op.mcp_tool``, inputSchema = ``op.params``,
description = ``op.summary`` + ``op.description``. ``capture_screenshot`` returns
``ImageContent`` for each inline PNG in addition to the JSON text block.

CLI::

    corex-mcp --mode auto|attach|private [--headless/--no-headless] [--instance-id ID]

``mcp`` is imported lazily inside ``build_server``/``main`` so importing this
module never requires the optional extra.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

SERVER_NAME = "corex"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="corex-mcp", description="COREX automation MCP server (stdio).")
    parser.add_argument("--mode", choices=("auto", "attach", "private"), default="auto")
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--headless", dest="headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    return parser.parse_args(list(argv) if argv is not None else None)


def build_server(client: object) -> object:
    raise NotImplementedError("build_server is implemented in T10")


def main(argv: Sequence[str] | None = None) -> int:
    raise NotImplementedError("corex-mcp main is implemented in T10")


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["SERVER_NAME", "build_server", "main", "parse_args"]
