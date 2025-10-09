# Checklist de Execução — Plano imagem_roupa.md

> Convenção: `[ ]` pendente · `[>]` em andamento · `[x]` concluído  
> Referência principal: `imagem_roupa.md`

## Fase 1 – Schemas e Cache de Referências
- [x] **1.1** Criar `app/schemas/reference_assets.py`
  - [x] **1.1.1** Definir `ReferenceImageMetadata` com campos obrigatórios.
  - [x] **1.1.2** Implementar métodos `model_dump(mode="json")` e `to_state_dict()`.
- [x] **1.2** Criar `app/utils/reference_cache.py`
  - [x] **1.2.1** Implementar `cache_reference_metadata`.
  - [x] **1.2.2** Implementar `resolve_reference_metadata`.
  - [x] **1.2.3** Implementar `merge_user_description`.
  - [x] **1.2.4** Implementar `build_reference_summary`.
  - [x] **1.2.5** Configurar cache em memória com TTL e pontos de extensão.
- [x] **1.3** Criar `app/utils/vision.py` com helper `analyze_reference_image`.
- [x] **1.4** Criar helper `upload_reference_image` em `app/utils/gcs.py`.
- [x] **1.5** Preparar testes unitários base (estrutura inicial).

> **Notas Fase 1:** Cache configurável com backend em memória (TTL derivado de `config.reference_cache_ttl_seconds`), helper Vision com exceções específicas e upload para GCS realizando limpeza em caso de falhas/unsafe.

## Fase 2 – Backend: Upload & Preflight
- [ ] **2.1** Implementar endpoint `POST /upload/reference-image`
  - [ ] **2.1.1** Definir assinatura com `UploadFile`, tipo e identificadores opcionais.
  - [ ] **2.1.2** Validar entrada, acionar upload/análise e retornar `{ id, signed_url, labels }`.
- [ ] **2.2** Criar schema `RunPreflightRequest` (`app/schemas/run_preflight.py`).
- [ ] **2.3** Atualizar `run_preflight` (`app/server.py:162-410`)
  - [ ] **2.3.1** Reutilizar `RunPreflightRequest`.
  - [ ] **2.3.2** Resolver metadados via `resolve_reference_metadata`.
  - [ ] **2.3.3** Popular `initial_state["reference_images"]` e summaries.
  - [ ] **2.3.4** Garantir resposta enriquecida sem manipulações externas.
  - [ ] **2.3.5** Documentar comportamento com `ENABLE_REFERENCE_IMAGES` desligada/ligada.
- [ ] **2.4** Registrar logs estruturados para upload e preflight.

## Fase 3 – Frontend (React + Vite)
- [ ] **3.1** Criar componente `ReferenceUpload.tsx` com validações.
- [ ] **3.2** Criar store/hook `useReferenceImages`.
- [ ] **3.3** Atualizar `frontend/src/App.tsx`
  - [ ] **3.3.1** Enviar uploads via `/upload/reference-image` usando `FormData`.
  - [ ] **3.3.2** Incluir `reference_images` no payload de `handleSubmit` quando existir.
- [ ] **3.4** Atualizar `frontend/src/components/InputForm.tsx` para usar o novo componente.
- [ ] **3.5** Adicionar mensagens de feedback para uploads.

## Fase 4 – Integração no Pipeline
- [ ] **4.1.1** Atualizar prompts (`VISUAL_DRAFT`, `COPY_DRAFT`, `final_assembler`) com placeholders condicionais.
  - [ ] **4.1.1.1** Ajustar `VISUAL_DRAFT`.
  - [ ] **4.1.1.2** Ajustar `COPY_DRAFT`.
  - [ ] **4.1.1.3** Ajustar `final_assembler`.
- [ ] **4.1.2** Atualizar `ImageAssetsAgent` para reidratar metadados e registrar flags.
- [ ] **4.1.3** Atualizar `generate_transformation_images` para aceitar referências opcionais e usar `_load_reference_image`.
- [ ] **4.1.4** Introduzir novos templates em `app/config.py`.
- [ ] **4.2.1** Garantir instruções de prompting quando personagem aprovado.
  - [ ] **4.2.1.1** Preservar descrição do personagem.
  - [ ] **4.2.1.2** Preservar características físicas nas três cenas.
  - [ ] **4.2.1.3** Injetar mudança de expressão orientada.
  - [ ] **4.2.1.4** Registrar emoção aplicada nos summaries.
- [ ] **4.2.2** Adicionar bloco de verificação em Markdown (`if reference_image_character_summary`).
- [ ] **4.3.1** Ajustar diretrizes quando apenas produto aprovado (prompts/copy/fallback).
  - [ ] **4.3.1.1** Remover menções a personagem.
  - [ ] **4.3.1.2** Adaptar `COPY_DRAFT`.
  - [ ] **4.3.1.3** Documentar fallback textual.
