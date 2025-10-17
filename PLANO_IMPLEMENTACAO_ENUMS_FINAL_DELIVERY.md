# 🎯 PLANO REVISADO: Implementação de Enums no Final Delivery
## Versão: Mínima e Pragmática (Fases 1, 2, 5, 6)

---

## 📋 Resumo Executivo

Implementar **enums nativos Python declarativos** para substituir validadores Pydantic em campos com valores restritos (CTAs, formato, aspect_ratio), garantindo que o Gemini API respeite essas restrições **durante a geração** via `output_schema`.

**Impacto:** Elimina 100% dos erros de valores enum inválidos gerados pelo LLM
**Complexidade:** Média (refatoração schemas + testes de sincronização)
**Duração estimada:** 2h 30min (sem fases opcionais)

---

## 🔬 Causa Raiz Identificada (Evidências Empíricas)

### ❌ Problema: Validadores Pydantic Não Geram Campo "enum" no JSON Schema

**Teste executado comprova:**

```python
# Cenário 1: @field_validator (ATUAL)
class StrictAdCopy(BaseModel):
    cta_texto: str = Field(..., min_length=1)

    @field_validator("cta_texto")
    def validate_cta(cls, value: str) -> str:
        if value not in CTA_INSTAGRAM_CHOICES:
            raise ValueError(...)
```

**JSON Schema gerado:**
```json
{
  "cta_texto": {
    "type": "string",      ← Sem restrição!
    "minLength": 1
  }
}
```

**Resultado:** Gemini gera `"Garantir o Meu"`, `"Ver Promoção"` (valores inválidos)

---

```python
# Cenário 2: enum.Enum (SOLUÇÃO)
class CtaEnum(str, enum.Enum):
    SAIBA_MAIS = "Saiba mais"
    COMPRAR_AGORA = "Comprar agora"

class StrictAdCopy(BaseModel):
    cta_texto: CtaEnum
```

**JSON Schema gerado:**
```json
{
  "$defs": {
    "CtaEnum": {
      "enum": ["Saiba mais", "Comprar agora", ...],  ← Restrição presente!
      "type": "string"
    }
  }
}
```

**Resultado:** Gemini **só pode** escolher valores da lista durante a geração

---

## 🎬 FASE 1: Criar Enums Declarativos (OBRIGATÓRIA)

**Arquivo:** `app/schemas/final_delivery.py`

### 1.1 Adicionar imports

```python
import enum
from typing import Any  # já existe
```

### 1.2 Definir enums (APÓS imports, ANTES dos modelos)

```python
# ============================================================================
# Enums - Valores restritos para geração controlada com Gemini API
# SINCRONIZADOS com fontes canônicas via testes obrigatórios
# ============================================================================

class CtaInstagramEnum(str, enum.Enum):
    """CTAs permitidos pelo Instagram Ads.

    FONTE CANÔNICA: app.config.CTA_INSTAGRAM_CHOICES
    SINCRONIZAÇÃO: Garantida por test_cta_enum_sincronizado_com_config()

    NOTA: Expansão futura para ~64 CTAs está prevista no
    PLAN_CORRECAO_FINAL_DELIVERY.md seção 5. Quando implementar,
    atualizar este enum E executar testes de sincronização.
    """
    SAIBA_MAIS = "Saiba mais"
    ENVIAR_MENSAGEM = "Enviar mensagem"
    LIGAR = "Ligar"
    COMPRAR_AGORA = "Comprar agora"
    CADASTRE_SE = "Cadastre-se"


class FormatoAnuncioEnum(str, enum.Enum):
    """Formatos de posicionamento suportados.

    FONTE CANÔNICA: app.format_specifications.FORMAT_SPECS.keys()
    SINCRONIZAÇÃO: Garantida por test_formato_enum_sincronizado_com_format_specs()
    """
    FEED = "Feed"
    REELS = "Reels"
    STORIES = "Stories"


class AspectRatioEnum(str, enum.Enum):
    """Aspect ratios permitidos.

    FONTE CANÔNICA: app.format_specifications.FORMAT_SPECS[*].visual
    SINCRONIZAÇÃO: Garantida por test_aspect_ratio_enum_sincronizado()

    Valores coletados de:
    - FORMAT_SPECS['Feed']['visual']['permitidos'] = ["1:1", "4:5"]
    - FORMAT_SPECS['Reels']['visual']['aspect_ratio'] = "9:16"
    - FORMAT_SPECS['Stories']['visual']['aspect_ratio'] = "9:16"
    """
    SQUARE = "1:1"      # Feed (permitido)
    VERTICAL = "4:5"    # Feed (padrão + permitido)
    STORY = "9:16"      # Reels, Stories (único)
```

