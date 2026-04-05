from __future__ import annotations

import unittest

import pytest

from tests.graph_surface import (
    GraphSurfaceBoundaryContractTests,
    GraphSurfaceInlineEditorContractTests,
    GraphSurfaceInputContractTests,
    GraphSurfaceMediaAndScopeContractTests,
)

pytestmark = pytest.mark.xdist_group("p03_graph_surface")

__all__ = [
    "GraphSurfaceBoundaryContractTests",
    "GraphSurfaceInlineEditorContractTests",
    "GraphSurfaceInputContractTests",
    "GraphSurfaceMediaAndScopeContractTests",
]

if __name__ == "__main__":
    unittest.main()
