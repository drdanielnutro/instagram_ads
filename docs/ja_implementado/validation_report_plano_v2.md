# Relatório de Validação: Plano de Validação Determinística v2

**Data de Execução**: 2025-10-04
**Plano Analisado**: `plano_validacao_json_v2.md`
**Repositório**: `/Users/institutorecriare/VSCodeProjects/instagram_ads`
**Versão do Schema**: 2.0.0

---

## Sumário Executivo

### Métricas Gerais
- **Creation Registry**: 26 elementos marcados para criação
- **Claims Extraídos**: 20 dependências/modificações
- **Claims Validados**: 20 (100%)
- **Findings Identificados**: **4 P0 Critical Blockers**
- **Blast Radius**: **MÉDIO** - Afeta validação de schemas e mapeamento de CTAs

### Status Geral
❌ **PLANO REQUER CORREÇÕES** - 4 bloqueadores P0 identificados

Todos os bloqueadores são **dependências ausentes** citadas como "já disponível" ou "existente" no plano, mas **não encontradas no código-base**. Estas são **pré-requisitos críticos** para as entregas da Fase 1 (schemas) e Fase 2 (validador).

---

## Achados Críticos (P0 - Blockers)

### F001: Enum `AspectRatio` Não Existe
**Severidade**: P0-A (Blocker - Alta Prioridade)
**Tipo**: Dependência Ausente

**Claim do Plano**:
- Linha 100: `aspect_ratio: AspectRatio  # importado de format_specifications`
- Linha 149: `app/format_specifications.py` - enums `AspectRatio`, `CTAInstagram` (já disponível, não será modificado)

**Evidência do Código**:
- ❌ **NÃO ENCONTRADO** em `app/format_specifications.py`
- ❌ **NÃO ENCONTRADO** em `app/config.py`
- ✅ **Alternativa Encontrada**: `Literal["9:16", "1:1", "4:5", "16:9"]` em `app/agent.py:72` (classe `AdVisual`)

**Impacto**:
- Schema `StrictAdVisual` (Fase 1.1) não pode ser criado sem este enum
- Importação falhará: `from app.format_specifications import AspectRatio`
- Bloqueio em cadeia: validador (Fase 2.1) depende de schemas (Fase 1.1)

**Ação Recomendada**:
```python
# CRIAR em app/format_specifications.py

from enum import Enum

class AspectRatio(str, Enum):
    """Aspect ratios válidos para anúncios Instagram."""
    REELS = "9:16"
    SQUARE = "1:1"
    PORTRAIT = "4:5"
    LANDSCAPE = "16:9"

__all__ = ["AspectRatio", "CTAInstagram", "FORMAT_SPECS", "get_specs_by_format"]
```

**Critérios de Aceitação**:
- [ ] Enum criado e exportado em `format_specifications.py`
- [ ] `AdVisual` em `agent.py` atualizado para usar enum (opcional, manter Literal funciona)
- [ ] Schema `StrictAdVisual` pode importar sem erros

---

### F002: Enum `CTAInstagram` Não Existe
**Severidade**: P0-A (Blocker - Alta Prioridade)
**Tipo**: Dependência Ausente

**Claim do Plano**:
- Linha 82: `cta_instagram: CTAInstagram  # importado de format_specifications`
- Linha 115: `cta_instagram: CTAInstagram`
- Linha 149: `app/format_specifications.py` - enums `AspectRatio`, `CTAInstagram` (já disponível)

**Evidência do Código**:
- ❌ **NÃO ENCONTRADO** em `app/format_specifications.py`
- ❌ **NÃO ENCONTRADO** em `app/config.py`
- ✅ **Alternativa Encontrada**: `Literal["Saiba mais", "Enviar mensagem", "Ligar", "Comprar agora", "Cadastre-se"]` em `app/agent.py:81` (classe `AdItem`)

**Impacto**:
- Schema `StrictAdItem` (Fase 1.1) não pode importar `CTAInstagram`
- Validação de CTA em `FinalDeliveryValidatorAgent` (Fase 2.1) ficará inconsistente
- Testes unitários (Fase 4.1) esperam `CTAInstagram` como enum