### 1.3 Por Quê Declarativo em Vez de Dinâmico? (Análise com Ultrathink)

**❌ Abordagens rejeitadas:**

1. **setattr() dinâmico:**
   ```python
   for cta in CTA_INSTAGRAM_CHOICES:
       setattr(CtaInstagramEnum, cta.upper().replace(" ", "_"), cta)
   ```
   - ❌ Não funciona após classe Enum ser definida (imutável por design)
   - ❌ Type checkers (mypy, pyright) não reconhecem
   - ❌ IDEs perdem autocompletion

2. **exec() para gerar código:**
   ```python
   exec(f"class CtaEnum(str, Enum): {members}")
   ```
   - ❌ Anti-pattern (segurança + debugging)
   - ❌ Stack traces confusos
   - ❌ Linters/formatters quebram

3. **Metaclasses personalizadas:**
   - ❌ Complexidade excessiva
   - ❌ Difícil manutenção
   - ❌ Não segue convenções Python

**✅ Solução escolhida: DECLARATIVA + TESTES DE SINCRONIZAÇÃO**

**Vantagens:**
- ✅ Type-safe (mypy, pyright funcionam perfeitamente)
- ✅ Autocompletion em IDEs (VSCode, PyCharm)
- ✅ Debugging claro (stack traces legíveis)
- ✅ Código explícito e pythonic (PEP 435)
- ✅ Testes de CI/CD detectam drift IMEDIATAMENTE
- ✅ Se config mudar, teste falha → desenvolvedor atualiza
- ✅ Sem "mágica" que pode quebrar em updates Python/Pydantic

**Trade-off aceito:**
- ⚠️ Requer atualização manual quando config muda
- ✅ **MAS:** Teste de sincronização falha, forçando correção
- ✅ É explícito e seguro, não "implícito e frágil"

---

## 🔧 FASE 2: Refatorar Modelos Pydantic (OBRIGATÓRIA)

**Arquivo:** `app/schemas/final_delivery.py`

### 2.1 Modificar `StrictAdCopy`

**ANTES:**
```python
class StrictAdCopy(StrictBaseModel):
    headline: str = Field(..., min_length=1, max_length=MAX_HEADLINE_LENGTH)
    corpo: str = Field(..., min_length=1)
    cta_texto: str = Field(..., min_length=1)

    @field_validator("cta_texto")
    @classmethod
    def validate_cta_texto(cls, value: str) -> str:
        if value not in CTA_INSTAGRAM_CHOICES:
            raise ValueError(f"cta_texto must be one of {CTA_INSTAGRAM_CHOICES}")
        return value
```

**DEPOIS:**
```python
class StrictAdCopy(StrictBaseModel):
    headline: str = Field(..., min_length=1, max_length=MAX_HEADLINE_LENGTH)
    corpo: str = Field(..., min_length=1)
    cta_texto: CtaInstagramEnum = Field(
        ...,
        description="Texto do CTA exibido no anúncio (enum garantido pelo Gemini durante geração)"
    )

    # REMOVER completamente: @field_validator("cta_texto")
```

### 2.2 Modificar `StrictAdVisual`

**ANTES:**
```python
class StrictAdVisual(StrictBaseModel):
    descricao_imagem: str = Field(..., min_length=1)
    prompt_estado_atual: str = Field(..., min_length=1)
    prompt_estado_intermediario: str = Field(..., min_length=1)
    prompt_estado_aspiracional: str = Field(..., min_length=1)
    aspect_ratio: str
    reference_assets: dict[str, Any] | None = Field(default=None)

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        if value not in ALLOWED_ASPECT_RATIOS:
            raise ValueError(f"aspect_ratio must be one of {ALLOWED_ASPECT_RATIOS}")
        return value
```

