#!/usr/bin/env python3
"""
Formata arquivos JavaScript/TypeScript após operações de edição.
Compatível com Write, Edit e MultiEdit (Claude Code Hooks Reference).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Set

FORMATTABLE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}

def resolve_paths(payload) -> Set[Path]:
    paths: Set[Path] = set()
    tool_response = payload.get("tool_response") or {}
    edits = tool_response.get("edits") or []
    for edit in edits:
        file_path = edit.get("filePath")
        if file_path:
            paths.add(Path(file_path))

    fallback = (
        tool_response.get("filePath")
        or payload.get("tool_input", {}).get("file_path")
    )
    if fallback:
        paths.add(Path(fallback))
    return paths

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"[hooks] Invalid JSON payload: {exc}", file=sys.stderr)
        return 0

    prettier = shutil.which("npx")
    if prettier is None:
        print("[hooks] npx não encontrado; pulando formatação automática.", file=sys.stderr)
        return 0

    project_root = Path(payload.get("cwd") or ".").resolve()
    exit_code = 0

    for path in resolve_paths(payload):
        candidate = (project_root / path).resolve() if not path.is_absolute() else path.resolve()
        if candidate.suffix not in FORMATTABLE_EXTENSIONS:
            continue

        result = subprocess.run(
            ["npx", "prettier", "--write", str(candidate)],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            exit_code = result.returncode
            print(f"[hooks] Falha ao formatar {candidate}: {result.stderr}", file=sys.stderr)
        else:
            print(f"[hooks] Formatted: {candidate}", file=sys.stderr)

    return exit_code

if __name__ == "__main__":
    sys.exit(main())