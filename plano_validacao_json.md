# Plano de Validação Determinística do JSON Final de Ads

## 1. Contexto e Problema Atual
- O `final_assembler` (`app/agent.py:1023`) monta as três variações do anúncio exclusivamente via LLM, sem reaproveitar determinística e integralmente o fragmento aprovado de `VISUAL_DRAFT`.
- A validação estrutural depende de outro LLM (`final_validator`, `app/agent.py:1053`), que deveria barrar campos obrigatórios vazios, mas pode aprovar falsos positivos (ex.: `null` em `visual.prompt_estado_intermediario`).
- O único gate determinístico hoje é o `ImageAssetsAgent` (`app/agent.py:310`), que apenas detecta campos ausentes momentos antes da geração de imagens, resultando em variações ignoradas em vez de corrigidas.
- Não existe uma validação em código (schema ou regra) que garanta contratos mínimos antes das etapas finais.
- O `persist_final_delivery` é acionado como callback do `final_assembler`, gravando artefatos locais/GCS mesmo quando as validações subsequentes falham.

## 2. Objetivos do Plano
- Criar uma camada determinística que valide o JSON final imediatamente após o `final_assembler`, antes de qualquer verificação LLM ou geração de imagens.
- Garantir aderência às especificações de formato (`app/format_specifications.py`) e aos contratos definidos pelos modelos Pydantic (`AdVisual`, `AdItem`, etc.).
- Reduzir a superfície de erro do `final_assembler`, limitando a liberdade criativa em campos críticos.
- Introduzir uma revisão semântica pós-validação determinística, dedicada a avaliar apenas coerência narrativa/visual.
- Persistir o JSON final somente após todos os estágios de validação terem sido aprovados, evitando artefatos inválidos.

## 3. Inventário da Arquitetura Atual
- **Modelos Pydantic (referência, não utilizados para validação):**
  - `AdVisual`, `AdItem` (`app/agent.py:67` e `app/agent.py:80`). Hoje estão acoplados a `app/agent.py`, e `AdItem.contexto_landing` é `str`, enquanto o JSON gerado traz um objeto estruturado; o plano precisa extrair/copiar esses modelos para um módulo neutro antes de reforçar o schema.
- **Orquestração do pipeline de execução:**
  - `execution_pipeline` reúne `final_assembler`, `final_validation_loop`, `ImageAssetsAgent` (`app/agent.py:1235-1261`).
- **Validação LLM:**
  - `final_validation_loop` → `final_validator` (LLM) → `EscalationChecker` → `final_fix_agent` (`app/agent.py:1240`). Atualmente o loop executa antes de qualquer validação determinística.
- **Dados auxiliares:**
  - Especificações de formato (`app/format_specifications.py`).
  - Plano fixo por formato (`app/plan_models/fixed_plans.py`) – somente referência de tarefas, não de validação.

## 4. Proposta Técnica e Sequência de Implementação

### Fase 1 – Estruturas de Base (Etapa 5.1)
Objetivo: Preparar contratos e utilitários independentes antes de tocar no pipeline principal.

1. **Schema de validação compartilhado**
   - Criar `app/schemas/final_delivery.py` com modelos estritos (`StrictAdCopy`, `StrictAdVisual`, `StrictAdItem`).
   - Permitir `contexto_landing` como `dict[str, Any] | str`, aplicar `Field(min_length=1)` e normalizar whitespace nos campos obrigatórios.
   - Centralizar enums de formato, aspect ratio e CTA em um único lugar para serem reutilizados por agentes e validação.

2. **Helper de auditoria e metadados**
   - Criar `app/utils/audit.py` com `append_delivery_audit_event` (seguindo o padrão do fallback StoryBrand) e outras funções necessárias para registrar sucessos/falhas.
   - Revisar utilitários existentes (`app/utils/delivery_status.py`) apenas se precisarem expor helpers comuns.

### Fase 2 – Validador Determinístico (Etapa 5.2)
Objetivo: Construir o agente que consome os componentes da Fase 1.

