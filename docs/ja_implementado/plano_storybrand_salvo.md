# Plano Expandido – Persistir StoryBrand Completo (16 seções) no fallback

## Objetivo
Salvar todas as seções geradas pelo fallback do StoryBrand (`storybrand_*`, `exposition_*`, `inciting_incident_*`, etc.) antes que o compilador as consolide em `StoryBrandAnalysis`, produzindo um artefato JSON reutilizável por sessão.

## Contexto Atual (referências no código)
- O fallback produz 16 blocos e armazena cada texto em `state[cfg.state_key]` dentro de `StoryBrandSectionRunner` (`app/agents/storybrand_fallback.py`, aprox. linhas 565-675).
- `FallbackStorybrandCompiler` resume os blocos para `StoryBrandAnalysis` e grava em `state["storybrand_analysis"]` (`app/agents/fallback_compiler.py:256-272`).
- A persistência final (`app/callbacks/persist_outputs.py:188-311`) grava o JSON final (`final_code_delivery`) e um `meta.json`, mas não inclui a versão granular das 16 seções.

---

## 1. Criar agente de persistência das seções
### Arquivo-alvo
- `app/agents/storybrand_fallback.py`

### Alterações
1. Inserir nova classe `PersistStorybrandSectionsAgent(BaseAgent)` imediatamente após `FallbackQualityReporter` (por volta das linhas 700-722).
2. Implementar lógica:
   - Verificar flag (ver item 6) antes de executar.
     - Se a flag estiver desativada, registrar log estruturado `storybrand_sections_persisted="skipped"` e retornar sem executar o restante (failsafe observável).
   - Iterar `SECTION_CONFIGS` (definido em `app/agents/storybrand_sections.py:44-146`) e montar `sections_payload = {cfg.state_key: state.get(cfg.state_key) or ""}` garantindo que conteúdos sejam strings.
   - Incluir metadados relevantes:  
     `audit = state.get("storybrand_audit_trail", [])`,  
     `enriched_inputs = state.get("storybrand_enriched_inputs", {})`,  
     `timestamp_utc = datetime.now(timezone.utc)...`.
   - Sanitizar valores que não sejam strings/nulos (converter para `str(value)` quando necessário) e remover dados sensíveis (ex.: URLs com tokens, caso surjam).
   - Criar diretório `artifacts/storybrand/` se ainda não existir (utilizar `_ensure_dir` similar ao de `persist_final_delivery`).
   - Salvar arquivo `artifacts/storybrand/{session_id}.json` contendo `{"sections": sections_payload, "audit": ..., "enriched_inputs": ..., "timestamp_utc": ...}`.
   - Guardar o caminho local em `state["storybrand_sections_saved_path"]`.
   - Se `DELIVERIES_BUCKET` estiver configurado, enviar cópia para `deliveries/{user_id}/{session_id}/storybrand_sections.json` utilizando `safe_user_id`/`safe_session_id` (de `app/utils/session_state.py`) para evitar `None`, e registrar URI (`state["storybrand_sections_gcs_uri"]`).
   - Registrar log estruturado `storybrand_sections_persisted` com `session_id`, `local_path`, `gcs_uri`.

### Justificativa
`StoryBrandSectionRunner` já deixa os 16 textos completos no estado; capturá-los antes de `FallbackStorybrandCompiler` garante acesso à narrativa original. Reaproveitamos o padrão de persistência existente para manter consistência operacional.

---

## 2. Ajustar pipeline sequencial do fallback
### Arquivo-alvo
- `app/agents/storybrand_fallback.py`

### Alterações
1. Na definição de `fallback_storybrand_pipeline` (aprox. linhas 721-733), inserir `PersistStorybrandSectionsAgent()` logo depois de `StoryBrandSectionRunner(SECTION_CONFIGS)` e antes de `FallbackStorybrandCompiler()`.

### Justificativa
A persistência precisa ocorrer imediatamente depois que as seções são aprovadas e antes que sejam condensadas. Mantemos `FallbackQualityReporter` como último passo porque ele depende do resultado final para montar o relatório de recuperação.

---

## 3. Referenciar caminhos persistidos na resposta final
### Arquivo-alvo
- `app/callbacks/persist_outputs.py`

### Alterações
1. Ao construir `meta` (linhas 270-309), incluir:
   - `storybrand_sections_saved_path = state.get("storybrand_sections_saved_path")`
   - `storybrand_sections_gcs_uri = state.get("storybrand_sections_gcs_uri")`
2. Persistir essas chaves tanto no `meta` local quanto na versão enviada ao GCS.
3. Opcional: se `storybrand_sections_saved_path` existir, marcar `meta["storybrand_sections_present"] = True` (caso contrário `False`).

### Justificativa
Os endpoints `/delivery/final/meta` e `/delivery/final/download` consultam `meta.json`. Incluir referências às seções completas fornece rastreabilidade e permite recuperar o StoryBrand expandido sem depender do estado em memória.

---

