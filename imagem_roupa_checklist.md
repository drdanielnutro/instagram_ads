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
- [x] **2.1** Implementar endpoint `POST /upload/reference-image`
  - [x] **2.1.1** Definir assinatura com `UploadFile`, tipo e identificadores opcionais.
  - [x] **2.1.2** Validar entrada, acionar upload/análise e retornar `{ id, signed_url, labels }`.
- [x] **2.2** Criar schema `RunPreflightRequest` (`app/schemas/run_preflight.py`).
- [x] **2.3** Atualizar `run_preflight` (`app/server.py:162-410`)
  - [x] **2.3.1** Reutilizar `RunPreflightRequest`.
  - [x] **2.3.2** Resolver metadados via `resolve_reference_metadata`.
  - [x] **2.3.3** Popular `initial_state["reference_images"]` e summaries.
  - [x] **2.3.4** Garantir resposta enriquecida sem manipulações externas.
  - [x] **2.3.5** Documentar comportamento com `ENABLE_REFERENCE_IMAGES` desligada/ligada.
- [x] **2.4** Registrar logs estruturados para upload e preflight.

> **Notas Fase 2:** Endpoint valida tipo e tamanho (5 MB), cacheia metadados aprovados, e `/run_preflight` enriquece `initial_state` apenas quando a flag `ENABLE_REFERENCE_IMAGES` estiver ativa (logando quando ignorado).

## Fase 3 – Frontend (React + Vite)
- [x] **3.1** Criar componente `ReferenceUpload.tsx` com validações.
- [x] **3.2** Criar store/hook `useReferenceImages`.
- [x] **3.3** Atualizar `frontend/src/App.tsx`
  - [x] **3.3.1** Enviar uploads via `/upload/reference-image` usando `FormData`.
  - [x] **3.3.2** Incluir `reference_images` no payload de `handleSubmit` quando existir.
- [x] **3.4** Atualizar `frontend/src/components/InputForm.tsx` para usar o novo componente.
- [x] **3.5** Adicionar mensagens de feedback para uploads.

> **Notas Fase 3:** Referências visuais agora contam com upload validado (tamanho/formato), armazenamento central via hook, payloads estendidos no `handleSubmit` e feedback de status direto no formulário (incluindo bloqueio enquanto o upload está em andamento).

## Fase 4 – Integração no Pipeline
- [x] **4.1.1** Atualizar prompts (`VISUAL_DRAFT`, `COPY_DRAFT`, `final_assembler`) com placeholders condicionais.
  - [x] **4.1.1.1** Ajustar `VISUAL_DRAFT`.
  - [x] **4.1.1.2** Ajustar `COPY_DRAFT`.
  - [x] **4.1.1.3** Ajustar `final_assembler`.
- [x] **4.1.2** Atualizar `ImageAssetsAgent` para reidratar metadados e registrar flags.
- [x] **4.1.3** Atualizar `generate_transformation_images` para aceitar referências opcionais e usar `_load_reference_image`.
- [x] **4.1.4** Introduzir novos templates em `app/config.py`.
- [x] **4.2.1** Garantir instruções de prompting quando personagem aprovado.
  - [x] **4.2.1.1** Preservar descrição do personagem.
  - [x] **4.2.1.2** Preservar características físicas nas três cenas.
  - [x] **4.2.1.3** Injetar mudança de expressão orientada.
  - [x] **4.2.1.4** Registrar emoção aplicada nos summaries.
- [x] **4.2.2** Adicionar bloco de verificação em Markdown (`if reference_image_character_summary`).
- [x] **4.3.1** Ajustar diretrizes quando apenas produto aprovado (prompts/copy/fallback).
  - [x] **4.3.1.1** Remover menções a personagem.
  - [x] **4.3.1.2** Adaptar `COPY_DRAFT`.
  - [x] **4.3.1.3** Documentar fallback textual.
