# Revisão das tarefas do checklist StoryBrand Fallback v2

A tabela abaixo registra o status de cada atividade marcada como concluída em `checklist.md`, confrontando o plano `aprimoramento_plano_storybrand_v2.md` com a implementação presente no repositório.

## 1. Objetivos e Contratos
### 1.1 Revisar métricas e logs do gate
- **Status:** Correto
- **Justificativa:** `StoryBrandQualityGate` salva as decisões no estado com os campos previstos (`score_obtained`, `score_threshold`, `decision_path`, `timestamp_utc`, `is_forced_fallback`, `debug_flag_active`) e realiza o `logger.info` estruturado conforme o contrato da Seção 16.1.【F:app/agents/storybrand_gate.py†L48-L105】【F:aprimoramento_plano_storybrand_v2.md†L162-L181】

### 1.2 Confirmar limiar `config.min_storybrand_completeness`
- **Status:** Correto
- **Justificativa:** O valor padrão e o override via `STORYBRAND_MIN_COMPLETENESS` estão definidos em `app/config.py`, garantindo que o gate consulte diretamente `config.min_storybrand_completeness` conforme solicitado.【F:app/config.py†L34-L126】【F:aprimoramento_plano_storybrand_v2.md†L114-L118】

## 2. Integração no `app/agent.py`
### 2.1 Substituir `PlanningOrRunSynth` pelo gate no pipeline
- **Status:** Correto
- **Justificativa:** O `complete_pipeline` agora inclui `storybrand_quality_gate`, que recebe o planner existente via construtor, atendendo ao plano.【F:app/agent.py†L1158-L1241】

### 2.2 Manter o gate no pipeline mesmo com fallback desativado
- **Status:** Correto
- **Justificativa:** A implementação calcula `fallback_enabled` com base nas flags, mas sempre executa o planner ao final e registra métricas, preservando o gate mesmo quando o fallback está desligado.【F:app/agents/storybrand_gate.py†L50-L110】

## 3. StoryBrandQualityGate
### 3.1 Implementar agente herdando `BaseAgent`
- **Status:** Correto
- **Justificativa:** `StoryBrandQualityGate` herda de `BaseAgent` e aceita os pipelines esperados no construtor.【F:app/agents/storybrand_gate.py†L38-L44】

### 3.2 Popular `state['storybrand_gate_metrics']` conforme contrato
- **Status:** Incorreto
- **Justificativa:** Embora os campos obrigatórios estejam presentes, o dicionário gravado inclui chaves extras (`force_flag_active`, `fallback_enabled`, `block_reason`) que não fazem parte do formato definido na Seção 16.1, violando o contrato estrito descrito no plano.【F:app/agents/storybrand_gate.py†L77-L88】【F:aprimoramento_plano_storybrand_v2.md†L162-L181】

### 3.3 Registrar fallback forçado quando score ausente/inválido
- **Status:** Correto
- **Justificativa:** Quando não há score válido, o gate ativa `should_run_fallback` e marca `is_forced_fallback=True`, atendendo à salvaguarda especificada.【F:app/agents/storybrand_gate.py†L55-L83】【F:aprimoramento_plano_storybrand_v2.md†L45-L47】

## 4. Fallback StoryBrand Pipeline
### 4.1 Criar `fallback_storybrand_pipeline` sequencial
- **Status:** Correto
- **Justificativa:** O arquivo `app/agents/storybrand_fallback.py` define o `SequentialAgent` com os subagentes requeridos.【F:app/agents/storybrand_fallback.py†L373-L383】

### 4.2 Implementar `fallback_input_initializer`
- **Status:** Correto
- **Justificativa:** O agente inicializa `storybrand_audit_trail` e garante que as chaves essenciais existam antes do fallback.【F:app/agents/storybrand_fallback.py†L45-L62】

### 4.3 Implementar `fallback_input_collector` conforme plano
- **Status:** Incorreto
- **Justificativa:** O coletor apenas valida valores existentes ou retornados pelo LLM; ele não consulta `landing_page_context` quando faltam dados nem realiza a “última tentativa” de inferência para `sexo_cliente_alvo`, tampouco registra um evento de erro com `EventActions` antes de abortar, contrariando as orientações da Seção 4 e 16.3.【F:app/agents/storybrand_fallback.py†L102-L156】【F:aprimoramento_plano_storybrand_v2.md†L45-L48】【F:aprimoramento_plano_storybrand_v2.md†L205-L213】