## 4. Atualizar documentação
### Arquivos-alvo
1. `README.md` – seção “Persistência do JSON Final” (linhas ~180-220):
   - Adicionar parágrafo informando que, quando o fallback executa, o sistema salva `artifacts/storybrand/<session_id>.json` contendo as 16 seções.
   - Indicar que o caminho também aparece no `meta.json` via `storybrand_sections_saved_path`.
2. `docs/playbooks/reference_images_rollout.md` (ou criar nota específica em `docs/playbooks/storybrand_fallback.md`, se preferirem):
   - Registrar procedimento: “Para reconstruir narrativa quando fallback ocorrer, consultar `storybrand_sections_saved_path` no meta ou arquivo em `artifacts/storybrand/`.”
3. `docs/changelog_reference_images.md` (ou changelog equivalente):
   - Acrescentar entrada descrevendo o novo artefato `storybrand_sections_saved_path`/`storybrand_sections_gcs_uri` para que consumidores externos saibam da mudança.

### Justificativa
Analistas e QA precisam saber onde encontrar a narrativa completa para auditorias e depurações. A documentação garante que a informação esteja disponível sem investigar o código.

---

## 5. Cobertura de testes
### Arquivos-alvo
1. `tests/unit/agents/test_storybrand_fallback.py`
   - Adicionar teste unitário simulando execução do pipeline com fallback habilitado.
   - Monckeypatch `Path`/`_ensure_dir` para usar `tmp_path`.
   - Verificar:  
     a) `PersistStorybrandSectionsAgent` cria arquivo JSON com 16 chaves esperadas.  
     b) Registra `storybrand_sections_saved_path` no estado.  
     c) (Se aplicável) chama upload GCS quando flag estiver ativa, reutilizando os stubs de cliente GCS já definidos em `tests/conftest.py` para evitar mocks duplicados.
2. (Opcional) `tests/integration/agents/test_reference_pipeline.py`
   - Se o teste de integração já cobrir fallback, acrescentar assert usando `state["storybrand_sections_saved_path"]` ou checar `meta` final quando fallback for forçado.

### Justificativa
Garantimos que a nova funcionalidade seja exercitada e evita regressões futuras. O teste unitário foca na persistência; o de integração assegura que o caminho aparece no fluxo completo.

---

## 6. Flag de configuração para isolar a refatoração
### Arquivo-alvo
- `app/config.py` (linhas 105-207)

### Alterações
1. Adicionar atributo `persist_storybrand_sections: bool = False` à configuração (com comentário indicando que a feature vem desativada por padrão).
2. Permitir override via env var (`PERSIST_STORYBRAND_SECTIONS`) logo após os demais overrides (`if os.getenv("PERSIST_STORYBRAND_SECTIONS"):` …).
3. `PersistStorybrandSectionsAgent` deve checar a flag antes de executar; se `False`, registrar log informativo e retornar sem salvar.
4. Atualizar arquivo de exemplo de variáveis (`app/.env.txt` ou `.env.example`, conforme padrão do repositório) acrescentando `PERSIST_STORYBRAND_SECTIONS=false` com comentário explicando o uso.

### Justificativa
Mantém a refatoração isolada: ambientes existentes continuam inalterados até ativar explicitamente a flag (`true`). Segue o padrão de outras features controladas por flag (`enable_reference_images`, etc.) e documenta claramente como habilitar/desabilitar.

---

## 7. Sanitização e segurança
### Considerações dentro de `PersistStorybrandSectionsAgent`
1. Normalizar dados para strings (ex.: se seção for `None`, salvar como `""`).
2. Remover tokens, URLs assinadas ou dados sensíveis (caso apareçam nos textos) antes de persistir.
3. Incluir logs estruturados (`log_struct_event`) com `event="storybrand_sections_persisted"`, `session_id`, `has_gcs_upload`, `sections_count`.

### Justificativa
Seguir padrões de observabilidade e segurança já adotados em `persist_final_delivery`, além de evitar vazamento de conteúdos críticos em caso de uso de fallback com dados sensíveis.

---

## Resumo do fluxo após implementação
1. `StoryBrandSectionRunner` gera e salva os 16 blocos em `state`.
2. `PersistStorybrandSectionsAgent` (novo) persiste o conteúdo completo e registra caminhos.
3. `FallbackStorybrandCompiler` converte para `StoryBrandAnalysis`.
4. `FallbackQualityReporter` finaliza com métricas.
5. `persist_final_delivery` salva o JSON final e inclui referências às seções completas no `meta.json`.
6. Documentação e testes garantem visibilidade e confiabilidade do novo artefato.

---

## Próximos passos sugeridos
- Executar `make test` após implementar para assegurar que novos testes passam e não afetam suíte existente.
- Validar manualmente um cenário com fallback: checar `artifacts/storybrand/<session_id>.json` e `meta.json`.
- Atualizar qualquer pipeline de ingestão externo que deseje consumir o StoryBrand completo usando os novos campos (`storybrand_sections_saved_path`, `storybrand_sections_gcs_uri`).
