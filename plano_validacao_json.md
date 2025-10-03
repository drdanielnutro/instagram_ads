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

## 4. Proposta Técnica Detalhada

### 4.1 Validador Determinístico (novo componente)
- **Arquivo sugerido:** `app/validators/final_delivery_validator.py` (classe `FinalDeliveryValidatorAgent`).
- **Responsabilidades:**
  1. Carregar `final_code_delivery` do estado (aceitar `str`, `list` ou objetos já carregados) e garantir parsing único.
  2. Validar contra um schema Pydantic dedicado (ex.: `app/schemas/final_delivery.py`) para evitar import circular com `app/agent.py`. Esse schema deve:
     - Declarar `contexto_landing` como `dict[str, Any] | str` (ou modelar estrutura própria) refletindo o payload real.
     - Reutilizar campos de `AdVisual`/`AdItem`, agora movidos/copied para o módulo compartilhado, adicionando `Field(min_length=1)` para strings obrigatórias e lidando com trimming.
     - Respeitar enums configuráveis: `formato` ∈ {"Reels","Stories","Feed"}; `aspect_ratio` baseado em `format_specs`; `cta_instagram` preenchido a partir de fonte única (enum local + overrides do config se existirem).
     - Normalizar e validar `cta_instagram` usando `state["objetivo_final"]` já normalizado; se o objetivo não mapear para CTA preferencial, emitir aviso e aceitar qualquer CTA permitido.
  3. Conferir regras por formato com `app/format_specifications.py`:
     - `visual.aspect_ratio` deve estar em `permitidos` (Feed) ou igual ao valor fixo para Reels/Stories.
     - `copy.headline` precisa respeitar `headline_max_chars` quando preenchida.
  4. Checar unicidade entre variações calculando uma tupla normalizada (ex.: `headline`, `corpo`, `visual.prompt_estado_*`) em lower/trim e comparando com um set; duplicatas geram falha com índice específico.
  5. Atualizar o estado com `final_delivery_validation = {"grade": "pass"|"fail", "issues": [...], "normalized_payload": ...}` para consumo posterior.
- **Falhas:**
  - Lançar `FinalDeliveryValidationError` contendo lista de problemas e anexar evento via novo helper `app/utils/audit.py::append_delivery_audit_event` (evita dependência de `_append_audit_event`).
  - O agente deve usar `make_failure_handler("final_delivery_validation", "JSON final não passou na validação determinística.")` como `after_agent_callback`, garantindo que o orquestrador informe o usuário.

### 4.2 Integração no Pipeline
- Reordenar o `execution_pipeline` para que a validação determinística ocorra imediatamente após o `final_assembler`:
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
- `persist_final_delivery_agent` pode ser um wrapper fino em torno de `persist_final_delivery` (ou converter o callback existente em agente) e deve ser executado apenas após todas as validações retornarem `pass`.
- O `final_validation_loop` atual passa a focar exclusivamente na coerência narrativa (renomeado para `semantic_validation_loop`). O prompt precisa ser ajustado para remover checagens determinísticas já cobertas pelo novo agente.

### 4.3 Ajustes no `final_assembler`
- Revisar `app/agent.py:1023-1049` para reforçar instruções:
  - Utilizar busca resiliente (`next(..., None)`) para localizar o snippet `VISUAL_DRAFT`; se ausente ou duplicado, registrar falha clara (`final_delivery_validation` com `fail`) e interromper o pipeline antes da montagem.
  - Incluir na instrução: “Use o `visual` aprovado; ajuste apenas quando o formato exigir variação textual. Nunca deixe prompts vazios.”
  - Opcional: pós-processar o resultado do assembler substituindo o campo `visual` por cópia literal do snippet aprovado e preservar apenas diferenças de copy.
- Avaliar se é preciso quebrar `final_assembler` em duas partes: montagem determinística do `visual` + LLM para copy (facilita reuso de prompts entre variações e reduz risco de vazios).

