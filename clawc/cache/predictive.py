from __future__ import annotations

import ast
import re
from pathlib import Path

_JS_IMPORT_RE = re.compile(r"""(?:import|require)\s*(?:\(?\s*)?['\"]([\'\"]+)['\"]""")


def extract_python_imports(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def extract_js_imports(source: str) -> list[str]:
    return _JS_IMPORT_RE.findall(source)


def resolve_local_imports(file_path: Path, module_names: list[str]) -> list[Path]:
    parent = file_path.parent
    candidates: list[Path] = []
    for name in module_names:
        if name.startswith("."):
            continue
        rel = name.replace(".", "/")
        for suffix in (".py", ".ts", ".js", ".tsx", ".jsx"):
            p = parent / f"{rel}{suffix}"
            if p.exists():
                candidates.append(p)
    return candidates


def get_prefetch_paths(file_path: Path, content: str) -> list[Path]:
    suffix = file_path.suffix
    if suffix == ".py":
        imports = extract_python_imports(content)
    elif suffix in {".ts", ".js", ".tsx", ".jsx"}:
        imports = extract_js_imports(content)
    else:
        return []
    return resolve_local_imports(file_path, imports)
