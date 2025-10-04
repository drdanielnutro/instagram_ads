# Plano de Validação Determinística do JSON Final de Ads (v2)

## Resumo Executivo

**Objetivo**: Implementar camada determinística de validação do JSON final de anúncios, eliminando dependência exclusiva de LLMs para garantias estruturais e reduzindo falsos positivos em campos obrigatórios.

**Escopo**: Este plano cobre a criação de:
- 4 novos módulos (schemas, validators, gating utils, audit helpers)
- 3 novos agentes (FinalDeliveryValidatorAgent, guards, normalizer)
- Modificações em 5 arquivos existentes (agent.py, config.py, callbacks, session-state)
- Reorquestração completa do execution_pipeline com feature flag

**Entregas principais**:
1. Schema Pydantic estrito com relaxamento condicional para fallback StoryBrand
2. Validador determinístico que substitui validação LLM estrutural
3. Pipeline reorganizado: guard → assembler → normalizer → validador → revisor semântico → imagens → persistência
4. Feature flag `ENABLE_DETERMINISTIC_FINAL_VALIDATION` para rollout gradual
5. Suite de testes cobrindo cenários de sucesso, falha e fallback

**Dependências do código atual**:
- `final_assembler` de `app/agent.py:1029` (LlmAgent existente - será modificado)
- `ImageAssetsAgent` de `app/agent.py:310` (BaseAgent existente - será ajustado)
- `execution_pipeline` de `app/agent.py:1261-1274` (SequentialAgent existente - será reorquestrado)
- Modelos `AdVisual`, `AdItem` de `app/agent.py:67,76` (serão extraídos para módulo compartilhado)
- `app/format_specifications.py` (já disponível - fonte de regras de formato)
- `app/plan_models/fixed_plans.py` (já disponível - apenas referência, não validação)

---

## 1. Contexto e Problema Atual

### Situação Existente no Código

- **`final_assembler`** (`app/agent.py:1029`): LlmAgent que monta três variações do anúncio sem reutilização determinística do fragmento aprovado de `VISUAL_DRAFT`
- **Validação LLM**: `final_validator` (`app/agent.py:1059`) pode aprovar falsos positivos (ex.: `null` em `visual.prompt_estado_intermediario`)
- **Gate determinístico único**: `ImageAssetsAgent` (`app/agent.py:310`) detecta campos ausentes tardiamente, resultando em variações ignoradas em vez de corrigidas
- **Ausência de validação em código**: Nenhum schema ou regra garante contratos mínimos antes das etapas finais
- **Persistência prematura**: `persist_final_delivery` é callback do `final_assembler`, gravando artefatos locais/GCS mesmo quando validações subsequentes falham

### Impactos

- Variações com campos vazios chegam até geração de imagens
- Feedback tardio ao usuário (após tentativa de gerar imagens)
- Artefatos inválidos persistidos no sistema
- Dependência excessiva de LLMs para validações estruturais

---

## 2. Objetivos do Plano

1. Criar camada determinística que valide JSON final imediatamente após `final_assembler`, antes de qualquer verificação LLM ou geração de imagens
2. Garantir aderência a especificações de formato (de `app/format_specifications.py`) e contratos Pydantic (`AdVisual`, `AdItem`)
3. Reduzir liberdade criativa do `final_assembler` em campos críticos via guards e normalizers
4. Introduzir revisão semântica pós-validação determinística, focada apenas em coerência narrativa/visual
5. Persistir JSON final somente após aprovação em todos os estágios de validação

---

## Faseamento e Ordem de Implementação

### Fase 1: Fundação - Schemas e Utilitários Base

**Objetivo**: Criar estruturas de dados e helpers independentes antes de tocar no pipeline principal.

**Razão da ordem**: Schemas, enums e utilitários devem existir antes de serem importados por validadores e agentes. Esta fase não tem dependências do pipeline modificado.

---

#### Entrega 1.1: Schema de Validação Compartilhado

**Tarefa**: Criar `app/schemas/final_delivery.py`

**Descrição**: Implementar schemas Pydantic estritos para validação do JSON final de ads, com suporte a relaxamento condicional baseado em fallback StoryBrand.

**Estrutura do código**:

```python
# app/schemas/final_delivery.py (NOVO - SERÁ CRIADO)

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from app.format_specifications import AspectRatio, CTAInstagram  # já disponível
from app.config import MIN_HEADLINE_LENGTH, MAX_HEADLINE_LENGTH  # já disponível


class StrictAdCopy(BaseModel):
    """Schema estrito para copy do anúncio."""
    headline: str = Field(..., min_length=1, max_length=60)
    corpo: str = Field(..., min_length=1)

    @field_validator('headline', 'corpo')
    def validate_non_empty(cls, v):
        if isinstance(v, str) and v.strip() == '':
            raise ValueError('Campo não pode conter apenas espaços')
        return v


class StrictAdVisual(BaseModel):
    """Schema estrito para visual do anúncio."""
    aspect_ratio: AspectRatio  # importado de format_specifications
    prompt_estado_intermediario: str = Field(..., min_length=1)
    prompt_estado_final: str = Field(..., min_length=1)

    @field_validator('prompt_estado_intermediario', 'prompt_estado_final')
    def validate_prompts(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Prompts visuais não podem estar vazios')
        return v


class StrictAdItem(BaseModel):
    """Schema estrito para item completo do anúncio."""
    copy: StrictAdCopy
    visual: StrictAdVisual
    cta_instagram: CTAInstagram  # importado de format_specifications
    fluxo: str = Field(..., min_length=1)
    contexto_landing: dict[str, Any] | str  # aceita dict ou string
    referencia_padroes: str | None = None

    @classmethod
    def from_state(cls, state: dict[str, Any], **data):
        """Factory que relaxa validações em cenários de fallback StoryBrand."""
        fallback_conditions = [
            state.get("force_storybrand_fallback"),
            state.get("storybrand_gate_metrics", {}).get("decision_path") == "fallback",
            state.get("storybrand_fallback_meta", {}).get("fallback_engaged"),
            state.get("landing_page_analysis_failed")
        ]

        is_fallback = any(fallback_conditions)

        if is_fallback:
            # Relaxar min_length para campos textuais
            # Registrar motivo no estado para auditoria
            state.setdefault("deterministic_final_validation", {})
            state["deterministic_final_validation"]["schema_relaxation_reason"] = (
                "StoryBrand fallback ativo ou landing page analysis falhou"
            )
            # Retornar versão relaxada (implementação específica omitida por brevidade)
            # Em produção, criar schema alternativo ou desabilitar validators

        return cls(**data)
```

**Dependências externas**:
- `pydantic` >= 2.0 (já em requirements.txt)
- `typing.Literal, Any` (Python stdlib)
- **Código existente que será importado**:
  - `app/format_specifications.py` - enums `AspectRatio`, `CTAInstagram` (já disponível, não será modificado)
  - `app/config.py` - constantes `MIN_HEADLINE_LENGTH`, `MAX_HEADLINE_LENGTH` (já disponível, será estendido com novos limites)

**Integrações futuras** (quem usará este código):
1. `app/validators/final_delivery_validator.py` - validador determinístico (Fase 2, Entrega 2.1)
2. `FinalAssemblyNormalizer` - agente que normaliza output do LLM (Fase 3, Entrega 3.2.3)

**Critérios de Aceitação**:

**Functional Requirements**:
- [ ] Arquivo criado em `app/schemas/final_delivery.py`
- [ ] Schemas validam campos obrigatórios corretamente
- [ ] Validator de strings vazias rejeita apenas espaços
- [ ] Factory `from_state()` relaxa validações quando `force_storybrand_fallback=True`
- [ ] Registra `schema_relaxation_reason` em `deterministic_final_validation`
- [ ] Imports de `format_specifications` e `config` funcionam

**Automated Validation** (plan-code-validator metrics):
- [ ] Plan validates with 0 P0 blockers
- [ ] Todas dependências citam código existente com paths/lines
- [ ] Entrega usa verbo "Criar" (declarativo)

**Integration Testing**:
- [ ] Schema rejeita `prompt_estado_intermediario` vazio em cenário normal
- [ ] Schema aceita campos vazios quando `fallback_engaged=True`
- [ ] `contexto_landing` aceita tanto dict quanto string

---

#### Entrega 1.2: Helper de Auditoria

**Tarefa**: Criar `app/utils/audit.py`

**Descrição**: Implementar utilitário de auditoria para registrar eventos de validação e metadados de entrega.

**Estrutura do código**:

```python
# app/utils/audit.py (NOVO - SERÁ CRIADO)

from datetime import datetime, timezone
from typing import Any
import logging

logger = logging.getLogger(__name__)


def append_delivery_audit_event(
    state: dict[str, Any],
    stage: str,
    status: str,
    detail: str = "",
    deterministic_grade: str | None = None,
    storybrand_fallback_engaged: bool = False
) -> None:
    """
    Registra evento de auditoria no histórico de entrega.

    Será usado por:
    - FinalDeliveryValidatorAgent (Fase 2)
    - Guards e normalizers (Fase 3)
    - Semantic reviewer (Fase 3)

    Args:
        state: Estado do agente ADK
        stage: Identificador da etapa (ex: "deterministic_validation")
        status: "success" | "fail" | "skipped"
        detail: Mensagem descritiva opcional
        deterministic_grade: Grade da validação determinística
        storybrand_fallback_engaged: Se fallback StoryBrand está ativo
    """
    audit_trail = state.setdefault("delivery_audit_trail", [])

    event = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "status": status,
        "detail": detail,
    }

    if deterministic_grade:
        event["deterministic_grade"] = deterministic_grade

    if storybrand_fallback_engaged:
        event["storybrand_fallback_engaged"] = True

    audit_trail.append(event)
    logger.info(f"Audit event: {stage} -> {status}", extra={"event": event})
```

**Dependências externas**:
- `datetime`, `timezone` (Python stdlib)
- `typing.Any` (Python stdlib)
- `logging` (Python stdlib)

**Nota importante**: Mapeamentos de CTA permanecem em `app/format_specifications.py` e `app/config.py` (já existentes). Este módulo apenas registra eventos, não define enums.

**Integrações futuras**:
1. Será importado por `FinalDeliveryValidatorAgent` (Fase 2.1)
2. Será importado por guards/normalizers (Fase 3.2)
3. Será chamado em callbacks `make_failure_handler` (Fase 3.3)

**Critérios de Aceitação**:
- [ ] Arquivo criado em `app/utils/audit.py`
- [ ] Função adiciona eventos a `state["delivery_audit_trail"]`
- [ ] Timestamps em UTC formato ISO
- [ ] Logger emite eventos estruturados
- [ ] Não duplica responsabilidades de `format_specifications`

