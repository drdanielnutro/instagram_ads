# Plano de Validação Determinística do JSON Final de Ads

## 1. Contexto e Problema Atual
- O `final_assembler` (`app/agent.py:1029`) monta as três variações do anúncio exclusivamente via LLM, sem reaproveitar determinística e integralmente o fragmento aprovado de `VISUAL_DRAFT`.
- A validação estrutural depende de outro LLM (`final_validator`, `app/agent.py:1059`), que deveria barrar campos obrigatórios vazios, mas pode aprovar falsos positivos (ex.: `null` em `visual.prompt_estado_intermediario`).
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
  - `execution_pipeline` reúne `final_assembler`, `final_validation_loop`, `ImageAssetsAgent` (`app/agent.py:1261-1274`).
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
   - Permitir `contexto_landing` como `dict[str, Any] | str`; campos textuais terão `min_length=1`, exceto quando o pipeline entrar de fato no fallback StoryBrand. O schema deverá relaxar campos quando qualquer uma das condições for verdadeira: `state.get("force_storybrand_fallback")`, `state.get("storybrand_gate_metrics", {}).get("decision_path") == "fallback"`, `state.get("storybrand_fallback_meta", {}).get("fallback_engaged")` ou `state.get("landing_page_analysis_failed")`. Registrar em `deterministic_final_validation['schema_relaxation_reason']` o motivo da flexibilização.
   - Reutilizar enums já existentes em `app/format_specifications.py`/`config.py`; o schema apenas os importa, não define valores próprios (evita múltiplas fontes de verdade) e centraliza os limites de caracteres.

2. **Helper de auditoria e metadados**
   - Criar `app/utils/audit.py` apenas com `append_delivery_audit_event` e funções de logging; mapeamentos de CTA permanecem onde já estão (`format_specifications`/`config`).
   - Revisar utilitários existentes (`app/utils/delivery_status.py`) apenas se precisarem expor helpers comuns (o helper não deve assumir responsabilidade por enums).

3. **Metadados StoryBrand e landing page**
  - Revisar `StoryBrandQualityGate` para documentar o comportamento atual de `state['storybrand_fallback_meta'] = {"decision_path", "trigger_reason", "fallback_engaged", "timestamp_utc"}` e complementar apenas se novos campos ou logs forem necessários.
  - Confirmar (e, se preciso, complementar com observabilidade) que o analisador de landing page preenche `state['landing_page_analysis_failed']` como flag booleana; hoje a flag já é inicializada com `False` e atualizada para `True` em fallback forçado ou erro de análise.

4. **Enriquecimento dos snippets aprovados**
   - Estender `collect_code_snippets_callback` para registrar, além de `task_id`/`category`, os campos `snippet_type`, `status="approved"`, `approved_at` (UTC) e `snippet_id` (hash SHA-256 de `task_id::snippet_type::payload`).
   - Criar estrutura auxiliar `state['approved_visual_drafts']` (mapa `variation_id -> snippet`) que os guards utilizarão sem quebrar consumidores existentes.
   - Atualizar `app/utils/session-state.py` (modelo `CodeSnippet` e helpers `get_session_state`/`add_approved_snippet`) para aceitar e preservar esses novos campos, evitando que o guard perca metadados ao alternar entre pipelines.

5. **Feature flag de ativação**
   - Adicionar no `config.py` a flag `enable_deterministic_final_validation` (default `False`) com suporte a env `ENABLE_DETERMINISTIC_FINAL_VALIDATION`.
   - Documentar que, enquanto `False`, o pipeline segue usando `final_validation_loop` + `ImageAssetsAgent` como hoje; quando `True`, o novo fluxo determinístico substitui essa etapa.
   - Registrar explicitamente que a flag é avaliada na inicialização do processo (exige restart para alternar) e salvar o valor lido em log estruturado (`log_config_flag`).
   - Atualizar README/ops docs para orientar rollout controlado e ambientes canário.

### Fase 2 – Validador Determinístico (Etapa 5.2)
Objetivo: Construir o agente que consome os componentes da Fase 1.

