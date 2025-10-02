# Plano de Validação Determinística do JSON Final de Ads

## 1. Contexto e Problema Atual
- O `final_assembler` (`app/agent.py:1023`) monta as três variações do anúncio exclusivamente via LLM, sem reaproveitar determinística e integralmente o fragmento aprovado de `VISUAL_DRAFT`.
- A validação estrutural depende de outro LLM (`final_validator`, `app/agent.py:1053`), que deveria barrar campos obrigatórios vazios, mas pode aprovar falsos positivos (ex.: `null` em `visual.prompt_estado_intermediario`).
- O único gate determinístico hoje é o `ImageAssetsAgent` (`app/agent.py:310`), que apenas detecta campos ausentes momentos antes da geração de imagens, resultando em variações ignoradas em vez de corrigidas.
- Não existe uma validação em código (schema ou regra) que garanta contratos mínimos antes das etapas finais.

## 2. Objetivos do Plano
- Criar uma camada determinística que valide o JSON final antes de qualquer verificação LLM ou geração de imagens.
- Garantir aderência às especificações de formato (`app/format_specifications.py`) e aos contratos definidos pelos modelos Pydantic (`AdVisual`, `AdItem`, etc.).
- Reduzir a superfície de erro do `final_assembler`, limitando a liberdade criativa em campos críticos.
- Introduzir uma revisão semântica pós-validação determinística, dedicada a avaliar apenas coerência narrativa/visual.

## 3. Inventário da Arquitetura Atual
- **Modelos Pydantic (referência, não utilizados para validação):**
  - `AdVisual`, `AdItem` (`app/agent.py:67` e `app/agent.py:80`).
- **Orquestração do pipeline de execução:**
  - `execution_pipeline` reúne `final_assembler`, `final_validation_loop`, `ImageAssetsAgent` (`app/agent.py:1235-1261`).
- **Validação LLM:**
  - `final_validation_loop` → `final_validator` (LLM) → `EscalationChecker` → `final_fix_agent` (`app/agent.py:1240`).
- **Dados auxiliares:**
  - Especificações de formato (`app/format_specifications.py`).
  - Plano fixo por formato (`app/plan_models/fixed_plans.py`) – somente referência de tarefas, não de validação.

## 4. Proposta Técnica Detalhada

### 4.1 Validador Determinístico (novo componente)
- **Arquivo sugerido:** `app/validators/final_delivery_validator.py`.
- **Responsabilidades:**
  1. Carregar `final_code_delivery` do estado (aceitar `str` JSON ou `list`).
  2. Validar contra um novo schema Pydantic estrito:
     - Reutilizar/estender `AdVisual` e `AdItem` com `constr(min_length=1)` para todos os campos textuais obrigatórios.
     - Forçar enums para `formato`, `aspect_ratio`, `cta_instagram`.
     - Rejeitar strings vazias ou whitespace.
  3. Conferir regras por formato usando `app/format_specifications.py`:
     - `visual.aspect_ratio` deve estar em `permitidos` (Feed) ou ser igual ao definido (Reels/Stories).
     - CTA precisa alinhar com `format_specs['strategy']['cta_preferencial'][objetivo_final_normalizado]` quando aplicável.
     - Headline ≤ `headline_max_chars` quando `copy.headline` estiver presente.
  4. Validar consistência entre variações (todas devem ser distintas em pelo menos copy ou prompts).
  5. Atualizar o estado com uma chave `final_delivery_validation` contendo `{"grade": "pass"|"fail", "issues": [...]}`.
- **Falhas:**
  - Em caso de erro, lançar exceção customizada (ex.: `FinalDeliveryValidationError`) e registrar evento no audit trail (reutilizar `_append_audit_event` do fallback ou criar função local).
  - A exceção deve ser capturada por um `EscalationBarrier` para interromper o pipeline e comunicar ao usuário.

### 4.2 Integração no Pipeline
- Inserir um novo `SequentialAgent` após `final_validation_loop` e antes de `ImageAssetsAgent`:
  ```python
  deterministic_validator = FinalDeliveryValidatorAgent(...)
  execution_pipeline = SequentialAgent(
      name="execution_pipeline",
      sub_agents=[
          ...
          final_assembler,
          EscalationBarrier(name="final_validation_stage", agent=final_validation_loop),
          deterministic_validator,  # NOVO
          semantic_visual_reviewer,  # ver 4.3
          image_assets_agent,
          ...
      ],
  )
  ```
- O novo agente não deve usar LLM. Ele apenas registra `Event` de sucesso ou lança erro com contexto.
- Atualizar `make_failure_handler` ou criar callback semelhante para marcar `final_delivery_validation_failed` em caso de falha determinística.

