"""
Planos fixos por formato (Reels, Stories, Feed) compatíveis com o pipeline ADK atual.

Cada plano segue o modelo esperado por ImplementationPlan/ImplementationTask em app/agent.py:
- ImplementationPlan: { feature_name, estimated_time, implementation_tasks }
- ImplementationTask: { id, category, title, description, file_path, action, dependencies }

Categorias suportadas pelo pipeline atual:
    STRATEGY, RESEARCH, COPY_DRAFT, COPY_QA, VISUAL_DRAFT, VISUAL_QA, COMPLIANCE_QA, ASSEMBLY

Uso esperado: o servidor (preflight) seleciona o plano pelo formato normalizado e
injeta no state como `implementation_plan`, junto com `format_specs` (ver app/format_specifications.py)
e os campos extraídos (landing_page_url, objetivo_final, perfil_cliente, formato_anuncio, foco).
"""

from __future__ import annotations

from typing import Any, Dict, List


def _tasks_reels() -> List[Dict[str, Any]]:
    base_dir = "ads/reels"
    return [
        {
            "id": "TASK-001",
            "category": "STRATEGY",
            "title": "Mensagens‑chave (Reels; topo de funil)",
            "description": (
                "Definir 3–4 mensagens‑chave com gancho forte e promessa central objetiva, refletindo o foco "
                "(se houver) e o conteúdo REAL da landing. Tom enérgico, claro, sem generalidades."
            ),
            "file_path": f"{base_dir}/TASK-001.json",
            "action": "CREATE",
            "dependencies": [],
        },
        {
            "id": "TASK-002",
            "category": "RESEARCH",
            "title": "Referências/padrões (Reels 2024–2025)",
            "description": (
                "Sintetizar padrões de Reels com alta performance no Brasil (2024–2025) em 2–4 linhas úteis; "
                "sem lorem ipsum, nada vago."
            ),
            "file_path": f"{base_dir}/TASK-002.json",
            "action": "CREATE",
            "dependencies": [],
        },
        {
            "id": "TASK-003",
            "category": "COPY_DRAFT",
            "title": "Copy (gancho curto + CTA)",
            "description": (
                "Gerar copy: headline curta (≤40 caracteres) com gancho específico; corpo conciso; cta_texto coerente "
                "com o objetivo_final. Evitar promessas médicas indevidas; pt‑BR."
            ),
            "file_path": f"{base_dir}/TASK-003.json",
            "action": "CREATE",
            "dependencies": ["TASK-001"],
        },
        {
            "id": "TASK-004",
            "category": "COPY_QA",
            "title": "QA da copy (Reels)",
            "description": (
                "Aprovar se: headline ≤40; coerência com foco e landing; CTA adequado ao objetivo. Se ‘ajustar’, "
                "listar motivos objetivos e uma proposta de ajuste."
            ),
            "file_path": f"{base_dir}/TASK-004.json",
            "action": "CREATE",
            "dependencies": ["TASK-003"],
        },
        {
            "id": "TASK-005",
            "category": "VISUAL_DRAFT",
            "title": "Visual estático 9:16 (Reels)",
            "description": (
                "Gerar draft visual com dois campos: descricao_imagem (pt-BR, detalhando composição/elementos) e "
                "prompt_imagem (inglês técnico para IA, cobrindo estilo, iluminação, lente, qualidade). Respeitar zonas de "
                "segurança da UI e definir aspect_ratio=\"9:16\"."
            ),
            "file_path": f"{base_dir}/TASK-005.json",
            "action": "CREATE",
            "dependencies": ["TASK-004"],
        },
        {
            "id": "TASK-006",
            "category": "VISUAL_QA",
            "title": "QA do visual (Reels)",
            "description": (
                "Validar legibilidade, contraste, zona segura e coerência com Reels; evitar excesso de texto."
            ),
            "file_path": f"{base_dir}/TASK-006.json",
            "action": "CREATE",
            "dependencies": ["TASK-005"],
        },
        {
            "id": "TASK-007",
            "category": "COMPLIANCE_QA",
            "title": "Compliance (saúde/Meta)",
            "description": (
                "Checar: sem ‘antes‑depois’, sem alegações médicas indevidas, sem termos proibidos; tom responsável."
            ),
            "file_path": f"{base_dir}/TASK-007.json",
            "action": "CREATE",
            "dependencies": ["TASK-004", "TASK-006"],
        },
        {
            "id": "TASK-008",
            "category": "ASSEMBLY",
            "title": "Montagem do JSON final (Reels)",
            "description": (
                "Combinar campos obrigatórios; definir formato=\"Reels\" e aspect_ratio=\"9:16\"; fluxo padrão "
                "‘Instagram Ad → Landing Page → Botão WhatsApp’, salvo orientação diversa."
            ),
            "file_path": f"{base_dir}/TASK-008.json",
            "action": "CREATE",
            "dependencies": ["TASK-002", "TASK-004", "TASK-006", "TASK-007"],
        },
    ]