3. **`FinalDeliveryValidatorAgent`**
   - Implementar `app/validators/final_delivery_validator.py` importando os schemas da Fase 1.
   - Responsabilidades principais:
     - Carregar `final_code_delivery` (string/list/objeto) e efetuar parsing único.
     - Validar com o schema estrito, incluindo regras por formato (`app/format_specifications.py`) e checagem de `cta_instagram` coerente com `state["objetivo_final"]`. O plano prevê um mapa `CTA_BY_OBJECTIVE` consolidado em `config.py` cobrindo todas as metas hoje aceitas (`agendamentos`, `leads`, `vendas`, `contato`, `awareness` e afins); quando o objetivo não estiver no mapa, o agente recorrerá ao enum global de CTAs sem reprovar automaticamente.
     - Detectar duplicidades entre variações usando tuplas normalizadas (`headline`, `corpo`, `prompt_estado_*`).
     - Persistir `deterministic_final_validation = {"grade", "issues", "normalized_payload", "source": "validator"}` no estado (mantido como referência) e sincronizar `state["final_code_delivery"]` para apontar para o JSON normalizado.
   - Tratamento de falhas:
     - Não lançar exceções customizadas; registrar `deterministic_final_validation = {"grade": "fail", ...}` e chamar `append_delivery_audit_event`.
     - Configurar `after_agent_callback=make_failure_handler("deterministic_final_validation", "JSON final não passou na validação determinística.")` e, quando necessário, acionar `write_failure_meta`.
     - Atualizar `state["final_code_delivery"]` com a versão normalizada aprovada (string JSON), mantendo o payload alinhado para agentes subsequentes.

4. **Utilitários de gating/reset**
   - Implementar `RunIfPassed` em `app/agents/gating.py`, aceitando `review_key`, `expected_grade` (default `"pass"`) e comportamento explícito para chaves ausentes (tratar como reprovação, logar via `append_delivery_audit_event`).
   - Implementar `ResetDeterministicValidationState` para limpar `approved_visual_drafts`, `deterministic_final_validation`, `deterministic_final_blocked`, `final_code_delivery_parsed` e demais artefatos quando o pipeline legado estiver ativo.

### Fase 3 – Reorquestração do Pipeline (Etapas 5.3–5.5)
Objetivo: Integrar o validador, reorganizar agentes e garantir observabilidade consistente.

#### 4.3.1 Reordenar o `execution_pipeline`
- Centralizar a criação do pipeline em `build_execution_pipeline(flag_enabled: bool)`, chamado na inicialização do módulo. O builder retorna duas versões (determinística e legado) sem mutar instâncias em runtime, evitando inconsistências quando a flag alternar.
- Converter o antigo `final_validation_loop` em `semantic_validation_loop`, focado apenas em coerência narrativa, mantendo o `EscalationBarrier` como etapa explícita após o `EscalationChecker` dentro do fluxo ativado pela flag.
- Substituir o `LlmAgent` `final_assembler` por um estágio composto, orquestrado via `SequentialAgent` com dois novos guards:
  - `FinalAssemblyGuardPre` (novo `BaseAgent`) filtra `state["approved_code_snippets"]` buscando entradas com `snippet_type == "VISUAL_DRAFT"` e `status == "approved"`, normaliza o fragmento (string JSON) e registra falha auditável quando o snippet estiver ausente, duplicado ou ilegível. Persistir o resultado em `state["approved_visual_drafts"]` como lista de dicionários `{snippet_id, task_id, approved_at, content}`. Em caso de falha, deve atualizar `state["deterministic_final_validation"] = {"grade": "fail", ...}`, definir `state["deterministic_final_blocked"] = True` e emitir `EventActions(escalate=True)` para impedir a continuação do estágio.
  - `final_assembler_llm` mantém o prompt atual e gera as três variações; o callback de coleta de snippets permanece inalterado.
  - `FinalAssemblyNormalizer` (novo `BaseAgent`) roda imediatamente após a resposta LLM, reaproveitando o snippet aprovado e validando a presença de seções obrigatórias (`copy`, `visual`, `cta_instagram`, `fluxo`, `referencia_padroes`). Se faltarem dados essenciais, deve falhar como o guard (atualizando `deterministic_final_validation`/`deterministic_final_blocked` e escalando o evento). Quando tudo estiver coerente, garante que `state["final_code_delivery"]` contenha JSON serializado e empurra metadados para `state["deterministic_final_validation"]` com `grade="pending"` e `source="normalizer"` até o validador determinístico executar.
- Inserir `deterministic_validation_stage` logo após o assembler composto.
- Introduzir dois utilitários leves:
  - `RunIfPassed` executa o agente encapsulado apenas quando `deterministic_final_validation.grade == "pass"` (ou outra chave configurada); definir comportamento explícito para ausência de chave (tratar como `fail`).
  - `RunIfFailed` continua disponível para loops que exigem correção (semântico).