---

#### Entrega 1.3: Metadados StoryBrand e Landing Page

**Tarefa**: Estender `app/agents/storybrand_gate.py` existente

**Descrição**: Documentar e complementar comportamento atual do `StoryBrandQualityGate` para garantir que metadados necessários sejam expostos ao schema relaxado.

**Código atual** (o que já existe):
- Arquivo `app/agents/storybrand_gate.py` (já disponível)
- `StoryBrandQualityGate` já preenche `state['storybrand_fallback_meta']` com:
  ```python
  {
      "decision_path": "fallback" | "proceed",
      "trigger_reason": str,
      "fallback_engaged": bool,
      "timestamp_utc": str
  }
  ```

**Modificações planejadas**:
1. Confirmar via leitura do código que `storybrand_fallback_meta` é populado corretamente
2. Se necessário, adicionar logs estruturados para observabilidade
3. Garantir que `landing_page_analysis_failed` é inicializado como `False` e atualizado para `True` em cenários de erro

**Dependências** (código existente):
- `app/agents/storybrand_gate.py` - StoryBrandQualityGate (já implementado)
- `app/agents/landing_page.py` - LandingPageStage (já implementado, inicializa `landing_page_analysis_failed`)

**Integrações**:
- Schema `StrictAdItem.from_state()` (criado na Fase 1.1) lerá esses metadados
- Validador determinístico (Fase 2.1) usará flags para decidir relaxamento

**Critérios de Aceitação**:
- [ ] `storybrand_fallback_meta` contém campos documentados
- [ ] `landing_page_analysis_failed` é boolean em `state`
- [ ] Logs estruturados facilitam debugging
- [ ] Nenhuma quebra em consumidores existentes

---

#### Entrega 1.4: Enriquecimento de Snippets Aprovados

**Tarefa**: Estender `app/callbacks/collect_code_snippets.py` existente

**Descrição**: Adicionar metadados (`snippet_type`, `approved_at`, `snippet_id`) aos snippets coletados para rastreabilidade e validação de unicidade.

**Código atual** (o que já existe):
- Callback `collect_code_snippets_callback` em `app/callbacks/collect_code_snippets.py` (já disponível)
- Registra `task_id` e `category` em `state['approved_code_snippets']`

**Modificações planejadas**:

```python
# app/callbacks/collect_code_snippets.py (EXISTENTE - SERÁ MODIFICADO)

import hashlib
from datetime import datetime, timezone

def collect_code_snippets_callback(state: dict, response: dict, config: dict) -> dict:
    """
    MODIFICAÇÃO: Adicionar snippet_type, status, approved_at, snippet_id.

    Novos campos:
    - snippet_type: "VISUAL_DRAFT" | "COPY_DRAFT" | etc.
    - status: "approved" (fixo por enquanto)
    - approved_at: timestamp UTC ISO
    - snippet_id: hash SHA-256 de task_id::snippet_type::payload
    """
    # ... código existente de extração de task_id/category ...

    # ADICIONAR:
    snippet_type = infer_snippet_type(category)  # mapear category → snippet_type
    payload_str = f"{task_id}::{snippet_type}::{code_content}"
    snippet_id = hashlib.sha256(payload_str.encode()).hexdigest()

    snippet_entry = {
        "task_id": task_id,
        "category": category,
        "snippet_type": snippet_type,  # NOVO
        "status": "approved",  # NOVO
        "approved_at": datetime.now(timezone.utc).isoformat(),  # NOVO
        "snippet_id": snippet_id,  # NOVO
        "code": code_content
    }

    state.setdefault("approved_code_snippets", []).append(snippet_entry)

    # ADICIONAR: estrutura auxiliar para guards
    if snippet_type == "VISUAL_DRAFT":
        variation_id = extract_variation_id(code_content)  # extrair ID da variação
        state.setdefault("approved_visual_drafts", {})[variation_id] = snippet_entry

    return state
```

**Dependências**:
- `hashlib`, `datetime` (Python stdlib)
- Callback existente em `app/callbacks/collect_code_snippets.py` (será modificado)

**Integrações futuras**:
1. `FinalAssemblyGuardPre` (Fase 3.2.1) lerá `approved_visual_drafts`
2. `FinalAssemblyNormalizer` (Fase 3.2.3) validará presença de snippets

**Critérios de Aceitação**:
- [ ] Snippets incluem `snippet_type`, `status`, `approved_at`, `snippet_id`
- [ ] `approved_visual_drafts` mapeado por `variation_id`
- [ ] Hash SHA-256 garante unicidade
- [ ] Consumidores existentes não quebram (campos novos são aditivos)

---

#### Entrega 1.5: Feature Flag de Ativação

**Tarefa**: Estender `app/config.py` existente

**Descrição**: Adicionar flag `enable_deterministic_final_validation` para controle de rollout gradual do novo pipeline.

**Código atual** (o que já existe):
- `app/config.py` com classe `Config` (já disponível)
- Sistema de loading de env vars já implementado

**Modificações planejadas**:

```python
# app/config.py (EXISTENTE - SERÁ MODIFICADO)

class Config:
    # ... campos existentes ...

    # ADICIONAR:
    enable_deterministic_final_validation: bool = Field(
        default=False,
        description="Ativa pipeline determinístico de validação (requer restart)"
    )

    @classmethod
    def from_env(cls):
        # ... código existente ...

        # ADICIONAR:
        enable_det_val = os.getenv("ENABLE_DETERMINISTIC_FINAL_VALIDATION", "false").lower() == "true"

        # Log estruturado da flag
        logger.info(
            "Feature flag loaded",
            extra={"flag": "enable_deterministic_final_validation", "value": enable_det_val}
        )

        return cls(enable_deterministic_final_validation=enable_det_val, ...)
```

**Comportamento**:
- Default: `False` (pipeline legado ativo)
- Quando `True`: Novo pipeline determinístico substitui `final_validation_loop`
- Avaliado na inicialização do processo (exige restart para alternar)
- Valor logged em startup para auditoria

**Dependências**:
- `app/config.py` existente (será modificado)
- `os.getenv` (Python stdlib)

**Integrações**:
- Será lido por `build_execution_pipeline()` (Fase 3.1)
- Condicional de branching do pipeline (Fase 3.1)

**Critérios de Aceitação**:
- [ ] Flag adicionada a `Config` com default `False`
- [ ] Env var `ENABLE_DETERMINISTIC_FINAL_VALIDATION` lida corretamente
- [ ] Startup logs registram valor da flag
- [ ] Restart necessário para alternar (não muta em runtime)
- [ ] README atualizado com documentação da flag

**Automated Validation**:
- [ ] Modificação usa verbo "Estender" (arquivo existente)
- [ ] Cita `app/config.py` como já disponível

---

### Fase 2: Validador Determinístico

**Objetivo**: Construir o agente que consome schemas da Fase 1 e valida JSON final.

**Razão da ordem**: Validador depende de schemas (Fase 1.1), enums de `format_specifications` e helpers de auditoria (Fase 1.2). Deve existir antes da integração ao pipeline (Fase 3).

---

#### Entrega 2.1: FinalDeliveryValidatorAgent

**Tarefa**: Criar `app/validators/final_delivery_validator.py`

**Descrição**: Implementar agente ADK que valida JSON final usando schemas estritos, detecta duplicidades e registra resultados no estado.

**Estrutura do código**:

```python
# app/validators/final_delivery_validator.py (NOVO - SERÁ CRIADO)

from typing import Any
import json
from google.genai.adk import BaseAgent
from app.schemas.final_delivery import StrictAdItem  # criado na Fase 1.1
from app.utils.audit import append_delivery_audit_event  # criado na Fase 1.2
from app.format_specifications import CTA_BY_OBJECTIVE  # já disponível (será criado em config.py se não existir)
import logging

logger = logging.getLogger(__name__)


class FinalDeliveryValidatorAgent(BaseAgent):
    """
    Valida JSON final de ads usando schemas Pydantic estritos.

    Responsabilidades:
    - Carregar e parsear `final_code_delivery` (string/list/object)
    - Validar com StrictAdItem (Fase 1.1)
    - Checar regras de formato (de app/format_specifications.py)
    - Validar CTA coerente com objetivo final
    - Detectar duplicidades entre variações
    - Registrar resultados em `deterministic_final_validation`
    """

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info("FinalDeliveryValidatorAgent: Iniciando validação determinística")

        # Carregar payload
        payload_raw = state.get("final_code_delivery")
        if not payload_raw:
            self._fail(state, "final_code_delivery ausente no estado")
            return state

        # Parsing único
        try:
            if isinstance(payload_raw, str):
                payload = json.loads(payload_raw)
            elif isinstance(payload_raw, list):
                payload = {"variations": payload_raw}
            else:
                payload = payload_raw
        except json.JSONDecodeError as e:
            self._fail(state, f"JSON inválido: {e}")
            return state

        # Validar cada variação com schema
        variations = payload.get("variations", [])
        if len(variations) != 3:
            self._fail(state, f"Esperadas 3 variações, recebidas {len(variations)}")
            return state

        issues = []
        normalized_variations = []

        for idx, var in enumerate(variations):
            try:
                # Usar factory que respeita fallback StoryBrand
                validated = StrictAdItem.from_state(state, **var)
                normalized_variations.append(validated.model_dump())

                # Validar CTA vs objetivo
                objetivo = state.get("objetivo_final", "").lower()
                cta = validated.cta_instagram
                expected_ctas = CTA_BY_OBJECTIVE.get(objetivo)

                if expected_ctas and cta not in expected_ctas:
                    issues.append(f"Variação {idx}: CTA '{cta}' incompatível com objetivo '{objetivo}'")

            except Exception as e:
                issues.append(f"Variação {idx}: {str(e)}")

        # Detectar duplicidades
        seen_tuples = set()
        for idx, var in enumerate(normalized_variations):
            key = (
                var["copy"]["headline"],
                var["copy"]["corpo"],
                var["visual"]["prompt_estado_intermediario"],
                var["visual"]["prompt_estado_final"]
            )
            if key in seen_tuples:
                issues.append(f"Variação {idx}: duplicada")
            seen_tuples.add(key)

        # Persistir resultado
        if issues:
            self._fail(state, f"{len(issues)} problemas encontrados: {issues}")
        else:
            state["deterministic_final_validation"] = {
                "grade": "pass",
                "issues": [],
                "normalized_payload": {"variations": normalized_variations},
                "source": "validator"
            }
            # Atualizar final_code_delivery com JSON normalizado
            state["final_code_delivery"] = json.dumps(
                {"variations": normalized_variations},
                ensure_ascii=False
            )
            append_delivery_audit_event(
                state,
                stage="deterministic_validation",
                status="success",
                deterministic_grade="pass"
            )
            logger.info("Validação determinística: APROVADA")

        return state

    def _fail(self, state: dict[str, Any], reason: str):
        """Registra falha sem lançar exceção."""
        state["deterministic_final_validation"] = {
            "grade": "fail",
            "issues": [reason],
            "source": "validator"
        }
        append_delivery_audit_event(
            state,
            stage="deterministic_validation",
            status="fail",
            detail=reason,
            deterministic_grade="fail"
        )
        logger.error(f"Validação determinística FALHOU: {reason}")
```

