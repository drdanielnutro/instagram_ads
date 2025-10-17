"""Testes de sincronização: detectam drift entre enums e fontes canônicas.

CRÍTICO: Estes testes DEVEM rodar em CI/CD e FALHAR se houver inconsistência.
"""

from app.config import CTA_INSTAGRAM_CHOICES
from app.format_specifications import FORMAT_SPECS
from app.schemas.final_delivery import (
    CtaInstagramEnum,
    FormatoAnuncioEnum,
    AspectRatioEnum,
)


def test_cta_enum_sincronizado_com_config():
    """Detecta drift entre CtaInstagramEnum e CTA_INSTAGRAM_CHOICES."""
    enum_values = {e.value for e in CtaInstagramEnum}
    config_values = set(CTA_INSTAGRAM_CHOICES)

    missing_in_enum = config_values - enum_values
    extra_in_enum = enum_values - config_values

    assert enum_values == config_values, (
        f"❌ DRIFT DETECTADO entre CtaInstagramEnum e CTA_INSTAGRAM_CHOICES!\n"
        f"  Em config mas não no enum: {missing_in_enum or 'nenhum'}\n"
        f"  No enum mas não em config: {extra_in_enum or 'nenhum'}\n"
        f"\n"
        f"  AÇÃO REQUERIDA:\n"
        f"  1. Atualizar CtaInstagramEnum em app/schemas/final_delivery.py\n"
        f"  2. Garantir sincronização 1:1 com CTA_INSTAGRAM_CHOICES\n"
        f"  3. Re-executar testes"
    )


def test_formato_enum_sincronizado_com_format_specs():
    """Detecta drift entre FormatoAnuncioEnum e FORMAT_SPECS.keys()."""
    enum_values = {e.value for e in FormatoAnuncioEnum}
    spec_keys = set(FORMAT_SPECS.keys())

    assert enum_values == spec_keys, (
        f"❌ DRIFT DETECTADO entre FormatoAnuncioEnum e FORMAT_SPECS!\n"
        f"  Em FORMAT_SPECS mas não no enum: {spec_keys - enum_values}\n"
        f"  No enum mas não em FORMAT_SPECS: {enum_values - spec_keys}"
    )


def test_aspect_ratio_enum_sincronizado():
    """Detecta drift entre AspectRatioEnum e aspect_ratios de FORMAT_SPECS."""
    # Coletar todos os ratios de FORMAT_SPECS
    expected = set()
    for spec in FORMAT_SPECS.values():
        visual = spec.get("visual", {})
        if "aspect_ratio" in visual:
            expected.add(visual["aspect_ratio"])
        if "permitidos" in visual:
            expected.update(visual["permitidos"])

    enum_values = {e.value for e in AspectRatioEnum}

    assert enum_values == expected, (
        f"❌ DRIFT DETECTADO entre AspectRatioEnum e FORMAT_SPECS!\n"
        f"  Esperado (coletado de FORMAT_SPECS): {expected}\n"
        f"  Atual (AspectRatioEnum): {enum_values}\n"
        f"  Faltam: {expected - enum_values}\n"
        f"  Sobram: {enum_values - expected}"
    )


def test_enums_tem_quantidade_correta():
    """Verifica cardinalidade esperada dos enums."""
    assert len(list(CtaInstagramEnum)) == 5, "Esperado 5 CTAs"
    assert len(list(FormatoAnuncioEnum)) == 3, "Esperado 3 formatos"
    assert len(list(AspectRatioEnum)) == 3, "Esperado 3 aspect ratios"