- Ajustar `make_failure_handler` para escrever/limpar `deterministic_final_validation_*` apenas quando o `state_key` for `"deterministic_final_validation"`; no caso do `final_validation_result` (LLM), manter compatibilidade com flags legadas sem sobrescrever os resultados determinísticos.
- Encadear `RunIfPassed` com o loop semântico e com os agentes de imagens/persistência, garantindo que nenhum deles seja chamado após falha determinística ou semântica e envolvendo o loop com um `EscalationBarrier` dedicado para consumir `EventActions(escalate=True)` sem abortar o pipeline antes que `make_failure_handler` atue.

```python
deterministic_validation_stage = SequentialAgent(
    name="deterministic_validation_stage",
    sub_agents=[final_delivery_validator_agent],
    after_agent_callback=make_failure_handler(
        "deterministic_final_validation",
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

semantic_validation_stage = EscalationBarrier(
    name="semantic_validation_stage",
    agent=semantic_validation_loop,
)

if config.enable_deterministic_final_validation:
    execution_pipeline = SequentialAgent(
        name="execution_pipeline",
        sub_agents=[
            ...
            FinalAssemblyGuardPre(...),
            final_assembler_llm,
            FinalAssemblyNormalizer(...),
            deterministic_validation_stage,
            RunIfPassed(name="semantic_only_if_passed", review_key="deterministic_final_validation", agent=semantic_validation_stage),
            RunIfPassed(name="images_only_if_passed", review_key="semantic_visual_review", agent=image_assets_agent),
            RunIfPassed(name="persist_only_if_passed", review_key="image_assets_review", agent=persist_final_delivery_agent),
            ...
        ],
    )
else:
    execution_pipeline = SequentialAgent(
        name="execution_pipeline",
        sub_agents=[
            ...
            final_assembler,
            EscalationBarrier(name="final_validation_stage", agent=final_validation_loop),
            image_assets_agent,
            EnhancedStatusReporter(name="status_reporter_final"),
        ],
    )
```

- No caminho legado (`flag=False`), inserir agente auxiliar `ResetDeterministicValidationState` logo antes do `final_assembler` para limpar chaves específicas (`approved_visual_drafts`, `deterministic_final_validation`, etc.) e evitar resíduos quando alternar entre os pipelines.
- Quando a flag estiver ativa, remover o `after_agent_callback` do `final_assembler` e a chamada direta a `persist_final_delivery` dentro do `ImageAssetsAgent`; a persistência passa a ser responsabilidade exclusiva do novo agente dedicado, que só roda quando `image_assets_review.grade == "pass"` (ou `"skipped"` documentado) ou quando explicitamente liberado por falhas toleráveis documentadas em `state["image_assets"]`. Com a flag desativada, manter os callbacks atuais para preservar o comportamento legado.
- Revisar o `ImageAssetsAgent` para sempre popular `state["image_assets_review"]` antes de retornar (ex.: `grade="skipped"`, `issues=[]` quando a geração estiver desativada ou o JSON ausente) e garantir que `RunIfPassed` trate `grade="skipped"` como passagem válida rumo à persistência.
- Atualizar `FeatureOrchestrator` e endpoints de entrega para observar `deterministic_final_validation_failed`, `semantic_visual_review_failed` e `image_assets_review_failed`, mantendo compatibilidade com `final_validation_result_failed` durante a transição e encerrando o pipeline em caso de falha determinística.

#### 4.3.2 Ajustes no `final_assembler`
- `FinalAssemblyGuardPre` realizará a checagem determinística pelos snippets `VISUAL_DRAFT` em `approved_code_snippets`, validando unicidade por `snippet_id`, presença de `code` serializável e preenchendo `state['approved_visual_drafts'][variation_id]` para consumo posterior.
- O `final_assembler_llm` terá o prompt reforçado para exigir reutilização do snippet aprovado e retornar JSON pronto para uso.
- `FinalAssemblyNormalizer` transformará a resposta LLM em string JSON canônica (`json.dumps(..., ensure_ascii=False)`), garantirá sincronismo com o snippet reutilizado e atualizará `state["final_code_delivery"]` e `state["deterministic_final_validation"]` (grade `pending`, `source="normalizer"`) antes de acionar o validador determinístico.