**Dependências**:
- **Código criado em fases anteriores**:
  - `StrictAdItem` de `app/schemas/final_delivery.py` (Fase 1.1)
  - `append_delivery_audit_event` de `app/utils/audit.py` (Fase 1.2)
- **Código existente**:
  - `BaseAgent` de `google.genai.adk` (já disponível em requirements.txt)
  - `app/format_specifications.py` (já disponível)
  - `CTA_BY_OBJECTIVE` de `app/config.py` (será criado se não existir - mapa de objetivos → CTAs)

**Tratamento de Falhas**:
- Não lança exceções customizadas
- Registra `grade="fail"` em `deterministic_final_validation`
- Callback `make_failure_handler` (Fase 3.3) tratará falhas downstream

**Integrações futuras**:
1. Será encapsulado por `deterministic_validation_stage` (Fase 3.1)
2. `RunIfPassed` (Fase 2.2) bloqueará agentes subsequentes em caso de falha

**Critérios de Aceitação**:

**Functional Requirements**:
- [ ] Arquivo criado em `app/validators/final_delivery_validator.py`
- [ ] Valida 3 variações obrigatórias
- [ ] Rejeita campos vazios (exceto em fallback StoryBrand)
- [ ] Detecta duplicidades por tupla normalizada
- [ ] Valida CTA vs objetivo usando `CTA_BY_OBJECTIVE`
- [ ] Atualiza `final_code_delivery` com JSON normalizado
- [ ] Registra eventos de auditoria

**Automated Validation**:
- [ ] Entrega usa verbo "Criar"
- [ ] Todas dependências citam módulos criados ou existentes
- [ ] Sem P0 blockers ao validar plano

**Integration Testing**:
- [ ] JSON válido com 3 variações → `grade="pass"`
- [ ] Campo `prompt_estado_intermediario` vazio → `grade="fail"`
- [ ] CTA incompatível com objetivo → issue registrado
- [ ] Variações duplicadas → detectadas
- [ ] Fallback StoryBrand ativo → campos vazios aceitos

---

#### Entrega 2.2: Utilitários de Gating/Reset

**Tarefa**: Criar `app/agents/gating.py`

**Descrição**: Implementar utilitários `RunIfPassed` e `ResetDeterministicValidationState` para controle de fluxo condicional no pipeline.

**Estrutura do código**:

```python
# app/agents/gating.py (NOVO - SERÁ CRIADO)

from typing import Any
from google.genai.adk import BaseAgent
from app.utils.audit import append_delivery_audit_event  # criado na Fase 1.2
import logging

logger = logging.getLogger(__name__)


class RunIfPassed(BaseAgent):
    """
    Executa agente encapsulado apenas se review_key.grade == expected_grade.

    Será usado por:
    - Pipeline determinístico (Fase 3.1) para gating de semantic review, images, persist
    """

    def __init__(self, name: str, review_key: str, agent: BaseAgent, expected_grade: str = "pass"):
        super().__init__(name=name)
        self.review_key = review_key
        self.agent = agent
        self.expected_grade = expected_grade

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        review = state.get(self.review_key, {})
        grade = review.get("grade")

        if grade is None:
            # Ausência de chave = tratar como fail
            logger.warning(f"RunIfPassed: {self.review_key} ausente, tratando como fail")
            append_delivery_audit_event(
                state,
                stage=f"{self.name}_gate",
                status="blocked",
                detail=f"Review key '{self.review_key}' ausente"
            )
            return state

        if grade == self.expected_grade:
            logger.info(f"RunIfPassed: {self.review_key} passou, executando {self.agent.name}")
            return self.agent.run(state)
        else:
            logger.info(f"RunIfPassed: {self.review_key} grade={grade}, pulando {self.agent.name}")
            append_delivery_audit_event(
                state,
                stage=f"{self.name}_gate",
                status="skipped",
                detail=f"Grade {grade} != {self.expected_grade}"
            )
            return state


class ResetDeterministicValidationState(BaseAgent):
    """
    Limpa chaves específicas do pipeline determinístico.

    Será usado por:
    - Pipeline legado (flag=False) para evitar resíduos (Fase 3.1)
    """

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        keys_to_clear = [
            "approved_visual_drafts",
            "deterministic_final_validation",
            "deterministic_final_blocked",
            "final_code_delivery_parsed"
        ]

        for key in keys_to_clear:
            if key in state:
                del state[key]
                logger.debug(f"ResetDeterministicValidationState: removeu '{key}'")

        append_delivery_audit_event(
            state,
            stage="reset_deterministic_state",
            status="success",
            detail="Estado determinístico limpo para pipeline legado"
        )

        return state
```

**Dependências**:
- `BaseAgent` de `google.genai.adk` (já disponível)
- `append_delivery_audit_event` de `app/utils/audit.py` (criado na Fase 1.2)

**Comportamento**:
- `RunIfPassed`: Executa agente encapsulado apenas quando grade == expected
- Ausência de chave: Trata como `fail` explícito e registra evento
- `ResetDeterministicValidationState`: Remove chaves específicas para evitar resíduos

**Integrações futuras**:
1. Pipeline determinístico (Fase 3.1) usará `RunIfPassed` para gating
2. Pipeline legado (Fase 3.1) usará `ResetDeterministicValidationState` antes do assembler

**Critérios de Aceitação**:
- [ ] Arquivo criado em `app/agents/gating.py`
- [ ] `RunIfPassed` executa agente quando `grade == expected_grade`
- [ ] `RunIfPassed` pula agente quando grade diferente
- [ ] `RunIfPassed` trata ausência de chave como fail
- [ ] `ResetDeterministicValidationState` remove chaves específicas
- [ ] Eventos de auditoria registrados

---

### Fase 3: Reorquestração do Pipeline

**Objetivo**: Integrar validador, reorganizar agentes, garantir observabilidade e persistência correta.

**Razão da ordem**: Pipeline só pode ser modificado após schemas (Fase 1) e validador (Fase 2) estarem disponíveis. Reorquestração toca arquivos críticos e deve ser última etapa antes de testes.

---

#### Entrega 3.1: Builder de Pipeline Condicional

**Tarefa**: Criar função `build_execution_pipeline()` em `app/agent.py`

**Descrição**: Centralizar criação do pipeline em builder que retorna versão determinística ou legado baseado em feature flag.

**Código atual** (o que já existe):
- `execution_pipeline` definido em `app/agent.py:1261-1274` como instância global de `SequentialAgent`
- Pipeline atual: `final_assembler` → `final_validation_loop` → `ImageAssetsAgent`

**Modificações planejadas**:

```python
# app/agent.py (EXISTENTE - SERÁ MODIFICADO)

from app.config import config  # já disponível
from app.validators.final_delivery_validator import FinalDeliveryValidatorAgent  # Fase 2.1
from app.agents.gating import RunIfPassed, ResetDeterministicValidationState  # Fase 2.2

def build_execution_pipeline(flag_enabled: bool) -> SequentialAgent:
    """
    Constrói pipeline de execução baseado em feature flag.

    Args:
        flag_enabled: Se True, usa pipeline determinístico. Se False, legado.

    Returns:
        SequentialAgent configurado
    """

    if flag_enabled:
        # PIPELINE DETERMINÍSTICO (NOVO)

        # Validador determinístico com failure handler
        deterministic_validation_stage = SequentialAgent(
            name="deterministic_validation_stage",
            sub_agents=[FinalDeliveryValidatorAgent(name="final_delivery_validator")],
            after_agent_callback=make_failure_handler(
                "deterministic_final_validation",
                "JSON final não passou na validação determinística."
            ),
        )

        # Revisor semântico (renomeado de final_validation_loop)
        semantic_validation_loop = LoopAgent(
            name="semantic_validation_loop",
            max_iterations=2,
            sub_agents=[
                semantic_visual_reviewer,  # será criado na Fase 3.3
                EscalationChecker(name="semantic_validation_escalator", review_key="semantic_visual_review"),
                RunIfFailed(name="semantic_fix_if_failed", review_key="semantic_visual_review", agent=semantic_fix_agent),
            ],
            after_agent_callback=make_failure_handler(
                "semantic_visual_review",
                "Não foi possível garantir coerência narrativa."
            ),
        )

        # Escalation barrier para semantic
        semantic_validation_stage = EscalationBarrier(
            name="semantic_validation_stage",
            agent=semantic_validation_loop,
        )

        # Persistência dedicada (não mais callback do assembler)
        persist_final_delivery_agent = PersistFinalDeliveryAgent(name="persist_final_delivery")  # Fase 3.4

        return SequentialAgent(
            name="execution_pipeline",
            sub_agents=[
                # ... agentes anteriores (planning, execution workers) ...
                FinalAssemblyGuardPre(name="final_assembly_guard_pre"),  # Fase 3.2.1
                final_assembler_llm,  # Fase 3.2.2 (modificado)
                FinalAssemblyNormalizer(name="final_assembly_normalizer"),  # Fase 3.2.3
                deterministic_validation_stage,
                RunIfPassed(name="semantic_only_if_passed", review_key="deterministic_final_validation", agent=semantic_validation_stage),
                RunIfPassed(name="images_only_if_passed", review_key="semantic_visual_review", agent=image_assets_agent),
                RunIfPassed(name="persist_only_if_passed", review_key="image_assets_review", agent=persist_final_delivery_agent),
                # ... agentes posteriores ...
            ],
        )

    else:
        # PIPELINE LEGADO (PRESERVADO)
        return SequentialAgent(
            name="execution_pipeline",
            sub_agents=[
                # ... agentes anteriores ...
                ResetDeterministicValidationState(name="reset_deterministic_state"),  # limpa resíduos
                final_assembler,  # mantém callbacks originais
                EscalationBarrier(name="final_validation_stage", agent=final_validation_loop),
                image_assets_agent,  # mantém comportamento legado
                EnhancedStatusReporter(name="status_reporter_final"),
                # ... agentes posteriores ...
            ],
        )

# Instanciar no módulo
execution_pipeline = build_execution_pipeline(config.enable_deterministic_final_validation)
```

