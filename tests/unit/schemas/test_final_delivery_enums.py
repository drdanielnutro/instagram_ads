"""Testes unitários: validam comportamento dos enums em modelos Pydantic."""

import pytest
from pydantic import ValidationError
from app.schemas.final_delivery import (
    CtaInstagramEnum,
    FormatoAnuncioEnum,
    AspectRatioEnum,
    StrictAdCopy,
    StrictAdVisual,
    StrictAdItem,
)


def test_cta_enum_aceita_valores_validos():
    """Enum aceita os 5 CTAs permitidos."""
    assert CtaInstagramEnum.SAIBA_MAIS.value == "Saiba mais"
    assert CtaInstagramEnum.COMPRAR_AGORA.value == "Comprar agora"
    assert CtaInstagramEnum.LIGAR.value == "Ligar"


def test_cta_enum_rejeita_valor_invalido():
    """Pydantic rejeita valores fora do enum."""
    with pytest.raises(ValidationError) as exc_info:
        StrictAdCopy(
            headline="Test",
            corpo="Test corpo",
            cta_texto="Garantir o Meu"  # ❌ Inválido (do JSON real do bug)
        )

    error_msg = str(exc_info.value)
    assert "cta_texto" in error_msg
    assert "Input should be" in error_msg or "not a valid enumeration member" in error_msg


def test_strict_ad_item_com_enums_validos():
    """StrictAdItem aceita valores de enum válidos."""
    item = StrictAdItem(
        landing_page_url="https://example.com",
        formato=FormatoAnuncioEnum.FEED,
        copy=StrictAdCopy(
            headline="Test",
            corpo="Test corpo",
            cta_texto=CtaInstagramEnum.COMPRAR_AGORA
        ),
        visual=StrictAdVisual(
            descricao_imagem="Test",
            prompt_estado_atual="Test",
            prompt_estado_intermediario="Test",
            prompt_estado_aspiracional="Test",
            aspect_ratio=AspectRatioEnum.VERTICAL
        ),
        cta_instagram=CtaInstagramEnum.COMPRAR_AGORA,
        fluxo="Instagram Ad → Landing → WhatsApp",
        referencia_padroes="Padrões de Feed"
    )

    # Verificar que enums foram aceitos
    assert item.formato == FormatoAnuncioEnum.FEED
    assert item.copy.cta_texto == CtaInstagramEnum.COMPRAR_AGORA
    assert item.visual.aspect_ratio == AspectRatioEnum.VERTICAL


def test_feed_aceita_dois_aspect_ratios():
    """Feed deve aceitar 1:1 E 4:5 (permitidos em FORMAT_SPECS)."""
    for ratio in [AspectRatioEnum.SQUARE, AspectRatioEnum.VERTICAL]:
        item = StrictAdItem(
            formato=FormatoAnuncioEnum.FEED,
            visual=StrictAdVisual(
                descricao_imagem="Test",
                prompt_estado_atual="Test",
                prompt_estado_intermediario="Test",
                prompt_estado_aspiracional="Test",
                aspect_ratio=ratio
            ),
            copy=StrictAdCopy(
                headline="Test",
                corpo="Test",
                cta_texto=CtaInstagramEnum.SAIBA_MAIS
            ),
            landing_page_url="https://test.com",
            cta_instagram=CtaInstagramEnum.SAIBA_MAIS,
            fluxo="Test",
            referencia_padroes="Test"
        )
        # Não deve lançar exceção
        assert item.formato == FormatoAnuncioEnum.FEED


def test_reels_so_aceita_9_16():
    """Reels só aceita 9:16 (não aceita 1:1 ou 4:5)."""
    with pytest.raises(ValidationError) as exc:
        StrictAdItem(
            formato=FormatoAnuncioEnum.REELS,
            visual=StrictAdVisual(
                descricao_imagem="Test",
                prompt_estado_atual="Test",
                prompt_estado_intermediario="Test",
                prompt_estado_aspiracional="Test",
                aspect_ratio=AspectRatioEnum.VERTICAL  # ❌ 4:5 não permitido em Reels
            ),
            copy=StrictAdCopy(
                headline="Test",
                corpo="Test",
                cta_texto=CtaInstagramEnum.SAIBA_MAIS
            ),
            landing_page_url="https://test.com",
            cta_instagram=CtaInstagramEnum.SAIBA_MAIS,
            fluxo="Test",
            referencia_padroes="Test"
        )

    assert "aspect_ratio" in str(exc.value)
    assert "not allowed" in str(exc.value)


def test_pydantic_converte_strings_para_enums():
    """Pydantic automaticamente converte strings válidas para enums."""
    item = StrictAdItem(
        landing_page_url="https://example.com",
        formato="Feed",  # ← String, não enum
        copy={
            "headline": "Test",
            "corpo": "Test",
            "cta_texto": "Comprar agora"  # ← String, não enum
        },
        visual={
            "descricao_imagem": "Test",
            "prompt_estado_atual": "Test",
            "prompt_estado_intermediario": "Test",
            "prompt_estado_aspiracional": "Test",
            "aspect_ratio": "4:5"  # ← String, não enum
        },
        cta_instagram="Comprar agora",  # ← String
        fluxo="Test",
        referencia_padroes="Test"
    )

    # Pydantic converte automaticamente
    assert isinstance(item.formato, FormatoAnuncioEnum)
    assert isinstance(item.copy.cta_texto, CtaInstagramEnum)
    assert isinstance(item.visual.aspect_ratio, AspectRatioEnum)
