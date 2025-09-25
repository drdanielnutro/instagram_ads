# Checklist — Implementação do Plano StoryBrand Fallback v2

> Convenção: `[ ]` pendente · `[>]` em andamento · `[x]` concluído
> Referência principal: `aprimoramento_plano_storybrand_v2.md`

## 1. Objetivos e Contratos
- [ ] Revisar métricas e logs existentes para garantir que decisões do `StoryBrandQualityGate` sigam o contrato da Seção 16.1.
- [ ] Definir/confirmar limiar `config.min_storybrand_completeness` e variáveis de ambiente associadas.

## 2. Integração no `app/agent.py`
- [ ] Criar/posicionar `StoryBrandQualityGate` após `landing_page_analyzer` reaproveitando `PlanningOrRunSynth`.
- [ ] Condicionar o gate à flag `ENABLE_STORYBRAND_FALLBACK` em `config`.

## 3. StoryBrandQualityGate
- [ ] Implementar agente (`app/agents/storybrand_gate.py` ou módulo equivalente) herdando de `BaseAgent`.
- [ ] Popular `state['storybrand_gate_metrics']` conforme contrato (score, threshold, path, timestamp, flags).
- [ ] Registrar fallback forçado quando score ausente/inválido.

## 4. Fallback StoryBrand Pipeline
- [ ] Criar `app/agents/storybrand_fallback.py` como `SequentialAgent` com subagentes listados (initializer, collector, section runner, compiler, reporter).
- [ ] Implementar `fallback_input_initializer` para garantir chaves presentes.
- [ ] Implementar `fallback_input_collector` com prompts em `prompts/storybrand_fallback/collector.txt`.
- [ ] Implementar `section_pipeline_runner` iterando sobre as 16 seções.
- [ ] Implementar `fallback_quality_reporter` (opcional) salvando `storybrand_recovery_report`.

## 5. Configuração das Seções
- [ ] Criar `StoryBrandSectionConfig` (dataclass/Pydantic) em `app/agents/storybrand_sections.py`.
- [ ] Mapear as 16 seções com prompts (`writer`, `reviewer`, `corrector`) e `narrative_goal`.

## 6. Loop de Revisão Compartilhado
- [ ] Implementar `section_review_loop` reaproveitando `LoopAgent` existente.
- [ ] Configurar `section_reviewer`, `approval_checker`, `section_corrector` conforme plano.
- [ ] Respeitar `config.fallback_storybrand_max_iterations` (Seção 10).

## 7. Prompts
- [ ] Criar diretório `prompts/storybrand_fallback/` com arquivos listados na Seção 7.
- [ ] Implementar `PromptLoader` em `app/utils/prompt_loader.py` com caching, encoding UTF-8 e renderização `{variavel}` (Seção 16.4).
- [ ] Adicionar tratamento fail-fast para prompts ausentes.

## 8. Coleta de Inputs Essenciais
- [x] Atualizar frontend para coletar obrigatoriamente `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo` quando `VITE_ENABLE_NEW_FIELDS=true`.
- [x] Atualizar `helpers/user_extract_data.py` para validar campos obrigatórios e rejeitar `neutro`.
- [ ] Garantir mensagens de erro propagadas ao `/run_preflight` e UI.

## 9. Contrato Pós-Fallback
- [ ] Garantir que `fallback_storybrand_compiler` popula `storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context` e sincroniza completeness (já implementado, validar).
- [ ] Atualizar `landing_page_context['storybrand_completeness'] = 1.0` ao final do fallback.

## 10. Configuração (`app/config.py`)
- [ ] Adicionar campos (`fallback_storybrand_max_iterations`, `fallback_storybrand_model`, `storybrand_gate_debug`, `ENABLE_STORYBRAND_FALLBACK`).
- [ ] Documentar variáveis de ambiente correspondentes.

## 11. Logs e Observabilidade
- [ ] Implementar logging estruturado do gate/fallback conforme Seção 11.
- [ ] Popular `state['storybrand_audit_trail']` seguindo contrato da Seção 16.2.

## 12. Testes
- [ ] Criar testes unitários para o gate (score acima/abaixo/ausente).
- [ ] Criar testes para `StoryBrandSectionConfig`/runner.
- [ ] Testar `fallback_storybrand_compiler` com entradas representativas.
- [ ] Criar testes de integração do fallback pipeline mockando LlmAgents.
- [ ] Revalidar caminho feliz para evitar regressões.

## 13. Documentação
- [ ] Atualizar `AGENTS.md` com gate e fallback.
- [ ] Criar `docs/storybrand_fallback.md` detalhando arquitetura e prompts.
- [ ] Atualizar README com novos campos obrigatórios e exemplos de payload/API.

## 14. Feature Flag & Rollout
- [ ] Garantir toggles (`ENABLE_STORYBRAND_FALLBACK`, `VITE_ENABLE_NEW_FIELDS`) documentados e controlados.
- [ ] Planejar rollout backend → frontend e estratégia de rollback.

## 15. Auditoria & Métricas Futuras
- [ ] Definir monitoramento para `storybrand_gate_metrics` (dashboards/alertas).
- [ ] Avaliar cache de resultados de fallback conforme Seção 15.
- [ ] Planejar auditoria via `storybrand_audit_trail`.

## 16. QA Final
- [ ] Executar `make lint`, `make test` e testes manuais completos.
- [ ] Capturar evidências (logs, screenshots) para PR.
- [ ] Revisar checklist e marcar itens concluídos antes de merge.
