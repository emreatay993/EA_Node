# Purpose: Prove the portable composed-view example, shared source and self-contained Save As.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_example.py
import json
from unittest.mock import patch

from scripts.generate_tabular_composer_example import generate
from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService
from ea_node_editor.ui.tabular_preview_provider import TabularPreviewProvider
from ea_node_editor.ui.shell.controllers.project_session_controller import ProjectSessionController
from tests.test_project_save_as_flow import _ProjectHostStub


def inspect_views(path, document, cache):
    loader = TabularLoaderCacheService(cache_dir=cache)
    provider = TabularPreviewProvider(service_factory=lambda: loader,
                                      project_context_provider=lambda: (str(path), document.get("metadata", {})))
    result = {}
    for node in document["workspaces"][0]["nodes"]:
        if node["type_id"] == "tabular.input":
            preview = provider.describe_preview(node["properties"])
            assert preview["state"] == "ready", preview
            result[node["node_id"]] = (preview["metadata"]["row_count"], preview["metadata"]["column_count"])
    return result


def test_example_has_three_views_sharing_one_portable_source(tmp_path):
    path = generate(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    assert len(document["metadata"]["artifact_store"]["artifacts"]) == 1
    result = inspect_views(path, document, tmp_path / "cache")
    assert result == {"input_temperature": (301, 4), "input_heatflow": (301, 3), "input_combined": (113, 6)}


def test_composed_views_reopen_after_self_contained_save_as(tmp_path):
    source = generate(tmp_path / "source")
    document = json.loads(source.read_text(encoding="utf-8"))
    host = _ProjectHostStub(project_path=str(source), persistent_document=document)
    controller = ProjectSessionController(host)
    destination = tmp_path / "copy" / "composed-copy.cxproj"
    destination.parent.mkdir()
    with patch.object(controller._project_files_service, "prompt_project_files_action", return_value=True), \
         patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(str(destination), "COREX Project (*.cxproj)")), \
         patch("PyQt6.QtWidgets.QMessageBox.warning"):
        result = controller.save_project_as()
    assert result.status == "saved", result.reason_code
    copied = json.loads(destination.read_text(encoding="utf-8"))
    assert inspect_views(destination, copied, tmp_path / "cache-copy") == {"input_temperature": (301, 4), "input_heatflow": (301, 3), "input_combined": (113, 6)}