### 4.3 Ajustes no `final_assembler`
- Revisar `app/agent.py:1023-1049` para reforçar instruções:
  - Passar os snippets aprovados explicitamente (ex.: `visual_snippet = next(snippet for snippet in approved_code_snippets if snippet["category"] == "VISUAL_DRAFT")`).
  - Incluir na instrução: “Use o `visual` aprovado; ajuste apenas quando o formato exigir variação textual. Nunca deixe prompts vazios.”
  - Alternativa mais rígida: pós-processar o resultado do assembler substituindo o campo `visual` por clonar do snippet aprovado e só variar copy/descrição se necessário.
- Avaliar se é preciso quebrar `final_assembler` em duas partes: montagem determinística do `visual` + LLM para copy. (Opcional, mas reduz risco.)

### 4.4 Revisor Semântico Pós-Validação
- Criar `semantic_visual_reviewer` (LLM) que roda apenas se o validador determinístico retornar `pass`.
- **Responsabilidades:**
  - Verificar coerência narrativa de `descricao_imagem` vs prompts (`prompt_estado_*`).
  - Checar tonalidade/aderência ao formato (ex.: Feed mais informativo).
  - Retornar `grade` + `comment`; falha gera escalonamento antes do `ImageAssetsAgent`.
- **Posicionamento:** imediatamente após `deterministic_validator`.
- **Prompt:** Incluir contexto (`format_specs_json`, `landing_page_context`, variações do JSON) e restringir a saída a `pass/fail` + texto.

### 4.5 Observabilidade e Estado
- Registrar logs estruturados ao estilo `storybrand_fallback_section` quando o validador e o revisor rodarem (ex.: `logger.info("final_delivery_validation", extra={...})`).
- Salvar no estado:
  - `final_delivery_validation` (resultado determinístico).
  - `semantic_visual_review` (resultado LLM).
- Atualizar mensagens emitidas ao usuário para explicar falhas (ex.: “Validação determinística encontrou prompts vazios na variação 1”).

## 5. Etapas de Implementação
1. **Preparação:**
   - Criar diretório `app/validators/` se não existir.
   - Escrever modelos Pydantic reforçados (`schemas/final_delivery.py` ou dentro do validador).
2. **Validador Determinístico:**
   - Implementar classe `FinalDeliveryValidatorAgent(BaseAgent)` em `app/validators/final_delivery_validator.py`.
   - Integrar com `execution_pipeline` conforme seção 4.2.
3. **Ajustes no `final_assembler`:**
   - Revisar instrução/prompt para reutilizar `visual` aprovado.
   - Opcional: pós-processamento determinístico para `visual`.
4. **Revisor Semântico:**
   - Criar agente LLM (ex.: `SemanticVisualReviewer`) com schema `Feedback` reutilizado.
   - Adicionar `EscalationChecker` e fallback similar ao `code_review_loop` se necessário.
5. **Mensagens & Estado:**
   - Atualizar `EnhancedStatusReporter` (`app/agent.py:283`) para refletir nova etapa.
   - Garantir que falhas atualizem `final_delivery_validation_failed` ou chave equivalente.
6. **Limpeza:**
   - Documentar comportamento no README (`README.md`, seção de pipeline).
   - Garantir consistência de imports e evitar ciclos (ex.: reusar `try_parse_json_string`).

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
- **Regression:**
  - Atualizar testes existentes que assumem ausência de validação.

## 7. Riscos e Mitigações
- **Rigidêz excessiva do schema:** pode bloquear casos legítimos. Mitigar com testes realistas e permitir campos opcionais justificados (ex.: `contexto_landing` não necessariamente longo).
- **Duplicação de lógica com prompts:** minimizar centralizando regras em `app/format_specifications.py` e importando-as tanto no validador quanto nos prompts.
- **Integração com `final_validation_loop`:** garantir que novas exceções não quebrem o fluxo; usar `EscalationBarrier` para normalizar respostas ao usuário.
- **Performance:** validação é leve (loop sobre 3 variações), impacto mínimo.

## 8. Entregáveis
- Código do validador determinístico + integração ao pipeline.
- Novo agente revisor semântico com prompts revisados.
- Ajustes no `final_assembler`/instruções.
- Testes unitários e integração.
- Atualização de documentação (README e, se necessário, playbooks internos).

## 9. Fora de Escopo
- Refatorar completamente o processo de planejamento (`app/plan_models/fixed_plans.py`).
- Alterar o StoryBrand fallback pipeline.
- Implementar geração automática de prompts alternativos (apenas validação).

---

**Conclusão:** O plano introduz uma barreira determinística robusta, alinha o assembler aos fragmentos aprovados e adiciona uma verificação semântica especializada. Com isso, reduzimos a dependência de decisões LLM em tarefas críticas de conformidade e prevenimos o envio de variações incompletas para a etapa de image generation.