**Dependências**:
- **Código existente** (será modificado):
  - `app/agent.py:1261-1274` - definição atual de `execution_pipeline`
  - `final_assembler` de `app/agent.py:1029` (LlmAgent)
  - `image_assets_agent` de `app/agent.py:733` (ImageAssetsAgent)
- **Código criado em fases anteriores**:
  - `FinalDeliveryValidatorAgent` (Fase 2.1)
  - `RunIfPassed`, `ResetDeterministicValidationState` (Fase 2.2)
- **Código a ser criado nesta fase**:
  - `FinalAssemblyGuardPre` (Fase 3.2.1)
  - `FinalAssemblyNormalizer` (Fase 3.2.3)
  - `semantic_visual_reviewer`, `semantic_fix_agent` (Fase 3.3)
  - `PersistFinalDeliveryAgent` (Fase 3.4)

**Razão da abordagem**:
- Builder evita mutação de instâncias em runtime
- Duas versões completas (determinística vs legado) sem condicionais internos
- Flag avaliada uma vez no startup (consistência garantida)

**Critérios de Aceitação**:
- [ ] Função `build_execution_pipeline()` criada em `app/agent.py`
- [ ] Retorna pipeline determinístico quando `flag_enabled=True`
- [ ] Retorna pipeline legado quando `flag_enabled=False`
- [ ] Pipeline legado mantém callbacks originais do `final_assembler`
- [ ] Pipeline determinístico remove callback de persistência do assembler
- [ ] Instância global `execution_pipeline` criada no módulo
- [ ] Logs indicam qual pipeline foi ativado

**Automated Validation**:
- [ ] Modificação usa verbo "Criar função em arquivo existente"
- [ ] Cita `app/agent.py:1261` como código existente

---

#### Entrega 3.2: Guards e Normalizer do Assembler

Esta entrega cria 3 novos agentes que trabalham em conjunto com o `final_assembler`.

##### Entrega 3.2.1: FinalAssemblyGuardPre

**Tarefa**: Criar agente `FinalAssemblyGuardPre` em `app/agents/assembly_guards.py`

**Descrição**: Guard que valida presença e unicidade de snippets `VISUAL_DRAFT` aprovados antes de acionar o LLM assembler.

**Estrutura do código**:

```python
# app/agents/assembly_guards.py (NOVO - SERÁ CRIADO)

from typing import Any
import json
from google.genai.adk import BaseAgent, EventActions
from app.utils.audit import append_delivery_audit_event  # Fase 1.2
import logging

logger = logging.getLogger(__name__)


class FinalAssemblyGuardPre(BaseAgent):
    """
    Valida snippets VISUAL_DRAFT antes do final_assembler.

    Responsabilidades:
    - Filtrar approved_code_snippets por snippet_type == "VISUAL_DRAFT"
    - Validar unicidade por snippet_id
    - Normalizar fragmento (JSON parsing)
    - Popular state["approved_visual_drafts"]
    - Bloquear com EventActions(escalate=True) se falhar
    """

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        snippets = state.get("approved_code_snippets", [])
        visual_drafts = [s for s in snippets if s.get("snippet_type") == "VISUAL_DRAFT" and s.get("status") == "approved"]

        if not visual_drafts:
            self._fail(state, "Nenhum snippet VISUAL_DRAFT aprovado encontrado")
            return state

        # Validar unicidade
        seen_ids = set()
        approved_visual_drafts = {}

        for snippet in visual_drafts:
            snippet_id = snippet.get("snippet_id")
            if snippet_id in seen_ids:
                self._fail(state, f"Snippet duplicado: {snippet_id}")
                return state
            seen_ids.add(snippet_id)

            # Tentar parsear JSON
            try:
                content = snippet.get("code", "")
                if isinstance(content, str):
                    parsed = json.loads(content)
                else:
                    parsed = content

                variation_id = snippet.get("task_id", snippet_id)
                approved_visual_drafts[variation_id] = {
                    "snippet_id": snippet_id,
                    "task_id": snippet.get("task_id"),
                    "approved_at": snippet.get("approved_at"),
                    "content": parsed
                }
            except json.JSONDecodeError as e:
                self._fail(state, f"Snippet ilegível: {snippet_id} - {e}")
                return state

        # Sucesso
        state["approved_visual_drafts"] = approved_visual_drafts
        append_delivery_audit_event(
            state,
            stage="final_assembly_guard_pre",
            status="success",
            detail=f"{len(approved_visual_drafts)} snippets validados"
        )
        logger.info(f"FinalAssemblyGuardPre: {len(approved_visual_drafts)} snippets aprovados")

        return state

    def _fail(self, state: dict[str, Any], reason: str):
        """Falha auditável com escalation."""
        state["deterministic_final_validation"] = {"grade": "fail", "issues": [reason], "source": "guard_pre"}
        state["deterministic_final_blocked"] = True

        append_delivery_audit_event(
            state,
            stage="final_assembly_guard_pre",
            status="fail",
            detail=reason,
            deterministic_grade="fail"
        )
        logger.error(f"FinalAssemblyGuardPre BLOQUEOU: {reason}")

        # Emitir escalation para impedir continuação
        return EventActions(escalate=True)
```

**Dependências**:
- `BaseAgent`, `EventActions` de `google.genai.adk` (já disponível)
- `append_delivery_audit_event` de `app/utils/audit.py` (Fase 1.2)
- `approved_code_snippets` populado por callback modificado (Fase 1.4)

**Integrações**:
- Executado antes de `final_assembler_llm` (Fase 3.2.2)
- Popula `approved_visual_drafts` para consumo pelo normalizer (Fase 3.2.3)

**Critérios de Aceitação**:
- [ ] Arquivo criado em `app/agents/assembly_guards.py`
- [ ] Valida presença de pelo menos 1 snippet VISUAL_DRAFT
- [ ] Detecta duplicidades por `snippet_id`
- [ ] Parseia JSON de cada snippet
- [ ] Popula `approved_visual_drafts` mapeado por `variation_id`
- [ ] Emite `EventActions(escalate=True)` em caso de falha
- [ ] Define `deterministic_final_blocked=True` para status reporters

---

##### Entrega 3.2.2: Modificação do final_assembler_llm

**Tarefa**: Modificar prompt de `final_assembler` existente em `app/agent.py:1029`

**Código atual** (o que já existe):
- `final_assembler` definido como `LlmAgent` em `app/agent.py:1029`
- Prompt atual gera 3 variações sem instrução explícita de reutilização de snippet

**Modificações planejadas**:

```diff
# app/agent.py:1029 (EXISTENTE - PROMPT SERÁ MODIFICADO)

 final_assembler_llm = LlmAgent(
     model="gemini-2.5-flash",
     name="final_assembler",
     system_instructions="""
     Você é o montador final de anúncios para Instagram.

+    **IMPORTANTE**: Reutilize INTEGRALMENTE o fragmento visual aprovado disponível em
+    `state['approved_visual_drafts']`. Não crie novos prompts visuais, apenas copie
+    os campos `prompt_estado_intermediario` e `prompt_estado_final` do snippet.
+
     Gere 3 variações do anúncio em formato JSON com estrutura:
     {
         "variations": [
             {
                 "copy": {"headline": "...", "corpo": "..."},
-                "visual": {"aspect_ratio": "...", "prompt_estado_intermediario": "...", "prompt_estado_final": "..."},
+                "visual": {
+                    "aspect_ratio": "...",
+                    "prompt_estado_intermediario": "<COPIAR DO SNIPPET APROVADO>",
+                    "prompt_estado_final": "<COPIAR DO SNIPPET APROVADO>"
+                },
                 "cta_instagram": "...",
                 "fluxo": "...",
                 "contexto_landing": {...},
                 "referencia_padroes": "..."
             }
         ]
     }

+    Retorne APENAS o JSON válido, sem markdown ou comentários.
     """,
-    after_agent_callback=persist_final_delivery_callback  # REMOVER no pipeline determinístico
 )
```

**Nota importante**: O callback `persist_final_delivery_callback` será removido APENAS quando `config.enable_deterministic_final_validation=True`. No pipeline legado, mantém-se inalterado.

**Dependências**:
- `app/agent.py:1029` - definição existente de `final_assembler`
- `approved_visual_drafts` populado por `FinalAssemblyGuardPre` (Fase 3.2.1)

**Integrações**:
- Roda após `FinalAssemblyGuardPre` (Fase 3.2.1)
- Output processado por `FinalAssemblyNormalizer` (Fase 3.2.3)

**Critérios de Aceitação**:
- [ ] Prompt atualizado com instrução de reutilização de snippet
- [ ] Instrução para retornar JSON puro (sem markdown)
- [ ] Callback de persistência removido no pipeline determinístico
- [ ] Callback mantido no pipeline legado

---

##### Entrega 3.2.3: FinalAssemblyNormalizer

**Tarefa**: Criar agente `FinalAssemblyNormalizer` em `app/agents/assembly_guards.py`

**Descrição**: Normaliza output do LLM assembler, garantindo JSON canônico e validando presença de seções obrigatórias.

**Estrutura do código**:

```python
# app/agents/assembly_guards.py (EXISTENTE - ADICIONAR CLASSE)

class FinalAssemblyNormalizer(BaseAgent):
    """
    Normaliza output do final_assembler_llm.

    Responsabilidades:
    - Extrair JSON da resposta LLM (remover markdown se presente)
    - Validar presença de seções obrigatórias (copy, visual, cta_instagram, fluxo)
    - Garantir reutilização do snippet aprovado
    - Converter para JSON string canônica
    - Atualizar state["final_code_delivery"]
    - Registrar grade="pending" até validador rodar
    """

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        # Extrair resposta do LLM (última mensagem)
        # Assumindo que ADK expõe response em state["last_agent_response"]
        response_text = state.get("last_agent_response", {}).get("content", "")

        # Remover markdown se presente
        json_text = self._extract_json(response_text)

        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as e:
            self._fail(state, f"LLM retornou JSON inválido: {e}")
            return state

        # Validar estrutura obrigatória
        variations = payload.get("variations", [])
        if len(variations) != 3:
            self._fail(state, f"Esperadas 3 variações, recebidas {len(variations)}")
            return state

        required_sections = ["copy", "visual", "cta_instagram", "fluxo"]
        for idx, var in enumerate(variations):
            missing = [sec for sec in required_sections if sec not in var]
            if missing:
                self._fail(state, f"Variação {idx}: faltam seções {missing}")
                return state

        # Verificar reutilização de snippet (comparar prompts)
        approved_drafts = state.get("approved_visual_drafts", {})
        if approved_drafts:
            # Lógica simplificada: verificar se pelo menos 1 variação reutiliza snippet
            # (implementação completa compararia todos os campos visuais)
            pass  # Implementar verificação detalhada conforme necessário

        # Normalizar contexto_landing (dict → mantém, str → mantém)
        for var in variations:
            ctx = var.get("contexto_landing")
            if isinstance(ctx, dict):
                # Manter como dict (schema aceita)
                pass
            elif isinstance(ctx, str):
                # Manter como string
                pass
            else:
                # Converter para string vazia se nulo (ou manter dict vazio)
                var["contexto_landing"] = ctx or {}

        # Serializar JSON canônico
        normalized_json = json.dumps(payload, ensure_ascii=False, indent=2)

        # Atualizar estado
        state["final_code_delivery"] = normalized_json
        state["deterministic_final_validation"] = {
            "grade": "pending",
            "source": "normalizer",
            "issues": []
        }

        append_delivery_audit_event(
            state,
            stage="final_assembly_normalizer",
            status="success",
            detail="JSON normalizado com sucesso"
        )
        logger.info("FinalAssemblyNormalizer: JSON normalizado")

        return state

    def _extract_json(self, text: str) -> str:
        """Remove markdown code blocks se presentes."""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        return text.strip()

    def _fail(self, state: dict[str, Any], reason: str):
        """Falha auditável com escalation."""
        state["deterministic_final_validation"] = {"grade": "fail", "issues": [reason], "source": "normalizer"}
        state["deterministic_final_blocked"] = True

        append_delivery_audit_event(
            state,
            stage="final_assembly_normalizer",
            status="fail",
            detail=reason,
            deterministic_grade="fail"
        )
        logger.error(f"FinalAssemblyNormalizer FALHOU: {reason}")

        return EventActions(escalate=True)
```