### 4.4 Implementar `section_pipeline_runner` iterando pelas 16 seções
- **Status:** Correto
- **Justificativa:** O runner percorre a lista de configurações, gera/revisa/corrige cada seção e respeita o limite de iterações.【F:app/agents/storybrand_fallback.py†L172-L338】

### 4.5 Implementar `fallback_quality_reporter`
- **Status:** Correto
- **Justificativa:** O agente agrega as informações de auditoria e grava `storybrand_recovery_report`, conforme item opcional do plano.【F:app/agents/storybrand_fallback.py†L341-L370】

## 5. Configuração das Seções
### 5.1 Criar `StoryBrandSectionConfig` com todos os campos previstos
- **Status:** Incorreto
- **Justificativa:** A dataclass inclui apenas `state_key`, `prompt_name` e `narrative_goal`; os campos exigidos (`display_name`, `writer_prompt_path`, `review_prompt_paths`, `corrector_prompt_path`) não foram implementados.【F:app/agents/storybrand_sections.py†L9-L103】【F:aprimoramento_plano_storybrand_v2.md†L62-L70】

### 5.2 Mapear prompts (`writer`, `reviewer`, `corrector`) e `narrative_goal`
- **Status:** Incorreto
- **Justificativa:** Apesar de listar as 16 seções e seus prompts de escrita, não há mapeamento por seção dos prompts de revisão e correção, contrariando o plano.【F:app/agents/storybrand_sections.py†L18-L103】【F:aprimoramento_plano_storybrand_v2.md†L62-L76】

## 6. Loop de Revisão Compartilhado
### 6.1 Implementar `section_review_loop` reutilizando `LoopAgent`
- **Status:** Incorreto
- **Justificativa:** O loop de revisão foi codificado manualmente dentro de `_run_section`; não existe um `LoopAgent` compartilhado que encapsule reviewer/checker/corrector como previsto.【F:app/agents/storybrand_fallback.py†L192-L338】【F:aprimoramento_plano_storybrand_v2.md†L78-L85】

### 6.2 Configurar `section_reviewer`, `approval_checker`, `section_corrector`
- **Status:** Incorreto
- **Justificativa:** Os agentes são instanciados inline a cada iteração e não há um `approval_checker` dedicado que sinalize escalonamento, descumprindo a arquitetura especificada.【F:app/agents/storybrand_fallback.py†L236-L326】【F:aprimoramento_plano_storybrand_v2.md†L78-L85】

### 6.3 Respeitar `config.fallback_storybrand_max_iterations`
- **Status:** Correto
- **Justificativa:** O limite de iterações é lido de `config` e aplicado no laço de revisão das seções.【F:app/agents/storybrand_fallback.py†L31-L33】【F:app/agents/storybrand_fallback.py†L192-L338】

## 7. Prompts
### 7.1 Criar diretório `prompts/storybrand_fallback/` com arquivos listados
- **Status:** Correto
- **Justificativa:** O diretório contém os arquivos `collector`, os 16 prompts de seção, revisores por gênero, `corrector` e `compiler`, conforme listado no plano.【b64700†L1-L2】【F:aprimoramento_plano_storybrand_v2.md†L87-L95】

### 7.2 Implementar `PromptLoader` com cache e renderização `{variavel}`
- **Status:** Correto
- **Justificativa:** O utilitário carrega todos os `.txt` na inicialização, armazena em cache e oferece `render` com placeholders, utilizando UTF-8.【F:app/utils/prompt_loader.py†L25-L60】

### 7.3 Adicionar fail-fast para prompts ausentes
- **Status:** Correto
- **Justificativa:** A construção lança `PromptNotFoundError` caso o diretório não exista ou algum arquivo requerido não seja encontrado, atendendo à exigência de fail-fast.【F:app/utils/prompt_loader.py†L28-L45】

## 8. Coleta de Inputs Essenciais
### 8.1 Frontend obrigatório com `VITE_ENABLE_NEW_FIELDS=true`
- **Status:** Correto
- **Justificativa:** Os passos adicionais (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) e suas validações só são incluídos quando a flag `VITE_ENABLE_NEW_FIELDS` está ativa, tornando os campos obrigatórios na UI.【F:frontend/src/constants/wizard.constants.ts†L41-L273】

