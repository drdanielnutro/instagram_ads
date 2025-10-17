"""Valida que Pydantic gera JSON Schema correto com campo 'enum'."""

import json
import pytest
from app.schemas.final_delivery import StrictAdCopy, CtaInstagramEnum


def test_enum_gera_campo_enum_no_json_schema():
    """Verifica que enum é convertido para OpenAPI schema com campo 'enum'."""
    schema = StrictAdCopy.model_json_schema()

    print("\n" + "=" * 80)
    print("JSON Schema gerado para StrictAdCopy:")
    print("=" * 80)
    print(json.dumps(schema, indent=2, ensure_ascii=False))

    # Verificar que enum está presente no schema
    if "$defs" in schema:
        cta_enum_def = schema["$defs"].get("CtaInstagramEnum", {})
        assert "enum" in cta_enum_def, "Campo 'enum' não encontrado no JSON Schema!"
        assert len(cta_enum_def["enum"]) == 5, "Esperado 5 valores no enum"
        assert "Saiba mais" in cta_enum_def["enum"]
        assert "Comprar agora" in cta_enum_def["enum"]

        print("\n✅ SUCESSO: Campo 'enum' presente no JSON Schema")
        print(f"   Valores: {cta_enum_def['enum']}")
    else:
        pytest.fail("$defs não encontrado no schema - estrutura inesperada")