**Dependências**:
- `BaseAgent`, `EventActions` de `google.genai.adk` (já disponível)
- `append_delivery_audit_event` de `app/utils/audit.py` (Fase 1.2)
- Output de `final_assembler_llm` (Fase 3.2.2)

**Integrações**:
- Executado imediatamente após `final_assembler_llm`
- Atualiza `final_code_delivery` para consumo pelo validador (Fase 2.1)

**Critérios de Aceitação**:
- [ ] Classe adicionada a `app/agents/assembly_guards.py`
- [ ] Remove markdown code blocks do output LLM
- [ ] Valida presença de seções obrigatórias
- [ ] Normaliza `contexto_landing` (dict ou string)
- [ ] Atualiza `final_code_delivery` com JSON canônico
- [ ] Define `grade="pending"` em `deterministic_final_validation`
- [ ] Emite `EventActions(escalate=True)` se estrutura inválida

---

#### Entrega 3.3: Revisor Semântico e Agentes Auxiliares

**Tarefa**: Criar `semantic_visual_reviewer` e `semantic_fix_agent` em `app/agent.py`

**Descrição**: Implementar revisores LLM focados APENAS em coerência narrativa, sem checagens estruturais (já feitas pelo validador determinístico).

**Estrutura do código**:

```python
# app/agent.py (EXISTENTE - ADICIONAR AGENTES)

# Schema reutilizado (já existe em app/agent.py)
# class Feedback(BaseModel): ...

semantic_visual_reviewer = LlmAgent(
    model="gemini-2.5-pro",  # Critic model
    name="semantic_visual_reviewer",
    system_instructions="""
    Você é um revisor de coerência narrativa e visual de anúncios para Instagram.

    **IMPORTANTE**: NÃO valide estrutura JSON, campos obrigatórios ou aspect ratios.
    Isso já foi feito pela validação determinística.

    Seu foco é APENAS:
    1. Coerência narrativa entre headline, corpo e prompts visuais
    2. Alinhamento com objetivo final e público-alvo
    3. Adequação ao formato especificado (Reels/Stories/Feed)
    4. Tom de voz e storytelling (seguindo StoryBrand se aplicável)
    5. Diferenciação entre as 3 variações

    Retorne Feedback com:
    - grade: "pass" | "fail"
    - issues: lista de problemas SEMÂNTICOS encontrados
    - fix_instructions: instruções narrativas para correção (se fail)

    JSON esperado:
    {
        "grade": "pass",
        "issues": [],
        "fix_instructions": ""
    }
    """,
    response_schema=Feedback,  # já disponível
)

semantic_fix_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="semantic_fix_agent",
    system_instructions="""
    Você é o agente de correção de coerência narrativa.

    Baseado nas instruções do revisor semântico, ajuste APENAS:
    - Headline e corpo (copy)
    - Descrições de storytelling
    - Tom de voz

    **NÃO MODIFIQUE**:
    - Prompts visuais (prompt_estado_intermediario, prompt_estado_final)
    - Aspect ratio
    - CTA
    - Estrutura JSON

    Retorne o JSON completo com correções aplicadas apenas nos campos narrativos.
    """,
)
```

**Dependências**:
- `LlmAgent` de `google.genai.adk` (já disponível)
- Schema `Feedback` de `app/agent.py` (já disponível)
- `final_code_delivery` normalizado (produzido na Fase 3.2.3)

**Contrato**:
- **Input**: `state["final_code_delivery"]` (JSON normalizado e validado estruturalmente)
- **Output**: `Feedback` com `grade`, `issues`, `fix_instructions`
- **Persistência**: Atualiza `state["semantic_visual_review"]`

**Integrações**:
- Encapsulado por `semantic_validation_loop` (Fase 3.1)
- Executado apenas se validador determinístico passou (`RunIfPassed`)

**Critérios de Aceitação**:
- [ ] Agentes adicionados a `app/agent.py`
- [ ] Reviewer foca APENAS em coerência narrativa
- [ ] Reviewer não valida estrutura JSON
- [ ] Fix agent não modifica prompts visuais já aprovados
- [ ] Schema `Feedback` reutilizado do código existente
- [ ] Prompts claramente instruem sobre escopo limitado

---

#### Entrega 3.4: Agente de Persistência Dedicado

**Tarefa**: Criar `PersistFinalDeliveryAgent` em `app/agents/persistence.py`

**Descrição**: Agente dedicado que persiste JSON final e imagens somente após todas as validações passarem.

**Estrutura do código**:

```python
# app/agents/persistence.py (NOVO - SERÁ CRIADO)

from typing import Any
from google.genai.adk import BaseAgent
from app.callbacks.persist_outputs import persist_final_delivery  # já disponível
from app.utils.audit import append_delivery_audit_event  # Fase 1.2
import logging

logger = logging.getLogger(__name__)


class PersistFinalDeliveryAgent(BaseAgent):
    """
    Persiste JSON final e imagens após todas as validações.

    Responsabilidades:
    - Ler image_assets_review para decidir anexar imagens ou não
    - Chamar persist_final_delivery exatamente uma vez
    - Registrar sucesso/falha parcial em auditoria
    - Popular image_assets_review se não existir
    """

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        # Garantir que image_assets_review existe
        image_review = state.get("image_assets_review", {})
        if not image_review:
            # Caso ImageAssetsAgent tenha pulado geração
            logger.info("PersistFinalDeliveryAgent: image_assets_review ausente, assumindo skipped")
            state["image_assets_review"] = {
                "grade": "skipped",
                "issues": [],
                "reason": "Geração de imagens desativada ou JSON ausente"
            }
            image_review = state["image_assets_review"]

        grade = image_review.get("grade")

        # Decidir estratégia de persistência
        if grade == "pass":
            # Persistir JSON + imagens
            logger.info("Persistindo JSON final com imagens")
            persist_final_delivery(state, attach_images=True)
            status = "success_with_images"

        elif grade == "skipped":
            # Persistir apenas JSON
            logger.info("Persistindo apenas JSON final (imagens skipadas)")
            persist_final_delivery(state, attach_images=False)
            status = "success_json_only"

        elif grade == "fail":
            # Registrar falha parcial mas persistir JSON
            logger.warning("Geração de imagens falhou, persistindo apenas JSON")
            persist_final_delivery(state, attach_images=False)
            status = "partial_failure"

        else:
            logger.error(f"image_assets_review.grade desconhecido: {grade}")
            status = "error"

        # Auditoria
        append_delivery_audit_event(
            state,
            stage="persist_final_delivery",
            status=status,
            detail=f"Persistência com grade={grade}"
        )

        return state
```

**Dependências**:
- `BaseAgent` de `google.genai.adk` (já disponível)
- `persist_final_delivery` de `app/callbacks/persist_outputs.py` (já disponível, será modificado para aceitar parâmetro `attach_images`)
- `append_delivery_audit_event` de `app/utils/audit.py` (Fase 1.2)
- `image_assets_review` populado por `ImageAssetsAgent` (modificado em Fase 3.5)

**Integrações**:
- Executado como último agente no pipeline determinístico
- Gated por `RunIfPassed(review_key="image_assets_review")` (Fase 3.1)

**Critérios de Aceitação**:
- [ ] Arquivo criado em `app/agents/persistence.py`
- [ ] Persiste JSON + imagens quando `grade="pass"`
- [ ] Persiste apenas JSON quando `grade="skipped"`
- [ ] Registra falha parcial quando `grade="fail"`
- [ ] Chama `persist_final_delivery` exatamente uma vez
- [ ] Popular `image_assets_review` se ausente (default: `skipped`)

---

#### Entrega 3.5: Ajustes no ImageAssetsAgent

**Tarefa**: Modificar `ImageAssetsAgent` em `app/agent.py:310`

**Código atual** (o que já existe):
- `ImageAssetsAgent` definido em `app/agent.py:310`
- Gera imagens quando `final_code_delivery` presente e flag de geração ativa
- Não popula `image_assets_review` consistentemente

**Modificações planejadas**:

```python
# app/agent.py:310 (EXISTENTE - SERÁ MODIFICADO)

class ImageAssetsAgent(BaseAgent):
    # ... código existente ...

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        # ... lógica existente de geração de imagens ...

        # ADICIONAR ao final:
        # Sempre popular image_assets_review antes de retornar

        if not state.get("final_code_delivery"):
            state["image_assets_review"] = {
                "grade": "skipped",
                "issues": [],
                "reason": "final_code_delivery ausente"
            }
            logger.info("ImageAssetsAgent: JSON ausente, skipando geração")
            return state

        if not config.enable_image_generation:
            state["image_assets_review"] = {
                "grade": "skipped",
                "issues": [],
                "reason": "Geração de imagens desativada (ENABLE_IMAGE_GENERATION=false)"
            }
            logger.info("ImageAssetsAgent: Geração desativada por flag")
            return state

        # ... lógica de geração de imagens ...

        # Ao final (sucesso ou falha)
        if all_images_generated_successfully:
            state["image_assets_review"] = {
                "grade": "pass",
                "issues": [],
                "images_generated": len(images)
            }
            logger.info(f"ImageAssetsAgent: {len(images)} imagens geradas com sucesso")
        else:
            state["image_assets_review"] = {
                "grade": "fail",
                "issues": list_of_errors,
                "images_partial": len(successful_images)
            }
            logger.error(f"ImageAssetsAgent: Falha na geração - {len(list_of_errors)} erros")

        return state
```

