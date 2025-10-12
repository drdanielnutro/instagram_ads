#!/usr/bin/env python3
"""
Replica arquivos template de planos e resultados para os diretórios operacionais.
Executar antes de iniciar uma nova tarefa para garantir estado limpo.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLANS_TEMPLATE_DIR = PROJECT_ROOT / ".claude" / "plans" / "templates"
RESULTS_TEMPLATE_DIR = PROJECT_ROOT / ".claude" / "results" / "templates"


def copy_templates(template_dir: Path, target_dir: Path) -> list[str]:
    copied: list[str] = []
    for template_path in sorted(template_dir.glob("*.template.json")):
        target_path = target_dir / template_path.name.replace(".template", "")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(template_path, target_path)
        copied.append(str(target_path.relative_to(PROJECT_ROOT)))
    return copied


def validate_templates(template_dir: Path) -> None:
    """
    Garante que templates sejam JSON válidos antes da cópia.
    Levanta ValueError em caso de erro.
    """
    for template_path in template_dir.glob("*.template.json"):
        with template_path.open("r", encoding="utf-8") as handle:
            json.load(handle)


def main() -> None:
    validate_templates(PLANS_TEMPLATE_DIR)
    validate_templates(RESULTS_TEMPLATE_DIR)

    plans_target_dir = PROJECT_ROOT / ".claude" / "plans"
    results_target_dir = PROJECT_ROOT / ".claude" / "results"

    plans_copied = copy_templates(PLANS_TEMPLATE_DIR, plans_target_dir)
    results_copied = copy_templates(RESULTS_TEMPLATE_DIR, results_target_dir)

    for path in plans_copied + results_copied:
        print(f"[templates] atualizado: {path}")


if __name__ == "__main__":
    main()
