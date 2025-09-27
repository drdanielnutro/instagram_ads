# Checklist — Implementação do Plano StoryBrand Fallback v2

> Convenção: `[ ]` pendente · `[>]` em andamento · `[x]` concluído
> Referência principal: `aprimoramento_plano_storybrand_v2.md`

## 1. Objetivos e Contratos
- [x] Revisar métricas e logs existentes para garantir que decisões do `StoryBrandQualityGate` sigam o contrato da Seção 16.1.
- [x] Definir/confirmar limiar `config.min_storybrand_completeness` e variáveis de ambiente associadas.

## 2. Integração no `app/agent.py`
- [x] Substituir o `PlanningOrRunSynth` da lista do `complete_pipeline` por `StoryBrandQualityGate`, repassando o planner existente via construtor.
- [x] Garantir que o gate permaneça no pipeline mesmo com `config.enable_storybrand_fallback=False`, realizando short-circuit e registrando métricas quando as flags estiverem desligadas.

## 3. StoryBrandQualityGate
- [x] Implementar agente (`app/agents/storybrand_gate.py` ou módulo equivalente) herdando de `BaseAgent`.
- [x] Popular `state['storybrand_gate_metrics']` conforme contrato (score, threshold, path, timestamp, flags).
- [x] Registrar fallback forçado quando score ausente/inválido.

## 4. Fallback StoryBrand Pipeline
- [x] Criar `app/agents/storybrand_fallback.py` como `SequentialAgent` com subagentes listados (initializer, collector, section runner, compiler, reporter).
- [x] Implementar `fallback_input_initializer` para garantir chaves presentes.
- [x] Implementar `fallback_input_collector` com prompts em `prompts/storybrand_fallback/collector.txt`.
- [x] Implementar `section_pipeline_runner` iterando sobre as 16 seções.
- [x] Implementar `fallback_quality_reporter` (opcional) salvando `storybrand_recovery_report`.

## 5. Configuração das Seções
- [x] Criar `StoryBrandSectionConfig` (dataclass/Pydantic) em `app/agents/storybrand_sections.py`.
- [x] Mapear as 16 seções com prompts (`writer`, `reviewer`, `corrector`) e `narrative_goal`.

## 6. Loop de Revisão Compartilhado
- [x] Implementar `section_review_loop` reaproveitando `LoopAgent` existente.
- [x] Configurar `section_reviewer`, `approval_checker`, `section_corrector` conforme plano.
- [x] Respeitar `config.fallback_storybrand_max_iterations` (Seção 10).

## 7. Prompts
- [x] Criar diretório `prompts/storybrand_fallback/` com arquivos listados na Seção 7.
- [x] Implementar `PromptLoader` em `app/utils/prompt_loader.py` com caching, encoding UTF-8 e renderização `{variavel}` (Seção 16.4).
- [x] Adicionar tratamento fail-fast para prompts ausentes.

## 8. Coleta de Inputs Essenciais
- [x] Atualizar frontend para coletar obrigatoriamente `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo` quando `VITE_ENABLE_NEW_FIELDS=true`.
- [x] Atualizar `helpers/user_extract_data.py` para validar campos obrigatórios e rejeitar `neutro`.
- [x] Garantir mensagens de erro propagadas ao `/run_preflight` e UI.

## 9. Contrato Pós-Fallback
- [x] Garantir que `fallback_storybrand_compiler` popula `storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context` e sincroniza completeness (já implementado, validar).
- [x] Atualizar `landing_page_context['storybrand_completeness'] = 1.0` ao final do fallback.

## 10. Configuração (`app/config.py`)
- [x] Adicionar campos (`fallback_storybrand_max_iterations`, `fallback_storybrand_model`, `storybrand_gate_debug`, `config.enable_storybrand_fallback`).
- [x] Documentar variáveis de ambiente correspondentes.

## 11. Logs e Observabilidade
- [x] Implementar logging estruturado do gate/fallback conforme Seção 11.
- [x] Popular `state['storybrand_audit_trail']` seguindo contrato da Seção 16.2.

## 12. Testes
- [x] Criar testes unitários para o gate (score acima/abaixo/ausente).
- [x] Criar testes para `StoryBrandSectionConfig`/runner.
- [x] Testar `fallback_storybrand_compiler` com entradas representativas.
- [x] Criar testes de integração do fallback pipeline mockando LlmAgents.
- [x] Revalidar caminho feliz para evitar regressões.

## 13. Documentação
- [x] Atualizar `AGENTS.md` com gate e fallback.
- [x] Criar `docs/storybrand_fallback.md` detalhando arquitetura e prompts.
- [x] Atualizar README com novos campos obrigatórios e exemplos de payload/API.

## 14. Feature Flag & Rollout
- [x] Garantir toggles (`config.enable_storybrand_fallback` / `ENABLE_STORYBRAND_FALLBACK`, `VITE_ENABLE_NEW_FIELDS`) documentados e controlados.
- [x] Planejar rollout backend → frontend e estratégia de rollback.

## 15. Auditoria & Métricas Futuras
- [x] Definir monitoramento para `storybrand_gate_metrics` (dashboards/alertas).
- [x] Avaliar cache de resultados de fallback conforme Seção 15.
- [x] Planejar auditoria via `storybrand_audit_trail`.

## 16. QA Final
- [x] Executar `make lint`, `make test` e testes manuais completos.
- [x] Capturar evidências (logs, screenshots) para PR.
- [x] Revisar checklist e marcar itens concluídos antes de merge.