**Dependências**:
- `app/agent.py:310` - código existente de `ImageAssetsAgent`
- `config.enable_image_generation` de `app/config.py` (já disponível)

**Integrações**:
- `image_assets_review` lido por `PersistFinalDeliveryAgent` (Fase 3.4)
- `RunIfPassed` usa `image_assets_review` para gating de persistência

**Critérios de Aceitação**:
- [ ] Sempre popula `image_assets_review` antes de retornar
- [ ] `grade="skipped"` quando JSON ausente ou geração desativada
- [ ] `grade="pass"` quando todas imagens geradas com sucesso
- [ ] `grade="fail"` quando erros ocorrerem
- [ ] `RunIfPassed` trata `grade="skipped"` como passagem válida

---

#### Entrega 3.6: Callbacks e Failure Handlers

**Tarefa**: Atualizar `make_failure_handler` em `app/callbacks/` (arquivo a confirmar)

**Descrição**: Garantir que failure handler trata `deterministic_final_validation` sem sobrescrever `final_validation_result` (LLM legado).

**Código atual** (o que já existe):
- `make_failure_handler` usado em callbacks de agentes (localização a confirmar em `app/callbacks/`)

**Modificações planejadas**:

```python
# app/callbacks/[arquivo_de_callbacks].py (EXISTENTE - SERÁ MODIFICADO)

def make_failure_handler(state_key: str, failure_message: str):
    """
    Factory de failure handlers.

    MODIFICAÇÃO: Tratar deterministic_final_validation separadamente de final_validation_result.
    """

    def handler(state: dict, response: dict, config: dict) -> dict:
        review = state.get(state_key, {})
        grade = review.get("grade")

        if grade == "fail":
            # Escrever failure meta específica
            if state_key == "deterministic_final_validation":
                # Usar chave dedicada para validação determinística
                write_failure_meta(state, "deterministic_final_validation_failed", failure_message)
                state["deterministic_final_blocked"] = True

            elif state_key == "semantic_visual_review":
                write_failure_meta(state, "semantic_visual_review_failed", failure_message)

            elif state_key == "final_validation_result":
                # Pipeline legado (manter compatibilidade)
                write_failure_meta(state, "final_validation_result_failed", failure_message)

            else:
                # Genérico
                write_failure_meta(state, f"{state_key}_failed", failure_message)

            logger.error(f"Failure handler: {state_key} -> {failure_message}")

        return state

    return handler
```

**Dependências**:
- Callback existente `make_failure_handler` (localização a confirmar)
- Função `write_failure_meta` (já disponível)

**Integrações**:
- Usado em `deterministic_validation_stage` (Fase 3.1)
- Usado em `semantic_validation_loop` (Fase 3.1)

**Critérios de Aceitação**:
- [ ] Trata `deterministic_final_validation` com chave dedicada
- [ ] Não sobrescreve `final_validation_result` do pipeline legado
- [ ] Define `deterministic_final_blocked=True` para status reporters
- [ ] Mantém compatibilidade com callbacks existentes

---

#### Entrega 3.7: Endpoints e Orchestrator

**Tarefa**: Atualizar `FeatureOrchestrator` e endpoints em `app/server.py`

**Código atual** (o que já existe):
- `FeatureOrchestrator` em `app/server.py` (já disponível)
- Endpoints `/delivery/final/meta`, `/delivery/final/download` (já disponíveis)

**Modificações planejadas**:

```python
# app/server.py (EXISTENTE - SERÁ MODIFICADO)

class FeatureOrchestrator:
    # ... código existente ...

    def check_delivery_status(self, state: dict) -> dict:
        """
        MODIFICAÇÃO: Adicionar checks para novas chaves de validação.
        """

        # Checks existentes
        final_validation_failed = state.get("final_validation_result_failed")  # legado

        # ADICIONAR: Checks determinísticos
        deterministic_failed = state.get("deterministic_final_validation_failed")
        semantic_failed = state.get("semantic_visual_review_failed")
        images_failed = state.get("image_assets_review_failed")

        # Lógica de decisão
        if deterministic_failed:
            return {
                "status": "failed",
                "reason": "Validação determinística reprovou JSON final",
                "stage": "deterministic_validation"
            }

        if semantic_failed:
            return {
                "status": "failed",
                "reason": "Validação semântica reprovou coerência narrativa",
                "stage": "semantic_validation"
            }

        if images_failed:
            # Falha parcial (JSON pode estar disponível)
            return {
                "status": "partial",
                "reason": "Geração de imagens falhou, JSON disponível",
                "stage": "image_generation",
                "json_available": True
            }

        # Manter check legado para compatibilidade
        if final_validation_failed:
            return {
                "status": "failed",
                "reason": "Validação LLM reprovou (pipeline legado)",
                "stage": "final_validation_loop"
            }

        return {"status": "success"}

# Endpoints
@app.get("/delivery/final/meta")
async def get_delivery_meta(session_id: str):
    """
    MODIFICAÇÃO: Expor novas chaves de estado.
    """
    state = get_session_state(session_id)
    orchestrator = FeatureOrchestrator()
    status = orchestrator.check_delivery_status(state)

    return {
        "status": status["status"],
        "reason": status.get("reason"),
        "stage": status.get("stage"),
        "deterministic_validation": state.get("deterministic_final_validation"),
        "semantic_review": state.get("semantic_visual_review"),
        "image_assets": state.get("image_assets_review"),
        "json_available": status.get("json_available", False)
    }
```

**Dependências**:
- `app/server.py` - FeatureOrchestrator e endpoints (já disponíveis)
- Chaves de estado populadas pelas fases anteriores

**Integrações**:
- Frontend consome `/delivery/final/meta` para exibir status
- SSE (se aplicável) envia atualizações de progresso

**Critérios de Aceitação**:
- [ ] FeatureOrchestrator checa `deterministic_final_validation_failed`
- [ ] FeatureOrchestrator checa `semantic_visual_review_failed`
- [ ] FeatureOrchestrator checa `image_assets_review_failed`
- [ ] Endpoint `/delivery/final/meta` expõe novas chaves
- [ ] Mantém compatibilidade com `final_validation_result_failed` (legado)
- [ ] Status `partial` indica JSON disponível mesmo com falha em imagens

---

### Fase 4: Testes, Documentação e Qualidade

**Objetivo**: Validar implementação ponta a ponta, documentar mudanças e garantir rollout seguro.

**Razão da ordem**: Testes só podem rodar após todas as fases anteriores estarem implementadas. Documentação deve refletir código final.

---

#### Entrega 4.1: Testes Unitários

**Tarefa**: Criar `tests/unit/validators/test_final_delivery_validator.py`

**Descrição**: Suite de testes unitários cobrindo validador determinístico, guards, normalizer e schemas.

**Estrutura do código**:

```python
# tests/unit/validators/test_final_delivery_validator.py (NOVO - SERÁ CRIADO)

import pytest
from app.validators.final_delivery_validator import FinalDeliveryValidatorAgent
from app.schemas.final_delivery import StrictAdItem
from app.agents.assembly_guards import FinalAssemblyGuardPre, FinalAssemblyNormalizer

class TestFinalDeliveryValidator:
    """Testes para FinalDeliveryValidatorAgent."""

    def test_valid_json_passes(self):
        """JSON válido com 3 variações completas deve passar."""
        state = {
            "final_code_delivery": json.dumps({
                "variations": [
                    {
                        "copy": {"headline": "Test", "corpo": "Body"},
                        "visual": {
                            "aspect_ratio": "9:16",
                            "prompt_estado_intermediario": "Prompt 1",
                            "prompt_estado_final": "Prompt 2"
                        },
                        "cta_instagram": "BOOK_NOW",
                        "fluxo": "Fluxo",
                        "contexto_landing": {},
                    }
                ] * 3
            }),
            "objetivo_final": "agendamentos"
        }

        agent = FinalDeliveryValidatorAgent(name="test_validator")
        result = agent.run(state)

        assert result["deterministic_final_validation"]["grade"] == "pass"
        assert len(result["deterministic_final_validation"]["issues"]) == 0

    def test_empty_prompt_fails(self):
        """Campo prompt_estado_intermediario vazio deve falhar."""
        state = {
            "final_code_delivery": json.dumps({
                "variations": [{
                    "copy": {"headline": "Test", "corpo": "Body"},
                    "visual": {
                        "aspect_ratio": "9:16",
                        "prompt_estado_intermediario": "",  # VAZIO
                        "prompt_estado_final": "Prompt"
                    },
                    "cta_instagram": "BOOK_NOW",
                    "fluxo": "Fluxo",
                    "contexto_landing": {},
                }] * 3
            }),
            "objetivo_final": "agendamentos"
        }

        agent = FinalDeliveryValidatorAgent(name="test_validator")
        result = agent.run(state)

        assert result["deterministic_final_validation"]["grade"] == "fail"
        assert any("prompt_estado_intermediario" in issue for issue in result["deterministic_final_validation"]["issues"])

    def test_invalid_cta_for_objective(self):
        """CTA incompatível com objetivo deve gerar issue."""
        state = {
            "final_code_delivery": json.dumps({
                "variations": [{
                    "copy": {"headline": "Test", "corpo": "Body"},
                    "visual": {
                        "aspect_ratio": "9:16",
                        "prompt_estado_intermediario": "Prompt 1",
                        "prompt_estado_final": "Prompt 2"
                    },
                    "cta_instagram": "SHOP_NOW",  # Incompatível com agendamentos
                    "fluxo": "Fluxo",
                    "contexto_landing": {},
                }] * 3
            }),
            "objetivo_final": "agendamentos"
        }

        agent = FinalDeliveryValidatorAgent(name="test_validator")
        result = agent.run(state)

        assert any("CTA" in issue and "incompatível" in issue for issue in result["deterministic_final_validation"]["issues"])

    def test_duplicates_detected(self):
        """Variações duplicadas devem ser detectadas."""
        variation = {
            "copy": {"headline": "Same", "corpo": "Same"},
            "visual": {
                "aspect_ratio": "9:16",
                "prompt_estado_intermediario": "Same",
                "prompt_estado_final": "Same"
            },
            "cta_instagram": "BOOK_NOW",
            "fluxo": "Fluxo",
            "contexto_landing": {},
        }

        state = {
            "final_code_delivery": json.dumps({"variations": [variation, variation, variation]}),
            "objetivo_final": "agendamentos"
        }

        agent = FinalDeliveryValidatorAgent(name="test_validator")
        result = agent.run(state)

        assert any("duplicada" in issue for issue in result["deterministic_final_validation"]["issues"])

    def test_storybrand_fallback_relaxes_validation(self):
        """Campos vazios aceitos quando force_storybrand_fallback=True."""
        state = {
            "final_code_delivery": json.dumps({
                "variations": [{
                    "copy": {"headline": "", "corpo": ""},  # Vazios
                    "visual": {
                        "aspect_ratio": "9:16",
                        "prompt_estado_intermediario": "",
                        "prompt_estado_final": ""
                    },
                    "cta_instagram": "BOOK_NOW",
                    "fluxo": "",
                    "contexto_landing": {},
                }] * 3
            }),
            "objetivo_final": "agendamentos",
            "force_storybrand_fallback": True  # Fallback ativo
        }

        agent = FinalDeliveryValidatorAgent(name="test_validator")
        result = agent.run(state)

        # Com fallback, deve relaxar validações
        assert result["deterministic_final_validation"]["grade"] == "pass" or \
               "schema_relaxation_reason" in result["deterministic_final_validation"]


class TestAssemblyGuards:
    """Testes para FinalAssemblyGuardPre e Normalizer."""

    def test_guard_blocks_missing_visual_draft(self):
        """Guard deve bloquear quando nenhum VISUAL_DRAFT aprovado."""
        state = {"approved_code_snippets": []}

        guard = FinalAssemblyGuardPre(name="test_guard")
        result = guard.run(state)

        assert state["deterministic_final_validation"]["grade"] == "fail"
        assert state["deterministic_final_blocked"] is True

    def test_normalizer_extracts_json_from_markdown(self):
        """Normalizer deve extrair JSON de markdown code blocks."""
        state = {
            "last_agent_response": {
                "content": """```json
                {"variations": [{"copy": {}, "visual": {}, "cta_instagram": "BOOK_NOW", "fluxo": "F", "contexto_landing": {}}]}
                ```"""
            }
        }

        normalizer = FinalAssemblyNormalizer(name="test_normalizer")
        result = normalizer.run(state)

        assert "final_code_delivery" in result
        assert result["final_code_delivery"].startswith("{")  # JSON puro, sem markdown
```

