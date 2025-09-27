# Checklist — Correção das Inconsistências do Plano StoryBrand Fallback v2

> Convenção: `[ ]` pendente · `[>]` em andamento · `[x]` concluído
> Este checklist deve ser marcado em paralelo ao `plano_correcao_inconsistencias_do_aprimoramento.md`.

## 3. StoryBrandQualityGate
- [ ] 3.2 Ajustar `storybrand_gate_metrics` ao contrato
    - Editar o método `_run_async_impl` da classe `StoryBrandQualityGate` para que `metrics` contenha apenas `score_obtained`, `score_threshold`, `decision_path`, `timestamp_utc`, `is_forced_fallback` e `debug_flag_active` antes de ser atribuído a `state['storybrand_gate_metrics']`.
    - Remover ou mover para outro registro as chaves adicionais (`force_flag_active`, `fallback_enabled`, `block_reason`). Se forem mantidas, salvar em uma chave separada (ex.: `state['storybrand_gate_debug']`).
    - Manter o log estruturado (`logger.info`) com as chaves úteis, mesmo que algumas não estejam mais em `storybrand_gate_metrics`.

## 4. Fallback StoryBrand Pipeline
- [ ] 4.3 Completar lógica do `fallback_input_collector`
    - Dentro de `fallback_input_collector_callback`, quando `sexo_cliente_alvo` permanecer inválido, analisar `state['landing_page_context']` (pronomes, depoimentos) para tentar inferir o gênero.
    - Caso continue indefinido, registrar no audit trail um evento de erro com detalhes sobre os campos ausentes e interromper a execução levantando exceção com `EventActions(escalate=True)`.
    - Documentar no estado (ex.: em `storybrand_audit_trail`) quais campos foram enriquecidos pelo coletor para facilitar auditoria.

## 5. Configuração das Seções
- [ ] 5.1/5.2 Expandir `StoryBrandSectionConfig` e mapeamento de prompts
    - Adicionar aos campos da dataclass: `display_name`, `writer_prompt_path`, `review_prompt_paths: dict[str, str]`, `corrector_prompt_path` (e outros que façam sentido, como `narrative_goal`).
    - Atualizar `build_storybrand_section_configs()` para preencher os novos campos apontando para arquivos sob `prompts/storybrand_fallback/`.
    - Modificar `StoryBrandSectionRunner` para usar esses caminhos diretamente ao montar `LlmAgent`s, eliminando o uso de `section.prompt_name`.

## 6. Loop de Revisão Compartilhado
- [ ] 6.1/6.2 Reintroduzir `LoopAgent` no fluxo de revisão
    - Criar um `LoopAgent` (ex.: `section_review_loop`) configurado com os subagentes `section_reviewer`, `approval_checker` (EscalationChecker) e `section_corrector`.
    - Instanciar esses subagentes utilizando os caminhos de prompt vindos de `StoryBrandSectionConfig`.
    - Dentro de `StoryBrandSectionRunner._run_section`, substituir o laço manual por uma chamada a esse `LoopAgent`, garantindo que os estágios `reviewer`, `checker` e `corrector` apareçam na trilha de auditoria.

## 11. Logs e Observabilidade
- [ ] 11.1 Emitir logs estruturados no fallback
    - Adicionar chamadas de logging (`logger.info('storybrand_fallback_section', extra={...})`) ao iniciar cada seção, após revisão e ao finalizar a compilação.
    - Padronizar as chaves (`section_key`, `iteration`, `status`, etc.) de forma semelhante ao que já é logado pelo gate.

- [ ] 11.2 Completar o contrato de `storybrand_audit_trail`
    - Registrar um evento `preparer` antes de montar o contexto da seção, `checker` após a decisão do approval checker e `compiler` na entrada/saída do compilador.
    - Sempre que possível, preencher `duration_ms` para estágios concluídos (ex.: usando timestamps antes/depois da execução).

## 12. Testes
- [ ] 12.1 Cobrir score ausente no gate
    - Adicionar um novo teste (ex.: `test_gate_forces_fallback_when_score_missing`) que inicializa o estado sem score, executa o gate e verifica se o fallback é chamado e `is_forced_fallback` fica `True`.

- [ ] 12.2 Testar configuração e runner de seções
    - Atualizar `test_storybrand_sections.py` para validar os novos campos (display name, caminhos de prompt).
    - Criar testes com mocks para `StoryBrandSectionRunner`, validando que os prompts corretos são utilizados e que o limite de iterações gera erro quando excedido.

- [ ] 12.4 Adicionar teste de integração do fallback
    - Criar um teste de integração (ex.: `tests/integration/test_storybrand_fallback_pipeline.py`) que configure o estado inicial, habilite as flags e use fixtures/mocks para `LlmAgent`, assegurando a geração das 16 seções e da compilação.
    - Incluir o cenário `force_storybrand_fallback=True` para verificar métricas e logs.

## 13. Documentação
- [ ] 13.3 Atualizar documentação sobre campos obrigatórios
    - Editar a seção de inputs no README para refletir que os campos são obrigatórios com as flags ativas e que `sexo_cliente_alvo` deve ser `masculino` ou `feminino`.
    - Revisar `docs/storybrand_fallback.md` e quaisquer outros documentos para alinhar a terminologia.

## 16. QA Final
- [ ] 16.1 Registrar execução de QA
    - Executar `make lint` e `make test` após aplicar as correções e anexar os resultados (logs ou referência) ao PR ou a um diretório `artifacts/`.

- [ ] 16.2 Anexar evidências gráficas/logs ao PR
    - Gerar logs e/ou screenshots demonstrando o fallback funcionando (por exemplo, saída de logs do gate + pipeline) e anexá-los ao PR ou ao repositório.