3. **`FinalDeliveryValidatorAgent`**
   - Implementar `app/validators/final_delivery_validator.py` importando os schemas da Fase 1.
   - Responsabilidades principais:
     - Carregar `final_code_delivery` (string/list/objeto) e efetuar parsing único.
     - Validar com o schema estrito, incluindo regras por formato (`app/format_specifications.py`) e checagem de `cta_instagram` coerente com `state["objetivo_final"]`.
     - Detectar duplicidades entre variações usando tuplas normalizadas (`headline`, `corpo`, `prompt_estado_*`).
     - Persistir `final_delivery_validation = {"grade", "issues", "normalized_payload"}` no estado.
   - Tratamento de falhas:
     - Levantar `FinalDeliveryValidationError` contendo os problemas e chamar `append_delivery_audit_event`.
     - Configurar `after_agent_callback=make_failure_handler("final_delivery_validation", "JSON final não passou na validação determinística.")` e, quando necessário, acionar `write_failure_meta`.

### Fase 3 – Reorquestração do Pipeline (Etapas 5.3–5.5)
Objetivo: Integrar o validador, reorganizar agentes e garantir observabilidade consistente.

#### 4.3.1 Reordenar o `execution_pipeline`
- Converter o antigo `final_validation_loop` em `semantic_validation_loop`, focado apenas em coerência narrativa.
- Inserir `deterministic_validation_stage` logo após o `final_assembler` e posicionar `persist_final_delivery_agent` somente após todas as validações passarem.

```python
deterministic_validation_stage = SequentialAgent(
    name="deterministic_validation_stage",
    sub_agents=[final_delivery_validator_agent],
    after_agent_callback=make_failure_handler(
        "final_delivery_validation",
        "JSON final não passou na validação determinística."
    ),
)

semantic_validation_loop = LoopAgent(
    name="semantic_validation_loop",
    max_iterations=2,
    sub_agents=[
        semantic_visual_reviewer,
        EscalationChecker(name="semantic_validation_escalator", review_key="semantic_visual_review"),
        RunIfFailed(name="semantic_fix_if_failed", review_key="semantic_visual_review", agent=semantic_fix_agent),
    ],
    after_agent_callback=make_failure_handler(
        "semantic_visual_review",
        "Não foi possível garantir coerência narrativa após as iterações."
    ),
)

execution_pipeline = SequentialAgent(
    name="execution_pipeline",
    sub_agents=[
        ...
        final_assembler,
        deterministic_validation_stage,
        EscalationBarrier(name="semantic_validation_stage", agent=semantic_validation_loop),
        image_assets_agent,
        persist_final_delivery_agent,
        ...
    ],
)
```

- Atualizar `FeatureOrchestrator` e endpoints de entrega para observar `final_delivery_validation_failed` e `semantic_visual_review_failed`.

#### 4.3.2 Ajustes no `final_assembler`
- Reforçar o prompt exigindo reaproveitamento do snippet `VISUAL_DRAFT` aprovado.
- Usar `next(..., None)` ao buscar o snippet; quando ausente ou duplicado, registrar falha clara (estado + audit) e interromper a montagem.
- Opcionalmente pós-processar o campo `visual`, copiando o snippet aprovado antes de devolver as variações.

#### 4.3.3 Revisor semântico e agentes auxiliares
- Criar `semantic_visual_reviewer` (LLM) e `semantic_fix_agent`, ambos reutilizando o schema `Feedback`.
- Ajustar prompts para remover checagens estruturais e focar em coerência narrativa, foco e aderência às especificações de formato.
- Garantir que `semantic_validation_loop` bloqueie o `ImageAssetsAgent` sempre que o resultado permanecer em `fail`.

#### 4.3.4 Observabilidade e persistência
- Registrar eventos estruturados via `append_delivery_audit_event` em cada estágio.
- Propagar `final_delivery_validation` e `semantic_visual_review` para `write_failure_meta`/`clear_failure_meta`, garantindo que as APIs de entrega reflitam o status real.
- Atualizar `EnhancedStatusReporter` para sinalizar as novas etapas ao usuário final.

### Fase 4 – Testes, Documentação e Qualidade (Etapas 5.6–6)
Objetivo: Validar o fluxo ponta a ponta e comunicar as mudanças.

