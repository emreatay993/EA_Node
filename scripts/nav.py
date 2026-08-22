#!/usr/bin/env python3
# Purpose: Query the committed agent navigation indexes from one CLI so agents
#          get a compact, complete answer instead of grepping megabyte JSON.
# Map: subsystems/verification_testing_docs_hygiene
# Tests: tests/test_nav_cli.py
"""Agent navigation query CLI.

Consumes the generated indexes under ``docs/`` and answers lookups without
forcing an agent to read or grep the full 600 KB / 3.4 MB index files:

  - ``agent_route_index.json``      (feature-route / subsystem / testing maps)
  - ``qml_navigation_index.json``   (QML components, properties, signals)
  - ``source_test_file_index.md``   (source + test path inventory)

Examples::

    python scripts/nav.py find graph canvas
    python scripts/nav.py route graph-canvas-feature-recipes
    python scripts/nav.py qml ManagedToolTip
    python scripts/nav.py source run_controller --json
    python scripts/nav.py line docs/agent_maps/INDEX.md "Agent Quick-Start"

This tool is read-only. Regenerate the indexes with the ``scripts/generate_*``
generators; do not hand-edit them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE_INDEX_REL = "docs/agent_route_index.json"
QML_INDEX_REL = "docs/qml_navigation_index.json"
SOURCE_TEST_INDEX_REL = "docs/source_test_file_index.md"
MAX_DEFAULT_PATHS = 5
MAX_DEFAULT_OUTPUT_BYTES = 4096
MAX_VERIFICATION_CHARS = 640
MAX_QUERY_ECHO_CHARS = 512

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
    "work",
}

_QML_QUERY_CONTEXT_WORDS = {
    "component",
    "components",
    "interface",
    "owner",
    "owners",
    "qml",
    "test",
    "tests",
    "ui",
}

_TABLE_PATH_RE = re.compile(r"^\|\s*`(?P<path>[^`]+)`\s*\|")
_TEST_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(tests[\\/][A-Za-z0-9_./\\-]+\.py)"
)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_route_entries(repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    data = _load_json(repo_root / ROUTE_INDEX_REL)
    entries = data.get("entries", []) if isinstance(data, dict) else []
    return [e for e in entries if isinstance(e, dict)]


def load_qml_entries(repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    data = _load_json(repo_root / QML_INDEX_REL)
    entries = data.get("entries", []) if isinstance(data, dict) else []
    return [e for e in entries if isinstance(e, dict)]


def load_source_test_paths(repo_root: Path = REPO_ROOT) -> tuple[list[str], list[str]]:
    path = repo_root / SOURCE_TEST_INDEX_REL
    if not path.is_file():
        return [], []
    source: list[str] = []
    tests: list[str] = []
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Source Code"):
            section = "source"
            continue
        if line.startswith("## Test Modules"):
            section = "test"
            continue
        match = _TABLE_PATH_RE.match(line)
        if not match:
            continue
        (source if section == "source" else tests).append(match.group("path"))
    return source, tests


# --------------------------------------------------------------------------- #
# Matching / scoring
# --------------------------------------------------------------------------- #
def _tokens(query: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if token not in _STOP_WORDS
    ]


def _route_haystack(entry: dict[str, Any]) -> str:
    values = [
        entry.get("route_key", ""),
        entry.get("title", ""),
        entry.get("map_path", ""),
    ]
    for field in (
        "keywords",
        "source_candidates",
        "test_candidates",
        "qml_candidates",
        "aliases",
        "start_here",
    ):
        values.extend(entry.get(field, []))
    return " ".join(str(value).lower().replace("\\", "/") for value in values)


def _score_route(entry: dict[str, Any], tokens: Sequence[str]) -> int:
    route_key = str(entry.get("route_key", "")).lower()
    title = str(entry.get("title", "")).lower()
    map_path = str(entry.get("map_path", "")).lower()
    keywords = " ".join(str(k).lower() for k in entry.get("keywords", []))
    candidates = " ".join(
        str(c).lower()
        for field in ("source_candidates", "test_candidates", "qml_candidates")
        for c in entry.get(field, [])
    )
    aliases = entry.get("aliases", [])
    score = (
        10 * len(tokens)
        if any(_tokens(str(alias)) == list(tokens) for alias in aliases)
        else 0
    )
    for token in tokens:
        if token == route_key:
            score += 10
        if token in route_key:
            score += 4
        if token in title:
            score += 3
        if token in map_path:
            score += 2
        if token in keywords:
            score += 1
        if token in candidates:
            score += 1
    return score


def rank_routes(
    entries: Sequence[dict[str, Any]], query: str, *, require_all: bool = True
) -> list[dict[str, Any]]:
    tokens = _tokens(query)
    if not tokens:
        return []
    scored: list[tuple[dict[str, Any], int]] = []
    for entry in entries:
        if str(entry.get("kind")) == "qml_component":
            continue
        haystack_tokens = set(_tokens(_route_haystack(entry)))
        if require_all and not all(token in haystack_tokens for token in tokens):
            continue
        score = _score_route(entry, tokens)
        if score > 0:
            scored.append((entry, score))
    return [
        entry
        for entry, _score in sorted(
            scored,
            key=lambda item: (-item[1], str(item[0].get("route_key", ""))),
        )
    ]


def _qml_haystack(entry: dict[str, Any]) -> str:
    parts = [str(entry.get("component_name", "")), str(entry.get("path", ""))]
    parts.extend(str(a) for a in entry.get("aliases", []))
    for field in (
        "ids",
        "object_names",
        "properties",
        "signals",
        "functions",
        "instantiated_components",
        "dynamic_refs",
        "signal_handlers",
        "connections",
        "property_bindings",
        "local_component_refs",
        "symbol_anchors",
    ):
        for value in entry.get(field, []):
            if isinstance(value, dict):
                parts.extend(
                    str(value.get(key, ""))
                    for key in ("name", "anchor", "kind", "detail")
                )
    return " ".join(parts).lower().replace("\\", "/")


def _score_qml(entry: dict[str, Any], tokens: Sequence[str]) -> int:
    name = str(entry.get("component_name", "")).lower()
    haystack = _qml_haystack(entry)
    score = 0
    for token in tokens:
        if token == name:
            score += 10
        if token in name:
            score += 4
        elif token in haystack:
            score += 1
    return score


def search_routes(
    entries: Sequence[dict[str, Any]],
    query: str,
    limit: int = 8,
    *,
    require_all: bool = True,
    ties_only: bool = True,
) -> list[dict[str, Any]]:
    ranked = rank_routes(entries, query, require_all=require_all)
    if not ranked or not ties_only:
        return ranked[:limit]
    tokens = _tokens(query)
    top_score = _score_route(ranked[0], tokens)
    return [entry for entry in ranked if _score_route(entry, tokens) == top_score][
        :limit
    ]


def search_qml(
    entries: Sequence[dict[str, Any]], query: str, limit: int = 8
) -> list[dict[str, Any]]:
    tokens = _tokens(query)
    ranked = sorted(
        (e for e in entries if _score_qml(e, tokens) > 0),
        key=lambda e: _score_qml(e, tokens),
        reverse=True,
    )
    return ranked[:limit]


def search_source(
    source_paths: Sequence[str],
    test_paths: Sequence[str],
    route_entries: Sequence[dict[str, Any]],
    query: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    tokens = _tokens(query)
    if not tokens:
        return []

    def matches(path: str) -> bool:
        low = path.lower()
        return all(t in low for t in tokens)

    owners = _build_owner_index(route_entries)
    results: list[dict[str, Any]] = []
    for kind, paths in (("source", source_paths), ("test", test_paths)):
        for path in paths:
            if matches(path):
                results.append(
                    {"path": path, "kind": kind, "owner_maps": owners.get(path, [])}
                )
    return results[:limit]


def _build_owner_index(route_entries: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    for entry in route_entries:
        map_path = str(entry.get("map_path", ""))
        for field in ("source_candidates", "test_candidates", "qml_candidates"):
            for path in entry.get(field, []):
                owners.setdefault(str(path), [])
                if map_path and map_path not in owners[str(path)]:
                    owners[str(path)].append(map_path)
    return owners


def _same_qml_path(candidate: str, qml_path: str) -> bool:
    candidate = candidate.replace("\\", "/").strip().lstrip("./")
    qml_path = qml_path.replace("\\", "/").strip().lstrip("./")
    return candidate == qml_path or (
        "/" not in candidate and qml_path.endswith(f"/{candidate}")
    )


def search_qml_owner_routes(
    entries: Sequence[dict[str, Any]], query: str, limit: int = 5
) -> list[dict[str, Any]]:
    tokens = [
        token
        for token in _tokens(query)
        if token not in _QML_QUERY_CONTEXT_WORDS
    ]
    if not tokens:
        return []

    scored_components: list[tuple[dict[str, Any], int, int]] = []
    for entry in entries:
        if str(entry.get("kind")) != "qml_component":
            continue
        haystack = _route_haystack(entry)
        matched = sum(token in haystack for token in tokens)
        if matched:
            scored_components.append((entry, matched, _score_route(entry, tokens)))
    if not scored_components:
        return []
    scored_components.sort(
        key=lambda item: (
            -item[1],
            -item[2],
            str(item[0].get("route_key", "")),
        )
    )
    best_matched, best_score = scored_components[0][1:]
    if best_matched < min(2, len(tokens)):
        return []
    best_components = [
        entry
        for entry, matched, score in scored_components
        if (matched, score) == (best_matched, best_score)
    ]
    if len(tokens) == 1 and best_score <= 1 and len(best_components) > 1:
        return []

    map_entries = [entry for entry in entries if entry.get("kind") != "qml_component"]
    owners: list[dict[str, Any]] = []
    seen_maps: set[str] = set()
    kind_order = {"feature_route": 0, "subsystem": 1, "testing": 2}
    for component in best_components:
        qml_paths = [str(path) for path in component.get("qml_candidates", [])]
        if not qml_paths:
            qml_paths = [str(path) for path in component.get("source_candidates", [])]
        if not qml_paths:
            continue
        qml_path = qml_paths[0]
        matching_owners = [
            entry
            for entry in map_entries
            if any(
                _same_qml_path(str(candidate), qml_path)
                for field in ("qml_candidates", "source_candidates", "start_here")
                for candidate in entry.get(field, [])
            )
        ]
        if not matching_owners:
            matching_owners = [
                entry
                for entry in map_entries
                if entry.get("map_path") == component.get("map_path")
            ]
        matching_owners.sort(
            key=lambda entry: (
                not any(
                    _same_qml_path(str(candidate), qml_path)
                    for candidate in entry.get("start_here", [])
                ),
                kind_order.get(str(entry.get("kind")), 3),
                -_score_route(entry, tokens),
                str(entry.get("route_key", "")),
            )
        )
        for owner in matching_owners:
            map_path = str(owner.get("map_path", ""))
            if not map_path or map_path in seen_maps:
                continue
            routed_owner = dict(owner)
            routed_owner["start_here"] = [qml_path, *owner.get("start_here", [])]
            owners.append(routed_owner)
            seen_maps.add(map_path)
            if len(owners) >= limit:
                return owners
    return owners


# --------------------------------------------------------------------------- #
# Text rendering
# --------------------------------------------------------------------------- #
def _trunc_list(values: Sequence[Any], show: int = 6) -> str:
    values = list(values)
    if not values:
        return "-"
    head = ", ".join(str(v) for v in values[:show])
    extra = len(values) - show
    return f"{head}{f'  (+{extra})' if extra > 0 else ''}"


def _format_anchors(anchors: Sequence[Any], show: int = 8) -> str:
    parts = []
    for a in anchors[:show]:
        if isinstance(a, dict):
            name = a.get("name") or a.get("anchor") or ""
        else:
            name = str(a)
        parts.append(str(name))
    extra = len(anchors) - show
    return ", ".join(parts) + (f"  (+{extra})" if extra > 0 else "")


def format_route(entry: dict[str, Any]) -> str:
    lines = [f"{entry.get('route_key')}  ->  {entry.get('map_path')}"]
    if entry.get("source_candidates"):
        lines.append(f"  source: {_trunc_list(entry['source_candidates'])}")
    if entry.get("test_candidates"):
        lines.append(f"  tests:  {_trunc_list(entry['test_candidates'])}")
    if entry.get("qml_candidates"):
        lines.append(f"  qml:    {_trunc_list(entry['qml_candidates'])}")
    if entry.get("focused_verification"):
        lines.append(f"  verify: {_trunc_list(entry['focused_verification'], show=3)}")
    if entry.get("section_anchors"):
        lines.append(f"  anchors: {_format_anchors(entry['section_anchors'])}")
    return "\n".join(lines)


def format_qml(entry: dict[str, Any]) -> str:
    lines = [
        f"{entry.get('component_name')}.qml  ->  {entry.get('path')}",
        f"  root: {entry.get('root_component') or '-'}",
    ]
    if entry.get("symbol_anchors"):
        lines.append(f"  symbols: {_format_anchors(entry['symbol_anchors'])}")
    return "\n".join(lines)


def format_source(item: dict[str, Any]) -> str:
    owners = item.get("owner_maps") or []
    owner = f"  owner: {_trunc_list(owners, show=3)}" if owners else ""
    return f"[{item['kind']}] {item['path']}{owner}"


def _qml_anchor_spec(
    repo_root: Path, relative_path: str, anchor: str
) -> dict[str, Any] | None:
    for entry in load_qml_entries(repo_root):
        if str(entry.get("path", "")).replace("\\", "/") != relative_path:
            continue
        for spec in entry.get("symbol_anchors", []):
            if not isinstance(spec, dict):
                continue
            if anchor in {str(spec.get("anchor", "")), str(spec.get("name", ""))}:
                return spec
        break
    return None


def _declaration_patterns(suffix: str, symbol: str, kind: str) -> tuple[re.Pattern[str], ...]:
    escaped = re.escape(symbol)
    boundary = r"(?![A-Za-z0-9_])"
    if suffix == ".md":
        return (re.compile(rf"^\s{{0,3}}#{{1,6}}\s+{escaped}\s*$"),)
    if suffix == ".py":
        return (
            re.compile(rf"^\s*(?:async\s+)?(?:class|def)\s+{escaped}{boundary}"),
            re.compile(rf"^\s*{escaped}\s*(?::[^=]+)?="),
        )
    if suffix in {".qml", ".js"}:
        patterns: list[re.Pattern[str]] = []
        if kind == "target":
            patterns.append(re.compile(rf"^\s*target\s*:\s*{escaped}\s*$"))
        if kind == "localComponent":
            patterns.append(re.compile(rf"^\s*{escaped}\s*\{{"))
        patterns.extend(
            (
                re.compile(
                    rf"^\s*(?:(?:default|required|readonly)\s+)*"
                    rf"property\s+\S+\s+{escaped}{boundary}"
                ),
                re.compile(rf"^\s*(?:signal|function)\s+{escaped}{boundary}"),
                re.compile(rf"^\s*(?:const|let|var)\s+{escaped}{boundary}"),
                re.compile(rf"^\s*id\s*:\s*{escaped}\s*$"),
                re.compile(rf"^\s*objectName\s*:\s*['\"]{escaped}['\"]\s*$"),
                re.compile(rf"^\s*{escaped}\s*:\s*"),
                re.compile(rf"^\s*{escaped}\s*\{{"),
            )
        )
        return tuple(patterns)
    return (
        re.compile(rf"^\s*(?:class|def|function|signal)\s+{escaped}{boundary}"),
        re.compile(rf"^\s*{escaped}\s*[:=]"),
    )


def _fallback_code(line: str, suffix: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith(("//", "/*", "*", "#", "<!--")):
        return ""
    code = re.sub(r"(['\"])(?:\\.|[^\\])*?\1", "", line)
    if suffix == ".py":
        return code.split("#", 1)[0]
    if suffix in {".qml", ".js"}:
        return code.split("//", 1)[0]
    return code


def resolve_current_line(
    repo_root: Path, selected_path: str, anchor: str
) -> dict[str, Any] | None:
    selected_anchor = anchor.strip()
    if not selected_anchor:
        raise ValueError("anchor must not be blank")
    candidate = Path(selected_path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve()
    try:
        relative_path = resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("selected path must stay inside the repository") from exc
    if not resolved.is_file():
        return None

    lines = resolved.read_text(encoding="utf-8-sig").splitlines()
    suffix = resolved.suffix.casefold()
    spec = _qml_anchor_spec(repo_root, relative_path, selected_anchor) if suffix == ".qml" else None
    symbol = str(spec.get("name", selected_anchor)) if spec else selected_anchor
    kind = str(spec.get("kind", "")) if spec else ""
    for line_number, line in enumerate(lines, start=1):
        if any(pattern.search(line) for pattern in _declaration_patterns(suffix, symbol, kind)):
            return {
                "path": relative_path,
                "anchor": anchor,
                "line": line_number,
                "text": line.strip(),
            }

    escaped = re.escape(symbol)
    exact_anchor = re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])")
    fallback_hits = [
        (line_number, line)
        for line_number, line in enumerate(lines, start=1)
        if exact_anchor.search(_fallback_code(line, suffix))
    ]
    if len(fallback_hits) == 1:
        line_number, line = fallback_hits[0]
        return {
            "path": relative_path,
            "anchor": anchor,
            "line": line_number,
            "text": line.strip(),
        }
    return None


def _looks_like_path(value: str) -> bool:
    normalized = value.replace("\\", "/").strip().lstrip("./")
    return normalized.startswith(
        ("ea_node_editor/", "tests/", "docs/", "scripts/", "examples/", "web/")
    )


def _best_path(values: Sequence[str], tokens: Sequence[str], *, tests: bool) -> str:
    candidates = [
        str(value)
        for value in values
        if _looks_like_path(str(value))
        and str(value).replace("\\", "/").startswith("tests/") is tests
    ]
    if not candidates:
        return ""
    return max(
        enumerate(candidates),
        key=lambda item: (
            sum(token in item[1].lower().replace("\\", "/") for token in tokens),
            -item[0],
        ),
    )[1]


def _verification_test_paths(entry: dict[str, Any]) -> list[str]:
    return [
        match.group(1).replace("\\", "/")
        for command in entry.get("focused_verification", [])
        for match in _TEST_PATH_RE.finditer(str(command))
    ]


def build_owner_capsules(
    entries: Sequence[dict[str, Any]], query: str
) -> list[dict[str, Any]]:
    if not entries:
        return []
    tokens = _tokens(query)
    used_paths: set[str] = set()

    def reserve(path: str) -> str:
        if not path or path in used_paths or len(used_paths) >= MAX_DEFAULT_PATHS:
            return ""
        used_paths.add(path)
        return path

    def candidate_details(entry: dict[str, Any]) -> tuple[str, str, str]:
        start_here = [str(value) for value in entry.get("start_here", [])]
        source_path = _best_path(start_here, tokens, tests=False)
        focused_test = _best_path(start_here, tokens, tests=True)
        verification_commands = [
            str(value) for value in entry.get("focused_verification", [])
        ]
        if not focused_test:
            focused_test = _best_path(
                _verification_test_paths(entry),
                tokens,
                tests=True,
            )
        if not focused_test:
            focused_test = _best_path(
                [str(value) for value in entry.get("test_candidates", [])],
                tokens,
                tests=True,
            )
        if focused_test:
            verification = next(
                (
                    command[:MAX_VERIFICATION_CHARS]
                    for command in verification_commands
                    if focused_test in command.replace("\\", "/")
                ),
                f".\\venv\\Scripts\\python.exe -m pytest {focused_test} "
                "--ignore=venv -q",
            )
        else:
            verification = (
                verification_commands[0][:MAX_VERIFICATION_CHARS]
                if verification_commands
                else ""
            )
        return source_path, focused_test, verification

    primary = entries[0]
    primary_owner = reserve(str(primary.get("map_path", "")))
    if not primary_owner:
        return []
    source_path, focused_test, verification = candidate_details(primary)
    primary_capsule: dict[str, Any] = {
        "route_key": primary.get("route_key"),
        "title": primary.get("title"),
        "owner_map": primary_owner,
    }
    if reserved_source := reserve(source_path):
        primary_capsule["path"] = reserved_source
    if reserved_test := reserve(focused_test):
        primary_capsule["focused_test"] = reserved_test
    if verification:
        primary_capsule["verification"] = verification

    selected_entries: list[dict[str, Any]] = []
    capsules = [primary_capsule]
    for entry in entries[1:]:
        owner_map = reserve(str(entry.get("map_path", "")))
        if not owner_map:
            break
        selected_entries.append(entry)
        capsules.append(
            {
                "route_key": entry.get("route_key"),
                "title": entry.get("title"),
                "owner_map": owner_map,
            }
        )

    avoid_paths = [
        reserved
        for value in primary.get("do_not_start_here", [])
        if _looks_like_path(str(value))
        and (reserved := reserve(str(value)))
    ]
    if avoid_paths:
        primary_capsule["do_not_start_here"] = avoid_paths

    for entry, capsule in zip(selected_entries, capsules[1:]):
        source_path, focused_test, verification = candidate_details(entry)
        if reserved_source := reserve(source_path):
            capsule["path"] = reserved_source
        if reserved_test := reserve(focused_test):
            capsule["focused_test"] = reserved_test
            capsule["verification"] = verification
    return capsules


def _format_owner_capsule(capsule: dict[str, Any]) -> str:
    lines = [
        f"Owner: {capsule.get('title')}",
        f"  map: {capsule.get('owner_map')}",
    ]
    if capsule.get("path"):
        lines.append(f"  path: {capsule['path']}")
    if capsule.get("focused_test"):
        lines.append(f"  test: {capsule['focused_test']}")
    if capsule.get("verification"):
        lines.append(f"  verify: {capsule['verification']}")
    if capsule.get("do_not_start_here"):
        lines.append(
            f"  avoid: {_trunc_list(capsule['do_not_start_here'], show=2)}"
        )
    return "\n".join(lines)


def _emit_owner_capsules(
    query: str, capsules: Sequence[dict[str, Any]], as_json: bool
) -> None:
    if not capsules:
        if as_json:
            print(
                json.dumps(
                    {"query": query[:MAX_QUERY_ECHO_CHARS], "owners": []},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
        else:
            print("No matches.")
        return
    if as_json:
        output = json.dumps(
            {"query": query[:MAX_QUERY_ECHO_CHARS], "owners": list(capsules)},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    else:
        heading = "Tied owners:" if len(capsules) > 1 else "Likely owner:"
        output = heading + "\n" + "\n\n".join(
            _format_owner_capsule(capsule) for capsule in capsules
        )
    if len(output.encode("utf-8")) > MAX_DEFAULT_OUTPUT_BYTES:
        raise ValueError("owner capsule exceeded the 4 KB default-output budget")
    print(output)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def _emit(payload: Any, text_lines: Sequence[str], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(text_lines) if text_lines else "No matches.")


def cmd_route(args: argparse.Namespace, repo_root: Path) -> int:
    entries = search_routes(load_route_entries(repo_root), args.query, args.limit)
    _emit(entries, [format_route(e) + "\n" for e in entries], args.json)
    return 0


def cmd_qml(args: argparse.Namespace, repo_root: Path) -> int:
    entries = search_qml(load_qml_entries(repo_root), args.query, args.limit)
    _emit(entries, [format_qml(e) + "\n" for e in entries], args.json)
    return 0


def cmd_source(args: argparse.Namespace, repo_root: Path) -> int:
    source_paths, test_paths = load_source_test_paths(repo_root)
    items = search_source(
        source_paths, test_paths, load_route_entries(repo_root), args.query, args.limit
    )
    _emit(items, [format_source(i) for i in items], args.json)
    return 0


def cmd_line(args: argparse.Namespace, repo_root: Path) -> int:
    try:
        result = resolve_current_line(repo_root, args.path, args.anchor)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    if result is None:
        print("No matches.")
        return 1
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"{result['path']}:{result['line']}: {result['text']}")
    return 0


def cmd_find(args: argparse.Namespace, repo_root: Path) -> int:
    route_entries = load_route_entries(repo_root)
    if not args.expand:
        query_tokens = _tokens(args.query)
        routes = sorted(
            (
                entry
                for entry in route_entries
                if query_tokens
                and entry.get("kind") != "qml_component"
                and any(
                    _tokens(str(alias)) == query_tokens
                    for alias in entry.get("aliases", [])
                )
            ),
            key=lambda entry: str(entry.get("route_key", "")),
        )[: args.limit]
        if not routes:
            routes = search_qml_owner_routes(route_entries, args.query, args.limit)
        if not routes:
            routes = search_routes(route_entries, args.query, args.limit)
        _emit_owner_capsules(
            args.query, build_owner_capsules(routes, args.query), args.json
        )
        return 0

    qml_entries = load_qml_entries(repo_root)
    source_paths, test_paths = load_source_test_paths(repo_root)
    limit = args.limit
    routes = search_routes(
        route_entries,
        args.query,
        limit,
        require_all=False,
        ties_only=False,
    )
    qml = search_qml(qml_entries, args.query, limit)
    source = search_source(source_paths, test_paths, route_entries, args.query, limit)

    if args.json:
        print(
            json.dumps(
                {"routes": routes, "qml": qml, "source": source},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    blocks: list[str] = []
    if routes:
        blocks.append("== Routes ==\n" + "\n".join(format_route(e) + "\n" for e in routes))
    if qml:
        blocks.append("== QML ==\n" + "\n".join(format_qml(e) + "\n" for e in qml))
    if source:
        blocks.append("== Source/Test ==\n" + "\n".join(format_source(i) for i in source))
    print("\n".join(blocks) if blocks else "No matches.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler, default_limit, help_text in (
        ("find", cmd_find, 5, "search routes + QML + source/test"),
        ("route", cmd_route, 8, "search agent-map routes"),
        ("qml", cmd_qml, 8, "search QML components"),
        ("source", cmd_source, 12, "search source/test paths (with owner map)"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("query", nargs="+", help="search terms")
        p.add_argument("--limit", type=int, default=default_limit, help="max results")
        p.add_argument("--json", action="store_true", help="emit JSON instead of text")
        if name == "find":
            p.add_argument(
                "--expand",
                action="store_true",
                help="show broad route, QML, and source/test candidates",
            )
        p.set_defaults(handler=handler)
    line_parser = sub.add_parser(
        "line", help="resolve a current line by scanning one selected file"
    )
    line_parser.add_argument("path", help="repository-relative map, QML, or source path")
    line_parser.add_argument("anchor", nargs="+", help="symbol or Markdown heading")
    line_parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    line_parser.set_defaults(handler=cmd_line)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # Map/QML data can contain non-ASCII (arrows, em dashes); the Windows console
    # defaults to cp1252 and would crash on print. Force UTF-8 where possible.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "query"):
        args.query = " ".join(args.query) if isinstance(args.query, list) else args.query
    if hasattr(args, "anchor"):
        args.anchor = " ".join(args.anchor) if isinstance(args.anchor, list) else args.anchor
    repo_root = Path(args.repo_root).resolve()
    return args.handler(args, repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
