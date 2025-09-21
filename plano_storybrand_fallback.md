# Plano Expandido — Branching com Fallback de Alta Fidelidade

## 1. Objetivos e Princípios
- **Garantir resiliência:** ativar reconstrução completa do StoryBrand quando a análise da landing page não atingir o limiar de qualidade.
- **Preservar eficiência:** manter o caminho atual (landing → planning → execution) quando `storybrand_completeness` for satisfatório.
- **Contratos claros:** ambos os caminhos devem popular exatamente as mesmas chaves em `session.state`, permitindo retomada transparente.
- **Observabilidade:** registrar decisões do gate, iterações do fallback e resultados para tuning futuro.

## 2. Pontos de Integração no `agent.py`
- Inserir o `StoryBrandQualityGate` logo após `landing_page_analyzer` em `complete_pipeline`.
- Passar `planning_pipeline` e o novo `fallback_storybrand_pipeline` como dependências do gate.
- Garantir que `StoryBrandQualityGate` respeite o valor `config.min_storybrand_completeness` (com override via env).

## 3. StoryBrandQualityGate (BaseAgent Customizado)
- **Arquivo sugerido:** `app/agents/storybrand_gate.py`.
- **Método `_run_async_impl`:**
  - Ler `ctx.session.state['storybrand_completeness']` e validar presença de `storybrand_analysis`.
  - Determinar caminho (`"happy_path"` ou `"fallback"`) e gravar em `state['storybrand_path']` e `state['storybrand_gate_metrics']` (com score, limiar, timestamp).
  - Invocar `planning_pipeline` quando score >= limiar, caso contrário chamar `fallback_storybrand_pipeline`.
  - Registrar logs estruturados (`logger.info`) para auditoria.
- **Fallback forçado:** se o score não existir ou for inválido, acionar pipeline de fallback por segurança.

## 4. Fallback StoryBrand Pipeline (SequentialAgent)
- **Arquivo sugerido:** `app/agents/storybrand_fallback.py`.
- **Sub-agentes principais:**
  1. `fallback_input_initializer` (BaseAgent) — garante chaves vazias e defaults para inputs obrigatórios.
  2. `fallback_input_collector` (LlmAgent) — coleta ou infere `nome_empresa`, `empresa_faz`, `sexo_cliente_alvo`, persona e tom.
  3. `section_pipeline_runner` (BaseAgent) — carrega configuração de seções e dispara blocos reutilizáveis (preparador + escritor + loop de revisão).
  4. `fallback_storybrand_compiler` (LlmAgent ou BaseAgent) — monta saída final e respeita o contrato de estado.
  5. `fallback_quality_reporter` (BaseAgent, opcional) — resume iterações e coloca checklist em `state['storybrand_recovery']`.

## 5. Configuração das Seções
- Criar dataclass `StoryBrandSectionConfig` (`app/agents/storybrand_sections.py`) com campos:
  - `key`, `display_name`, `writer_prompt_path`, `review_prompt_paths`, `corrector_prompt_path`, `context_keys_required`.
- Definir lista ordenada das seções: `character`, `problem`, `guide`, `plan`, `action`, `failure`, `success`, `identity`.
- `section_pipeline_runner` deve percorrer a lista e para cada item:
  - Executar `context_preparer` (BaseAgent) para povar `state['chave_secao_atual']`, `state['nome_secao_atual']`, `state['contexto_anterior']`.
  - Invocar `section_writer` (LlmAgent) com prompt específico.
  - Rodar `section_review_loop` (LoopAgent compartilhado) até aprovação ou atingir `config.fallback_storybrand_max_iterations`.

## 6. Loop de Revisão Compartilhado
- **Componentes do Loop:**
  - `section_reviewer` (LlmAgent) — escolhe prompt por gênero (`masculino`, `feminino`, `neutro`) e produz JSON `{ "grade": "pass|fail", "comment": "..." }`.
  - `approval_checker` (BaseAgent) — dispara `actions.escalate=True` quando `grade == "pass"`.
  - `section_corrector` (LlmAgent) — usa feedback para sobrescrever `state[state['chave_secao_atual']]`.
- **Parâmetros:**
  - Iterações máximas via `config.fallback_storybrand_max_iterations` (default 3, override via `FALLBACK_STORYBRAND_MAX_ITERATIONS`).
  - Logar cada iteração com seção, status e comentário do revisor.

