
# Checklist de Implementação – Correções no Plano StoryBrand Fallback

> Convenção de status: substitua manualmente o marcador de cada item conforme avança.
> - `[ ]` = pending (padrão)
> - `[>]` = in progress
> - `[x]` = done

## 1. Correções de Referências de Estado
- [ ] Substituir no `aprimoramento_plano_storybrand_v2.md` todas as menções a `state['storybrand_completeness_score']` por leitura de `state['storybrand_analysis']['completeness_score']`.
- [ ] Incluir fallback de leitura do score em `state['landing_page_context']['storybrand_completeness']` quando `storybrand_analysis` não estiver disponível.
- [ ] Trocar todas as referências a `state['landing_page_analysis']` por `state['landing_page_context']`.
- [ ] Ajustar a recomendação de “definir `state['storybrand_completeness'] = 1.0`” para: atualizar `storybrand_analysis['completeness_score']` e, opcionalmente, sincronizar `landing_page_context['storybrand_completeness']`.

## 2. Integração no Pipeline (`agent.py`)
- [ ] Atualizar o plano para o gate reutilizar `PlanningOrRunSynth` no caminho feliz, em vez de invocar `planning_pipeline` diretamente.
- [ ] Manter o posicionamento do gate imediatamente após `landing_page_analyzer` no `complete_pipeline`.

## 3. Estrutura de Diretórios e Arquitetura
- [ ] Corrigir no plano os caminhos sugeridos `app/agents/...` para refletir a estrutura atual (agentes em `app/agent.py` e submódulos existentes), ou documentar explicitamente a criação de `app/agents/` com `__init__.py` e os impactos de import.
- [ ] Especificar claramente onde as novas classes (`StoryBrandQualityGate`, pipelines e utilitários) viverão no projeto.

## 4. Mapeamento das 16 Seções → `StoryBrandAnalysis` (7 elementos)
- [ ] Adicionar ao plano um mapeamento explícito de cada uma das 16 seções narrativas para os campos de `StoryBrandAnalysis` (ex.: `exposition_1` → `character.description`; `problem_external` → `problem.types.external`; `plan` → `plan.steps`).
- [ ] Definir como o `fallback_storybrand_compiler` consolidará as 16 saídas no objeto Pydantic final e validará o schema.

## 5. Observabilidade e Métricas
- [ ] Definir no plano o formato JSON de `state['storybrand_gate_metrics']` (campos mínimos: `score`, `threshold`, `path`, `timestamp`).
- [ ] Definir o formato e conteúdo de `state['storybrand_audit_trail']` (lista ordenada de eventos com `stage`, `section`, `iteration`, `status`, `comment`).

## 6. Coleta de Inputs Essenciais (Frontend/Backend)
- [ ] Atualizar o plano para descrever as mudanças no `helpers/user_extract_data.py` (extração de `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`).
- [ ] Atualizar o plano para descrever as mudanças no Wizard do frontend (novos campos no `WIZARD_INITIAL_STATE`, validações, submissão) mantendo-os opcionais.
- [ ] Definir o vocabulário aceito para `sexo_cliente_alvo` e implicações nos prompts de revisão (masculino/feminino/outras opções, se aplicável).

## 7. Prompts e Carregamento
- [ ] Confirmar no plano o diretório `prompts/storybrand_fallback/` e listar os arquivos necessários (collector, 16 writers, reviews por gênero, corrector, compiler).
- [ ] Descrever como os prompts serão carregados (caminho relativo, encoding, tratamento de erro) pelos agentes.

## 8. Testes e Validação
- [ ] Especificar no plano os testes unitários do gate (scores acima/abaixo/igual ao limiar) mockando os pipelines invocados.
- [ ] Especificar testes de integração para o `fallback_storybrand_pipeline`, incluindo como mockar respostas de `LlmAgent` e verificar o contrato de estado final.
- [ ] Garantir no plano que o “caminho feliz” permanece funcional e testado após as alterações.

## 9. Documentação e Checklist
- [ ] Alinhar no plano o processo com `AGENTS.md` e o fluxo “Checklist Primeiro, Código Depois” (uso do `checklist.md` na raiz).
- [ ] Ajustar a seção de documentação para indicar onde viverá a documentação do fallback (ex.: `docs/storybrand_fallback.md`) e como o novo checklist se integra ao fluxo existente.

## 10. Feature Flag
- [ ] Garantir no plano a definição da flag `ENABLE_STORYBRAND_FALLBACK` em `app/config.py` e a lógica de inclusão condicional do gate no `complete_pipeline`.
- [ ] Documentar variáveis de ambiente relacionadas (ex.: `FALLBACK_STORYBRAND_MAX_ITERATIONS`, `FALLBACK_STORYBRAND_MODEL`, `STORYBRAND_GATE_DEBUG`).

## 11. Etapas Futuras (Opcional)
- [ ] Documentar no plano a estratégia de métricas para recalibração do `min_storybrand_completeness`.
- [ ] Documentar a política de cache para resultados de fallback e implicações de auditoria (versionamento do `storybrand_analysis`).

---

**Observações:**
- Este checklist destina-se a guiar a edição do documento `aprimoramento_plano_storybrand_v2.md` conforme as correções indicadas em `revisao_plano_fallback_storybrand.md`.
- Não execute alterações de código antes de concluir e marcar como done as seções pertinentes deste checklist.

