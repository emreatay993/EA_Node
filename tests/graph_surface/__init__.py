from __future__ import annotations

from tests.graph_surface.inline_editor_suite import (
    GraphSurfaceInlineEditorContractTests,
    PassiveGraphSurfaceInlineEditorTests,
)
from tests.graph_surface.media_and_scope_suite import (
    GraphSurfaceMediaAndScopeContractTests,
    PassiveGraphSurfaceMediaAndScopeTests,
)
from tests.graph_surface.passive_host_boundary_suite import (
    GraphSurfaceBoundaryContractTests,
    PassiveGraphSurfaceHostBoundaryTests,
)
from tests.graph_surface.passive_host_interaction_suite import PassiveGraphSurfaceHostTests
from tests.graph_surface.pointer_and_modal_suite import GraphSurfaceInputContractTests

__all__ = [
    "GraphSurfaceBoundaryContractTests",
    "GraphSurfaceInlineEditorContractTests",
    "GraphSurfaceInputContractTests",
    "GraphSurfaceMediaAndScopeContractTests",
    "PassiveGraphSurfaceHostBoundaryTests",
    "PassiveGraphSurfaceHostTests",
    "PassiveGraphSurfaceInlineEditorTests",
    "PassiveGraphSurfaceMediaAndScopeTests",
]
