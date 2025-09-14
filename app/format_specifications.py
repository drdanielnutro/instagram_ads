"""
Especificações curtas por formato para orientar prompts e validações.

Uso: injetar `FORMAT_SPECS[formato]` no state como `format_specs` e
`format_specs_json` (json.dumps) para consumo nos prompts dos agentes.
"""

from __future__ import annotations

from typing import Any, Dict
import json


FORMAT_SPECS: Dict[str, Dict[str, Any]] = {
    "Reels": {
        "copy": {
            "headline_max_chars": 40,
            "estrutura": "gancho-desenvolvimento-cta",
            "estilo": "direto, curto, com verbos de ação",
        },
        "visual": {
            "aspect_ratio": "9:16",
            "notas": [
                "zona segura para texto/logos",
                "parecer nativo do feed de Reels",
                "minimizar texto sobreposto",
            ],
        },
        "strategy": {
            "etapa_funil": "topo",
            "cta_preferencial": {
                "agendamentos": "Enviar mensagem",
                "leads": "Cadastre-se",
                "vendas": "Saiba mais",
            },
        },
    },
    "Stories": {
        "copy": {
            "headline_max_chars": 40,
            "estrutura": "gancho-desenvolvimento-cta",
            "estilo": "curto, urgente, conversacional",
        },
        "visual": {
            "aspect_ratio": "9:16",
            "notas": [
                "texto on-screen curto e legível",
                "evitar elementos interativos proibidos em ads",
                "manter contraste e hierarquia visual",
            ],
        },
        "strategy": {
            "etapa_funil": "meio",
            "cta_preferencial": {
                "agendamentos": "Enviar mensagem",
                "leads": "Cadastre-se",
                "vendas": "Saiba mais",
            },
        },
    },
    "Feed": {
        "copy": {
            "headline_max_chars": 60,
            "estrutura": "gancho-desenvolvimento-cta",
            "estilo": "informativo, claro",
        },
        "visual": {
            "aspect_ratio_preferido": "4:5",
            "aspect_ratio": "4:5",
            "permitidos": ["1:1", "4:5"],
            "notas": [
                "evitar excesso de texto sobreposto",
                "foco em legibilidade e composição",
            ],
        },
        "strategy": {
            "etapa_funil": "fundo",
            "cta_preferencial": {
                "agendamentos": "Enviar mensagem",
                "leads": "Cadastre-se",
                "vendas": "Comprar agora",
            },
        },
    },
}


def get_specs_by_format(formato_anuncio: str) -> Dict[str, Any]:
    fmt = (formato_anuncio or "").strip().title()
    if fmt not in FORMAT_SPECS:
        raise ValueError(f"Formato não suportado: {formato_anuncio}")
    return FORMAT_SPECS[fmt]


def get_specs_json_by_format(formato_anuncio: str) -> str:
    specs = get_specs_by_format(formato_anuncio)
    return json.dumps(specs, ensure_ascii=False, separators=(",", ":"))

