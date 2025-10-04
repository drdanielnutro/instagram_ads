# Revisão Técnica — plano_validacao_json_v3.md

## Resumo Executivo
- Foram identificados **3 bloqueios críticos (P0)** e **1 ajuste de precisão (P2)** antes que o plano possa avançar para implementação.
- Os bloqueios concentram-se em divergências de referência: o plano aponta arquivos/agentes inexistentes ou caminhos incorretos, o que inviabiliza a execução das fases 1 e 3 sem correções prévias.
- O registro de criações planejadas totaliza **37 artefatos** entre arquivos, agentes, utilitários, chaves de estado e suítes de teste, exigindo alinhamento com as equipes responsáveis por backend e QA.

## Métricas
- Claims totais analisados: **12**
- Claims validados (sem ação): **9**
- Claims classificados como entregas futuras (Creation Registry): **37**
- Severidade dos achados: **P0 = 3**, **P1 = 0**, **P2 = 1**, **P3 = 0**
- Status geral: **ACTION_REQUIRED** (bloqueadores precisam de correção no plano)

## Achados Críticos (P0)

### P0-001 — Arquivo alvo incorreto para preservar metadados de snippets
**Claim**: “Modificar `app/utils/session_state.py:13-120` para aceitar os novos campos persistidos.”【F:plano_validacao_json_v3.md†L11-L19】  
**Evidência**: O arquivo citado contém apenas utilitários de resolução (`resolve_state`, `safe_*`) e **não** possui `CodeSnippet` nem `add_approved_snippet`【F:app/utils/session_state.py†L10-L91】. A estrutura tipada que descarta campos extras está em `app/utils/session-state.py` e, no estado atual, perderá `snippet_type/approved_at/snippet_id` ao serializar o estado.【F:app/utils/session-state.py†L33-L138】  
**Impacto**: `FinalAssemblyGuardPre` jamais encontrará os metadados enriquecidos, bloqueando o pipeline determinístico logo na fase 1.  
**Ação recomendada**: Atualizar explicitamente `app/utils/session-state.py` (ou abandonar esses helpers quando a flag estiver ativa) antes de executar qualquer implementação.

### P0-002 — `final_assembler_llm` não existe no código
**Claim**: “Modificaremos o `final_assembler` para rodar como estágio composto com `FinalAssemblyGuardPre` → `final_assembler_llM` (existente) → `FinalAssemblyNormalizer`.”【F:plano_validacao_json_v3.md†L71-L81】  
**Evidência**: O repositório contém apenas o agente `final_assembler`; não há símbolo `final_assembler_llm` definido ou importado.【F:app/agent.py†L1029-L1056】【33e932†L1-L15】  
**Impacto**: Não é possível construir o estágio composto sem primeiro criar/renomear o agente LLM.  
**Ação recomendada**: Registrar a criação/renomeação do agente (`final_assembler_llm`) e ajustar todas as referências antes de prosseguir com a Fase 3.

### P0-003 — `persist_final_delivery_agent` é pressuposto, mas inexistente
**Claim**: “Encadear `RunIfPassed` com `semantic_validation_stage`, `image_assets_agent` e `persist_final_delivery_agent` (existente).”【F:plano_validacao_json_v3.md†L57-L80】  
**Evidência**: O pipeline atual persiste o JSON diretamente dentro de `ImageAssetsAgent`, chamando `persist_final_delivery` sem qualquer agente intermediário, e o `execution_pipeline` termina no próprio `image_assets_agent` antes do status reporter.【F:app/agent.py†L520-L583】【F:app/agent.py†L1261-L1272】 Pesquisas por `persist_final_delivery_agent` retornam apenas referências históricas em documentos, não em código executável.【012706†L1-L23】  
**Impacto**: Sem definir esse agente, não há como inserir o gating determinístico/persistência única descritos na Fase 3.  
**Ação recomendada**: Adicionar explicitamente a criação do agente de persistência (ou ajustar o desenho para manter o callback) e revisar responsabilidades de `ImageAssetsAgent` antes de reorquestrar o pipeline.

## Achados Complementares (P2)

### P2-001 — Faixa de linhas incorreta para `collect_code_snippets_callback`
**Claim**: “Modificar `app/agent.py:880-950` para estender `collect_code_snippets_callback`.”【F:plano_validacao_json_v3.md†L11-L19】  
**Evidência**: A função está localizada nas linhas 122-136, muito acima da faixa indicada.【F:app/agent.py†L122-L136】  
**Impacto**: Risco de buscas equivocadas e retrabalho durante a execução.  
**Ação recomendada**: Atualizar a referência de linha (≈122-136) ou remover o intervalo numérico do plano.

## ✅ Planned Creations (não validar em código agora)
Itens extraídos do Creation Registry (37 elementos):
1. `app/schemas/final_delivery.py`, incluindo `StrictAdCopy`, `StrictAdVisual`, `StrictAdItem`, `model_dump` e `from_state`.【F:plano_validacao_json_v3.md†L11-L19】
2. `app/utils/audit.py` com `append_delivery_audit_event`。【F:plano_validacao_json_v3.md†L11-L19】
3. `app/validators/final_delivery_validator.py` e `FinalDeliveryValidatorAgent`。【F:plano_validacao_json_v3.md†L41-L48】
4. `app/agents/gating.py` contendo `RunIfPassed` e `ResetDeterministicValidationState`。【F:plano_validacao_json_v3.md†L41-L48】
5. Função `build_execution_pipeline` e agentes auxiliares `FinalAssemblyGuardPre`, `FinalAssemblyNormalizer`, `deterministic_validation_stage`, `semantic_validation_stage` e `semantic_visual_reviewer`/`semantic_fix_agent`.【F:plano_validacao_json_v3.md†L71-L81】
6. Novas chaves de estado: `approved_visual_drafts`, `deterministic_final_validation`, `deterministic_final_blocked`, `semantic_visual_review`, `image_assets_review` e correlatos。【F:plano_validacao_json_v3.md†L41-L80】
7. Flags/configs: `enable_deterministic_final_validation` e `config.CTA_BY_OBJECTIVE` (caso não exista).【F:plano_validacao_json_v3.md†L11-L48】
8. Suítes de teste listadas na Fase 5 (unitárias e integração).【F:plano_validacao_json_v3.md†L135-L159】

## Mapa Plano ↔ Código
| Seção do plano | Situação | Evidência |
| --- | --- | --- |
| Fase 1 – `collect_code_snippets_callback` | Alinhado (com ajuste de linha) | `app/agent.py:122-136`【F:app/agent.py†L122-L136】 |
| Fase 1 – Helpers de sessão | **Bloqueado** (arquivo alvo incorreto) | `app/utils/session-state.py:33-138`【F:app/utils/session-state.py†L33-L138】 |
| Fase 3 – Pipeline de execução | **Bloqueado** (agente inexistente) | `app/agent.py:1261-1272`【F:app/agent.py†L1261-L1272】 |

## Incertezas / Próximos Passos
- Não foram registradas incertezas adicionais além dos blockers citados. Após corrigir o plano, recomenda-se uma nova rodada rápida de validação para garantir que os agentes/arquivos recém-planejados estejam devidamente enumerados.
