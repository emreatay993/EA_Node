"""Generate Markdown documentation for every DPF operator available on a local DPF server.

Mirrors ``ansys.dpf.core.documentation.generate_operators_doc`` but owns the top-level
orchestration so the known issues in that module (``None`` category producing a bad path,
Windows-invalid filename characters, and an ``update_toc_tree`` that requires a pre-existing
``toc.yml``) do not surface here.

Usage::

    python scripts/generate_dpf_operator_docs.py --output_path ./docs/dpf_operator_docs \
        --include_private
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jinja2

from ansys.dpf import core as dpf
from ansys.dpf.core.documentation.generate_operators_doc import (
    fetch_doc_info,
    get_operator_routing_info,
    get_plugin_operators,
    initialize_server,
    update_categories,
    update_operator_descriptions,
    update_operator_index,
)
from ansys.dpf.core.dpf_operator import available_operator_names
from ansys.dpf.core.documentation import generate_operators_doc as _gen_module
from ea_node_editor.addons.ansys_dpf.doc_generation import (
    _DOC_INDEX_FILENAME,
    _UNCATEGORIZED,
    operator_doc_relative_path,
    sanitize_operator_doc_filename,
)

_TEMPLATE_DIR = Path(_gen_module.__file__).parent
_OPERATOR_TEMPLATE = _TEMPLATE_DIR / "operator_doc_template.j2"
_TOC_TEMPLATE = _TEMPLATE_DIR / "toc_template.j2"


def _write_operator_page(
    server: dpf.AnyServerType,
    operator_name: str,
    include_private: bool,
    output_path: Path,
    router_info: dict | None,
    template: jinja2.Template,
    index: dict[str, str],
) -> None:
    info = fetch_doc_info(server, operator_name)
    if not include_private and info["exposure"] == "private":
        return

    supported_file_types: dict[str, list[str] | str] = {}
    if router_info is not None:
        info["is_router"] = operator_name in router_info["router_map"]
        if info["is_router"]:
            for key in router_info["router_map"].get(operator_name, "").split(";"):
                namespace = router_info["namespace_ext_map"].get(key)
                if namespace:
                    supported_file_types.setdefault(namespace, []).append(key)
        for namespace, keys in supported_file_types.items():
            supported_file_types[namespace] = ", ".join(sorted(keys))
    else:
        info["is_router"] = False
    info["supported_file_types"] = supported_file_types

    scripting_name = info["scripting_info"]["scripting_name"]
    category = info["scripting_info"]["category"] or _UNCATEGORIZED
    file_name = sanitize_operator_doc_filename(scripting_name or operator_name)

    category_dir = output_path / "operator-specifications" / category
    category_dir.mkdir(parents=True, exist_ok=True)
    (category_dir / f"{file_name}.md").write_text(template.render(info), encoding="utf-8")
    index[operator_name] = operator_doc_relative_path(
        operator_name=operator_name,
        scripting_name=scripting_name,
        category=category,
    )


def _write_doc_index(output_path: Path, index: dict[str, str]) -> None:
    payload = {key: index[key] for key in sorted(index)}
    (output_path / _DOC_INDEX_FILENAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_toc(output_path: Path) -> None:
    specs_path = output_path / "operator-specifications"
    data = []
    for folder in sorted(specs_path.iterdir()):
        if not folder.is_dir():
            continue
        operators = [
            {
                "operator_name": file.stem.replace("_", " "),
                "file_path": f"{folder.name}/{file.name}",
            }
            for file in sorted(folder.iterdir())
            if file.is_file()
            and file.suffix == ".md"
            and not file.name.endswith("_upd.md")
            and not file.name.endswith("_category.md")
        ]
        data.append({"category": folder.name, "operators": operators})

    template = jinja2.Template(_TOC_TEMPLATE.read_text())
    (output_path / "toc.yml").write_text(template.render(data=data), encoding="utf-8")


def generate(
    output_path: Path,
    ansys_path: str | None = None,
    include_composites: bool = False,
    include_sound: bool = False,
    include_private: bool = False,
    desired_plugin: str | None = None,
    verbose: bool = True,
) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    server = initialize_server(ansys_path, include_composites, include_sound, verbose)
    operators = (
        get_plugin_operators(server, desired_plugin)
        if desired_plugin
        else available_operator_names(server)
    )
    router_info = (
        get_operator_routing_info(server) if server.meet_version(required_version="11.0") else None
    )
    template = jinja2.Template(_OPERATOR_TEMPLATE.read_text())

    index: dict[str, str] = {}
    for operator_name in operators:
        _write_operator_page(
            server, operator_name, include_private, output_path, router_info, template, index
        )

    _write_toc(output_path)
    _write_doc_index(output_path, index)
    update_categories(output_path)
    update_operator_index(output_path)
    update_operator_descriptions(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_path", default="./docs/dpf_operator_docs")
    parser.add_argument("--ansys_path", default=None)
    parser.add_argument("--include_private", action="store_true")
    parser.add_argument("--include_composites", action="store_true")
    parser.add_argument("--include_sound", action="store_true")
    parser.add_argument("--plugin", default=None)
    args = parser.parse_args()

    generate(
        output_path=Path(args.output_path),
        ansys_path=args.ansys_path,
        include_composites=args.include_composites,
        include_sound=args.include_sound,
        include_private=args.include_private,
        desired_plugin=args.plugin,
    )


if __name__ == "__main__":
    main()