**Ação Recomendada**:
```python
# CRIAR em app/format_specifications.py

class CTAInstagram(str, Enum):
    """CTAs (Call-to-Action) válidos para Instagram Ads."""
    LEARN_MORE = "Saiba mais"
    SEND_MESSAGE = "Enviar mensagem"
    CALL = "Ligar"
    SHOP_NOW = "Comprar agora"
    SIGN_UP = "Cadastre-se"
    BOOK_NOW = "Agendar"  # Mencionado em testes do plano
```

**Critérios de Aceitação**:
- [ ] Enum criado com todos os valores do Literal existente
- [ ] Incluir `BOOK_NOW` conforme linha 1692 do plano (testes)
- [ ] Exportado em `__all__`
- [ ] Schema `StrictAdItem` pode importar sem erros

---

### F003: Constantes `MIN_HEADLINE_LENGTH` e `MAX_HEADLINE_LENGTH` Não Existem
**Severidade**: P0-A (Blocker - Alta Prioridade)
**Tipo**: Dependência Ausente

**Claim do Plano**:
- Linha 83: `from app.config import MIN_HEADLINE_LENGTH, MAX_HEADLINE_LENGTH  # já disponível`
- Linha 150: `app/config.py` - constantes `MIN_HEADLINE_LENGTH`, `MAX_HEADLINE_LENGTH` (já disponível, será estendido)

**Evidência do Código**:
- ❌ **NÃO ENCONTRADO** em `app/config.py` (classe `DevelopmentConfiguration`)
- ✅ **Alternativa Encontrada**: `headline_max_chars` em `FORMAT_SPECS` (40 para Reels/Stories, 60 para Feed)

**Impacto**:
- Schema `StrictAdCopy` (Fase 1.1) linha 88 não pode importar constantes
- Validação de comprimento de headline ficará sem limites superiores

**Ação Recomendada - Opção 1 (Preferida)**:
```python
# MODIFICAR app/config.py - adicionar à classe DevelopmentConfiguration

@dataclass
class DevelopmentConfiguration:
    # ... campos existentes ...

    # Validação de headline
    min_headline_length: int = 1
    max_headline_length: int = 60  # Máximo entre formatos (Feed=60)
```

**Ação Recomendada - Opção 2 (Alternativa)**:
Atualizar plano para usar `FORMAT_SPECS` diretamente:
```python
# Em app/schemas/final_delivery.py
from app.format_specifications import FORMAT_SPECS

class StrictAdCopy(BaseModel):
    headline: str = Field(..., min_length=1, max_length=60)  # Hardcoded max
```

**Critérios de Aceitação**:
- [ ] Constantes adicionadas a `config.py` OU plano atualizado para não requerer constantes
- [ ] Schema pode ser criado sem erros de importação
- [ ] Valores alinhados com `FORMAT_SPECS` existente

---

### F004: Mapa `CTA_BY_OBJECTIVE` Não Existe
**Severidade**: P0-A (Blocker - Alta Prioridade)
**Tipo**: Dependência Ausente

**Claim do Plano**:
- Linha 461: `from app.format_specifications import CTA_BY_OBJECTIVE`
- Linha 519: `expected_ctas = CTA_BY_OBJECTIVE.get(objetivo)`
- Linha 589: `CTA_BY_OBJECTIVE` de `app/config.py` (será criado se não existir)

**Evidência do Código**:
- ❌ **NÃO ENCONTRADO** em `app/config.py`
- ❌ **NÃO ENCONTRADO** em `app/format_specifications.py`
- ✅ **Alternativa Encontrada**: `cta_preferencial` em `FORMAT_SPECS` mapeia objetivos a CTAs **por formato**

**Impacto**:
- `FinalDeliveryValidatorAgent` (Fase 2.1) não pode validar CTA vs objetivo
- Lógica de validação nas linhas 516-522 do plano falhará
- Testes unitários (Fase 4.1) esperam validação de CTA incompatível

**Ação Recomendada**:
```python
# CRIAR em app/format_specifications.py (após criar CTAInstagram enum)

CTA_BY_OBJECTIVE: Dict[str, List[str]] = {
    "agendamentos": [
        CTAInstagram.SEND_MESSAGE.value,
        CTAInstagram.CALL.value,
        CTAInstagram.BOOK_NOW.value,
    ],
    "leads": [
        CTAInstagram.SIGN_UP.value,
        CTAInstagram.LEARN_MORE.value,
        CTAInstagram.SEND_MESSAGE.value,
    ],
    "vendas": [
        CTAInstagram.SHOP_NOW.value,
        CTAInstagram.LEARN_MORE.value,
    ],
}

__all__ = [..., "CTA_BY_OBJECTIVE"]
```

