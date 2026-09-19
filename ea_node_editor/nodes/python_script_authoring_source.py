# Purpose: Preserve Python source while editing bounded AST and token spans.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_python_script_authoring.py

from __future__ import annotations

import ast
import io
import tokenize
from bisect import bisect_right
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceRange:
    """Python character offsets, with one-based line and column for display."""

    start: int
    end: int
    line: int
    column: int
    end_line: int
    end_column: int


class SourceDocument:
    """AST columns are UTF-8 bytes; editor ranges are Unicode character offsets."""

    def __init__(self, source: str) -> None:
        self.source = source
        # Python's AST/tokenizer count LF rows; str.splitlines also splits valid
        # characters such as U+2028 inside strings and would corrupt offsets.
        parts = source.split("\n")
        self.lines = [part + "\n" for part in parts[:-1]] + [parts[-1]]
        self.offsets = [0]
        for line in self.lines:
            self.offsets.append(self.offsets[-1] + len(line))
        self.tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        self.newline = "\r\n" if "\r\n" in source else "\n"

    def position(self, row: int, byte_column: int) -> int:
        return self.offsets[row - 1] + len(
            self.lines[row - 1].encode("utf-8")[:byte_column].decode("utf-8")
        )

    def token_position(self, position: tuple[int, int]) -> int:
        row, column = position
        return self.offsets[min(row - 1, len(self.offsets) - 1)] + column

    def start(self, node: ast.AST) -> int:
        return self.position(node.lineno, node.col_offset)

    def end(self, node: ast.AST) -> int:
        return self.position(node.end_lineno, node.end_col_offset)

    def text(self, node: ast.AST) -> str:
        return self.source[self.start(node):self.end(node)]

    def range(self, node: ast.AST) -> SourceRange:
        start, end = self.start(node), self.end(node)
        return SourceRange(
            start, end, node.lineno, start - self.offsets[node.lineno - 1] + 1,
            node.end_lineno, end - self.offsets[node.end_lineno - 1] + 1,
        )

    def decorator_range(self, node: ast.AST) -> SourceRange:
        first, last = self.decorator_span(node)
        line = bisect_right(self.offsets, first)
        end_line = bisect_right(self.offsets, last)
        return SourceRange(first, last, line, first - self.offsets[line - 1] + 1,
                           end_line, last - self.offsets[end_line - 1] + 1)

    def decorator_span(self, node: ast.AST) -> tuple[int, int]:
        at = max(
            index for index, token in enumerate(self.tokens)
            if token.string == "@" and self.token_position(token.start) <= self.start(node)
        )
        first = self.token_position(self.tokens[at].start)
        last = first
        for token in self.tokens[at:]:
            if token.type == tokenize.NEWLINE:
                break
            if token.type not in {tokenize.COMMENT, tokenize.NL}:
                last = self.token_position(token.end)
        return first, last

    def comma_between(self, first: int, last: int) -> int | None:
        return next((
            self.token_position(token.start) for token in self.tokens
            if token.string == "," and first <= self.token_position(token.start) < last
        ), None)

    def argument_edits(
        self, function: ast.FunctionDef, desired: tuple[str, ...],
    ) -> list[tuple[int, int, str]]:
        """Keep surviving annotations/comments and remove only argument/comma tokens."""
        arguments = function.args.args
        desired_set = set(desired)
        edits: list[tuple[int, int, str]] = []
        survivors = [arg for arg in arguments if arg.arg in desired_set]
        for index, arg in enumerate(arguments):
            if arg.arg in desired_set:
                continue
            edits.append((self.start(arg), self.end(arg), ""))
            if index:
                comma = self.comma_between(self.end(arguments[index - 1]), self.start(arg))
            else:
                comma = self.comma_between(self.end(arg), self.start(arguments[index + 1]))
            if comma is not None:
                edits.append((comma, comma + 1, ""))
        missing = [key for key in desired if key not in {arg.arg for arg in arguments}]
        if missing:
            # The declaration parser requires ctx, so one parameter always survives.
            last = self.end(survivors[-1])
            edits.append((last, last, ", " + ", ".join(missing)))
        return edits


def apply_edits(source: str, edits: list[tuple[int, int, str]]) -> str:
    """Apply non-overlapping edits; duplicate spans indicate a caller error."""
    ordered = sorted(edits, key=lambda edit: (edit[0], edit[1]))
    previous = -1
    for first, last, _value in ordered:
        if first < previous or not 0 <= first <= last <= len(source):
            raise ValueError("Overlapping or invalid Python source edits")
        previous = last
    for first, last, value in reversed(ordered):
        source = source[:first] + value + source[last:]
    return source
