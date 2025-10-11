# Checklist – Persistir StoryBrand Completo (16 seções) no fallback

## 1. Criar agente de persistência das seções (`app/agents/storybrand_fallback.py`)
- [ ] Inserir classe `PersistStorybrandSectionsAgent(BaseAgent)` logo após `FallbackQualityReporter`.
- [ ] Implementar checagem da flag de configuração antes de executar e registrar log `storybrand_sections_persisted="skipped"` quando desativada.
- [ ] Construir `sections_payload` iterando `SECTION_CONFIGS`, garantindo strings (usar `state.get(cfg.state_key) or ""`).
- [ ] Anexar metadados: `audit`, `enriched_inputs`, `timestamp_utc`.
- [ ] Sanitizar valores não string/remover dados sensíveis antes de persistir.
- [ ] Garantir criação de `artifacts/storybrand/` (_ensure_dir_) e salvar `{session_id}.json`.
- [ ] Gravar caminho local em `state["storybrand_sections_saved_path"]`.
- [ ] Se `DELIVERIES_BUCKET` estiver setado, enviar cópia para GCS (`deliveries/{user_id}/{session_id}/storybrand_sections.json`) e guardar URI em `state["storybrand_sections_gcs_uri"]`.
- [ ] Registrar log estruturado `storybrand_sections_persisted` com `session_id`, `local_path`, `gcs_uri`.

## 2. Ajustar pipeline sequencial do fallback
- [ ] Adicionar `PersistStorybrandSectionsAgent()` após `StoryBrandSectionRunner(SECTION_CONFIGS)` e antes de `FallbackStorybrandCompiler()` em `fallback_storybrand_pipeline`.

## 3. Referenciar caminhos persistidos na resposta final (`app/callbacks/persist_outputs.py`)
- [ ] Incluir `storybrand_sections_saved_path` e `storybrand_sections_gcs_uri` em `meta`.
- [ ] Persistir os novos campos tanto localmente quanto no upload GCS.
- [ ] Definir `meta["storybrand_sections_present"]` (True/False) com base na existência do arquivo.

## 4. Atualizar documentação
- [ ] Atualizar `README.md` (seção “Persistência do JSON Final”) com a nova saída `artifacts/storybrand/<session_id>.json`.
- [ ] Documentar procedimento em `docs/playbooks/reference_images_rollout.md` ou playbook específico do fallback.
- [ ] Registrar mudança no changelog relevante (ex.: `docs/changelog_reference_images.md`).

## 5. Cobertura de testes
- [ ] Adicionar teste unitário em `tests/unit/agents/test_storybrand_fallback.py` cobrindo criação do JSON, campos no estado e upload condicional ao GCS.
- [ ] (Opcional) Estender teste de integração para validar presença do caminho salvo quando fallback é executado.

## 6. Flag de configuração (`app/config.py` + arquivos de ambiente)
- [ ] Introduzir atributo `persist_storybrand_sections` com valor padrão `False` e suporte a `PERSIST_STORYBRAND_SECTIONS` via env.
- [ ] Atualizar `PersistStorybrandSectionsAgent` para checar a flag (se ainda não feito na etapa 1).
- [ ] Incluir `PERSIST_STORYBRAND_SECTIONS=false` nos arquivos de exemplo (`app/.env.txt` ou `.env.example`) com comentário.

## 7. Sanitização e segurança adicionais
- [ ] Confirmar que conteúdos são normalizados para string e sensíveis removidos.
- [ ] Garantir logs estruturados (`log_struct_event`) com campos necessários (`event`, `session_id`, `has_gcs_upload`, `sections_count`).

## 8. Validação final
- [ ] Executar `make test` (ou comando equivalente) para toda a suíte.
- [ ] Realizar teste manual forçando fallback e conferir `artifacts/storybrand/<session_id>.json`, `meta.json` e URIs no GCS.