**DEPOIS:**
```python
class StrictAdVisual(StrictBaseModel):
    descricao_imagem: str = Field(..., min_length=1)
    prompt_estado_atual: str = Field(..., min_length=1)
    prompt_estado_intermediario: str = Field(..., min_length=1)
    prompt_estado_aspiracional: str = Field(..., min_length=1)
    aspect_ratio: AspectRatioEnum = Field(
        ...,
        description="Proporção da imagem conforme FORMAT_SPECS (enum garantido)"
    )
    reference_assets: dict[str, Any] | None = Field(default=None)

    # REMOVER completamente: @field_validator("aspect_ratio")
```

### 2.3 Modificar `StrictAdItem`

**ANTES:**
```python
class StrictAdItem(StrictBaseModel):
    landing_page_url: str = Field(..., min_length=1)
    formato: str
    copy: StrictAdCopy
    visual: StrictAdVisual
    cta_instagram: str = Field(..., min_length=1)
    fluxo: str = Field(..., min_length=1)
    referencia_padroes: str = Field(..., min_length=1)
    contexto_landing: str | dict[str, Any] | None = Field(default=None)

    @field_validator("formato")
    @classmethod
    def validate_formato(cls, value: str) -> str:
        if value not in ALLOWED_FORMATS:
            raise ValueError(f"formato must be one of {ALLOWED_FORMATS}")
        return value

    @field_validator("cta_instagram")
    @classmethod
    def validate_cta_instagram(cls, value: str) -> str:
        if value not in CTA_INSTAGRAM_CHOICES:
            raise ValueError(f"cta_instagram must be one of {CTA_INSTAGRAM_CHOICES}")
        return value

    @field_validator("contexto_landing", mode="before")
    @classmethod
    def normalize_contexto_landing(cls, value: Any) -> str | dict[str, Any] | None:
        # ... MANTER este validador (não é enum)

    @model_validator(mode="after")
    def validate_with_format_specs(self) -> "StrictAdItem":
        # ... MANTER este validador (valida Feed: 1:1 ou 4:5)
```

**DEPOIS:**
```python
class StrictAdItem(StrictBaseModel):
    landing_page_url: str = Field(..., min_length=1)
    formato: FormatoAnuncioEnum = Field(
        ...,
        description="Formato de posicionamento do anúncio (enum garantido)"
    )
    copy: StrictAdCopy
    visual: StrictAdVisual
    cta_instagram: CtaInstagramEnum = Field(
        ...,
        description="CTA nativo do Instagram (enum garantido)"
    )
    fluxo: str = Field(..., min_length=1)
    referencia_padroes: str = Field(..., min_length=1)
    contexto_landing: str | dict[str, Any] | None = Field(default=None)

    # REMOVER: @field_validator("formato")
    # REMOVER: @field_validator("cta_instagram")

    # MANTER: @field_validator("contexto_landing") - não é enum
    @field_validator("contexto_landing", mode="before")
    @classmethod
    def normalize_contexto_landing(cls, value: Any) -> str | dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return ""
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return stripped
            if isinstance(parsed, dict):
                return parsed
            return stripped
        raise TypeError("contexto_landing must be a string or dict")

    # MANTER E AJUSTAR: @model_validator - valida formato × aspect_ratio
    @model_validator(mode="after")
    def validate_with_format_specs(self) -> "StrictAdItem":
        """Valida coerência formato × aspect_ratio usando FORMAT_SPECS.

        MANTIDO após migração para enums: garante que Feed aceita 1:1 ou 4:5,
        Reels/Stories aceitam apenas 9:16.

        ⚠️ CRÍTICO: Usar .value para extrair strings dos enums ao comparar
        com dicionários e sets que contêm strings.
        """
        specs = FORMAT_SPECS.get(self.formato.value, {})  # ← .value para extrair string!

        copy_specs = specs.get("copy", {})
        max_chars = copy_specs.get("headline_max_chars")
        if isinstance(max_chars, int) and max_chars > 0:
            if len(self.copy.headline) > max_chars:
                raise ValueError(
                    f"headline length {len(self.copy.headline)} exceeds limit {max_chars} "
                    f"for formato {self.formato.value}"
                )

        visual_specs = specs.get("visual", {})
        allowed_ratios: set[str] = set()
        ratio = visual_specs.get("aspect_ratio")
        if isinstance(ratio, str):
            allowed_ratios.add(ratio)
        # Feed: adiciona "permitidos" (1:1 e 4:5)
        permitted = visual_specs.get("permitidos")
        if isinstance(permitted, (list, tuple, set)):
            allowed_ratios.update({r for r in permitted if isinstance(r, str)})

        if allowed_ratios and self.visual.aspect_ratio.value not in allowed_ratios:  # ← .value!
            raise ValueError(
                f"aspect_ratio {self.visual.aspect_ratio.value} not allowed for "
                f"formato {self.formato.value}: {sorted(allowed_ratios)}"
            )

        return self
```

