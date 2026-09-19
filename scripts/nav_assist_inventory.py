# Purpose: Build safe live navigation candidates and inspect freshness-bound source evidence.
# Map: subsystems/verification_testing_docs_hygiene.md
# Tests: tests/test_nav_assist_inventory.py
"""Development-only evidence for nav_assist; never import or execute target files.

Membership and route associations are complete, while content parsing is lazy.
Shared-route tests are advisory; only explicit source headers form direct test links.
Git visibility is required so a missing Git installation cannot expose ignored files.
"""
from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from ea_node_editor.common.path_safety import is_reparse_point
from scripts import generate_agent_route_index as route_index
from scripts import generate_qml_navigation_index as qml_index
from scripts import generate_source_test_file_index as file_index

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (*file_index.DEFAULT_SOURCE_ROOTS, Path("scripts"), Path("examples"))
TEST_ROOTS = file_index.DEFAULT_TEST_ROOTS
ASSOCIATION_ROOTS = (Path("docs/agent_maps"), Path("docs/qml_navigation_index.json"), Path("docs/source_test_file_index.md"))
ASSOCIATION_SUFFIXES = frozenset({".md", ".json"})
SUFFIXES = frozenset(file_index.DEFAULT_SOURCE_SUFFIXES)
EXCLUDED_PARTS = frozenset({
    *file_index.EXCLUDED_DIR_NAMES, "vendor", "vendors", "third_party", "third-party",
    "generated", "private", "research", "scratch",
})
HEADER_RE = re.compile(r"^\s*(?:#|//)\s*(Purpose|Map|Tests):\s*(.*)$", re.MULTILINE)
PATH_RE = re.compile(r"(?:corex|ea_node_editor|tests|scripts|examples|web)/[\w./-]+")
IDENTIFIER_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\Z")
JS_DECL_RE = re.compile(
    r"^\s*(?:(?:export|default|async)\s+)*(?:function\s*\*?\s*|class\s+|"
    r"(?:const|let|var)\s+)([A-Za-z_$][\w$]*)"
)


class InventoryUnavailable(RuntimeError):
    """Safe file visibility could not be established."""


class StaleEvidenceError(ValueError):
    """The candidate or its evidence no longer describes the live file."""


@dataclass(frozen=True)
class Symbol:
    name: str
    qualified_name: str
    kind: str
    line: int
    end_line: int


@dataclass(frozen=True)
class NumberedLine:
    line: int
    text: str


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    path: str
    kind: str
    purpose: str
    owner_maps: tuple[str, ...]
    route_keys: tuple[str, ...]
    source_paths: tuple[str, ...]
    test_paths: tuple[str, ...]
    size_bytes: int
    mtime_ns: int
    content_sha256: str
    retrieval_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class Evidence:
    candidate: Candidate
    sha256: str
    symbols: tuple[Symbol, ...]
    excerpt: tuple[NumberedLine, ...]
    total_lines: int
    truncated: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExactMatch:
    status: str
    paths: tuple[str, ...] = ()
    symbol: str = ""
    reason: str = ""


@dataclass(frozen=True)
class Association:
    source_path: str
    test_path: str
    basis: str
    line: int


def _sorted(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values), key=lambda value: (value.casefold(), value)))


def navigation_terms(text: str) -> set[str]:
    """Retain identifier spellings as well as camel-case/underscore word parts."""
    split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return {word for word in re.findall(r"[a-z0-9]+", text.lower() + " " + split.lower()) if len(word) > 1}


def _retrieval_terms(text: str) -> tuple[str, ...]:
    """Cheap local recall hints, not parsed declarations or outbound evidence.

    Scan all declaration/comment/docstring/property-binding lines, including late
    methods. AST parsing remains lazy and is still required for displayed symbols.
    Quoted examples may improve recall but cannot establish authoritative symbols.
    The full-file hash binds these hints to the same inventory snapshot as excerpts.
    """
    lines = re.findall(
        r"(?m)^[ \t]*(?:(?:async[ \t]+)?(?:def|class|function)[ \t]+[^\r\n]+|"
        r"(?:(?:export|default|async)[ \t]+)*(?:const|let|var)[ \t]+[^\r\n]+|"
        r"(?:(?:readonly|required|default)[ \t]+)*property[ \t]+[^\r\n]+|"
        r"[A-Za-z_][\w.]*[ \t]*:[^\r\n]+|(?:#|//)[^\r\n]*)", text)
    docs = re.findall(r'(?ms)^[ \t]*[rRuU]?(\"\"\"|\'\'\')(.*?)\1', text)
    comments = re.findall(r"/\*.*?\*/", text, flags=re.DOTALL)
    return tuple(sorted(navigation_terms("\n".join((*lines, *(body for _, body in docs), *comments)))))