1. **Testes unitários**
   - Criar `tests/unit/validators/test_final_delivery_validator.py` cobrindo casos de sucesso/falha (campos vazios, aspect ratio inválido, CTA incoerente, duplicidades, strings vazias).

2. **Testes de integração/regressão**
   - Atualizar ou criar testes que simulem o pipeline completo (`final_assembler` → validador → loop semântico → imagens).
   - Incluir cenários com `force_storybrand_fallback=True` e diferentes objetivos para assegurar compatibilidade.
   - Adicionar verificações automáticas para detectar divergências entre enums de CTA, specs e configurações.

3. **Documentação e comunicação**
   - Atualizar README/playbooks detalhando a nova ordem de validação e impactos nas APIs de entrega.
   - Registrar notas de migração (ex.: remoção do `after_agent_callback` no `final_assembler`) e sinalizar a necessidade de testes quando novos formatos/CTAs forem adicionados.

## 5. Checklist Operacional
1. **Fase 1** – Schema compartilhado e helper de auditoria prontos.
2. **Fase 2** – `FinalDeliveryValidatorAgent` implementado e emitindo estados/audit esperados.
3. **Fase 3** – Pipeline reorquestrado, `final_assembler` ajustado, revisor semântico e persistência na nova ordem.
4. **Fase 4** – Testes (unitários, integração, regressão) e documentação atualizados, com CTAs e fallback cobertos.

## 6. Estratégia de Testes
- **Unit Tests:**
  - `tests/unit/validators/test_final_delivery_validator.py` cobrindo cenários:
    - JSON válido (3 variações completas).
    - Campo `prompt_estado_intermediario` vazio → falha.
    - `aspect_ratio` fora do permitido conforme formato.
    - CTA incompatível com objetivo (usar fixtures de `format_specs`).
    - Strings contendo apenas espaços.
  - Testar comparações de unicidade entre variações.
- **Integration Tests:**
  - Simular pipeline parcial (`final_assembler` → validador) com estado mockado.
  - Garantir que falha determinística impede execução do `ImageAssetsAgent`.
  - Validar sessões com `force_storybrand_fallback=True`, cobrindo campos opcionais/estruturados emitidos pelo fallback.
- **Regression:**
  - Atualizar testes existentes que assumem ausência de validação.
  - Cobrir mapeamentos de CTA para objetivos suportados (agendamentos, leads, vendas, contato) assegurando que alterações futuras nos specs não quebrem o validador.

## 7. Riscos e Mitigações
- **Rigidêz excessiva do schema:** pode bloquear casos legítimos. Mitigar com testes realistas e permitir campos opcionais justificados (ex.: `contexto_landing` não necessariamente longo).
- **Duplicação de lógica com prompts:** minimizar centralizando regras em `app/format_specifications.py` e importando-as tanto no validador quanto nos prompts.
- **Integração com `final_validation_loop`:** garantir que novas exceções não quebrem o fluxo; usar `EscalationBarrier` para normalizar respostas ao usuário.
- **Performance:** validação é leve (loop sobre 3 variações), impacto mínimo.
- **Evolução do catálogo de CTAs:** manter enum e specs alinhados a `config.py`; planejar testes automatizados para detectar divergências.

## 8. Entregáveis
- Código do validador determinístico + integração ao pipeline.
- Novo agente revisor semântico com prompts revisados.
- Ajustes no `final_assembler`/instruções.
- Helper de auditoria/persistência atualizada (`append_delivery_audit_event`, `persist_final_delivery_agent`).
- Testes unitários e integração.
- Atualização de documentação (README e, se necessário, playbooks internos).

## 9. Fora de Escopo
- Refatorar completamente o processo de planejamento (`app/plan_models/fixed_plans.py`).
- Alterar o StoryBrand fallback pipeline.
- Implementar geração automática de prompts alternativos (apenas validação).

---

**Conclusão:** O plano introduz uma barreira determinística robusta, alinha o assembler aos fragmentos aprovados e adiciona uma verificação semântica especializada. Com isso, reduzimos a dependência de decisões LLM em tarefas críticas de conformidade e prevenimos o envio de variações incompletas para a etapa de image generation.
