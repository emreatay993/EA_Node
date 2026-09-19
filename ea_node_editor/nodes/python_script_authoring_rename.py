# Purpose: Produce reviewable, scope-aware Python Script variable and output-key renames.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_python_script_authoring.py

from __future__ import annotations

import ast
import tokenize

from ea_node_editor.nodes import declaration_engine as engine
from ea_node_editor.nodes.python_script_authoring_source import SourceDocument
from ea_node_editor.nodes.python_script_declaration import PythonScriptDeclarationError


class _Bindings(ast.NodeVisitor):
    """Names local to one lexical scope, without nested/comprehension bindings."""

    def __init__(self) -> None:
        self.locals: set[str] = set()
        self.globals: set[str] = set()
        self.nonlocals: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.locals.add(node.id)

    def visit_Global(self, node: ast.Global) -> None:
        self.globals.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocals.update(node.names)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.locals.add(node.name)
        for value in [*node.decorator_list, *node.args.defaults, *node.args.kw_defaults]:
            if value is not None:
                self.visit(value)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.locals.add(node.name)
        for value in [*node.bases, *node.decorator_list, *(item.value for item in node.keywords)]:
            self.visit(value)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for value in [*node.args.defaults, *node.args.kw_defaults]:
            if value is not None:
                self.visit(value)

    def visit_Import(self, node: ast.Import) -> None:
        self.locals.update(item.asname or item.name.split(".")[0] for item in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.locals.update(item.asname or item.name for item in node.names)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.locals.add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.locals.add(node.name)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest:
            self.locals.add(node.rest)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        for generator in node.generators:
            self.visit(generator.iter)
            for condition in generator.ifs:
                self.visit(condition)
        for value in ([node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]):
            self.visit(value)

    visit_SetComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp
    visit_DictComp = visit_ListComp


def _argument_names(args: ast.arguments) -> set[str]:
    return {item.arg for item in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                                  *([args.vararg] if args.vararg else []),
                                  *([args.kwarg] if args.kwarg else [])]}


def used_python_names(function: ast.FunctionDef) -> set[str]:
    """Include identifiers stored outside ast.Name, including captures/imports."""
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.split(".")[0])
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
        elif isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
    return names


