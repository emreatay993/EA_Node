from __future__ import annotations

import pytest

from tests.main_window_shell.bridge_support import (
    GraphCanvasBridgeTests as _GraphCanvasBridgeTests,
)

pytestmark = pytest.mark.xdist_group("p03_bridge_contracts")


class GraphCanvasBridgeTests(_GraphCanvasBridgeTests):
    __test__ = True


__all__ = ["GraphCanvasBridgeTests"]