def _safe_path(repo_root: Path, relative: str, *, suffixes: frozenset[str] = SUFFIXES) -> Path | None:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return None
    if any(part.startswith(".") or part.casefold() in EXCLUDED_PARTS for part in path.parts):
        return None
    if path.suffix.casefold() not in suffixes or file_index.is_excluded_path(path):
        return None
    candidate = repo_root / path
    # Reject aliases even when their resolved target happens to stay in the repo.
    for parent in (candidate, *candidate.parents):
        if parent == repo_root:
            break
        if is_reparse_point(parent):
            return None
    try:
        candidate.resolve().relative_to(repo_root)
    except (ValueError, OSError):
        return None
    return candidate if candidate.is_file() else None


def _ignored_paths(repo_root: Path, paths: Iterable[str]) -> set[str]:
    paths = tuple(paths)
    if not paths:
        return set()
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "--no-index", "--stdin", "-z"],
            input="\0".join(paths).encode("utf-8") + b"\0", capture_output=True, check=False,
        )
    except OSError as exc:
        raise InventoryUnavailable("Git ignore rules are unavailable") from exc
    if result.returncode not in (0, 1):
        raise InventoryUnavailable("Git ignore rules are unavailable")
    return {raw.decode("utf-8") for raw in result.stdout.split(b"\0") if raw}


def _headers(text: str) -> tuple[dict[str, str], int]:
    """Read only the initial line-comment banner, never quoted code examples."""
    headers: dict[str, str] = {}
    tests_line = 0
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith(("#", "//")):
            break
        match = HEADER_RE.match(line)
        if match and match.group(1) not in headers:
            headers[match.group(1)] = match.group(2).strip()
            if match.group(1) == "Tests":
                tests_line = number
    return headers, tests_line


def _map_paths(raw: str, allowed_maps: set[str]) -> tuple[str, ...]:
    paths = []
    for token in raw.replace("\\", "/").split(","):
        token = token.strip().strip("`")
        path = token if token.startswith("docs/agent_maps/") else f"docs/agent_maps/{token}"
        if token and path in allowed_maps:
            paths.append(path)
    return _sorted(paths)


def _expand_paths(tokens: Iterable[str], paths: set[str]) -> tuple[str, ...]:
    result = set()
    for token in tokens:
        normalized = token.replace("\\", "/").removeprefix("./").rstrip("/")
        if normalized in paths:
            result.add(normalized)
        else:
            result.update(path for path in paths if path.startswith(normalized + "/"))
    return _sorted(result)