## 7. Prompts Necessários (novo diretório sugerido `prompts/storybrand_fallback/`)
- `collector.txt` — instruções para levantar dados faltantes (formato JSON, confirmação explícita).
- `section_<nome>.txt` — oito prompts de escrita (personagem, problema, guia, plano, ação, fracasso, sucesso, identidade) com diretrizes de conteúdo e tom.
- `review_masculino.txt`, `review_feminino.txt`, `review_neutro.txt` — checklists detalhados para avaliar clareza, coerência com inputs, tom, CTA etc.
- `corrector.txt` — instruções para reescritura orientada pelo comentário.
- `compiler.txt` (se usar LLM) — transformar seções aprovadas em estrutura compatível com `StoryBrandAnalysis`; alternativa: compilar via BaseAgent sem prompt.
- `quality_report.txt` (opcional) — gerar resumo final do fallback.

## 8. Novos Campos no Input Processor
- Atualizar instrução do `input_processor` (em `app/agent.py`) para reconhecer:
  - Linhas ou tags para `sexo_cliente_alvo`, `nome_empresa`, `empresa_faz`.
- Ajustar `unpack_extracted_input_callback` para salvar esses campos no estado.
- Documentar formato esperado no README/backend (`frontend/README.md` se relevante) e em exemplos de entrada.

## 9. Contrato de Estado Pós-Fallback
- `fallback_storybrand_compiler` deve garantir:
  - `state['storybrand_analysis']` — objeto compatível com `StoryBrandAnalysis` (usar instância Pydantic + `.model_dump()`).
  - `state['storybrand_summary']` — string gerada via `to_summary()` ou prompt dedicado.
  - `state['storybrand_ad_context']` — dicionário com campos exigidos (`persona`, `dores_principais`, etc.).
  - `state['storybrand_completeness']` — valor >= limiar (usar 1.0 por padrão) para impedir loops adicionais.
  - `state['storybrand_recovery']` — metadados `{ "status": "success", "sections": [...], "iterations": {...} }`.

## 10. Ajustes em `app/config.py`
- Adicionar parâmetros:
  - `fallback_storybrand_max_iterations: int = 3`.
  - `fallback_storybrand_model: str | None = None` (usar modelo mais potente quando definido).
  - `storybrand_gate_debug: bool = False`.
- Permitir overrides via variáveis de ambiente (`FALLBACK_STORYBRAND_MODEL`, `STORYBRAND_GATE_DEBUG`, etc.).

## 11. Logs, Métricas e Observabilidade
- Gate: logar decisão (`score`, `threshold`, `path`) e salvar em `state['storybrand_gate_metrics']`.
- Fallback: logar início/fim de cada seção, número de iterações, feedbacks relevantes.
- Persistir em `state['storybrand_audit_trail']` uma lista ordenada de etapas para depuração.
- Considerar hook para enviar métricas a sistemas externos (futuro).

## 12. Testes e Validação
- **Unitários:**
  - `StoryBrandQualityGate` com scores acima/abaixo do limiar (mock pipelines).
  - `StoryBrandSectionConfig` e carregamento das seções.
  - Funções utilitárias de compilação (`StoryBrandAnalysis` instantiation).
- **Integração:**
  - Simular execução completa do fallback com mocks de LlmAgents (verificar contrato de estado).
  - Verificar caminho feliz permanece funcional.
- **QA manual:**
  - Rodar `make dev-backend-all`, forçar `storybrand_completeness=0` e observar logs/resultados.
  - Testar diferentes inputs (`sexo_cliente_alvo` ausente, empresa com nome incomum, etc.).

## 13. Documentação
- Atualizar `AGENTS.md` explicando novo gate e pipelines.
- Criar/atualizar `docs/storybrand_fallback.md` (ou revisar `recuperacao_storybrand.md`) com fluxo real.
- Inserir novo checklist no repositório (ex.: `checklists/storybrand_fallback.md`) para controle de implementação.
- Registrar novos campos de entrada em README e exemplos.

## 14. Feature Flag (Opcional)
- introduzir `ENABLE_STORYBRAND_FALLBACK` (default `true`) para emergências.
- Condicionar registro do gate/pipeline à flag em `agent.py`.

## 15. Etapas Futuras (Opcional)
- Monitorar métricas do gate para recalibrar `min_storybrand_completeness`.
- Avaliar cache/armazenamento de StoryBrand reconstruídos para reutilização.
- Considerar interface de auditoria para revisar `storybrand_audit_trail`.
