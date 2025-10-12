#!/usr/bin/env python3
"""
Valida file boundaries antes de editar arquivo.
Hook PreToolUse para sistema multi-agente.
"""
import json
import sys
from pathlib import Path

# Diretórios protegidos (nunca editar) - ver Hooks Reference (File Boundaries)
PROTECTED_DIRS = [
    ".claude/state",
    ".claude/hooks",
    ".claude/agents",
    ".claude/plans/templates",
    ".claude/results/templates",
    "node_modules",
    "dist",
    "build",
    ".git",
]

# Arquivos protegidos (nunca editar)
PROTECTED_FILES = [
    ".env",
    "package-lock.json",
    "yarn.lock",
    "app/.env",
    "frontend/.env.local",
]

try:
    input_data = json.load(sys.stdin)
    file_path = input_data.get('tool_input', {}).get('file_path', '')
    
    if not file_path:
        sys.exit(0)  # Sem file_path, skip validation
    
    project_root = Path(input_data.get("cwd") or ".").resolve()
    raw_path = Path(file_path)
    candidate = (project_root / raw_path).resolve() if not raw_path.is_absolute() else raw_path.resolve()

    # Impede path traversal (.. escapando do repositório)
    if project_root not in candidate.parents and candidate != project_root:
        error_msg = (
            "[hooks] FILE BOUNDARY VIOLATION\n"
            f"Tentativa de acessar fora do repositório: {candidate}"
        )
        print(error_msg, file=sys.stderr)
        sys.exit(2)

    def is_within(path: Path, directory: Path) -> bool:
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            return False

    protected_dirs = [(project_root / d).resolve() for d in PROTECTED_DIRS]
    for protected_dir in protected_dirs:
        if is_within(candidate, protected_dir):
            error_msg = (
                "[hooks] FILE BOUNDARY VIOLATION\n"
                f"Tentativa de editar diretório protegido: {candidate}\n"
                f"Diretório protegido: {protected_dir}\n"
                "Consulte seção 'FILE BOUNDARIES' no CLAUDE.md"
            )
            print(error_msg, file=sys.stderr)
            sys.exit(2)

    protected_files = {(project_root / f).resolve() for f in PROTECTED_FILES}
    if candidate in protected_files:
        error_msg = (
            "[hooks] FILE BOUNDARY VIOLATION\n"
            f"Tentativa de editar arquivo protegido: {candidate}\n"
            "Consulte seção 'FILE BOUNDARIES' no CLAUDE.md"
        )
        print(error_msg, file=sys.stderr)
        sys.exit(2)

    # Se chegou aqui, arquivo é permitido
    sys.exit(0)

except Exception as exc:
    print(f"[hooks] Erro na validação de boundaries: {exc}", file=sys.stderr)
    sys.exit(1)  # Non-blocking error