class _ParameterRename(ast.NodeVisitor):
    def __init__(self, document: SourceDocument, old: str, new: str) -> None:
        self.document, self.old, self.new = document, old, new
        self.active = True
        self.closure_active = True
        self.edits: list[tuple[int, int, str]] = []

    def _replace(self, node: ast.AST) -> None:
        self.edits.append((self.document.start(node), self.document.end(node), self.new))

    def _binding_tokens(self, node: ast.AST, *, end: int | None = None) -> None:
        first, last = self.document.start(node), end if end is not None else self.document.end(node)
        for token in self.document.tokens:
            position = self.document.token_position(token.start)
            if first <= position < last and token.type == tokenize.NAME and token.string == self.old:
                self.edits.append((position, self.document.token_position(token.end), self.new))

    def visit_Name(self, node: ast.Name) -> None:
        if self.active and node.id == self.old:
            self._replace(node)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        if self.active and self.old in node.names:
            self._binding_tokens(node)

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> None:
        args = node.args
        # Defaults and annotations belong to the defining scope, not the new one.
        values = [*args.defaults, *args.kw_defaults]
        if not isinstance(node, ast.Lambda):
            values.extend(node.decorator_list)
            if node.returns is not None:
                values.append(node.returns)
            if self.active and node.name == self.old:
                # Locate only the def name; defaults/annotations are visited below.
                for token in self.document.tokens:
                    if token.type == tokenize.NAME and token.string == self.old and self.document.start(node) <= self.document.token_position(token.start):
                        self.edits.append((self.document.token_position(token.start), self.document.token_position(token.end), self.new))
                        break
        for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                    *([args.vararg] if args.vararg else []), *([args.kwarg] if args.kwarg else [])]:
            if arg.annotation is not None:
                values.append(arg.annotation)
        for value in values:
            if value is not None:
                self.visit(value)
        body = [node.body] if isinstance(node, ast.Lambda) else node.body
        bindings = _Bindings()
        for value in body:
            bindings.visit(value)
        local = bindings.locals | _argument_names(args)
        active = self.closure_active and self.old not in bindings.globals and (
            self.old not in local or self.old in bindings.nonlocals
        )
        previous = self.active, self.closure_active
        self.active = self.closure_active = active
        for value in body:
            self.visit(value)
        self.active, self.closure_active = previous

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function
    visit_Lambda = _function

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Classes use dynamic LOAD_NAME resolution. A same-name class binding
        # cannot be safely rewritten, while methods still capture outer locals.
        bindings = _Bindings()
        for value in node.body:
            bindings.visit(value)
        if self.active and (self.old in bindings.locals or node.name == self.old):
            raise PythonScriptDeclarationError(
                "Rename cannot safely resolve a class-body binding with the same name; edit this code manually"
            )
        for value in [*node.decorator_list, *node.bases, *(item.value for item in node.keywords)]:
            self.visit(value)
        previous = self.active
        self.active = self.closure_active and self.old not in bindings.globals
        for value in node.body:
            self.visit(value)
        self.active = previous

    def visit_ListComp(self, node: ast.ListComp) -> None:
        # Only the first iterable is evaluated in the enclosing scope. All
        # targets bind for the entire implicit comprehension function.
        self.visit(node.generators[0].iter)
        bound = {child.id for generator in node.generators for child in ast.walk(generator.target)
                 if isinstance(child, ast.Name)}
        previous = self.active, self.closure_active
        self.active = self.closure_active = self.closure_active and self.old not in bound
        for index, generator in enumerate(node.generators):
            if index:
                self.visit(generator.iter)
            self.visit(generator.target)
            for value in generator.ifs:
                self.visit(value)
        for value in ([node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]):
            self.visit(value)
        self.active, self.closure_active = previous

    visit_SetComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp
    visit_DictComp = visit_ListComp

    def visit_Import(self, node: ast.Import) -> None:
        if self.active:
            for item in node.names:
                if (item.asname or item.name.split(".")[0]) == self.old:
                    if item.asname:
                        # Only the alias is a binding: importing the same module
                        # name is unrelated to the variable rename.
                        last = self.document.end(item)
                        self.edits.append((last - len(self.old), last, self.new))
                    elif "." in item.name:
                        raise PythonScriptDeclarationError("Rename cannot safely rewrite this dotted import binding")
                    else:
                        self.edits.append((self.document.end(item), self.document.end(item), " as " + self.new))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.visit_Import(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is not None:
            self.visit(node.type)
        if self.active and node.name == self.old:
            # Exception type might itself refer to the parameter; only change
            # the capture identifier following 'as'.
            end = self.document.start(node.body[0])
            tokens = [token for token in self.document.tokens
                      if self.document.start(node) <= self.document.token_position(token.start) < end]
            for first, token in zip(tokens, tokens[1:]):
                if first.string == "as" and token.string == self.old:
                    self.edits.append((self.document.token_position(token.start), self.document.token_position(token.end), self.new))
        for value in node.body:
            self.visit(value)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if self.active and node.name == self.old:
            tokens = [token for token in self.document.tokens if token.type == tokenize.NAME
                      and token.string == self.old and self.document.start(node) <= self.document.token_position(token.start) < self.document.end(node)]
            token = tokens[-1]
            self.edits.append((self.document.token_position(token.start), self.document.token_position(token.end), self.new))
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if self.active and node.rest == self.old:
            tokens = [token for token in self.document.tokens if token.type == tokenize.NAME and token.string == self.old
                      and self.document.start(node) <= self.document.token_position(token.start) < self.document.end(node)]
            token = tokens[-1]
            self.edits.append((self.document.token_position(token.start), self.document.token_position(token.end), self.new))
        self.generic_visit(node)


class _Returns(ast.NodeVisitor):
    def __init__(self) -> None:
        self.values: list[ast.Return] = []

    def visit_Return(self, node: ast.Return) -> None:
        self.values.append(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        pass

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef


def rename_edits(
    source: str, document: SourceDocument, function: ast.FunctionDef,
    decorator: ast.Call, old: str, new: str,
) -> list[tuple[int, int, str]]:
    kind = engine.corex_decorator_name(decorator)
    edits = [(document.start(decorator.args[0]), document.end(decorator.args[0]), repr(new))]
    if kind == "output":
        returns = _Returns()
        for statement in function.body:
            returns.visit(statement)
        if not returns.values or any(
            not isinstance(item.value, ast.Dict) or any(
                not isinstance(key, ast.Constant) or not isinstance(key.value, str)
                for key in item.value.keys
            ) for item in returns.values
        ):
            raise PythonScriptDeclarationError(
                "Output rename requires literal returned dictionaries; dynamic output construction remains code-managed"
            )
        for returned in returns.values:
            assert isinstance(returned.value, ast.Dict)
            if any(key.value == new for key in returned.value.keys):
                raise PythonScriptDeclarationError(f"A returned dictionary already contains {new!r}")
            for key_node in returned.value.keys:
                if key_node.value == old:
                    edits.append((document.start(key_node), document.end(key_node), repr(new)))
        return edits

    blocked_names = {"eval", "exec", "globals", "locals", "vars", "__import__"}
    blocked_attributes = {"f_locals", "f_globals", "__dict__", "__code__", "__globals__", "__closure__", "currentframe", "_getframe"}
    # Aliases can be declared before run; scanning only its body misses
    # ``from builtins import locals as inspect_values`` and qualified calls.
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Name) and node.id in blocked_names
                or isinstance(node, ast.Attribute) and node.attr in blocked_attributes | blocked_names
                or isinstance(node, ast.alias) and node.name.split(".")[-1] in blocked_names | blocked_attributes
                or isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr"
                and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in blocked_names | blocked_attributes):
            raise PythonScriptDeclarationError(
                f"Rename is unavailable because dynamic name lookup appears on line {node.lineno}"
            )
    for node in ast.walk(function):
        if (isinstance(node, ast.Name) and node.id == new
                or isinstance(node, ast.arg) and node.arg == new
                or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == new):
            raise PythonScriptDeclarationError(f"The Python name {new!r} is already used on line {node.lineno}")
    # Include less common string-backed bindings in collision checks.
    for node in ast.walk(function):
        if isinstance(node, ast.alias) and (node.asname or node.name.split(".")[0]) == new:
            raise PythonScriptDeclarationError(f"The import name {new!r} is already used")
        if isinstance(node, (ast.Global, ast.Nonlocal)) and new in node.names:
            raise PythonScriptDeclarationError(f"The Python name {new!r} is already declared")
        if isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)) and node.name == new:
            raise PythonScriptDeclarationError(f"The Python name {new!r} is already bound")
        if isinstance(node, ast.MatchMapping) and node.rest == new:
            raise PythonScriptDeclarationError(f"The Python name {new!r} is already bound")
    argument = next((item for item in function.args.args if item.arg == old), None)
    if argument is None:
        raise PythonScriptDeclarationError("Synchronize parameters before renaming this variable")
    edits.append((document.start(argument), document.start(argument) + len(old), new))
    visitor = _ParameterRename(document, old, new)
    for statement in function.body:
        visitor.visit(statement)
    edits.extend(visitor.edits)
    for item in function.decorator_list:
        if isinstance(item, ast.Call):
            for field in item.keywords:
                if field.arg == "type_from_input" and isinstance(field.value, ast.Constant) and field.value.value == old:
                    edits.append((document.start(field.value), document.end(field.value), repr(new)))
    return edits