def _tasks_stories() -> List[Dict[str, Any]]:
    base_dir = "ads/stories"
    return [
        {
            "id": "TASK-001",
            "category": "STRATEGY",
            "title": "Mensagens‑chave (Stories; urgência)",
            "description": (
                "Definir 3–4 mensagens com tom conversacional e senso de urgência moderado, alinhadas ao foco e à "
                "landing. Sem sensacionalismo."
            ),
            "file_path": f"{base_dir}/TASK-001.json",
            "action": "CREATE",
            "dependencies": [],
        },
        {
            "id": "TASK-002",
            "category": "RESEARCH",
            "title": "Referências/padrões (Stories 2024–2025)",
            "description": (
                "Sintetizar padrões de Stories de alta performance (2–4 linhas úteis); considerar restrições de ads a "
                "elementos interativos."
            ),
            "file_path": f"{base_dir}/TASK-002.json",
            "action": "CREATE",
            "dependencies": [],
        },
        {
            "id": "TASK-003",
            "category": "COPY_DRAFT",
            "title": "Copy curta (Stories)",
            "description": (
                "Gerar copy com headline curta (≤40), corpo direto e cta_texto claro; sem legenda tradicional; "
                "pt‑BR; evitar exageros."
            ),
            "file_path": f"{base_dir}/TASK-003.json",
            "action": "CREATE",
            "dependencies": ["TASK-001"],
        },
        {
            "id": "TASK-004",
            "category": "COPY_QA",
            "title": "QA da copy (Stories)",
            "description": (
                "Aprovar se: headline ≤40; urgência adequada; coerência com landing/foco; CTA compatível. Em ‘ajustar’, "
                "fornecer motivos e sugestão."
            ),
            "file_path": f"{base_dir}/TASK-004.json",
            "action": "CREATE",
            "dependencies": ["TASK-003"],
        },
        {
            "id": "TASK-005",
            "category": "VISUAL_DRAFT",
            "title": "Visual estático 9:16 (Stories)",
            "description": (
                "Gerar descricao_imagem (pt-BR, foco em legibilidade/elementos verticais) e prompt_imagem (inglês técnico "
                "para IA destacando composição vertical, contraste, estilo). Garantir aspect_ratio=\"9:16\"."
            ),
            "file_path": f"{base_dir}/TASK-005.json",
            "action": "CREATE",
            "dependencies": ["TASK-004"],
        },
        {
            "id": "TASK-006",
            "category": "VISUAL_QA",
            "title": "QA do visual (Stories)",
            "description": (
                "Validar legibilidade, contraste e compatibilidade com Stories; sem elementos interativos bloqueados em ads."
            ),
            "file_path": f"{base_dir}/TASK-006.json",
            "action": "CREATE",
            "dependencies": ["TASK-005"],
        },
        {
            "id": "TASK-007",
            "category": "COMPLIANCE_QA",
            "title": "Compliance (saúde/Meta)",
            "description": (
                "Checar: sem ‘antes‑depois’, sem alegações médicas indevidas; respeitar restrições de stickers em ads."
            ),
            "file_path": f"{base_dir}/TASK-007.json",
            "action": "CREATE",
            "dependencies": ["TASK-004", "TASK-006"],
        },
        {
            "id": "TASK-008",
            "category": "ASSEMBLY",
            "title": "Montagem do JSON final (Stories)",
            "description": (
                "Combinar campos obrigatórios; definir formato=\"Stories\" e aspect_ratio=\"9:16\"; fluxo padrão "
                "‘Instagram Ad → Landing Page → Botão WhatsApp’, salvo orientação diversa."
            ),
            "file_path": f"{base_dir}/TASK-008.json",
            "action": "CREATE",
            "dependencies": ["TASK-002", "TASK-004", "TASK-006", "TASK-007"],
        },
    ]


