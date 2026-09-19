# Purpose: Expose an opt-in TypeSafe navigation CLI with bounded, freshness-checked evidence packs.
# Map: subsystems/verification_testing_docs_hygiene.md
# Tests: tests/test_nav_assist.py
"""Run ``python -m scripts.nav_assist '<task>' [--json]``; suggestions are advisory."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from time import perf_counter

from scripts.nav_assist_client import MODEL, ServiceUnavailable, TypeSafeClient
from scripts.nav_assist_inventory import REPO_ROOT, CandidateInventory, Evidence, ExactMatch, InventoryUnavailable, StaleEvidenceError, build_inventory
from scripts.nav_assist_selection import PROMPT_VERSION, Selection, evidence_record, lexical_scores, owner_probability, rank_paths, safe_text, safe_value

MAX_JSON_CHARS = 24_000
MAX_TEXT_CHARS = 16_000
MAX_QUERY_CHARS = 2_000
MIN_EXCERPT_LINES = 5
ADVISORY = "Suggestions are advisory. Inspect current source and focused tests before choosing an owner or making changes."


def _base(query: str) -> dict:
    return {"schema_version": 1, "status": "unresolved", "mode": "local_fallback", "query": query,
            "sources": [], "tests": [], "uncertainty": [ADVISORY], "gaps": [], "error": None,
            "model": None, "usage": {"input_tokens": 0, "output_tokens": 0, "requests": 0, "attempted_requests": 0},
            "latency": {"total_seconds": 0.0, "api_request_seconds": 0.0},
            "diagnostics": {"prompt_version": PROMPT_VERSION}, "output_truncated": False}


def _pack(inventory: CandidateInventory, evidence: Evidence, query: str, answer: dict | None, sources: set[str]) -> dict:
    result = evidence_record(evidence, query)
    result.update({"score": answer["score"] if answer else None,
                   "confidence": answer["confidence"] if answer else None,
                   "owner_probability": round(owner_probability(answer), 4) if answer else None,
                   "probabilities": answer["probabilities"] if answer else None})
    associations = [link for link in inventory.associations if link.test_path == evidence.candidate.path and link.source_path in sources]
    result["associations"] = [{"source": link.source_path, "basis": link.basis, "line": link.line} for link in associations[:12]]
    if evidence.candidate.kind == "test":
        shared = [path for path in sorted(sources) if set(inventory.candidates[path].route_keys) & set(evidence.candidate.route_keys)]
        result["relationship"] = "direct" if associations else "shared_route" if shared else "semantic_or_lexical"
        result["shared_route_sources"] = shared
    return result


def _set_evidence(result: dict, inventory: CandidateInventory, query: str, sources: list, tests: list) -> None:
    all_evidence = [evidence for evidence, _ in sources + tests]
    if not inventory.validate_batch(all_evidence):
        raise StaleEvidenceError("selected evidence changed before display")
    paths = {evidence.candidate.path for evidence, _ in sources}
    result["sources"] = [_pack(inventory, evidence, query, answer, paths) for evidence, answer in sources[:3]]
    result["tests"] = [_pack(inventory, evidence, query, answer, paths) for evidence, answer in tests[:3]]
    if sources and not tests:
        result["gaps"].append("No focused test candidate was established.")
    if tests and not sources:
        result["gaps"].append("No implementation owner was established.")


def _local(inventory: CandidateInventory, query: str, exact_paths: tuple[str, ...] = (), symbol: str = "") -> tuple[list, list]:
    scores = lexical_scores(inventory, query)
    if exact_paths:
        sources = [path for path in exact_paths if inventory.candidates[path].kind == "source"][:3]
        tests = [path for path in exact_paths if inventory.candidates[path].kind == "test"][:3]
        related = set(path for selected in exact_paths for path in inventory.related_paths(selected))
        if not sources:
            sources = rank_paths(inventory, scores, "source", 3, related)
        if not tests:
            tests = rank_paths(inventory, scores, "test", 3, related)
    else:
        sources = rank_paths(inventory, scores, "source", 3, [path for path, score in scores.items() if score > 0])
        related = set(path for selected in sources for path in inventory.related_paths(selected))
        tests = rank_paths(inventory, scores, "test", 3, related)
        if not tests:
            tests = rank_paths(inventory, scores, "test", 3, [path for path, score in scores.items() if score > 0])
    evidence = inventory.evidence_batch((*sources, *tests), query=query, symbol=symbol, max_lines=24, max_chars=2600)
    # Credentials are never emitted even by local fallback; exact source remains on disk.
    evidence = [item for item in evidence if safe_text(item.candidate.purpose) and safe_value(evidence_record(item, query))]
    return ([(item, None) for item in evidence if item.candidate.kind == "source"],
            [(item, None) for item in evidence if item.candidate.kind == "test"])


def run(query: str, *, root: Path = REPO_ROOT, inventory: CandidateInventory | None = None,
        client=None, include_trace: bool = False) -> dict:
    """Programmatic entry for CLI/evaluation; no result cache or held-out fixture reads.

    A supplied client implements ``evaluate(state, questions) -> HTTP-shaped dict``.
    Trace is opt-in local diagnostic data and is never included by the normal CLI.
    Latency includes inventory construction unless a caller supplies its own inventory.
    """
    started = perf_counter()
    query = query.strip()
    result = _base(query[:MAX_QUERY_CHARS])
    selection = None
    try:
        if not safe_text(query):
            result["query"] = "[potential credential content omitted]"
            raise ServiceUnavailable("unsafe_input")
        if not query or len(query) > MAX_QUERY_CHARS:
            result["gaps"].append("Provide a nonempty task of at most 2000 characters.")
            return result
        inventory = inventory if inventory is not None else build_inventory(Path(root))
        result["diagnostics"]["inventory_candidates"] = len(inventory.candidates)
        whole = query.strip("`\"'")
        exact = (inventory.resolve_exact(query) if not any(char.isspace() for char in whole)
                 or Path(whole).is_absolute() or whole in inventory.candidates else ExactMatch("not_exact"))
        # This branch is intentionally before client construction, credential lookup,
        # or any model request, including ambiguous/missing explicit identifiers.
        if exact.status != "not_exact":
            result["mode"] = "exact"
            result["status"] = "ok" if exact.status == "resolved" else "unresolved"
            if "changed" in exact.reason:
                result["status"] = "stale"
            if exact.status != "resolved":
                result["gaps"].append(exact.reason or "Exact lookup is unresolved.")
            if exact.paths and result["status"] != "stale":
                sources, tests = _local(inventory, query, exact.paths, exact.symbol)
                _set_evidence(result, inventory, query, sources, tests)
                displayed = {item.candidate.path for item, _ in sources + tests}
                if exact.status == "resolved" and not set(exact.paths).issubset(displayed):
                    result["status"] = "unresolved"
                    result["gaps"].append("Requested evidence was excluded because it may contain credentials; inspect the file locally.")
            return result
        selection = Selection(inventory, query, client if client is not None else TypeSafeClient())
        result["mode"], result["model"] = "semantic", MODEL
        status, sources, tests = selection.run()
        result["status"] = status
        _set_evidence(result, inventory, query, sources, tests)
        result["uncertainty"].append("Scores measure relevance, not correctness. Owner probability combines useful and exact ownership; confidence is distribution concentration. Multiple owners may be valid.")
        if status == "no_match":
            result["gaps"].append("The task was judged outside repository navigation or unsupported by the supplied candidate areas; this is not an exhaustive absence proof.")
        elif status == "unresolved":
            result["gaps"].append("No candidate reached an owner category; inspect local navigation or broaden the evidence.")
    except ServiceUnavailable as exc:
        result["status"], result["mode"] = "unavailable", "local_fallback"
        result["error"] = {"code": exc.code, "message": str(exc)}
        result["uncertainty"].append("Semantic selection is unavailable; these are local lexical/direct-link suggestions.")
        if inventory is not None and exc.code != "unsafe_input":
            try:
                if selection is not None:
                    selection.guard()  # Reject stale inputs even when unselected.
                sources, tests = _local(inventory, query)
                _set_evidence(result, inventory, query, sources, tests)
            except (StaleEvidenceError, OSError, UnicodeError):
                result["status"] = "stale"
                result["sources"], result["tests"] = [], []
                result["gaps"].append("Local evidence changed; rerun the command.")
            except InventoryUnavailable:
                result["sources"], result["tests"] = [], []
                result["gaps"].append("Safe local inventory validation became unavailable.")
    except (StaleEvidenceError, OSError, UnicodeError):
        result["status"] = "stale"
        result["sources"], result["tests"] = [], []
        result["gaps"].append("Input evidence or navigation associations changed; rerun the command.")
    except InventoryUnavailable:
        result["status"] = "unavailable"
        result["error"] = {"code": "inventory_unavailable", "message": "Safe Git-visible navigation is unavailable; use local source search or nav.py."}
    finally:
        if selection is not None:
            result["usage"] = dict(selection.usage)
            result["latency"]["api_request_seconds"] = round(selection.api_seconds, 4)
            result["diagnostics"] = selection.diagnostics()
            if selection.excluded:
                result["gaps"].append("Potential credential material was excluded from candidate evidence.")
            if include_trace:
                result["trace"] = selection.trace
        result["latency"]["total_seconds"] = round(perf_counter() - started, 4)
        if inventory is not None:
            result["diagnostics"]["inventory_sha256"] = hashlib.sha256("\n".join(
                path + ":" + candidate.content_sha256 for path, candidate in inventory.candidates.items()).encode()).hexdigest()
    return result


def bounded_result(result: dict, max_chars: int = MAX_JSON_CHARS) -> dict:
    """Bound optional detail without retaining a candidate stripped of evidence."""
    if max_chars < 2048:
        raise ValueError("output limit must be at least 2048 characters")
    value = copy.deepcopy({key: item for key, item in result.items() if key != "trace"})
    omitted = {"sources": 0, "tests": 0}
    omission_gap = None
    protected = {}

    def omit(group, candidate):
        nonlocal omission_gap
        value[group].remove(candidate)
        omitted[group] += 1
        value["output_omitted"] = dict(omitted)
        value["output_truncated"] = True
        gap = (f"Display omitted {omitted['sources']} source and {omitted['tests']} test candidates: "
               "a useful exact excerpt was unavailable or could not fit the output budget.")
        if omission_gap is None:
            omission_gap = len(value["gaps"])
            value["gaps"].append(gap)
        else:
            value["gaps"][omission_gap] = gap

    for group in ("sources", "tests"):
        for candidate in tuple(value[group]):
            excerpt = candidate.get("excerpt", [])
            nonblank = [index for index, line in enumerate(excerpt) if line["text"].strip()]
            if not nonblank:
                omit(group, candidate)
                continue
            by_line = {line["line"]: index for index, line in enumerate(excerpt)}
            anchors = [by_line[symbol["line"]] for symbol in candidate.get("symbols", [])
                       if symbol["line"] in by_line and excerpt[by_line[symbol["line"]]]["text"].strip()]
            anchor = anchors[0] if anchors else nonblank[0]
            width = min(MIN_EXCERPT_LINES, len(excerpt))
            start = max(0, min(anchor - 1, len(excerpt) - width))
            protected[id(candidate)] = {line["line"] for line in excerpt[start:start + width]}

    def size():
        return len(json.dumps(value, ensure_ascii=True, separators=(",", ":")))

    def largest(items, field):
        return max(items, key=lambda item: len(json.dumps(item.get(field), ensure_ascii=True)), default=None)

    while size() > max_chars:
        value["output_truncated"] = True
        candidates = value["sources"] + value["tests"]
        extra_symbols = largest([item for item in candidates if len(item.get("symbols", [])) > 3], "symbols")
        extra_excerpt = largest([item for item in candidates if len(item["excerpt"]) > len(protected[id(item)])], "excerpt")
        if extra_symbols:
            extra_symbols["symbols"].pop()
        elif value.get("diagnostics"):
            value["diagnostics"] = {}
        elif extra_excerpt:
            # Trim from the edges around the protected declaration/nonblank window.
            # Every kept line remains complete, exact and in original source order.
            edge = -1 if extra_excerpt["excerpt"][-1]["line"] not in protected[id(extra_excerpt)] else 0
            extra_excerpt["excerpt"].pop(edge)
            extra_excerpt["truncated"] = True
        elif len(value.get("query", "")) > 120:
            value["query"] = value["query"][:117] + "..."
        else:
            symbol = largest([item for item in candidates if item.get("symbols")], "symbols")
            purpose = largest([item for item in candidates if item.get("purpose")], "purpose")
            if symbol:
                symbol["symbols"].pop()
            elif purpose:
                purpose["purpose"] = ""
            elif candidates:
                # Preserve both kinds when possible; omit a lowest-ranked candidate
                # whole rather than claiming it still has an empty evidence pack.
                groups = [group for group in ("sources", "tests") if len(value[group]) > 1]
                groups = groups or [group for group in ("sources", "tests") if value[group]]
                group = max(groups, key=lambda group: len(json.dumps(value[group][-1], ensure_ascii=True)))
                omit(group, value[group][-1])
            else:
                raise ValueError("output budget cannot contain required status and uncertainty")
    return value


def render_json(result: dict, max_chars: int = MAX_JSON_CHARS) -> str:
    return json.dumps(bounded_result(result, max_chars), ensure_ascii=True, separators=(",", ":"))


def render_text(result: dict, max_chars: int = MAX_TEXT_CHARS) -> str:
    value = bounded_result(result, max_chars)
    lines = [f"Navigation: {value['status']} ({value['mode']})"]
    if value["error"]:
        lines.append(f"Error [{value['error']['code']}]: {value['error']['message']}")
    lines.extend(value["uncertainty"])
    lines.extend("Gap: " + gap for gap in value["gaps"])
    for label in ("sources", "tests"):
        lines.append(label.title() + ":")
        for candidate in value[label]:
            score = "local" if candidate["score"] is None else f"score={candidate['score']:.2f}, confidence={candidate['confidence']:.2f}"
            lines.append(f"  {candidate['path']} ({score})")
            if candidate.get("relationship"):
                lines.append("    Test relationship: " + candidate["relationship"])
            for symbol in candidate["symbols"][:6]:
                lines.append(f"    {symbol['qualified_name']} at line {symbol['line']}")
            lines.extend(f"    {item['line']}: {item['text']}" for item in candidate["excerpt"])
    lines.append(f"Model: {value['model'] or 'none'}; tokens: {value['usage']['input_tokens']} in / {value['usage']['output_tokens']} out; elapsed: {value['latency']['total_seconds']:.3f}s")
    if value["output_truncated"]:
        lines.append("Optional evidence shortened to fit the output budget.")
    text = "\n".join(lines)
    if len(text) > max_chars:
        # JSON escaping generally costs more, but short source lines add indentation.
        return render_text(result, max_chars=max_chars - max(128, len(text) - max_chars))
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task")
    parser.add_argument("--json", action="store_true", help="emit a bounded JSON evidence pack")
    args = parser.parse_args(argv)
    result = run(args.task)
    print(render_json(result) if args.json else render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
