# Plano de Correção – Falha na Validação Determinística (CTAs do Fallback)

## 1. Contexto e Objetivo
- Flags atuais (dev): `ENABLE_DETERMINISTIC_FINAL_VALIDATION=true`, `ENABLE_STORYBRAND_FALLBACK=true`, `STORYBRAND_GATE_DEBUG=true`, `PERSIST_STORYBRAND_SECTIONS=false`, `ENABLE_REFERENCE_IMAGES=false`.
- Forçar o fallback + validação determinística expõe CTAs fora de `CTA_INSTAGRAM_CHOICES`, quebrando a pipeline antes da persistência final.
- Objetivo: garantir que todas as variações (inclusive fallback) respeitem os enums rígidos (`cta_texto`, `cta_instagram`, `formato`, `visual.aspect_ratio`) sem afrouxar os validadores.

## 2. Estratégia Geral
1. **P0 – Normalizar na origem (fallback)**  
   Corrigir os CTAs imediatamente após serem extraídos do StoryBrand Action. Isso resolve o bug na raiz e protege qualquer consumidor do fallback.
2. **P1 – Reforçar camada de geração**  
   Atualizar prompts e estado inicial para orientar o LLM a escolher apenas CTAs válidos, reduzindo chance de regressão.
3. **P2 – Melhoria opcional**  
   Documentar CTAs em `format_specifications.py` para futuras validações/UX.

## 3. Passos Detalhados

### P0 – Normalização no Fallback (OBRIGATÓRIO)
1. **Criar helper `_normalize_cta`**  
   - Arquivo: `app/agents/fallback_compiler.py` (logo após os imports – este é o arquivo onde `_extract_ctas` vive; não mover para `storybrand_fallback.py`).  
   - Importar `CTA_INSTAGRAM_CHOICES`, `CTA_BY_OBJECTIVE` e `logger`.  
   - Função deve:
     - Limpar espaços e comparar case-insensitive com valores oficiais.  
     - Mapear sinônimos via `synonym_map` (ex.: “agendar” → “Enviar mensagem”, “fale conosco” → “Enviar mensagem”, “Saiba Mais” → “Saiba mais”).  
     - Usar objetivo (`config.cta_by_objective`) como fallback contextual.  
     - Default final seguro: `"Saiba mais"`.  
     - Garantir que strings vazias ou `None` retornem o fallback seguro sem log de erro repetitivo.
2. **Adaptar `_extract_ctas`**  
   - Local: `app/agents/fallback_compiler.py:71-88`.  
   - Atualizar assinatura para aceitar `action_text: str, objetivo: str`.  
   - Ao retornar, aplicar `_normalize_cta` tanto no `cta_principal` quanto no `cta_backup`.  
   - Atualizar chamada em `_run_async_impl` (linha ~197) para `cta_primary, cta_secondary = _extract_ctas(action_text, state.get("objetivo_final", ""))`.  
   - Registrar log informativo (`logger.info`) quando uma normalização ocorrer (incluindo CTA original e o mapeado) e warning apenas quando cair na opção padrão.
3. **Propagar CTA normalizado no estado**  
   - Os valores normalizados alimentam `ActionElement.primary/secondary`; estes campos são serializados em `storybrand_analysis` e, mais adiante, utilizados pelo pipeline principal para construir o JSON final. Não é necessário mexer em payloads aqui, apenas assegurar que todo consumidor use os campos do estado.
4. **Testes**  
   - Adicionar caso unitário em `tests/unit/agents/test_storybrand_fallback.py` simulando `storybrand_action` com CTA inválido (ex.: “Agendar Avaliação”).  
   - Forçar fallback + determinística em teste de integração (`tests/integration/pipeline` ou novo teste focado) e verificar:  
     - CTAs finais ∈ `CTA_INSTAGRAM_CHOICES`.  
     - Validação determinística retorna `grade="pass"`.  
     - `persist_final_delivery` não é pulado.

### P1 – Reforço de Camada (RECOMENDADO)
1. **Prompts dos planos fixos** (`app/plan_models/fixed_plans.py`)  
   - Em cada `TASK-003` (Reels, Stories, Feed), deixar explícito:  
     > “cta_texto OBRIGATÓRIO: escolha EXATAMENTE um valor de `['Saiba mais', 'Enviar mensagem', 'Ligar', 'Comprar agora', 'Cadastre-se']`.”  
     - Mencionar preferências por objetivo (`agendamentos`: “Enviar mensagem”/“Ligar”; `leads`: “Cadastre-se”/“Saiba mais”; etc.).
2. **Estado inicial enriquecido** (`app/server.py` – `/run_preflight`, antes do `return PreflightResponse(...)`)  
   - Adicionar `initial_state["cta_instagram_choices"] = list(CTA_INSTAGRAM_CHOICES)`.  
   - Adicionar `initial_state["cta_by_objective"] = CTA_BY_OBJECTIVE`.  
   - Calcular `recommended_cta` com base no objetivo (`CTA_BY_OBJECTIVE.get(obj, ("Saiba mais",))[0]`).  
   - Registrar log de debug para monitorar recomendações.
3. **Prompts dependentes do state**  
   - Conferir se `context_synthesizer` e `code_generator` já se referem à lista; se não, atualizar instruções para mencionar `cta_instagram_choices` e `recommended_cta` quando disponíveis.

### P2 – Documentação/Specs (Opcional)
1. **`format_specifications.py`**  
   - Incluir campo opcional `"cta": {"allowed": list(CTA_INSTAGRAM_CHOICES), "preferred": [...], "notes": "Case-sensitive"}` em cada formato.  
   - Futuro: usar esse campo em UI/validação adicional.

## 4. Verificações Pós-Implementação
- Rodar `make dev` e executar `/run_preflight` com `STORYBRAND_GATE_DEBUG=true`.  
- Confirmar nos logs:  
  - Mensagens “CTA normalizado: 'Agendar Avaliação' → 'Enviar mensagem'”.  
  - `deterministic_final_validation.grade == "pass"`.  
  - `persist_final_delivery` não pulado; `artifacts/ads_final/` atualizado.  
- Se `PERSIST_STORYBRAND_SECTIONS=true`, verificar `meta.json` com `storybrand_sections_present=True`.  
- Executar suíte relevante: `uv run pytest tests/unit/agents/test_storybrand_fallback.py tests/unit/callbacks/test_persist_final_delivery.py tests/integration/pipeline/test_deterministic_flow.py`.

## 5. Riscos e Considerações
- Garantir que `_normalize_cta` não introduza dependência circular (imports).  
- Evitar logs em excesso (usar `info` para normalização esperada e `warning` para quedas no fallback).  
- Caso outros enums falhem futuramente (ex.: `aspect_ratio`, `formato`), aplicar a mesma abordagem: normalizar no fallback usando specs oficiais.

## 6. Entregáveis
1. Código ajustado (fallback + prompts + state).  
2. Testes unitários e integração cobrindo o cenário.  
3. Logs de verificação anexados ou descritos na resposta.  
4. Atualização opcional de documentação (README/playbook) mencionando que o fallback agora respeita CTAs oficiais.
