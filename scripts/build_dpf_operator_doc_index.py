"""Emit ``docs/dpf_operator_docs/doc_index.json`` from the loaded DPF catalog.

The main doc generator [generate_dpf_operator_docs.py](./generate_dpf_operator_docs.py)
emits the JSON index as part of a full Markdown regeneration pass. This helper
produces the same file without regenerating the 2,270 Markdown pages — it walks
the generated operator definitions discovered by
``ea_node_editor.addons.ansys_dpf.operator_catalog`` and reuses each
operator's specification to derive the file path.

Run once (from the project root)::

    python scripts/build_dpf_operator_doc_index.py

The result is committed alongside the Markdown tree and consumed at runtime by
``ea_node_editor.help.dpf_operator_docs``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ea_node_editor.addons.ansys_dpf.doc_generation import (
    _DOC_INDEX_FILENAME,
    _UNCATEGORIZED,
    operator_doc_relative_path,
)
from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    _discovered_generated_operator_definitions,
)


def build_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for definition in _discovered_generated_operator_definitions():
        properties = getattr(definition.specification, "properties", {}) or {}
        scripting_name = str(properties.get("scripting_name", "") or "").strip()
        category = str(properties.get("category", "") or definition.family or "").strip() or _UNCATEGORIZED
        index[definition.operator_name] = operator_doc_relative_path(
            operator_name=definition.operator_name,
            scripting_name=scripting_name,
            category=category,
        )
    return index


def write_index(output_path: Path, index: dict[str, str]) -> Path:
    output_path.mkdir(parents=True, exist_ok=True)
    payload = {key: index[key] for key in sorted(index)}
    index_path = output_path / _DOC_INDEX_FILENAME
    index_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_path", default="./docs/dpf_operator_docs")
    args = parser.parse_args()

    index = build_index()
    index_path = write_index(Path(args.output_path), index)
    print(f"Wrote {len(index)} entries to {index_path}")


if __name__ == "__main__":
    main()