**Critérios de Aceitação**:
- [ ] Mapa criado consolidando `cta_preferencial` de `FORMAT_SPECS`
- [ ] Usar valores do enum `CTAInstagram` (após F002 resolvido)
- [ ] Exportado e acessível
- [ ] Validador pode importar e usar sem erros

---

## Mapeamento Plano ↔ Código (Elementos Validados)

| Elemento do Plano | Código Correspondente | Status | Notas |
|-------------------|----------------------|--------|-------|
| `app/agent.py:1029` | `final_assembler = LlmAgent(...)` | ✅ EXISTE | LlmAgent confirmado, será modificado (prompt) |
| `app/agent.py:310` | `class ImageAssetsAgent(BaseAgent)` | ✅ EXISTE | Classe confirmada, será modificada (populate review) |
| `app/agent.py:1261-1274` | `execution_pipeline = SequentialAgent(...)` | ✅ EXISTE | Pipeline confirmado, será reorquestrado |
| `app/agent.py:67` | `class AdVisual(BaseModel)` | ✅ EXISTE | Schema existente, pode ser extraído |
| `app/agent.py:76` | `class AdItem(BaseModel)` | ✅ EXISTE | Schema existente, pode ser extraído |
| `app/agent.py:54` | `class Feedback(BaseModel)` | ✅ EXISTE | Schema reutilizável para semantic reviewer |
| `app/format_specifications.py` | `FORMAT_SPECS` dict | ✅ EXISTE | Arquivo existe, faltam enums (F001, F002, F004) |
| `app/callbacks/collect_code_snippets.py` | ❌ NÃO EXISTE | ⚠️ ATENÇÃO | Callback definido em `agent.py:122`, não em arquivo separado |
| `app/agents/storybrand_gate.py` | `class StoryBrandQualityGate` | ✅ EXISTE | Agente confirmado, preenche `storybrand_fallback_meta` |
| `app/callbacks/persist_outputs.py` | `persist_final_delivery()` | ✅ EXISTE | Callback confirmado, pode ser estendido |

---

## Planned Creations (Não são Bloqueadores)

Os seguintes elementos são **entregas do plano** (marcados como "NOVO - SERÁ CRIADO"). Estes **NÃO** foram validados contra o código (correto, pois ainda não existem):

### Novos Módulos (Fase 1-2)
- ✅ `app/schemas/final_delivery.py` - Schema Pydantic estrito
- ✅ `app/utils/audit.py` - Helper de auditoria
- ✅ `app/validators/final_delivery_validator.py` - Validador determinístico
- ✅ `app/agents/gating.py` - Utilitários RunIfPassed/Reset

### Novos Agentes (Fase 3)
- ✅ `app/agents/assembly_guards.py` - Guards e Normalizer
- ✅ `app/agents/persistence.py` - Agente de persistência dedicado
- ✅ `FinalDeliveryValidatorAgent` - Validador principal
- ✅ `RunIfPassed` / `ResetDeterministicValidationState` - Gating
- ✅ `FinalAssemblyGuardPre` / `FinalAssemblyNormalizer` - Guards
- ✅ `semantic_visual_reviewer` / `semantic_fix_agent` - Reviewers LLM
- ✅ `PersistFinalDeliveryAgent` - Persistência

### Função Builder (Fase 3.1)
- ✅ `build_execution_pipeline()` - Constrói pipeline baseado em flag

### Testes (Fase 4)
- ✅ `tests/unit/validators/test_final_delivery_validator.py`
- ✅ `tests/integration/test_deterministic_pipeline.py`

### Documentação (Fase 4.4)
- ✅ `docs/rollout_deterministic_validation.md`

---

## Atenção: Inconsistência de Localização

### Callback `collect_code_snippets`
**Claim do Plano** (Fase 1.4):
- Estender `app/callbacks/collect_code_snippets.py` existente

**Código Real**:
- ❌ Arquivo `app/callbacks/collect_code_snippets.py` **NÃO EXISTE**
- ✅ Função `collect_code_snippets_callback()` definida em **`app/agent.py:122`**