### 2.4 Limpar código obsoleto (OPCIONAL)

```python
# Linhas ~27-28 (atualmente):
ALLOWED_FORMATS: tuple[str, ...] = tuple(sorted(FORMAT_SPECS.keys()))
ALLOWED_ASPECT_RATIOS: tuple[str, ...] = tuple(sorted(_collect_aspect_ratios(...)))

# Adicionar comentário:
# DEPRECATED após migração para enums: Substituído por FormatoAnuncioEnum e AspectRatioEnum.
# Mantido temporariamente para compatibilidade com código legado.
```

---

## ⏭️ FASE 3 e 4: OPCIONAIS (Pular)

**⚠️ FASES 3 (Atualizar prompts) e 4 (Comentar validador) são OPCIONAIS.**

**Por quê?**
- ✅ O schema já impede valores inválidos
- ✅ Prompts atuais continuam válidos
- ✅ Modificá-los só reduz verbosidade, mas não afeta funcionalidade

**Decisão:** Pular Fases 3 e 4. Focar apenas no essencial (Fases 1, 2, 5, 6).

---

## ✅ FASE 5: Testes de Validação (OBRIGATÓRIA)

### 5.1 Testes de Sincronização (CRÍTICOS - Detectam Drift)

**Arquivo:** `tests/unit/schemas/test_enum_sync.py` (NOVO)

```python
"""Testes de sincronização: detectam drift entre enums e fontes canônicas.

CRÍTICO: Estes testes DEVEM rodar em CI/CD e FALHAR se houver inconsistência.
"""

import pytest
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
```

### 5.2 Testes Unitários de Schemas

**Arquivo:** `tests/unit/schemas/test_final_delivery_enums.py` (NOVO)

```python
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
```

### 5.3 Teste de Conversão para JSON Schema (Validação Técnica)

**Arquivo:** `tests/unit/schemas/test_pydantic_json_schema.py` (NOVO)

```python
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
```

---

## 🧪 FASE 6: Testes de Integração (OBRIGATÓRIA)

### 6.1 Executar suite de testes

```bash
# 1. Testes de sincronização (CRÍTICOS - detectam drift)
uv run pytest tests/unit/schemas/test_enum_sync.py -v

# 2. Testes unitários de schemas
uv run pytest tests/unit/schemas/test_final_delivery_enums.py -v

# 3. Teste de JSON Schema
uv run pytest tests/unit/schemas/test_pydantic_json_schema.py -v -s

# 4. Testes do validador (devem passar sem modificações)
uv run pytest tests/unit/validators/test_final_delivery_validator.py -v

# 5. Suite completa
uv run pytest tests/ -v --tb=short
```

### 6.2 Validação de que testes detectam drift

**Teste manual para confirmar que sincronização funciona:**

```bash
# Temporariamente remover um CTA do enum para forçar drift
# Editar app/schemas/final_delivery.py:
#   class CtaInstagramEnum:
#       # Comentar: CADASTRE_SE = "Cadastre-se"

# Executar teste
uv run pytest tests/unit/schemas/test_enum_sync.py::test_cta_enum_sincronizado_com_config -v

# Deve FALHAR com mensagem clara:
# ❌ DRIFT DETECTADO entre CtaInstagramEnum e CTA_INSTAGRAM_CHOICES!
#   Em config mas não no enum: {'Cadastre-se'}

# Reverter alteração
```

---

## 📊 Resumo: Arquivos Modificados

| Arquivo | Ação | LOC |
|---------|------|-----|
| `app/schemas/final_delivery.py` | Adicionar 3 enums, refatorar 3 modelos, ajustar @model_validator | +60, -30 |
| `tests/unit/schemas/test_enum_sync.py` | Criar novo (testes sincronização) | +80 |
| `tests/unit/schemas/test_final_delivery_enums.py` | Criar novo (testes unitários) | +120 |
| `tests/unit/schemas/test_pydantic_json_schema.py` | Criar novo (teste técnico) | +25 |