**Dependências**:
- `pytest` (já em requirements.txt)
- Módulos criados nas fases anteriores

**Cobertura**:
- Cenários de sucesso (JSON válido)
- Falhas estruturais (campos vazios, tipos inválidos)
- Validações de negócio (CTA vs objetivo, duplicidades)
- Fallback StoryBrand (relaxamento de validações)
- Guards e normalizers

**Critérios de Aceitação**:
- [ ] Arquivo criado em `tests/unit/validators/test_final_delivery_validator.py`
- [ ] Todos os testes passam com `pytest tests/unit/validators/`
- [ ] Cobertura > 80% do validador e guards
- [ ] Cenários de fallback cobertos

---

#### Entrega 4.2: Testes de Integração

**Tarefa**: Criar `tests/integration/test_deterministic_pipeline.py`

**Descrição**: Testes de integração simulando pipeline completo com estado mockado.

**Estrutura do código**:

```python
# tests/integration/test_deterministic_pipeline.py (NOVO - SERÁ CRIADO)

import pytest
from app.agent import build_execution_pipeline
from google.genai.adk.testing import FakeAgent  # Fake de LlmAgent do ADK

class TestDeterministicPipeline:
    """Testes de integração do pipeline determinístico."""

    def test_full_pipeline_success(self):
        """Pipeline completo deve processar JSON válido até persistência."""
        # Mockar LLMs com FakeAgent
        fake_assembler = FakeAgent(
            name="fake_assembler",
            response=json.dumps({"variations": [valid_variation] * 3})
        )

        # Construir pipeline com flag ativa
        pipeline = build_execution_pipeline(flag_enabled=True)

        # Estado inicial
        state = {
            "approved_code_snippets": [
                {
                    "snippet_type": "VISUAL_DRAFT",
                    "status": "approved",
                    "snippet_id": "abc123",
                    "task_id": "task1",
                    "approved_at": "2025-01-01T00:00:00Z",
                    "code": json.dumps({"visual": {...}})
                }
            ],
            "objetivo_final": "agendamentos",
            "formato_anuncio": "Reels"
        }

        # Executar pipeline
        result = pipeline.run(state)

        # Validações
        assert result["deterministic_final_validation"]["grade"] == "pass"
        assert result["semantic_visual_review"]["grade"] == "pass"
        assert result["image_assets_review"]["grade"] in ["pass", "skipped"]
        assert "delivery_audit_trail" in result
        assert len(result["delivery_audit_trail"]) > 0

    def test_deterministic_fail_blocks_downstream(self):
        """Falha determinística deve impedir execução de semantic/images/persist."""
        # JSON inválido (campos vazios)
        state = {
            "approved_code_snippets": [...],
            "final_code_delivery": json.dumps({"variations": [invalid_variation] * 3}),
            "objetivo_final": "agendamentos"
        }

        pipeline = build_execution_pipeline(flag_enabled=True)
        result = pipeline.run(state)

        assert result["deterministic_final_validation"]["grade"] == "fail"
        # Agentes downstream não devem ter executado
        assert "semantic_visual_review" not in result or result.get("semantic_visual_review") == {}
        assert "image_assets_review" not in result or result.get("image_assets_review") == {}

    def test_legacy_pipeline_still_works(self):
        """Pipeline legado (flag=False) deve funcionar normalmente."""
        pipeline = build_execution_pipeline(flag_enabled=False)

        state = {
            "final_code_delivery": json.dumps({"variations": [valid_variation] * 3}),
            "objetivo_final": "agendamentos"
        }

        result = pipeline.run(state)

        # Pipeline legado usa final_validation_result
        assert "final_validation_result" in result or "final_validation_loop" in result
        # Chaves determinísticas não devem existir (limpas por Reset)
        assert "deterministic_final_validation" not in result

    def test_flag_toggle_cleans_state(self):
        """Alternar flag deve limpar estado determinístico."""
        # Executar com flag ativa
        pipeline_det = build_execution_pipeline(flag_enabled=True)
        state = {
            "approved_code_snippets": [...],
            "objetivo_final": "agendamentos"
        }
        result_det = pipeline_det.run(state)
        assert "deterministic_final_validation" in result_det

        # Reexecutar com flag desativada
        pipeline_legacy = build_execution_pipeline(flag_enabled=False)
        result_legacy = pipeline_legacy.run(result_det)

        # Estado determinístico deve ter sido limpo
        assert "deterministic_final_validation" not in result_legacy
        assert "approved_visual_drafts" not in result_legacy
```

**Dependências**:
- `pytest` (já em requirements.txt)
- `FakeAgent` de `google.genai.adk.testing` (se disponível, ou mock manual)
- Pipeline completo de fases anteriores

**Cobertura**:
- Pipeline completo (guard → assembler → normalizer → validador → semantic → images → persist)
- Gating de `RunIfPassed` bloqueando agentes downstream
- Alternância de flag (determinístico vs legado)
- Limpeza de estado por `ResetDeterministicValidationState`
- Cenários de fallback StoryBrand

**Critérios de Aceitação**:
- [ ] Arquivo criado em `tests/integration/test_deterministic_pipeline.py`
- [ ] Todos os testes passam
- [ ] Pipeline determinístico executa todas as etapas quando flag ativa
- [ ] Pipeline legado funciona quando flag desativada
- [ ] Estado limpo ao alternar flag

---

#### Entrega 4.3: Testes de Regressão

**Tarefa**: Atualizar testes existentes em `tests/`

**Descrição**: Garantir que testes existentes ainda passam e adicionar verificações para novos comportamentos.

**Modificações planejadas**:

```python
# tests/[arquivos_existentes].py (EXISTENTES - SERÃO ATUALIZADOS)

# ADICIONAR: Verificações de mapeamento CTA
def test_cta_objective_mapping():
    """Enums de CTA em config.py e format_specifications devem estar alinhados."""
    from app.config import CTA_BY_OBJECTIVE
    from app.format_specifications import CTAInstagram

    # Verificar que todos os objetivos têm CTAs válidos
    for objetivo, ctas in CTA_BY_OBJECTIVE.items():
        for cta in ctas:
            assert cta in [e.value for e in CTAInstagram], f"CTA '{cta}' inválido para objetivo '{objetivo}'"

# ATUALIZAR: Testes de final_assembler
def test_final_assembler_with_flag_active():
    """final_assembler sem callback de persistência quando flag ativa."""
    from app.agent import final_assembler_llm

    # Verificar que callback foi removido no pipeline determinístico
    # (implementação específica depende de como callbacks são expostos)
    pass

# ATUALIZAR: Testes de ImageAssetsAgent
def test_image_assets_always_populates_review():
    """ImageAssetsAgent deve sempre popular image_assets_review."""
    from app.agent import ImageAssetsAgent

    agent = ImageAssetsAgent()
    state = {"final_code_delivery": None}
    result = agent.run(state)

    assert "image_assets_review" in result
    assert result["image_assets_review"]["grade"] == "skipped"
```

**Cobertura**:
- Alinhamento de enums (CTA, formatos, aspect ratios)
- Comportamento de callbacks alterados
- Compatibilidade com código existente

**Critérios de Aceitação**:
- [ ] Todos os testes existentes continuam passando
- [ ] Adicionadas verificações de alinhamento de enums
- [ ] Testes cobrem alternância de flag sem quebras

---

#### Entrega 4.4: Documentação

**Tarefa**: Atualizar README e criar guia de rollout

**Descrição**: Documentar nova arquitetura, feature flag e procedimentos de deploy.

**Arquivos a criar/modificar**:

1. **README.md (EXISTENTE - ADICIONAR SEÇÃO)**

