# Explicação das correções aplicadas ao plano de validação determinística

## 1. Reversão do código experimental
- **O que foi feito:** Restaurei `app/agent.py`, `app/config.py` e `app/agents/storybrand_gate.py` para o estado do commit de referência (`e58b4c1`). Também removi `tests/unit/test_deterministic_validation.py`, arquivo introduzido apenas para a implementação fictícia anterior.
- **Motivo:** As alterações da última iteração inseriram uma versão completa do pipeline que não existe no repositório, quebrando o alinhamento com o ADK real e adicionando dependências inexistentes. Reverter garante que o código continue funcional enquanto o time analisa e prioriza o plano atualizado.

## 2. Atualizações estruturais no `plano_validacao_json.md`
### 2.1 Metadados de StoryBrand e fallback
- **O que foi feito:** Incluí instruções para criar `storybrand_fallback_meta` e o flag `landing_page_analysis_failed`, substituindo verificações em chaves que não existem (`storybrand_audit_trail.fallback_triggered`, `landing_page_context.error`).
- **Motivo:** O plano agora reflete os dados realmente disponíveis no estado e orienta como produzir metadados formais para justificar relaxamentos de schema.

### 2.2 Enriquecimento de snippets aprovados
- **O que foi feito:** Documentei a necessidade de ampliar o callback que popula `approved_code_snippets`, gerando `snippet_id`, `status` e `approved_at`, além de mapear os VISUAL_DRAFT aprovados em `approved_visual_drafts`.
- **Motivo:** Os guards previstos pelo plano dependem de atributos que ainda não existiam. Ao orientar explicitamente o enriquecimento, evitamos suposições e garantimos compatibilidade com consumidores atuais.

### 2.3 Flag e rollback determinístico
- **O que foi feito:** Especificamos que `enable_deterministic_final_validation` deve ser avaliada apenas no boot, com logging estruturado, e adicionamos o helper `reset_deterministic_validation_state` para rollback limpo.
- **Motivo:** A flag precisa de regras claras para alternância e limpeza de estado, reduzindo o risco de resíduos quando for desativada após testes em produção.

### 2.4 Pipeline e agentes auxiliares
- **O que foi feito:** Reescrevi a seção de reorquestração para usar uma fábrica `build_execution_pipeline(flag_enabled: bool)`, introduzindo `RunIfPassed` e detalhando como reinstalar callbacks legados quando a flag estiver desligada.
- **Motivo:** A versão anterior assumia mutação de agentes já instanciados. O novo texto descreve uma implementação compatível com o ADK e protege contra efeitos colaterais em runtime.

### 2.5 Observabilidade e auditoria
- **O que foi feito:** Padronizei os campos que devem ser registrados em `append_delivery_audit_event`, incluindo `fallback_engaged` e `landing_page_analysis_failed`.
- **Motivo:** Os indicadores ajudam o time de operações a entender por que cada variação foi bloqueada ou flexibilizada, facilitando dashboards e alertas.

### 2.6 Estratégia de testes
- **O que foi feito:** Ampliei os cenários de unitários/integrados para cobrir normalização do assembler, alternância da flag, uso de `RunIfPassed` e limpeza de estado durante rollback.
- **Motivo:** Com a validação determinística introduzindo novos caminhos, os testes precisam observar ambos os pipelines e o comportamento do helper de reset para evitar regressões silenciosas.

## 3. Próximos passos
- Validar o plano atualizado com as equipes de pipeline e observabilidade.
- Priorizar a implementação incremental seguindo as fases descritas, reaproveitando os insights da análise crítica (`analise_plano_validacao_json_creative_spark.md`).