**Impacto**:
- **Baixo** - Modificação ainda é viável, mas no arquivo correto
- Plano cita caminho incorreto para modificação

**Ação Recomendada**:
1. **Opção A (Preferida)**: Modificar `app/agent.py:122` diretamente conforme instruções da Fase 1.4
2. **Opção B**: Criar `app/callbacks/collect_code_snippets.py`, mover função para lá, atualizar imports

---

## Verificação de Consistência (Chain-of-Verification)

### Anti-Contradiction Check
✅ **PASSOU** - Nenhum elemento aparece simultaneamente em:
- Creation Registry (26 elementos)
- P0 Findings (4 bloqueadores)

### Análise de Precedência
**Verificado**: Nenhum elemento do Creation Registry foi erroneamente marcado como P0.

Exemplo de verificação correta:
- `FinalDeliveryValidatorAgent` → ✅ Em Creation Registry → ❌ NÃO validado contra código (correto)
- `AspectRatio` enum → ❌ NÃO em Creation Registry → ✅ Validado e reportado como P0 (correto)

### Métricas de Qualidade
- **Symbol Coverage**: 100% (20/20 claims processados)
- **Phantom Links Rate**: 20% (4/20 dependências ausentes)
- **Matching Precision**: 80% (16/20 dependências confirmadas)
- **Blast Radius**: MÉDIO (afeta 2 fases: schemas e validador)

---

## Incertezas

**Nenhuma incerteza identificada** nesta validação.

Todos os bloqueadores são casos claros de dependências ausentes com alternativas documentadas no código (Literals, FORMAT_SPECS).

---

## Recomendações e Próximos Passos

### Ações Imediatas (Antes de Implementar)
1. **Criar Enums Faltantes** (Resolver F001, F002):
   ```bash
   # Adicionar a app/format_specifications.py
   - class AspectRatio(str, Enum)
   - class CTAInstagram(str, Enum)
   ```

2. **Criar Mapa CTA_BY_OBJECTIVE** (Resolver F004):
   ```python
   # Em format_specifications.py ou config.py
   CTA_BY_OBJECTIVE: Dict[str, List[str]] = {...}
   ```

3. **Resolver Constantes de Headline** (Resolver F003):
   - **Opção A**: Adicionar a `config.py`
   - **Opção B**: Atualizar plano para usar `FORMAT_SPECS` diretamente

4. **Corrigir Localização de Callback** (Atenção):
   - Atualizar Fase 1.4 do plano para modificar `app/agent.py:122` em vez de arquivo inexistente

### Ordem de Implementação Recomendada
1. ✅ Resolver **todos os 4 bloqueadores P0** primeiro
2. ✅ Validar schemas (Fase 1.1) após resolução
3. ✅ Implementar validador (Fase 2.1) com enums corretos
4. ✅ Prosseguir com reorquestração (Fase 3)
5. ✅ Testes (Fase 4) com dependências resolvidas

### Alternativa: Atualizar Plano
Se preferir não criar enums, **atualizar plano** para:
- Usar `Literal` em vez de `AspectRatio` / `CTAInstagram` enums
- Usar `FORMAT_SPECS["formato"]["strategy"]["cta_preferencial"]` em vez de `CTA_BY_OBJECTIVE`
- Hardcode limites de headline ou use valores de `FORMAT_SPECS`

---

## Conclusão

O plano **plano_validacao_json_v2.md** está **bem estruturado** com linguagem declarativa clara (Criar vs Usar), mas contém **4 dependências críticas ausentes** (P0 blockers) que **impedem a implementação** das Fases 1 e 2.

**Todos os bloqueadores têm soluções diretas**:
- Criar enums `AspectRatio` e `CTAInstagram` em `format_specifications.py`
- Criar mapa `CTA_BY_OBJECTIVE`
- Adicionar constantes de headline ou atualizar plano

**Status Final**: ❌ **PLANO REQUER CORREÇÕES** antes de implementação.

**Próxima Ação Recomendada**: Resolver F001-F004, depois re-validar plano atualizado antes de iniciar implementação.

---

**Validado por**: Plan-Code Drift Validator Agent
**Data**: 2025-10-04
**Versão do Relatório**: 2.0.0