#### 4.3.3 Revisor semântico e agentes auxiliares
- Criar `semantic_visual_reviewer` (LLM) e `semantic_fix_agent`, ambos reutilizando o schema `Feedback`.
- Ajustar prompts para remover checagens estruturais e focar em coerência narrativa, foco e aderência às especificações de formato.
- O loop consumirá o JSON já normalizado presente em `state["final_code_delivery"]`; atualizar o plano para que o validador sempre substitua essa chave antes de acionar o revisor.
- `RunIfPassed` impede a execução do revisor quando o validador falhar.
- `RunIfPassed` tratará ausência da chave de review como `fail` explícito, registrando evento em `append_delivery_audit_event` para garantir rastreabilidade.
- Documentar o contrato de saída do `semantic_visual_reviewer` (`Feedback` com `grade`, `issues`, `fix_instructions`) e alinhar o `semantic_fix_agent` para atuar somente em problemas narrativos (não reescrever campos estruturais já validados).

- Em paralelo, documentar (em planilha/checklist interno) os endpoints afetados: `/delivery/final/meta`, `/delivery/final/download`, streaming SSE e mensagens do `FeatureOrchestrator`.
- Ajustar consumidores para checar `deterministic_final_validation_failed`, `semantic_visual_review_failed` e `image_assets_review_failed` antes de solicitar imagens.
- Garantir que `LandingPageStage` inicialize `state["landing_page_analysis_failed"] = False` e atualize para `True` em cenários de fallback forçado ou erro de fetch, e que `StoryBrandQualityGate` preencherá `state["storybrand_fallback_meta"] = {fallback_engaged, decision_path, trigger_reason, timestamp}` para consumo do schema determinístico.

#### 4.3.4 Observabilidade e persistência
- Registrar eventos estruturados via `append_delivery_audit_event` em cada estágio (guard, validador, revisor, persistência).
- Com a flag ativa, `persist_final_delivery_agent` chamará `persist_final_delivery` exatamente uma vez, lendo `state["image_assets"]` para decidir entre anexar imagens, registrar falha parcial (`image_assets_review.grade == "fail"`) ou persistir somente o JSON. O agente deve também popular `state["image_assets_review"]` com `grade` e `issues` antes de liberar a persistência. Quando a flag estiver desativada, manter o fluxo legado de callbacks.
- Propagar `deterministic_final_validation`, `semantic_visual_review` e `image_assets_review` para `write_failure_meta`/`clear_failure_meta`, garantindo que as APIs de entrega reflitam o status real e preservem o contrato atual (`final_delivery_status`).
- Atualizar `EnhancedStatusReporter` para sinalizar as novas etapas ao usuário final apenas quando a flag estiver habilitada; fora desse cenário, preservar as mensagens atuais.
- Definir contrato dos eventos de auditoria (`stage`, `status`, `detail`, `deterministic_grade`, `storybrand_fallback_engaged`) e das métricas associadas, facilitando monitoramento paralelo dos pipelines legado e determinístico.
- Registrar e limpar a flag auxiliar `deterministic_final_blocked` (exposta para status reporters) para diferenciar falhas do guard/normalizer de reprovações do LLM.

### Fase 4 – Testes, Documentação e Qualidade (Etapas 5.6–6)
Objetivo: Validar o fluxo ponta a ponta e comunicar as mudanças.

1. **Testes unitários**
   - Criar `tests/unit/validators/test_final_delivery_validator.py` cobrindo casos de sucesso/falha (campos vazios, aspect ratio inválido, CTA incoerente, duplicidades, strings vazias) e incluindo cenários com `force_storybrand_fallback=True` e `storybrand_fallback_meta.fallback_engaged=True` onde campos vazios são aceitáveis.
   - Adicionar testes para o normalizador do assembler (reuso do snippet aprovado, conversão de `contexto_landing` dict→string, limpeza de espaços) e para o helper `reset_deterministic_validation_state`.

2. **Testes de integração/regressão**
   - Atualizar ou criar testes que simulem o pipeline completo (`final_assembler` → validador → loop semântico → imagens) exercitando `RunIfPassed`, `EscalationBarrier` e o novo agente de persistência.
   - Incluir cenários com `force_storybrand_fallback=True`, `storybrand_fallback_meta` populado pelo gate e diferentes objetivos para assegurar compatibilidade.
   - Cobrir alternância da flag (`True`→`False`) verificando que `reset_deterministic_validation_state` remove chaves específicas e que o fluxo legado volta a persistir via callbacks.
   - Adicionar verificações automáticas para detectar divergências entre enums de CTA, specs e configurações (falha caso `config.py` e `format_specifications` entrem em conflito).