**Total:** ~285 linhas adicionadas, ~30 removidas
**Net:** +255 linhas (maioria testes)

---

## ⏱️ Estimativa de Tempo (Fases Essenciais)

| Fase | Duração | Observação |
|------|---------|------------|
| FASE 1: Criar enums declarativos | 20min | Copiar template + ajustar docstrings |
| FASE 2: Refatorar modelos | 40min | Remover validadores + ajustar @model_validator |
| FASE 5: Escrever testes | 60min | 3 arquivos novos (~225 linhas) |
| FASE 6: Executar e validar | 30min | Rodar suite + teste de drift |
| **TOTAL** | **2h 30min** | Sem fases opcionais |

---

## ✅ Critérios de Aceitação

1. ✅ Todos os testes pytest passam (incluindo suite existente)
2. ✅ Testes de sincronização detectam drift quando forçado manualmente
3. ✅ JSON Schema gerado contém campos `"enum"` para CTAs, formato e aspect_ratio
4. ✅ Pipeline completo executa sem erros de validação de enum
5. ✅ Teste com CTA inválido `"Garantir o Meu"` é bloqueado pelo Pydantic
6. ✅ Validador determinístico continua detectando duplicatas e cardinalidade
7. ✅ @model_validator continua validando Feed (1:1 ou 4:5) vs Reels/Stories (9:16)

---

## 🛡️ Por Que Manter Validação Determinística (Defense-in-Depth)

**NÃO remover `FinalDeliveryValidatorAgent` após implementar enums.**

### O que enums resolvem:
✅ Valores de CTAs, formato, aspect_ratio garantidos pelo Gemini

### O que validador continua fazendo:
✅ Exatamente 3 variações (Gemini pode gerar 2 ou 4)
✅ Detecção de duplicatas semânticas (headline + corpo + prompts)
✅ CTA × objetivo_final usando `CTA_BY_OBJECTIVE`

### Comparação:

| Aspecto | Sem Validador | Com Validador |
|---------|---------------|---------------|
| Enums válidos | ✅ Gemini garante | ✅ Gemini garante |
| 3 variações | ⚠️ "Provável" | ✅ Garantido |
| Sem duplicatas | ❌ Não | ✅ Detecta |
| CTA×objetivo | ❌ Não | ✅ Valida |
| Erro antes de gerar imagens | ❌ Não | ✅ Sim (economia) |

---

## 🔄 Rollback Plan

Se houver problemas:

1. **Reverter schemas:** `git checkout HEAD~1 app/schemas/final_delivery.py`
2. **Remover testes:** `git rm tests/unit/schemas/test_enum_*.py tests/unit/schemas/test_pydantic_json_schema.py`
3. **Re-executar suite:** `uv run pytest`
4. **Validadores antigos** voltam automaticamente

---

## 📚 Referências

1. **Documentação Gemini:** [gemini_saida_estruturada.md:36](gemini_saida_estruturada.md#L36) - Validadores Pydantic não suportados
2. **Pesquisa ADK:** [deep_research_saida_estruturada_llmagent_adk.md](deep_research_saida_estruturada_llmagent_adk.md) - Recomenda enum.Enum
3. **Plano Amplo:** [PLAN_CORRECAO_FINAL_DELIVERY.md seção 5](PLAN_CORRECAO_FINAL_DELIVERY.md) - Expansão futura para ~64 CTAs

---

## 🚀 Próxima Fase (Após Esta Implementação)

**Expansão de CTAs (futura):**
- Atualmente: 5 CTAs (`CTA_INSTAGRAM_CHOICES`)
- Identificados: ~64 CTAs oficiais do Instagram ([novos_ctas_mapeados.md](novos_ctas_mapeados.md))
- Plano de expansão: Já documentado em `PLAN_CORRECAO_FINAL_DELIVERY.md` seção 5
- **Quando implementar:** Atualizar `CtaInstagramEnum` + testes de sincronização detectarão automaticamente

---

**Data:** 2025-10-16
**Versão:** Revisada (Pragmática + Ultrathink)
**Status:** ✅ Pronto para execução (Fases 1, 2, 5, 6)
