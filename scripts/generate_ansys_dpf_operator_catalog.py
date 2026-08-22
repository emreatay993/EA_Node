from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    OPERATOR_CATALOG_PATH,
    render_ansys_dpf_operator_catalog,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the versioned Ansys DPF operator catalog.")
    parser.add_argument("--check", action="store_true", help="Fail if the committed catalog is stale.")
    parser.add_argument("--output", type=Path, default=OPERATOR_CATALOG_PATH)
    args = parser.parse_args(argv)

    expected = render_ansys_dpf_operator_catalog()
    if args.check:
        try:
            current = args.output.read_text(encoding="utf-8")
        except OSError:
            current = ""
        if current != expected:
            print(f"Ansys DPF operator catalog is stale: {args.output}", file=sys.stderr)
            return 1
        print(f"Ansys DPF operator catalog is current: {args.output}")
        return 0

    args.output.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Wrote Ansys DPF operator catalog: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
