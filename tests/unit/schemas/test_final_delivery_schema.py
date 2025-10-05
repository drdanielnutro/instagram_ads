from __future__ import annotations

import json
import pytest

from app.schemas.final_delivery import (
    StrictAdCopy,
    StrictAdItem,
    StrictAdVisual,
    model_dump,
)


def _valid_copy(**overrides: str) -> StrictAdCopy:
    data = {
        "headline": "Ganhe tempo com nosso app",
        "corpo": "Simplifique o agendamento com poucos cliques.",
        "cta_texto": "Saiba mais",
    }
    data.update(overrides)
    return StrictAdCopy(**data)


def _valid_visual(**overrides: str) -> StrictAdVisual:
    data = {
        "descricao_imagem": "Mulher usando smartphone em consultório",
        "prompt_estado_atual": "female professional stressed at desk",
        "prompt_estado_intermediario": "same professional smiling scheduling",
        "prompt_estado_aspiracional": "same professional relaxed after scheduling",
        "aspect_ratio": "9:16",
    }
    data.update(overrides)
    return StrictAdVisual(**data)


def _valid_item(**overrides) -> StrictAdItem:
    payload = {
        "landing_page_url": "https://example.com",
        "formato": "Reels",
        "copy": _valid_copy(),
        "visual": _valid_visual(),
        "cta_instagram": "Saiba mais",
        "fluxo": "Instagram → Landing Page",
        "referencia_padroes": "Referências",
        "contexto_landing": "{\"hero\": \"Consultas online\"}",
    }
    payload.update(overrides)
    return StrictAdItem(**payload)


def test_contexto_landing_accepts_json_string_and_model_dump_normalizes():
    item = _valid_item()
    assert item.contexto_landing == {"hero": "Consultas online"}

    dumped = item.canonical_dict()
    assert dumped["contexto_landing"] == {"hero": "Consultas online"}

    as_json = model_dump([item])
    assert as_json == {"variations": [dumped]}


def test_from_state_infers_defaults_and_preserves_contexto():
    state = {
        "landing_page_url": "https://landing.example",
        "formato_anuncio": "Stories",
        "fluxo": "Instagram → LP → Whatsapp",
        "referencia_padroes": "StoryBrand",
        "contexto_landing": {"foco": "agendamentos"},
    }
    item = StrictAdItem.from_state(
        state,
        copy=_valid_copy(cta_texto="Cadastre-se").model_dump(mode="python"),
        visual=_valid_visual(aspect_ratio="9:16").model_dump(mode="python"),
    )

    assert item.formato == "Stories"
    assert item.cta_instagram == "Cadastre-se"
    assert item.contexto_landing == {"foco": "agendamentos"}
    assert item.canonical_dict()["contexto_landing"] == {"foco": "agendamentos"}


def test_invalid_cta_texto_raises_validation_error():
    with pytest.raises(ValueError):
        _valid_item(copy=_valid_copy(cta_texto="Invalid CTA"))