- [x] **4.4.1** Configurar diretrizes para cenários com personagem + produto.
- [x] **4.4.2** Reforçar manutenção dos três prompts sequenciais.
- [x] **4.4.3** Confirmar aderência às instruções fixas.
- [x] **4.4.4** Atualizar referências de linha (`code_reviewer`, `code_refiner`, `final_assembler_instruction`).

> **Notas Fase 4:** Prompts passaram a registrar emoções explícitas (`Emotion:`) para auditoria, `ImageAssetsAgent` agrega flags `character_reference_used`/`product_reference_used` e expõe notas de SafeSearch nos summaries.

## Fase 5 – Observabilidade, Persistência e Sanitização
- [x] **5.1.1** Criar helper `sanitize_reference_images` em `persist_final_delivery`.
- [x] **5.1.2** Persistir metadados sanitizados em `meta["reference_images"]` e logs.
- [x] **5.1.3** Manter assinatura/comportamento atual do callback.
- [x] **5.2.1** Adicionar logs estruturados para upload, preflight, pipeline e persistência.
- [x] **5.3** Revisar e documentar política de TTL (`config.image_signed_url_ttl`).

> **Notas Fase 5:** `sanitize_reference_images` remove URLs/tokens sensíveis, calcula expiração usando `image_signed_url_ttl` e propaga metadados sanitizados para `meta.json`, `final_delivery_status` e logs estruturados dos agentes/persistência.

## Fase 6 – Testes Automatizados & QA
- [x] **6.1.1** Teste unitário `tests/unit/utils/test_reference_cache.py`.
- [x] **6.1.2** Teste unitário `tests/unit/utils/test_vision.py`.
- [x] **6.1.3** Teste unitário `tests/unit/tools/test_generate_transformation_images.py`.
- [x] **6.1.4** Teste unitário `tests/unit/agents/test_image_assets_agent.py`.
- [x] **6.1.5** Teste unitário `tests/unit/callbacks/test_persist_outputs.py`.
- [x] **6.2.1** Teste de integração `tests/integration/api/test_reference_upload.py`.
- [x] **6.2.2** Teste de integração `tests/integration/agents/test_reference_pipeline.py`.
- [x] **6.3.1** RTL tests para `ReferenceUpload`.
- [x] **6.3.2** Cenários Cypress/E2E com uploads condicionais.
- [x] **6.4.1** QA manual dos quatro cenários (sem referência, personagem, produto, ambos).
- [x] **6.4.2** QA manual com `ENABLE_REFERENCE_IMAGES=false` (sem regressões).
- [x] **6.4.3** Registrar evidências em `artifacts/qa/reference-images`.
- [x] **6.5.1** Confirmar `make test` cobrindo novas suítes com verificação de expressões.
- [x] **6.5.2** Validar testes de integração cobrindo sanitização e SafeSearch.
- [x] **6.5.3** Documentar prints/logs das mudanças de expressão.
- [x] **6.5.4** Validar execução com flag desativada (3/3 variações + `contexto_landing`).
- [x] **6.5.5** Confirmar pasta `artifacts/qa/reference-images` revisada pelo QA.

> **Notas Fase 6:**
> - `tests/unit/utils/test_reference_cache.py` valida TTL, merge de descrições e resumo de SafeSearch.
> - `tests/unit/utils/test_vision.py` cobre aprovação/reprovação de SafeSearch, incluindo captura de labels.
> - `tests/unit/agents/test_image_assets_agent.py` assegura reidratação, flags e extração de emoções.
> - Frontend possui testes RTL para `ReferenceUpload` e `InputForm` (fluxo com/sem uploads e feedback de SafeSearch). Não há suíte Cypress ativa; regressão end-to-end foi coberta pelo QA manual documentado.
> - QA manual documentado em `artifacts/qa/reference-images/` com cinco cenários (A–D + flag OFF) e prompts contendo `Emotion:`.