### 4.4 Revisor Semântico Pós-Validação
- Criar `semantic_visual_reviewer` (LLM) e um loop leve (`semantic_validation_loop`), executado somente quando `final_delivery_validation.grade == "pass"`.
- **Responsabilidades:**
  - Verificar coerência narrativa de `descricao_imagem` vs `prompt_estado_*`, avaliando continuidade e persona única.
  - Checar tonalidade/aderência ao formato (ex.: Feed mais informativo, Reels/Stories curtos) usando `format_specs_json`.
  - Validar se cada variação respeita o foco e a promessa central sem contradizer o contexto da landing.
  - Retornar `semantic_visual_review = {"grade": "pass"|"fail", "comment": "..."}`; em caso de `fail`, o loop chama `semantic_fix_agent` e, persistindo a falha, bloqueia o `ImageAssetsAgent`.
- **Prompt:** Incluir `final_code_delivery` (já normalizado pelo validador), `landing_page_context`, `objetivo_final`, `foco`, `format_specs_json` e instruir a evitar checagens estruturais.

### 4.5 Observabilidade e Estado
- Registrar logs estruturados ao estilo `storybrand_fallback_section` quando o validador e o revisor rodarem (ex.: `logger.info("final_delivery_validation", extra={...})`).
- Salvar no estado:
  - `final_delivery_validation` (resultado determinístico).
  - `semantic_visual_review` (resultado LLM).
- Atualizar mensagens emitidas ao usuário para explicar falhas (ex.: “Validação determinística encontrou prompts vazios na variação 1”).
- Persistir eventos via `append_delivery_audit_event` tanto para sucesso quanto para falha, e usar `write_failure_meta`/`clear_failure_meta` conforme resultado final.

## 5. Etapas de Implementação
1. **Preparação de estruturas compartilhadas:**
   - Criar diretório `app/validators/` (se necessário) e módulo `app/schemas/final_delivery.py` contendo cópia/extração dos modelos `AdCopy`, `AdVisual`, `AdItem`, já com tipos atualizados para `contexto_landing` estruturado.
   - Introduzir helper `app/utils/audit.py::append_delivery_audit_event` inspirado no fallback StoryBrand, além de centralizar enums de CTA e mapeamentos objetivo→CTA preferencial.
2. **Validador Determinístico:**
   - Implementar `FinalDeliveryValidatorAgent(BaseAgent)` em `app/validators/final_delivery_validator.py`, utilizando o schema novo, normalização de strings e verificação de unicidade.
   - Aplicar `make_failure_handler("final_delivery_validation", ...)` e garantir escrita opcional de `write_failure_meta` para sessões reprovadas.
3. **Reorganização do pipeline:**
   - Converter `final_validation_loop` em `semantic_validation_loop` (ajustar prompts e nomes) e inserir `deterministic_validation_stage` antes dele, conforme seção 4.2.
   - Remover o `after_agent_callback` de `final_assembler` e substituir por `persist_final_delivery_agent` posicionado após as validações.
4. **Ajustes no `final_assembler`:**
   - Reforçar instruções, aplicar busca resiliente por `VISUAL_DRAFT` e, se necessário, pós-processar `visual` antes de retornar.
   - Considerar divisão entre montagem determinística e copy para facilitar reuse.
5. **Revisor Semântico e correções automáticas:**
   - Criar `semantic_visual_reviewer` e `semantic_fix_agent`, configurando `semantic_validation_loop` com `EscalationChecker` e `RunIfFailed`.
   - Bloquear `ImageAssetsAgent` quando `semantic_visual_review` estiver em `fail`.
6. **Mensagens, estado e documentação:**
   - Atualizar `EnhancedStatusReporter`, `FeatureOrchestrator` e endpoints de delivery para refletir novos estados/erros.
   - Propagar `final_delivery_validation` e `semantic_visual_review` para `write_failure_meta`/`clear_failure_meta`, garantindo que sessões reprovadas sejam refletidas nas APIs de entrega.
   - Documentar o novo fluxo no README/playbooks e revisar imports para evitar ciclos.

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
