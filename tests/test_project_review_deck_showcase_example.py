from __future__ import annotations

from pathlib import Path

import pytest

from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui.pptx_export import create_project_review_pptx
from ea_node_editor.ui.project_review_deck import (
    PROJECT_REVIEW_SLIDE_IMAGE,
    PROJECT_REVIEW_SLIDE_PDF,
    build_project_review_deck_plan,
    iter_project_review_slides,
    materialize_project_review_pptx_slides,
    selected_project_review_slides,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SHOWCASE_DIR = REPO_ROOT / "examples" / "project_review_deck_airworthiness"
PROJECT_PATH = SHOWCASE_DIR / "rotor_llp_review_showcase.cxproj"
TEMPLATE_PATH = SHOWCASE_DIR / "templates" / "corex_airworthiness_template.pptx"
EXPORTED_DECK_PATH = SHOWCASE_DIR / "exports" / "rotor_llp_review_showcase.pptx"


def _load_showcase():
    registry = build_default_registry()
    project = JsonProjectSerializer(registry=registry).load(str(PROJECT_PATH.resolve()))
    return project, registry


def _nodes_by_type(project) -> dict[str, list]:  # noqa: ANN001
    nodes: dict[str, list] = {}
    for workspace in project.workspaces.values():
        for node in workspace.nodes.values():
            nodes.setdefault(node.type_id, []).append(node)
    return nodes


def test_showcase_project_contains_expected_node_families() -> None:
    project, _registry = _load_showcase()
    workspaces = {workspace.name for workspace in project.workspaces.values()}
    nodes_by_type = _nodes_by_type(project)

    assert workspaces == {
        "Certification Review Map",
        "DPF Evidence Canvases",
        "Evidence Binder",
    }
    assert any(
        node.properties.get("body_format") == "markdown"
        for node in nodes_by_type["passive.annotation.sticky_note"]
    )
    assert any(
        node.properties.get("format") == "markdown"
        for node in nodes_by_type["passive.annotation.text"]
    )
    assert len(nodes_by_type["dpf.workflow.result_viewer"]) == 2
    assert {node.properties.get("result_name") for node in nodes_by_type["dpf.workflow.result_viewer"]} == {
        "displacement",
        "stress",
    }
    assert {
        node.properties.get("named_selection")
        for node in nodes_by_type["dpf.workflow.result_viewer"]
    } == {"BOLT_NODES"}
    assert {
        float(node.properties.get("time_values"))
        for node in nodes_by_type["dpf.workflow.result_viewer"]
    } == {2.0}
    assert nodes_by_type["passive.media.image_panel"]
    assert nodes_by_type["passive.media.pdf_panel"]
    assert nodes_by_type["web.page_viewer"]


def test_showcase_project_includes_reference_web_nodes() -> None:
    project, _registry = _load_showcase()
    web_urls = {
        node.properties.get("start_location")
        for workspace in project.workspaces.values()
        for node in workspace.nodes.values()
        if node.type_id == "web.page_viewer"
    }

    assert {
        "https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-engines-cs-e",
        "https://www.easa.europa.eu/en/document-library/product-certification-consultations/easa-cm-pifs-007",
        "https://www.easa.europa.eu/en/document-library/product-certification-consultations/integrity-nickel-powder-metallurgy-rotating",
        "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-33/subpart-E/section-33.70",
        "https://www.faa.gov/airports/resources/advisory_circulars/index.cfm/go/document.information/documentNumber/33.70-1",
        "https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/1042036",
        "https://dpf.docs.pyansys.com/version/stable/user_guide/index.html",
        "https://developer.ansys.com/docs/dpf",
    }.issubset(web_urls)
    assert "saved://local_traceability_guide_html" in web_urls


def test_showcase_project_review_plan_discovers_evidence_and_warnings(qapp) -> None:  # noqa: ANN001
    project, registry = _load_showcase()
    plan = build_project_review_deck_plan(
        project=project,
        project_path=PROJECT_PATH.resolve(),
        registry=registry,
    )
    evidence = {
        slide.artifact_id: slide
        for slide in iter_project_review_slides(plan)
        if slide.kind in {PROJECT_REVIEW_SLIDE_IMAGE, PROJECT_REVIEW_SLIDE_PDF}
    }

    assert "stress_hotspot_map_png" in evidence
    assert "displacement_envelope_png" in evidence
    assert "margin_summary_chart_png" in evidence
    assert "local_traceability_guide_preview_png" in evidence
    assert {artifact_id for artifact_id in evidence if artifact_id.startswith("web_")} >= {
        "web_01_preview_png",
        "web_02_preview_png",
        "web_03_preview_png",
        "web_04_preview_png",
        "web_05_preview_png",
        "web_06_preview_png",
        "web_07_preview_png",
        "web_08_preview_png",
    }
    assert evidence["compliance_memo_pdf"].kind == PROJECT_REVIEW_SLIDE_PDF
    assert evidence["compliance_memo_pdf"].page_number == 3
    assert evidence["compliance_memo_pdf"].page_count == 8
    assert evidence["fea_appendix_pdf"].kind == PROJECT_REVIEW_SLIDE_PDF
    assert evidence["fea_appendix_pdf"].page_number == 2
    assert evidence["fea_appendix_pdf"].page_count == 25

    warnings = "\n".join(plan.warnings)
    assert "unsupported evidence file type '.csv'" in warnings
    assert "unsupported evidence file type '.md'" in warnings
    assert "unsupported evidence file type '.html'" in warnings
    assert "external file paths are listed but not embedded" in warnings
    assert "file.rst" in warnings


def test_showcase_artifacts_record_skill_and_web_provenance() -> None:
    project, _registry = _load_showcase()
    artifact_store = project.metadata["artifact_store"]["artifacts"]

    assert artifact_store["web_01_preview_png"]["source_origin"] == "airworthiness-compliance-engineer"
    assert "cs-e-amendment-8_assets" in artifact_store["web_01_preview_png"]["source_asset"]
    assert artifact_store["web_05_preview_png"]["source_origin"] == "airworthiness-compliance-engineer"
    assert "ac-33-70-1-life-limited-parts" in artifact_store["web_05_preview_png"]["source_asset"]
    assert artifact_store["compliance_memo_pdf"]["source_origin"] == "airworthiness-compliance-engineer"
    assert artifact_store["fea_appendix_pdf"]["source_origin"] == "airworthiness-compliance-engineer"
    assert artifact_store["displacement_envelope_png"]["source_origin"] == "web:pyansys-docs"
    assert "Rotor_Blade_Inverse_solve_005" in artifact_store["displacement_envelope_png"]["source_asset"]
    assert artifact_store["stress_hotspot_map_png"]["source_origin"] == "web:pyansys-docs"
    assert "Rotor_Blade_Inverse_solve_006" in artifact_store["stress_hotspot_map_png"]["source_asset"]


def test_showcase_selected_evidence_materializes_to_template_deck(tmp_path: Path, qapp) -> None:  # noqa: ANN001
    pytest.importorskip("pptx")
    project, registry = _load_showcase()
    plan = build_project_review_deck_plan(
        project=project,
        project_path=PROJECT_PATH.resolve(),
        registry=registry,
    )
    selected = selected_project_review_slides(
        plan,
        [
            "summary:title",
            "artifact:saved:stress_hotspot_map_png",
            "artifact:saved:local_traceability_guide_preview_png",
            "artifact:saved:compliance_memo_pdf",
            "artifact:saved:fea_appendix_pdf",
        ],
    )

    materialized = materialize_project_review_pptx_slides(
        slides=selected,
        canvas_images_by_slide_id={},
        temp_dir=tmp_path / "materialized",
    )
    output_path = tmp_path / "showcase-selected.pptx"
    create_project_review_pptx(
        slides=list(materialized.slides),
        output_path=output_path,
        template_path=TEMPLATE_PATH,
        slide_size="16:9 landscape",
    )

    assert not materialized.warnings
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert EXPORTED_DECK_PATH.exists()
    assert TEMPLATE_PATH.exists()
