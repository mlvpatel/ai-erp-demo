#!/usr/bin/env python3
"""Statically resolve the in-repo symbols that capacity.py depends on.

capacity.py runs only from the manual AWS capacity workflow, so a renamed
helper in one of its in-repo dependencies would otherwise surface in no run at
all. This parses source with ast and symtable only: no frappe import, no
network, no database. Passing says the symbols resolve; it says nothing about
capacity behavior.

1. Every `from ai_erp_service... import name` in capacity.py must name a
   module-scope definition of the module it points at.
2. In capacity.py and in each in-repo module it imports from, every
   module-scope name that a function or class reads must be defined at module
   scope or be a builtin.
"""

from __future__ import annotations

import ast
import builtins
import symtable
from pathlib import Path

from _gate import REPO_ROOT, parse_python, read_text, rel, report


APP_ROOT = REPO_ROOT / "apps" / "ai_erp_service"
CAPACITY_PATH = APP_ROOT / "ai_erp_service" / "capacity.py"
PACKAGE = "ai_erp_service"
MODULE_DUNDERS = {"__builtins__", "__doc__", "__file__", "__loader__", "__name__", "__package__", "__spec__"}


def module_file(module_name: str) -> Path | None:
    base = APP_ROOT.joinpath(*module_name.split("."))
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def module_scope(path: Path, failures: list[str]) -> tuple[symtable.SymbolTable, set[str]] | None:
    """Return the module symbol table and the names bound at module scope."""
    source = read_text(path, failures)
    if not source:
        return None
    try:
        table = symtable.symtable(source, str(path), "exec")
    except SyntaxError as exc:
        failures.append(f"invalid Python in {rel(path)}: {exc}")
        return None
    defined = {symbol.get_name() for symbol in table.get_symbols() if symbol.is_assigned() or symbol.is_imported()}
    defined.update(child.get_name() for child in table.get_children())
    return table, defined


def check_module_scope_reads(path: Path, scope: tuple[symtable.SymbolTable, set[str]], failures: list[str]) -> None:
    table, defined = scope

    def walk(parent: symtable.SymbolTable) -> None:
        for child in parent.get_children():
            for symbol in child.get_symbols():
                name = symbol.get_name()
                if not symbol.is_global() or symbol.is_declared_global():
                    continue
                if name in defined or name in MODULE_DUNDERS or hasattr(builtins, name):
                    continue
                where = f"{rel(path)}" if path == CAPACITY_PATH else f"{rel(CAPACITY_PATH)} imports from {rel(path)}, whose"
                failures.append(
                    f"{where} scope {child.get_name()!r} references the undefined module-level name {name!r}"
                )
            walk(child)

    walk(table)


def main() -> int:
    failures: list[str] = []
    capacity = parse_python(CAPACITY_PATH, failures)
    capacity_scope = module_scope(CAPACITY_PATH, failures)
    dependencies: dict[Path, tuple[symtable.SymbolTable, set[str]]] = {}
    for node in ast.walk(capacity) if capacity else ():
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == PACKAGE and module_file(alias.name) is None:
                    failures.append(f"{rel(CAPACITY_PATH)}: in-repo module {alias.name} does not resolve to a file")
            continue
        if not isinstance(node, ast.ImportFrom) or node.level or (node.module or "").split(".")[0] != PACKAGE:
            continue
        target = module_file(node.module or "")
        if target is None:
            failures.append(f"{rel(CAPACITY_PATH)}: in-repo module {node.module} does not resolve to a file")
            continue
        scope = dependencies.get(target) or module_scope(target, failures)
        if scope is None:
            continue
        dependencies[target] = scope
        for alias in node.names:
            if alias.name not in scope[1]:
                failures.append(
                    f"{rel(CAPACITY_PATH)} imports {alias.name!r}, which is not defined at module scope of {rel(target)}"
                )

    if capacity is not None and not dependencies:
        failures.append(f"{rel(CAPACITY_PATH)}: found no in-repo imports to resolve")
    if capacity_scope is not None:
        check_module_scope_reads(CAPACITY_PATH, capacity_scope, failures)
    for target in sorted(dependencies):
        check_module_scope_reads(target, dependencies[target], failures)

    resolved = ", ".join(rel(path) for path in sorted(dependencies))
    return report(
        "Capacity import resolution check",
        failures,
        f"Capacity import resolution check passed ({resolved}).",
    )


if __name__ == "__main__":
    raise SystemExit(main())