3. **Documentação e comunicação**
   - Atualizar README/playbooks detalhando a nova ordem de validação e impactos nas APIs de entrega.
   - Registrar notas de migração (ex.: remoção do `after_agent_callback` no `final_assembler`) e sinalizar a necessidade de testes quando novos formatos/CTAs forem adicionados.
   - Documentar a flag `ENABLE_DETERMINISTIC_FINAL_VALIDATION`, incluindo valores recomendados por ambiente, passos para rollout gradual e plano de rollback.
   - Atualizar guias de observabilidade e SSE com as novas chaves de estado (`deterministic_final_validation`, `deterministic_final_blocked`, `image_assets_review` com status `skipped`) e mensagens do `FeatureOrchestrator`.

## 5. Checklist Operacional
1. **Fase 1** – Schema compartilhado (com regras para fallback) e helper de auditoria disponíveis, sem duplicar enums.
2. **Fase 2** – `FinalDeliveryValidatorAgent` atualiza `final_code_delivery`, gera audit/failure meta e respeita exceções de fallback.
3. **Fase 3** – Guard do assembler, RunIfPassed, pipeline reorquestrado, persistência única e endpoints/orchestrator ajustados.
4. **Fase 4** – Testes (unitários, integração, regressão) e documentação atualizados, incluindo cenários de fallback e monitoramento de enums.
5. **Feature flag** – `enable_deterministic_final_validation` documentada, com default `False`, e checklist de rollout/observabilidade definido.

## 6. Estratégia de Testes
- **Unit Tests:**
  - `tests/unit/validators/test_final_delivery_validator.py` cobrindo cenários:
    - JSON válido (3 variações completas).
    - Campo `prompt_estado_intermediario` vazio → falha.
    - `aspect_ratio` fora do permitido conforme formato.
    - CTA incompatível com objetivo (usar fixtures de `format_specs`).
    - Strings contendo apenas espaços.
  - Testar comparações de unicidade entre variações.
  - Cobrir `collect_code_snippets_callback` enriquecendo metadados (`snippet_id`, `approved_at`).
  - Exercitar `FinalAssemblyGuardPre` bloqueando quando não houver VISUAL_DRAFT ou quando duplicado (verificando `EventActions.escalate` e `deterministic_final_validation` = fail).
  - Exercitar `FinalAssemblyNormalizer` garantindo que campos obrigatórios permaneçam presentes, serialização de `contexto_landing` e falha quando o payload retornar apenas blocos parciais.
  - Validar `RunIfPassed`/`ResetDeterministicValidationState` nos cenários pass/fail/ausente.
- **Integration Tests:**
  - Simular pipeline parcial (`final_assembler` → validador) com estado mockado.
  - Garantir que falha determinística impede execução do `ImageAssetsAgent`, registrando o motivo no audit trail.
  - Exercitar `ImageAssetsAgent` nas rotas com geração desativada ou JSON ausente, verificando que `image_assets_review` produz `grade="skipped"`/`issues=[]` e que a persistência ainda é liberada pelo `RunIfPassed`.
  - Validar sessões com `force_storybrand_fallback=True` e `storybrand_fallback_meta.fallback_engaged=True`, cobrindo campos opcionais/estruturados emitidos pelo fallback e confirmando normalização posterior.
  - Utilizar fakes de `LlmAgent`/`BaseAgent` do ADK (ex.: `FakeAgent`) para orquestrar `RunIfPassed`, `EscalationBarrier` e `SequentialAgent`, evitando dependência de chamadas reais ao LLM.
  - Exercitar os dois estados da flag (`True`/`False`) garantindo que o fluxo legado continue funcional, que `reset_deterministic_validation_state` limpe o estado ao reverter e que o novo pipeline seja acionado somente quando habilitado.
  - Verificar rollback da flag: habilitar → gerar entrega → desabilitar → confirmar limpeza de `deterministic_final_validation`/`approved_visual_drafts` e ausência de callbacks duplicados.
  - Assegurar que `persist_final_delivery` é chamado exatamente uma vez por execução e que `image_assets_review` reflete `pass`/`skipped` quando imagens são puladas.
  - Cobrir cenários de fallback StoryBrand medindo `storybrand_fallback_meta` e `landing_page_analysis_failed`, garantindo que o schema relaxado aceite os campos vazios esperados.
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