- [ ] **4.4.1** Configurar diretrizes para cenários com personagem + produto.
- [ ] **4.4.2** Reforçar manutenção dos três prompts sequenciais.
- [ ] **4.4.3** Confirmar aderência às instruções fixas.
- [ ] **4.4.4** Atualizar referências de linha (`code_reviewer`, `code_refiner`, `final_assembler_instruction`).

## Fase 5 – Observabilidade, Persistência e Sanitização
- [ ] **5.1.1** Criar helper `sanitize_reference_images` em `persist_final_delivery`.
- [ ] **5.1.2** Persistir metadados sanitizados em `meta["reference_images"]` e logs.
- [ ] **5.1.3** Manter assinatura/comportamento atual do callback.
- [ ] **5.2.1** Adicionar logs estruturados para upload, preflight, pipeline e persistência.
- [ ] **5.3** Revisar e documentar política de TTL (`config.image_signed_url_ttl`).

## Fase 6 – Testes Automatizados & QA
- [ ] **6.1.1** Teste unitário `tests/unit/utils/test_reference_cache.py`.
- [ ] **6.1.2** Teste unitário `tests/unit/utils/test_vision.py`.
- [ ] **6.1.3** Teste unitário `tests/unit/tools/test_generate_transformation_images.py`.
- [ ] **6.1.4** Teste unitário `tests/unit/agents/test_image_assets_agent.py`.
- [ ] **6.1.5** Teste unitário `tests/unit/callbacks/test_persist_outputs.py`.
- [ ] **6.2.1** Teste de integração `tests/integration/api/test_reference_upload.py`.
- [ ] **6.2.2** Teste de integração `tests/integration/agents/test_reference_pipeline.py`.
- [ ] **6.3.1** RTL tests para `ReferenceUpload`.
- [ ] **6.3.2** Cenários Cypress/E2E com uploads condicionais.
- [ ] **6.4.1** QA manual dos quatro cenários (sem referência, personagem, produto, ambos).
- [ ] **6.4.2** QA manual com `ENABLE_REFERENCE_IMAGES=false` (sem regressões).
- [ ] **6.4.3** Registrar evidências em `artifacts/qa/reference-images`.
- [ ] **6.5.1** Confirmar `make test` cobrindo novas suítes com verificação de expressões.
- [ ] **6.5.2** Validar testes de integração cobrindo sanitização e SafeSearch.
- [ ] **6.5.3** Documentar prints/logs das mudanças de expressão.
- [ ] **6.5.4** Validar execução com flag desativada (3/3 variações + `contexto_landing`).
- [ ] **6.5.5** Confirmar pasta `artifacts/qa/reference-images` revisada pelo QA.

## Fase 7 – Documentação & Rollout
- [ ] **7.1** Atualizar `README.md` com fluxo de uploads e limitações.
- [ ] **7.2** Atualizar playbooks em `docs/` (auditoria e monitoramento).
- [ ] **7.3** Registrar notas de migração/changelog.
- [ ] **7.4** Planejar estratégia de rollout (`ENABLE_REFERENCE_IMAGES`).
- [ ] **7.5.1** Revisão do time sobre documentação atualizada.
- [ ] **7.5.2** Definir plano de rollback (desativar flag + limpeza GCS/cache).

## Dependências Externas & Configuração
- [ ] **8.1** Adicionar `google-cloud-vision>=3.4.0` a `requirements.txt` e `uv.lock`.
- [ ] **8.2** Confirmar reutilização de `google-cloud-storage` existente.
- [ ] **8.3.1** Configurar `reference_cache_ttl_seconds` em `app/config.py`.
- [ ] **8.3.2** Configurar `enable_reference_images` com default `False` documentado.

## Checklist Final do Plano
- [ ] **9.1** Garantir verbos declarativos nos entregáveis.
- [ ] **9.2** Confirmar caminhos/linhas das dependências existentes.
- [ ] **9.3** Marcar itens referenciados com “(criado na Fase X)”.
- [ ] **9.4** Anexar diffs/resumos de arquivos existentes.
- [ ] **9.5** Validar critérios de aceitação por fase.
- [ ] **9.6** Revisar documentação de dependências externas e flags.
- [ ] **9.7** Checar cobertura de testes (unitário, integração, frontend, QA manual).
- [ ] **9.8** Confirmar validação pelo `plan-code-validator` sem falsos P0.

## Aprovação & Governança
- [ ] **10.1** Conferir tabela “Lacunas de Detalhamento”.
- [ ] **10.2** Verificar descrição dos cenários e política pós-aprovação.
- [ ] **10.3** Revisar Fase 4 (expressão e aparência) com exemplos.
- [ ] **10.4** Garantir critérios da Fase 6 (mudança de expressão + SafeSearch).
- [ ] **10.5** Revisar “Resumo das Atualizações de Prompt”.
- [ ] **10.6** Registrar aprovação das lideranças antes da implementação.