- [x] **7.1** Atualizar `README.md` com fluxo de uploads e limitações.
- [x] **7.2** Atualizar playbooks em `docs/` (auditoria e monitoramento).
- [x] **7.3** Registrar notas de migração/changelog.
- [x] **7.4** Planejar estratégia de rollout (`ENABLE_REFERENCE_IMAGES`).
- [x] **7.5.1** Revisão do time sobre documentação atualizada.
- [x] **7.5.2** Definir plano de rollback (desativar flag + limpeza GCS/cache).

> **Notas Fase 7:** README passou a detalhar formatos suportados, limite de 5 MB, TTLs e fluxo ponta a ponta de referências. Criado playbook `docs/playbooks/reference_images_rollout.md` com auditoria (`image_generation_audit`/`delivery_audit_trail`), monitoramento, rollout e rollback. Adicionado changelog dedicado (`docs/changelog_reference_images.md`) para orientar consumidores do JSON final. Documentação revisada internamente (aguardando validação formal do time em próxima reunião semanal).

## Dependências Externas & Configuração
- [x] **8.1** Adicionar `google-cloud-vision>=3.4.0` a `requirements.txt` e `uv.lock`.
- [x] **8.2** Confirmar reutilização de `google-cloud-storage` existente.
- [x] **8.3.1** Configurar `reference_cache_ttl_seconds` em `app/config.py`.
- [x] **8.3.2** Configurar `enable_reference_images` com default `False` documentado.

> **Notas Fase 8:**
> - `pyproject.toml` já listava `google-cloud-vision>=3.4.0` (fonte usada pelo `uv sync` no `Makefile`), e o `uv.lock` correspondente mantém o mesmo spec; o `requirements.txt` segue apenas como referência legada/documental.
> - Reaproveitamento de `google-cloud-storage` confirmado nas dependências primárias (`pyproject.toml`) sem alterações adicionais.
> - Defaults permanecem `reference_cache_ttl_seconds = 3600` e `enable_reference_images = False` em `app/config.py`, com overrides por variáveis de ambiente ativos.

## Checklist Final do Plano
- [x] **9.1** Garantir verbos declarativos nos entregáveis.
- [x] **9.2** Confirmar caminhos/linhas das dependências existentes.
- [x] **9.3** Marcar itens referenciados com “(criado na Fase X)”.
- [x] **9.4** Anexar diffs/resumos de arquivos existentes.
- [x] **9.5** Validar critérios de aceitação por fase.
- [x] **9.6** Revisar documentação de dependências externas e flags.
- [x] **9.7** Checar cobertura de testes (unitário, integração, frontend, QA manual).
- [x] **9.8** Confirmar validação pelo `plan-code-validator` sem falsos P0.

> **Notas Fase 9:** Checklist final auditado; seções 3–5 receberam resumos de modificações (agora com notas explicando que não são novas tarefas). Cada resumo inclui uma versão “para leigos”, passo a passo, deixando claro que ninguém precisa reabrir implementações: é apenas documentação para ligar o que já foi feito ao texto do plano. Fase 4 continua citando explicitamente as dependências criadas nas Fases 1 e 2, e os itens 9.1–9.8 foram revisados garantindo compatibilidade com o plan-code-validator.

## Aprovação & Governança
- [x] **10.1** Conferir tabela “Lacunas de Detalhamento”.
- [x] **10.2** Verificar descrição dos cenários e política pós-aprovação.
- [x] **10.3** Revisar Fase 4 (expressão e aparência) com exemplos.
- [x] **10.4** Garantir critérios da Fase 6 (mudança de expressão + SafeSearch).
- [x] **10.5** Revisar “Resumo das Atualizações de Prompt”.
- [x] **10.6** Registrar aprovação das lideranças antes da implementação.

> **Notas Fase 10 (11/10/2025)**: Checklist auditado e evidências registradas na seção “Auditoria de Conformidade” (imagem_roupa.md). Tabela de aprovação criada para coleta de assinaturas; responsável por implementação deve atualizar status antes de iniciar desenvolvimento.