def _tasks_feed() -> List[Dict[str, Any]]:
    base_dir = "ads/feed"
    return [
        {
            "id": "TASK-001",
            "category": "STRATEGY",
            "title": "Mensagens‑chave (Feed; informativo)",
            "description": (
                "Definir 3–4 mensagens informativas e de valor, alinhadas à landing e ao foco; clareza e objetividade."
            ),
            "file_path": f"{base_dir}/TASK-001.json",
            "action": "CREATE",
            "dependencies": [],
        },
        {
            "id": "TASK-002",
            "category": "RESEARCH",
            "title": "Referências/padrões (Feed 2024–2025)",
            "description": (
                "Sintetizar padrões de criativos de Feed (de preferência 4:5) com boa performance em 2–4 linhas úteis."
            ),
            "file_path": f"{base_dir}/TASK-002.json",
            "action": "CREATE",
            "dependencies": [],
        },
        {
            "id": "TASK-003",
            "category": "COPY_DRAFT",
            "title": "Copy informativa (Feed)",
            "description": (
                "Gerar copy: headline clara (≤60), corpo informativo e cta_texto coerente com o objetivo_final; pt‑BR."
            ),
            "file_path": f"{base_dir}/TASK-003.json",
            "action": "CREATE",
            "dependencies": ["TASK-001"],
        },
        {
            "id": "TASK-004",
            "category": "COPY_QA",
            "title": "QA da copy (Feed)",
            "description": (
                "Aprovar se: headline ≤60; copy clara e relevante; CTA adequado ao objetivo; coerência com landing/foco."
            ),
            "file_path": f"{base_dir}/TASK-004.json",
            "action": "CREATE",
            "dependencies": ["TASK-003"],
        },
        {
            "id": "TASK-005",
            "category": "VISUAL_DRAFT",
            "title": "Visual estático 4:5 (preferido)",
            "description": (
                "Produzir descricao_imagem (pt-BR, composição limpa e legível) e prompt_imagem (inglês técnico para IA "
                "detalhando paleta, iluminação, ângulo). Manter aspect_ratio=\"4:5\" (preferido) ou \"1:1\" justificável."
            ),
            "file_path": f"{base_dir}/TASK-005.json",
            "action": "CREATE",
            "dependencies": ["TASK-004"],
        },
        {
            "id": "TASK-006",
            "category": "VISUAL_QA",
            "title": "QA do visual (Feed)",
            "description": (
                "Validar legibilidade, proporção e baixa densidade de texto; coerência com Feed e objetivo_final."
            ),
            "file_path": f"{base_dir}/TASK-006.json",
            "action": "CREATE",
            "dependencies": ["TASK-005"],
        },
        {
            "id": "TASK-007",
            "category": "COMPLIANCE_QA",
            "title": "Compliance (saúde/Meta)",
            "description": (
                "Checar: sem ‘antes‑depois’, sem alegações médicas indevidas, sem termos proibidos; tom responsável."
            ),
            "file_path": f"{base_dir}/TASK-007.json",
            "action": "CREATE",
            "dependencies": ["TASK-004", "TASK-006"],
        },
        {
            "id": "TASK-008",
            "category": "ASSEMBLY",
            "title": "Montagem do JSON final (Feed)",
            "description": (
                "Combinar campos obrigatórios; definir formato=\"Feed\" e aspect_ratio=\"4:5\" (preferido); "
                "fluxo padrão ‘Instagram Ad → Landing Page → Botão WhatsApp’, salvo orientação diversa."
            ),
            "file_path": f"{base_dir}/TASK-008.json",
            "action": "CREATE",
            "dependencies": ["TASK-002", "TASK-004", "TASK-006", "TASK-007"],
        },
    ]


# Planos por formato (apenas metadados e sequência variam por pasta)

REELS_PLAN: Dict[str, Any] = {
    "feature_name": "Instagram Ads – Reels (fixo)",
    "estimated_time": "~10m",
    "implementation_tasks": _tasks_reels(),
}

STORIES_PLAN: Dict[str, Any] = {
    "feature_name": "Instagram Ads – Stories (fixo)",
    "estimated_time": "~10m",
    "implementation_tasks": _tasks_stories(),
}

FEED_PLAN: Dict[str, Any] = {
    "feature_name": "Instagram Ads – Feed (fixo)",
    "estimated_time": "~10m",
    "implementation_tasks": _tasks_feed(),
}


def get_plan_by_format(formato_anuncio: str) -> Dict[str, Any]:
    """Seleciona o plano fixo pelo formato normalizado (Reels|Stories|Feed)."""
    fmt = (formato_anuncio or "").strip().lower()
    if fmt == "reels":
        return REELS_PLAN
    if fmt == "stories":
        return STORIES_PLAN
    if fmt == "feed":
        return FEED_PLAN
    raise ValueError(f"Formato não suportado: {formato_anuncio}")
