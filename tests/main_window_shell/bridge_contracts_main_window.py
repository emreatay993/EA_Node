from __future__ import annotations

import pytest

from tests.main_window_shell.bridge_support import (
    MainWindowGraphCanvasBridgeTests as _MainWindowGraphCanvasBridgeTests,
)

pytestmark = pytest.mark.xdist_group("p03_bridge_contracts")


class MainWindowGraphCanvasBridgeTests(_MainWindowGraphCanvasBridgeTests):
    __test__ = True


__all__ = ["MainWindowGraphCanvasBridgeTests"]