```markdown
# README.md (EXISTENTE - SERÁ MODIFICADO)

## Validação Determinística do JSON Final

### Visão Geral

O sistema agora inclui validação determinística do JSON final de ads, reduzindo dependência de LLMs para garantias estruturais.

### Arquitetura

**Pipeline Determinístico** (quando `ENABLE_DETERMINISTIC_FINAL_VALIDATION=true`):

1. **FinalAssemblyGuardPre**: Valida snippets VISUAL_DRAFT aprovados
2. **final_assembler_llm**: Gera 3 variações reutilizando snippets
3. **FinalAssemblyNormalizer**: Normaliza JSON e valida estrutura
4. **FinalDeliveryValidatorAgent**: Validação determinística com schemas Pydantic
5. **Semantic Reviewer**: Valida coerência narrativa (não estrutural)
6. **ImageAssetsAgent**: Gera imagens (se habilitado)
7. **PersistFinalDeliveryAgent**: Persiste JSON e imagens

**Pipeline Legado** (quando `ENABLE_DETERMINISTIC_FINAL_VALIDATION=false`):

- Mantém fluxo atual: assembler → final_validation_loop → ImageAssetsAgent

### Feature Flag

**Env Var**: `ENABLE_DETERMINISTIC_FINAL_VALIDATION`
- **Default**: `false` (pipeline legado)
- **Requer restart**: Sim (flag lida no startup)

**Como habilitar**:
```bash
# .env ou variável de ambiente
ENABLE_DETERMINISTIC_FINAL_VALIDATION=true
```

### Rollout Gradual

1. **Dev**: Habilitar flag e testar localmente
2. **Staging**: Habilitar em ambiente canário
3. **Produção**: Rollout progressivo (10% → 50% → 100%)
4. **Monitoramento**: Observar métricas `deterministic_final_validation` em logs

### Rollback

Se problemas forem detectados:
```bash
# Desabilitar flag
ENABLE_DETERMINISTIC_FINAL_VALIDATION=false

# Restart do serviço
make restart
```

### Logs e Observabilidade

Novos eventos de auditoria:
- `delivery_audit_trail[].stage`: `deterministic_validation`, `semantic_validation`, `persist_final_delivery`
- `delivery_audit_trail[].deterministic_grade`: `pass` | `fail` | `pending`

Chaves de estado expostas:
- `deterministic_final_validation`: Resultado da validação determinística
- `semantic_visual_review`: Resultado da revisão semântica
- `image_assets_review`: Status de geração de imagens

### StoryBrand Fallback

Quando fallback StoryBrand está ativo:
- Schema relaxa validações de `min_length`
- Campos vazios são aceitos
- `schema_relaxation_reason` registrado em `deterministic_final_validation`

Condições de fallback:
- `force_storybrand_fallback=True`
- `storybrand_fallback_meta.fallback_engaged=True`
- `landing_page_analysis_failed=True`

### APIs Afetadas

**GET `/delivery/final/meta`**:
```json
{
  "status": "success" | "failed" | "partial",
  "reason": "...",
  "stage": "deterministic_validation" | "semantic_validation" | "image_generation",
  "deterministic_validation": {...},
  "semantic_review": {...},
  "image_assets": {...},
  "json_available": true
}
```
```

2. **docs/rollout_deterministic_validation.md (NOVO - SERÁ CRIADO)**

```markdown
# Rollout: Validação Determinística

## Pré-requisitos

- [ ] Testes unitários passando (`pytest tests/unit/validators/`)
- [ ] Testes de integração passando (`pytest tests/integration/`)
- [ ] Testes de regressão passando (`pytest tests/`)
- [ ] Logs estruturados configurados
- [ ] Monitoramento de métricas ativo

## Passos de Deploy

### 1. Ambiente Dev

```bash
# Habilitar flag
export ENABLE_DETERMINISTIC_FINAL_VALIDATION=true

# Restart
make dev

# Verificar logs
make logs | grep "Feature flag loaded"
# Esperado: "enable_deterministic_final_validation=true"

# Testar manualmente
curl -X POST http://localhost:8000/run_preflight ...
```

### 2. Ambiente Staging

```bash
# Habilitar flag em staging
kubectl set env deployment/instagram-ads ENABLE_DETERMINISTIC_FINAL_VALIDATION=true -n staging

# Aguardar rollout
kubectl rollout status deployment/instagram-ads -n staging

# Smoke test
./scripts/smoke_test_staging.sh
```

### 3. Produção (Canário)

```bash
# Deploy canário (10% do tráfego)
kubectl apply -f k8s/canary-deployment.yaml

# Monitorar métricas
# - Taxa de falha determinística vs LLM
# - Latência do pipeline
# - Qualidade das variações geradas

# Se métricas OK, aumentar para 50%
kubectl scale deployment/instagram-ads-canary --replicas=5

# Se métricas OK, rollout completo (100%)
kubectl apply -f k8s/production-deployment.yaml
```

### 4. Rollback

```bash
# Desabilitar flag
kubectl set env deployment/instagram-ads ENABLE_DETERMINISTIC_FINAL_VALIDATION=false -n production

# Ou reverter deployment
kubectl rollout undo deployment/instagram-ads -n production
```

## Métricas de Sucesso

- Taxa de aprovação determinística > 95%
- Latência adicional < 200ms
- Taxa de falhas semânticas < 5%
- Qualidade de variações mantida ou melhorada

## Troubleshooting

### Flag não carrega
- Verificar env var: `kubectl describe pod <pod> | grep ENABLE_DETERMINISTIC`
- Confirmar restart: `kubectl get pods -w`

### Validador reprova JSON válido
- Verificar logs: `kubectl logs <pod> | grep deterministic_validation`
- Checar schema relaxation: `storybrand_fallback_meta`

### Pipeline legado não funciona após rollback
- Confirmar `ResetDeterministicValidationState` executou
- Verificar `delivery_audit_trail` para eventos de reset
```

**Critérios de Aceitação**:
- [ ] README atualizado com seção de validação determinística
- [ ] Guia de rollout criado em `docs/rollout_deterministic_validation.md`
- [ ] Documentação de feature flag incluída
- [ ] Procedimentos de rollback documentados
- [ ] Métricas de observabilidade listadas

---

## Checklist Operacional

Este checklist resume todas as entregas e serve como guia de implementação:

### ✅ Fase 1: Fundação
- [ ] 1.1: Schema `app/schemas/final_delivery.py` criado com relaxamento condicional
- [ ] 1.2: Helper `app/utils/audit.py` criado
- [ ] 1.3: Metadados StoryBrand documentados e verificados
- [ ] 1.4: Callback `collect_code_snippets` estendido com metadados
- [ ] 1.5: Feature flag adicionada em `app/config.py`

### ✅ Fase 2: Validador
- [ ] 2.1: `FinalDeliveryValidatorAgent` criado em `app/validators/`
- [ ] 2.2: Utilitários `RunIfPassed` e `ResetDeterministicValidationState` criados

### ✅ Fase 3: Pipeline
- [ ] 3.1: Builder `build_execution_pipeline()` criado em `app/agent.py`
- [ ] 3.2.1: `FinalAssemblyGuardPre` criado
- [ ] 3.2.2: Prompt de `final_assembler_llm` modificado
- [ ] 3.2.3: `FinalAssemblyNormalizer` criado
- [ ] 3.3: Reviewers `semantic_visual_reviewer` e `semantic_fix_agent` criados
- [ ] 3.4: `PersistFinalDeliveryAgent` criado
- [ ] 3.5: `ImageAssetsAgent` modificado para popular `image_assets_review`
- [ ] 3.6: `make_failure_handler` atualizado
- [ ] 3.7: Endpoints e `FeatureOrchestrator` atualizados

### ✅ Fase 4: Testes e Documentação
- [ ] 4.1: Testes unitários criados (`tests/unit/validators/`)
- [ ] 4.2: Testes de integração criados (`tests/integration/`)
- [ ] 4.3: Testes de regressão atualizados
- [ ] 4.4: README e guia de rollout documentados

### ✅ Validação Final
- [ ] Todos os testes passam (`pytest tests/`)
- [ ] Plano validado com `plan-code-validator` (0 P0 blockers)
- [ ] Feature flag testada (toggle entre `true`/`false`)
- [ ] Pipeline legado funcional
- [ ] Pipeline determinístico funcional
- [ ] Documentação revisada

---

## Riscos e Mitigações

### Risco 1: Rigidez Excessiva do Schema
**Descrição**: Schema muito estrito pode bloquear casos legítimos de ads.

**Mitigação**:
- Testes realistas com JSONs de produção
- Factory `from_state()` relaxa validações em fallback StoryBrand
- Monitoramento de taxa de rejeição (target < 5%)

### Risco 2: Duplicação de Lógica com Prompts
**Descrição**: Regras podem divergir entre schema e prompts do LLM.

**Mitigação**:
- Centralizar regras em `app/format_specifications.py`
- Importar enums em schemas e prompts
- Testes automatizados detectam divergências

### Risco 3: Quebra do Fluxo Legado
**Descrição**: Modificações podem quebrar pipeline legado.

**Mitigação**:
- Builder retorna duas versões isoladas (determinística vs legado)
- `ResetDeterministicValidationState` limpa resíduos
- Testes de regressão cobrem ambos os pipelines
- Feature flag permite rollback imediato

### Risco 4: Performance
**Descrição**: Validação adicional pode aumentar latência.

**Mitigação**:
- Validação é leve (loop sobre 3 variações, sem I/O)
- Impacto estimado < 200ms
- Monitorar latência em produção

### Risco 5: Evolução do Catálogo de CTAs
**Descrição**: Novos CTAs ou objetivos podem quebrar validação.

**Mitigação**:
- Centralizar em `CTA_BY_OBJECTIVE` em `app/config.py`
- Testes automatizados verificam alinhamento
- Quando objetivo desconhecido, não reprovar automaticamente (usar enum global)

---

## Entregáveis Finais

1. **Código**:
   - Validador determinístico (`app/validators/final_delivery_validator.py`)
   - Schemas estritos (`app/schemas/final_delivery.py`)
   - Guards e normalizer (`app/agents/assembly_guards.py`)
   - Utilitários de gating (`app/agents/gating.py`)
   - Agente de persistência (`app/agents/persistence.py`)
   - Pipeline reorquestrado (`app/agent.py` modificado)

2. **Testes**:
   - Suite unitária completa
   - Testes de integração com mocks
   - Testes de regressão atualizados

3. **Documentação**:
   - README atualizado
   - Guia de rollout
   - Documentação de feature flag

---

## Fora de Escopo

- Refatorar completamente `app/plan_models/fixed_plans.py`
- Alterar lógica do StoryBrand fallback pipeline
- Implementar geração automática de prompts alternativos
- Modificar frontend (apenas APIs backend)

---

## Conclusão

Este plano introduz uma barreira determinística robusta que:

1. **Elimina falsos positivos**: Validação estrutural determinística antes de LLMs
2. **Alinha assembler a snippets aprovados**: Reutilização obrigatória via guards
3. **Separa validações**: Determinística (estrutural) vs Semântica (narrativa)
4. **Garante persistência correta**: Apenas após todas as validações passarem
5. **Permite rollout gradual**: Feature flag com fallback para pipeline legado
6. **Mantém compatibilidade**: Pipeline legado preservado para rollback seguro

**Resultado esperado**: Redução de variações incompletas, feedback mais rápido ao usuário e maior confiabilidade do sistema de geração de ads.