### 8.2 Validar e rejeitar `neutro` em `helpers/user_extract_data.py`
- **Status:** Correto
- **Justificativa:** O preflight exige valores para os novos campos, normaliza o gênero e rejeita entradas que não resultem em `masculino` ou `feminino`.【F:helpers/user_extract_data.py†L520-L588】

### 8.3 Propagar erros para `/run_preflight` e UI
- **Status:** Correto
- **Justificativa:** O endpoint retorna 422 com detalhes estruturados e o frontend apresenta a mensagem e os erros ao usuário quando a validação falha.【F:app/server.py†L130-L209】【F:frontend/src/App.tsx†L180-L203】

## 9. Contrato Pós-Fallback
### 9.1 `fallback_storybrand_compiler` preencher análises e sincronizar score
- **Status:** Correto
- **Justificativa:** O compilador monta o objeto `StoryBrandAnalysis`, gera `storybrand_summary`, `storybrand_ad_context` e força `completeness_score=1.0`, sincronizando também o contexto da landing page.【F:app/agents/fallback_compiler.py†L210-L237】

### 9.2 Atualizar `landing_page_context['storybrand_completeness']`
- **Status:** Correto
- **Justificativa:** Após compilar, o código define explicitamente o score 1.0 no `landing_page_context`, conforme previsto.【F:app/agents/fallback_compiler.py†L227-L231】

## 10. Configuração (`app/config.py`)
### 10.1 Adicionar novos campos de configuração
- **Status:** Correto
- **Justificativa:** `DevelopmentConfiguration` inclui `enable_storybrand_fallback`, `storybrand_gate_debug`, `fallback_storybrand_max_iterations` e `fallback_storybrand_model`, com leitura das variáveis de ambiente correspondentes.【F:app/config.py†L34-L118】

### 10.2 Documentar variáveis de ambiente
- **Status:** Correto
- **Justificativa:** O README lista e explica `ENABLE_STORYBRAND_FALLBACK`, `ENABLE_NEW_INPUT_FIELDS`, `FALLBACK_STORYBRAND_MAX_ITERATIONS`, `FALLBACK_STORYBRAND_MODEL` e `STORYBRAND_GATE_DEBUG`.【F:README.md†L300-L361】

## 11. Logs e Observabilidade
### 11.1 Logging estruturado do gate/fallback
- **Status:** Correto
- **Justificativa:** O gate faz `logger.info` com os campos relevantes e o fallback adiciona eventos detalhados à trilha de auditoria, atendendo à seção 11.【F:app/agents/storybrand_gate.py†L92-L104】【F:app/agents/storybrand_fallback.py†L217-L326】

### 11.2 Preencher `state['storybrand_audit_trail']` conforme contrato
- **Status:** Incorreto
- **Justificativa:** Os eventos gravados usam apenas os estágios `collector`, `writer`, `reviewer` e `corrector`, sempre com `duration_ms=None`. As etapas `preparer`, `checker` e `compiler` previstas na Seção 16.2 não são registradas, e não há medição de duração para estágios concluídos.【F:app/agents/storybrand_fallback.py†L65-L338】【F:aprimoramento_plano_storybrand_v2.md†L183-L201】

## 12. Testes
### 12.1 Testes unitários do gate (score acima/abaixo/ausente)
- **Status:** Incorreto
- **Justificativa:** Há casos para score alto, baixo, force flag e flags desativadas, mas falta um teste cobrindo o cenário de score ausente/inválido exigido pelo plano.【F:tests/unit/agents/test_storybrand_gate.py†L28-L119】【F:aprimoramento_plano_storybrand_v2.md†L124-L126】

### 12.2 Testes para `StoryBrandSectionConfig` e runner
- **Status:** Incorreto
- **Justificativa:** Existe apenas um teste verificando a contagem e unicidade das seções; não há cobertura para o runner nem validação dos campos adicionais solicitados (display name, prompts), deixando a lógica central sem testes.【F:tests/unit/agents/test_storybrand_sections.py†L1-L8】【09c1ae†L1-L1】【F:aprimoramento_plano_storybrand_v2.md†L62-L76】

### 12.3 Testar `fallback_storybrand_compiler`
- **Status:** Correto
- **Justificativa:** O teste assíncrono valida que o compilador popula as chaves esperadas e sincroniza o score para 1.0, conforme o plano.【F:tests/unit/agents/test_storybrand_fallback.py†L53-L84】