def _python_symbols(text: str) -> tuple[Symbol, ...]:
    tree = ast.parse(text)
    symbols = []

    def visit(node: ast.AST, scope: tuple[str, ...] = ()) -> None:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            qualified = (*scope, node.name)
            symbols.append(Symbol(node.name, ".".join(qualified), type(node).__name__, node.lineno, node.end_lineno or node.lineno))
            for child in ast.iter_child_nodes(node):
                visit(child, qualified)
        else:
            # Module/class constants are useful; function-local assignments are not symbols.
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and (not scope or isinstance_parent_class(scope)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        symbols.append(Symbol(target.id, ".".join((*scope, target.id)), "assignment", node.lineno, node.end_lineno or node.lineno))
            for child in ast.iter_child_nodes(node):
                visit(child, scope)

    def isinstance_parent_class(scope: tuple[str, ...]) -> bool:
        return any(symbol.qualified_name == ".".join(scope) and symbol.kind == "ClassDef" for symbol in symbols)

    visit(tree)
    return tuple(symbols)


def _symbols(path: str, text: str) -> tuple[Symbol, ...]:
    suffix = Path(path).suffix.casefold()
    if suffix in {".py", ".pyi"}:
        return _python_symbols(text)
    result = []
    code_lines = _javascript_code_lines(text)
    if suffix == ".qml":
        stem = Path(path).stem
        root_line = next((number for number, line in code_lines if qml_index._ROOT_OR_COMPONENT_RE.match(line)), 1)
        result.append(Symbol(stem, stem, "component", root_line, len(text.splitlines())))
    # Reuse the repository's QML declaration patterns, over masked current code.
    if suffix in {".qml", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}:
        for line_number, line in code_lines:
            patterns = (("declaration", JS_DECL_RE),)
            if suffix == ".qml":
                patterns += (("property", qml_index._PROPERTY_RE), ("signal", qml_index._SIGNAL_RE), ("function", qml_index._FUNCTION_RE), ("id", qml_index._ID_RE))
            for kind, pattern in patterns:
                match = pattern.match(line.lstrip())
                if match:
                    name = match.group("name") if kind == "property" else match.group(1)
                    if not any(item.name == name and item.line == line_number for item in result):
                        result.append(Symbol(name, name, kind, line_number, line_number))
    return tuple(result)


def _javascript_code_lines(text: str) -> tuple[tuple[int, str], ...]:
    """Mask comments and strings, including multiline templates, before declarations.

    This is lexical evidence, not a JavaScript parser; masking template expressions
    deliberately prefers missed declarations over resolving a quoted example as code.
    """
    masked = list(text)
    state = ""
    index = 0
    while index < len(text):
        char = text[index]
        pair = text[index:index + 2]
        if state:
            if char != "\n":
                masked[index] = " "
            if state == "//" and char == "\n":
                state = ""
            elif state == "/*" and pair == "*/":
                masked[index:index + 2] = "  "
                state = ""
                index += 1
            elif state in {"'", '"', "`"}:
                if char == "\\":
                    if index + 1 < len(text) and text[index + 1] != "\n":
                        masked[index + 1] = " "
                    index += 1
                elif char == state:
                    state = ""
        elif pair in {"//", "/*"}:
            state = pair
            masked[index:index + 2] = "  "
            index += 1
        elif char in {"'", '"', "`"}:
            state = char
            masked[index] = " "
        index += 1
    return tuple(enumerate("".join(masked).splitlines(), 1))


def _excerpt(lines: list[str], query: str, symbols: tuple[Symbol, ...], symbol: str,
             center_line: int | None, max_lines: int, max_chars: int) -> tuple[NumberedLine, ...]:
    if not 1 <= max_lines <= 200 or not 1 <= max_chars <= 60000:
        raise ValueError("excerpt limits must be 1..200 lines and 1..60000 characters")
    if not lines:
        return ()
    if center_line is not None and not 1 <= center_line <= len(lines):
        raise ValueError("excerpt center is outside the current file")
    if center_line is None and symbol:
        matches = [item for item in symbols if symbol in {item.name, item.qualified_name}]
        if len(matches) == 1:
            center_line = matches[0].line
    if center_line is None and query:
        terms = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", query.casefold()))
        scores = [len(terms.intersection(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", line.casefold()))) for line in lines]
        if max(scores, default=0):
            center_line = scores.index(max(scores)) + 1
    if center_line is None:
        center_line = next((item.line for item in symbols if item.kind != "component"), 1)
    start = max(0, center_line - 1 - min(3, max_lines // 4))
    selected = []
    used = 0
    for number in range(start, min(len(lines), start + max_lines)):
        cost = len(lines[number]) + len(str(number + 1)) + 3
        if used + cost > max_chars:
            break  # Preserve exact line contents; never silently clip a line.
        selected.append(NumberedLine(number + 1, lines[number]))
        used += cost
    return tuple(selected)


class CandidateInventory:
    """One live membership snapshot; rebuild after source or association changes.

    ``candidates`` and ``routes`` include all safe files/associations, never a ranking
    cutoff. ``evidence`` lazily parses selected files and hashes their full bytes.
    ``resolve_exact`` resolves only a whole path or declaration name; free-form
    natural language goes to semantic selection instead of filename heuristics.
    """

    def __init__(self, repo_root: Path, candidates: dict[str, Candidate], routes: tuple[route_index.RouteEntry, ...], issues: tuple[str, ...] = (), associations: tuple[Association, ...] = (), association_hashes: dict[str, str] | None = None):
        self.repo_root = repo_root
        self.candidates = candidates
        self.routes = routes
        self.issues = issues
        self.associations = associations
        self._association_hashes = dict(association_hashes or {})
        self._content: dict[str, tuple[str, str, tuple[Symbol, ...], tuple[str, ...]]] = {}

    def _read(self, path: str) -> tuple[str, str, tuple[Symbol, ...], tuple[str, ...]]:
        candidate = self.candidates.get(path)
        live = _safe_path(self.repo_root, path)
        if candidate is None or live is None:
            raise StaleEvidenceError("candidate is missing or outside the safe inventory")
        stat = live.stat()
        if (stat.st_size, stat.st_mtime_ns) != (candidate.size_bytes, candidate.mtime_ns):
            raise StaleEvidenceError(f"candidate changed: {path}; rebuild inventory")
        raw = live.read_bytes()
        after = live.stat()
        if (after.st_size, after.st_mtime_ns) != (candidate.size_bytes, candidate.mtime_ns):
            raise StaleEvidenceError(f"candidate changed while reading: {path}")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != candidate.content_sha256:
            raise StaleEvidenceError(f"candidate content changed: {path}; rebuild inventory")
        cached = self._content.get(path)
        if cached and cached[1] == digest:
            return cached
        text = raw.decode("utf-8-sig")
        warnings = ()
        try:
            symbols = _symbols(path, text)
        except (SyntaxError, ValueError, RecursionError):
            symbols = ()
            warnings = ("Declarations could not be parsed; numbered source remains available.",)
        value = (text, digest, symbols, warnings)
        self._content[path] = value
        return value

    def evidence(self, path: str, *, query: str = "", symbol: str = "", center_line: int | None = None,
                 max_lines: int = 24, max_chars: int = 6000) -> Evidence:
        return self.evidence_batch((path,), query=query, symbol=symbol, center_line=center_line,
                                   max_lines=max_lines, max_chars=max_chars)[0]

    def _check_associations(self) -> None:
        for relative, digest in self._association_hashes.items():
            live = _safe_path(self.repo_root, relative, suffixes=ASSOCIATION_SUFFIXES)
            if live is None or hashlib.sha256(live.read_bytes()).hexdigest() != digest:
                raise StaleEvidenceError("navigation association inputs changed; rebuild inventory")

    def evidence_batch(self, paths: Iterable[str], *, query: str = "", symbol: str = "", center_line: int | None = None,
                       max_lines: int = 24, max_chars: int = 6000) -> tuple[Evidence, ...]:
        """Read a safe batch with one ignore check, preserving per-file hash checks.

        Also verifies the maps and index inputs from which associations were built.
        No caller can use this method to bypass eligibility or freshness checks.
        """
        paths = tuple(paths)
        if _ignored_paths(self.repo_root, (*paths, *self._association_hashes)):
            raise StaleEvidenceError("candidate or association input is now ignored; rebuild inventory")
        self._check_associations()
        return tuple(self._evidence(path, query, symbol, center_line, max_lines, max_chars) for path in paths)

    def _evidence(self, path: str, query: str, symbol: str, center_line: int | None, max_lines: int, max_chars: int) -> Evidence:
        text, digest, symbols, warnings = self._read(path)
        lines = text.splitlines()
        excerpt = _excerpt(lines, query, symbols, symbol, center_line, max_lines, max_chars)
        return Evidence(self.candidates[path], digest, symbols, excerpt, len(lines), len(excerpt) < len(lines), warnings)

    def validate_evidence(self, evidence: Evidence) -> bool:
        """Recheck allowlisted path, current ignore rules, full bytes and exact lines."""
        return self.validate_batch((evidence,))

    def validate_batch(self, evidence: Iterable[Evidence]) -> bool:
        """Validate all input evidence and its association provenance as one batch."""
        evidence = tuple(evidence)
        if _ignored_paths(self.repo_root, (*(item.candidate.path for item in evidence), *self._association_hashes)):
            return False
        try:
            self._check_associations()
        except (OSError, ValueError):
            return False
        return all(self._validate_evidence(item) for item in evidence)

    def _validate_evidence(self, evidence: Evidence) -> bool:
        path = evidence.candidate.path
        if self.candidates.get(path) != evidence.candidate:
            return False
        try:
            text, digest, symbols, _ = self._read(path)
        except (OSError, ValueError, UnicodeError):
            return False
        lines = text.splitlines()
        return digest == evidence.sha256 and symbols == evidence.symbols and len(lines) == evidence.total_lines and all(
            1 <= item.line <= len(lines) and lines[item.line - 1] == item.text
            for item in evidence.excerpt
        )

    def related_paths(self, path: str, *, include_routes: bool = False) -> tuple[str, ...]:
        candidate = self.candidates[path]
        related = set((*candidate.source_paths, *candidate.test_paths))
        if include_routes:
            for route in self.routes:
                if route.route_key in candidate.route_keys:
                    related.update((*route.source_candidates, *route.test_candidates))
        related.discard(path)
        return _sorted(related)

    def resolve_exact(self, query: str) -> ExactMatch:
        value = query.strip().strip("`\"'")
        normalized = value.replace("\\", "/")
        if Path(value).is_absolute():
            try:
                normalized = Path(value).relative_to(self.repo_root).as_posix()
            except ValueError:
                return ExactMatch("unresolved", reason="path is outside the inventory")
        normalized = normalized.removeprefix("./")
        # Filename-only lookup is exact only when the filename is unique.
        paths = [path for path in self.candidates if path == normalized or ("/" not in normalized and Path(path).name == normalized)]
        if paths:
            try:
                for path in paths:
                    self.evidence(path, max_lines=1)
            except (StaleEvidenceError, OSError, UnicodeError):
                return ExactMatch("unresolved", reason="path changed; rebuild inventory")
            return ExactMatch("resolved" if len(paths) == 1 else "ambiguous", _sorted(paths), reason="existing path")
        if "/" in normalized or Path(normalized).suffix.casefold() in SUFFIXES:
            return ExactMatch("unresolved", reason="path is not in the safe inventory")
        if not IDENTIFIER_RE.fullmatch(value):
            return ExactMatch("not_exact", reason="query is not a path or declaration name")
        # A lexical prefilter avoids AST-parsing every file for a single symbol.
        name = value.rsplit(".", 1)[-1]
        pattern = re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])")
        found = []
        stale = False
        ignored = _ignored_paths(self.repo_root, self.candidates)
        for path, candidate in self.candidates.items():
            if path in ignored:
                continue
            if Path(path).suffix.casefold() not in {".py", ".pyi", ".qml", ".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx"}:
                continue
            live = _safe_path(self.repo_root, path)
            if live is None:
                stale = True
                continue
            try:
                stat = live.stat()
                if (stat.st_size, stat.st_mtime_ns) != (candidate.size_bytes, candidate.mtime_ns):
                    stale = True
                    continue
                raw = live.read_bytes()
                if hashlib.sha256(raw).hexdigest() != candidate.content_sha256:
                    stale = True
                    continue
                prefix = raw.decode("utf-8-sig")
                if not pattern.search(prefix) and not (Path(path).suffix == ".qml" and Path(path).stem == name):
                    continue
                _, _, symbols, warnings = self._read(path)
            except (OSError, ValueError, UnicodeError):
                stale = True
                continue
            if warnings:
                stale = True
            for item in symbols:
                if value in {item.name, item.qualified_name}:
                    found.append(path)
        if stale:
            return ExactMatch("unresolved", _sorted(found), value, "some files changed or could not be parsed; rebuild or inspect locally")
        if len(found) == 1:
            return ExactMatch("resolved", tuple(found), value, "unique declaration")
        return ExactMatch("ambiguous" if found else "unresolved", _sorted(found), value, "declaration is not unique" if found else "no declaration")


def build_inventory(repo_root: Path = REPO_ROOT) -> CandidateInventory:
    repo_root = repo_root.resolve()
    visible = file_index._git_visible_files(repo_root, (*SOURCE_ROOTS, *TEST_ROOTS, *ASSOCIATION_ROOTS))
    if visible is None:
        raise InventoryUnavailable("Git-visible inventory unavailable; use local nav.py or source search")
    # Unlike the legacy path index, do not fall back to an ignore-blind walk.
    relative_paths = _sorted(path.relative_to(repo_root).as_posix() for path in visible)
    ignored = _ignored_paths(repo_root, relative_paths)
    allowed_inputs = frozenset(
        path for relative in relative_paths if relative not in ignored
        and (path := _safe_path(repo_root, relative, suffixes=ASSOCIATION_SUFFIXES)) is not None
        and any(path.is_relative_to(repo_root / root) for root in ASSOCIATION_ROOTS)
    )
    allowed_maps = {path.relative_to(repo_root).as_posix() for path in allowed_inputs if path.suffix == ".md"}
    association_hashes = {path.relative_to(repo_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in allowed_inputs}
    candidates: dict[str, Candidate] = {}
    headers: dict[str, dict[str, str]] = {}
    header_lines: dict[str, int] = {}
    test_imports: dict[str, list[tuple[str, int]]] = {}
    issues = []
    for relative in relative_paths:
        if relative in ignored or (path := _safe_path(repo_root, relative)) is None:
            continue
        try:
            stat = path.stat()
            raw = path.read_bytes()
            after = path.stat()
            if (after.st_size, after.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
                issues.append(f"candidate changed while reading: {relative}")
                continue
            text = raw.decode("utf-8-sig")
            header, header_lines[relative] = _headers(text)
            headers[relative] = header
            if relative.startswith("tests/") and path.suffix in {".py", ".pyi"}:
                # Static test imports establish reverse links without importing tests.
                test_imports[relative] = _test_import_modules(text)
            candidates[relative] = Candidate(
                relative, relative, "test" if relative.startswith("tests/") else "source",
                header.get("Purpose", ""), _map_paths(header.get("Map", ""), allowed_maps), (), (), (),
                stat.st_size, stat.st_mtime_ns, hashlib.sha256(raw).hexdigest(),
                _retrieval_terms(text),
            )
        except (OSError, UnicodeError):
            issues.append(f"unreadable candidate: {relative}")
    source_paths = {path for path, entry in candidates.items() if entry.kind == "source"}
    test_paths = set(candidates) - source_paths
    index = route_index.build_index_data(repo_root, source_paths=_sorted(source_paths), test_paths=_sorted(test_paths), candidate_limit=None, allowed_input_paths=allowed_inputs)
    routes = []
    route_keys: dict[str, set[str]] = {path: set() for path in candidates}
    owner_maps = {path: set(entry.owner_maps) for path, entry in candidates.items()}
    for route in index.entries:
        header_members = tuple(path for path, candidate in candidates.items() if route.kind != "qml_component" and route.map_path in candidate.owner_maps)
        sources = _expand_paths((*route.source_candidates, *route.qml_candidates, *header_members), source_paths)
        tests = _expand_paths((*route.test_candidates, *header_members), test_paths)
        clean = replace(route, source_candidates=sources, test_candidates=tests, qml_candidates=tuple(path for path in sources if path.endswith(".qml")))
        routes.append(clean)
        for path in (*sources, *tests):
            route_keys[path].add(route.route_key)
            owner_maps[path].add(route.map_path)
    source_links: dict[str, set[str]] = {path: set() for path in candidates}
    test_links: dict[str, set[str]] = {path: set() for path in candidates}
    associations = []
    for path, header in headers.items():
        if path not in source_paths:
            continue
        for test in PATH_RE.findall(header.get("Tests", "").replace("\\", "/")):
            if test in test_paths:
                test_links[path].add(test)
                source_links[test].add(path)
                associations.append(Association(path, test, "source_header", header_lines[path]))
    module_paths: dict[str, list[str]] = {}
    for path in _sorted(source_paths):
        if path.endswith(".py"):
            module = path.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
            module_paths.setdefault(module, []).append(path)
    for test, modules in test_imports.items():
        for module, line in modules:
            for source in module_paths.get(module, ()):
                source_links[test].add(source)
                test_links[source].add(test)
                associations.append(Association(source, test, "test_import", line))
    for path, candidate in candidates.items():
        # Header ownership also joins routes even if an old map omits this new file.
        route_keys[path].update(route.route_key for route in routes if route.map_path in candidate.owner_maps and route.kind != "qml_component")
        candidates[path] = replace(candidate, route_keys=_sorted(route_keys[path]), owner_maps=_sorted(owner_maps[path]),
                                   source_paths=_sorted(source_links[path]), test_paths=_sorted(test_links[path]))
    inventory = CandidateInventory(repo_root, candidates, tuple(routes), tuple(issues), tuple(associations), association_hashes)
    if not inventory.validate_batch(()):
        raise InventoryUnavailable("navigation association inputs changed while building inventory")
    return inventory


def _test_import_modules(text: str) -> list[tuple[str, int]]:
    statements = []
    try:
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                statements.extend((alias.name, node.lineno) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                statements.append((node.module, node.lineno))
                statements.extend((f"{node.module}.{alias.name}", node.lineno) for alias in node.names)
    except (SyntaxError, ValueError, RecursionError):
        pass
    return statements