### 12.4 Testes de integração do fallback pipeline
- **Status:** Incorreto
- **Justificativa:** Não há testes de integração simulando o `fallback_storybrand_pipeline`; a busca por "fallback" em `tests/integration` não retorna referências, descumprindo o item do plano.【832440†L1-L1】【F:aprimoramento_plano_storybrand_v2.md†L131-L136】

### 12.5 Revalidar caminho feliz
- **Status:** Correto
- **Justificativa:** O teste `test_gate_runs_happy_path_when_score_high` confirma que, com score acima do limiar, o gate segue pelo caminho feliz e não aciona o fallback.【F:tests/unit/agents/test_storybrand_gate.py†L28-L49】

## 13. Documentação
### 13.1 Atualizar `AGENTS.md` com gate e fallback
- **Status:** Correto
- **Justificativa:** A seção “StoryBrand Fallback Pipeline” descreve o gate, o pipeline de fallback, os prompts e os novos parâmetros de configuração.【F:AGENTS.md†L44-L50】

### 13.2 Criar `docs/storybrand_fallback.md`
- **Status:** Correto
- **Justificativa:** O documento existe e detalha arquitetura, prompts, métricas e próximos passos do fallback.【F:docs/storybrand_fallback.md†L1-L47】

### 13.3 Atualizar README com novos campos obrigatórios
- **Status:** Incorreto
- **Justificativa:** O README continua classificando `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` como opcionais e indica `neutro` como default, divergindo do comportamento obrigatório definido no plano e implementado no backend.【F:README.md†L167-L170】【F:aprimoramento_plano_storybrand_v2.md†L45-L48】【F:aprimoramento_plano_storybrand_v2.md†L203-L213】

## 14. Feature Flag & Rollout
### 14.1 Garantir toggles documentados e controlados
- **Status:** Correto
- **Justificativa:** O gate só ativa o fallback quando ambas as flags estão ligadas, e o README documenta como habilitá-las e combiná-las com `VITE_ENABLE_NEW_FIELDS` no frontend.【F:app/agents/storybrand_gate.py†L50-L74】【F:README.md†L300-L351】

### 14.2 Planejar rollout backend → frontend e rollback
- **Status:** Correto
- **Justificativa:** O README descreve as fases de rollout coordenando backend e frontend, incluindo recomendações de observação e rollback.【F:README.md†L335-L351】

## 15. Auditoria & Métricas Futuras
### 15.1 Definir monitoramento para `storybrand_gate_metrics`
- **Status:** Correto
- **Justificativa:** A seção “Futuro” do documento de fallback prevê monitoramento dedicado para as métricas do gate, alinhado ao plano.【F:docs/storybrand_fallback.md†L44-L47】【F:aprimoramento_plano_storybrand_v2.md†L153-L155】

### 15.2 Avaliar cache de resultados do fallback
- **Status:** Correto
- **Justificativa:** O mesmo documento registra a avaliação de cache como ação futura, atendendo ao item do checklist.【F:docs/storybrand_fallback.md†L44-L47】【F:aprimoramento_plano_storybrand_v2.md†L154-L155】

### 15.3 Planejar auditoria via `storybrand_audit_trail`
- **Status:** Correto
- **Justificativa:** O plano de documentação cita a criação de auditorias baseadas em `storybrand_audit_trail`, conforme solicitado.【F:docs/storybrand_fallback.md†L44-L47】【F:aprimoramento_plano_storybrand_v2.md†L155-L156】

## 16. QA Final
### 16.1 Executar `make lint`, `make test` e testes manuais completos
- **Status:** Sem evidência
- **Justificativa:** O repositório não contém registros (logs, relatórios ou scripts) comprovando a execução dos comandos de QA exigidos; apenas o checklist marca o item como concluído.【F:checklist.md†L57-L60】

### 16.2 Capturar evidências (logs, screenshots) para PR
- **Status:** Sem evidência
- **Justificativa:** Não há artefatos versionados (imagens ou logs) demonstrando as evidências mencionadas, apesar de o checklist indicar conclusão.【F:checklist.md†L60-L61】

### 16.3 Revisar checklist antes do merge
- **Status:** Sem evidência
- **Justificativa:** O checklist está marcado como concluído, mas não há documentação complementar comprovando a revisão final exigida neste item.【F:checklist.md†L61-L62】
