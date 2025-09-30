# Registro de Contexto — Sessão Codex

## Linha do tempo do diálogo
- **Leitura inicial:** Usuário solicitou a leitura de `README.md`; Codex resumiu os pontos principais do sistema multiagente e do problema de travamento.
- **Diagnóstico adicional:** Usuário pediu análise do documento `correcao_erros_endpoint_e_cota.md`; Codex confirmou que o crescimento dos prompts no fallback pode explicar o erro 429.
- **Discussão sobre origem do erro:** Usuário questionou se o tamanho do HTML era o real culpado; Codex apontou que o `process_and_extract_sb7` já usa texto limpo e truncado, e que o problema está na serialização de `approved_sections` em `storybrand_fallback.py`.
- **Avaliação do fluxo padrão vs. fallback:** Usuário compartilhou `.env` e pediu rastreamento da criação do StoryBrand quando o fallback está desligado. Codex mapeou:
  - **Fase padrão:** `landing_page_analyzer` → `web_fetch_tool` → callback `process_and_extract_sb7` → `StoryBrandExtractor` (LangExtract/Vertex). Referências: `app/agent.py:628-689`, `app/callbacks/landing_page_callbacks.py:65-199`, `app/tools/langextract_sb7.py:446-551`.
  - **Gate:** `StoryBrandQualityGate` decide com base em `config.min_storybrand_completeness`; fallback só roda se `ENABLE_STORYBRAND_FALLBACK=true` **e** `ENABLE_NEW_INPUT_FIELDS=true`. Referência: `app/agents/storybrand_gate.py:20-126`.
  - **Fallback ligado:** pipeline `fallback_storybrand_pipeline` recompõe 16 seções, revisa com loops limitados, compila em `StoryBrandAnalysis` score 1.0. Referências: `app/agents/storybrand_fallback.py:200-731`, `app/agents/fallback_compiler.py:83-279`.
  - **Fallback desligado:** gate registra bloqueio (`block_reason='fallback_disabled'`) e continua para planejamento mesmo com StoryBrand incompleto. Falhas Vertex assinaladas por `_mark_storybrand_failure` (`app/callbacks/landing_page_callbacks.py:17-63`).

## Última mensagem do Codex (contexto técnico)
> O StoryBrand "fraco" nasce antes do gate, durante o `landing_page_stage`: o agente `landing_page_analyzer` chama `web_fetch_tool` e, logo depois, o callback `process_and_extract_sb7` roda o `StoryBrandExtractor` com LangExtract/Vertex AI (`app/agent.py:628-689`, `app/callbacks/landing_page_callbacks.py:65-199`). Esse callback prefere o texto limpo vindo da Trafilatura, aplica truncagem configurável (12k caracteres por padrão) e salva `storybrand_analysis`, `storybrand_summary` e `storybrand_ad_context` no estado mesmo que o score seja baixo (`app/callbacks/landing_page_callbacks.py:99-186`). Ou seja, com fallback desligado, todo o pipeline feliz continua recebendo esses campos — só que com `completeness_score` pequeno.
>
> - **Fase sem fallback**
>   - O `StoryBrandExtractor` normaliza o payload, corta head+tail se passar dos limites (`app/tools/langextract_sb7.py:446-495`) e chama Vertex sob `call_with_vertex_retry`, respeitando `VERTEX_CONCURRENCY_LIMIT` (seu `.env` fixa em 1) e até cinco tentativas com backoff (`app/tools/langextract_sb7.py:511-551`, `app/utils/vertex_retry.py:32-161`).
>   - Se Vertex saturar (429/503), `_mark_storybrand_failure` grava `final_delivery_status`, persiste sidecar de falha e marca `force_storybrand_fallback` (`app/callbacks/landing_page_callbacks.py:17-63`). Com fallback desativado (`ENABLE_STORYBRAND_FALLBACK=false` ou `ENABLE_NEW_INPUT_FIELDS=false`), o gate bloqueia o caminho alternativo e apenas registra `block_reason='fallback_disabled'` (`app/agents/storybrand_gate.py:47-109`). Resultado: o orquestrador segue para o planejamento com o StoryBrand incompleto; se o LangExtract travar antes de devolver algo, a sessão fica parada nessa etapa porque não há rota de recuperação.
>   - O enriquecimento posterior do contexto de landing page simplesmente replica o que vier de `storybrand_ad_context` sem reforçar a completude (`app/callbacks/landing_page_callbacks.py:292-335`).
>
> - **Quando o fallback está ligado**
>   - O gate avalia `score < config.min_storybrand_completeness` (0.6 por padrão) e, se `ENABLE_STORYBRAND_FALLBACK=true` **e** `ENABLE_NEW_INPUT_FIELDS=true`, executa `fallback_storybrand_pipeline` antes de chamar `PlanningOrRunSynth` (`app/agents/storybrand_gate.py:49-126`, `app/agent.py:1270-1277`).
>   - O fallback roda em cinco fases: `FallbackInputInitializer`, `fallback_input_collector`, `StoryBrandSectionRunner`, `FallbackStorybrandCompiler`, `FallbackQualityReporter`, com loops limitados e score final forçado a 1.0 (`app/agents/storybrand_fallback.py:200-731`, `app/agents/fallback_compiler.py:246-270`).
>   - Cada seção pode disparar múltiplas chamadas ao modelo (writer + reviewer + corrector), mas `MAX_ITERATIONS` controla o total. Logs ficam em `storybrand_audit_trail` e `storybrand_gate_metrics`.
>
> Portanto, a criação inicial do StoryBrand (mesmo fraco) é sempre responsabilidade do LangExtract via `landing_page_analyzer`. Quando o fallback está desligado, qualquer travamento acontece antes do gate porque a chamada ao LangExtract/Vertex é a única fonte de dados. Com fallback ligado, scores baixos (<0.6) ou falhas sinalizadas pelo callback disparam o pipeline alternativo que recompõe a narrativa e garante score cheio antes do planejamento.
>
> Possíveis próximos passos:
> 1. Habilitar temporariamente `ENABLE_NEW_INPUT_FIELDS=true` e `ENABLE_STORYBRAND_FALLBACK=true` para validar se o fallback recupera essa página problemática.
> 2. Se quiser manter fallback off, reduzir `STORYBRAND_SOFT_CHAR_LIMIT`/`HARD_CHAR_LIMIT` ou pré-processar o HTML antes do LangExtract para evitar 429 na fase inicial.

## Ideias para localizar o ponto exato da exaustão Vertex (RESOURCE_EXHAUSTED)
- **Instrumentar logs do callback** `process_and_extract_sb7`: registrar início/fim de cada chamada ao `StoryBrandExtractor`, incluindo tamanho do payload pós-truncagem (`truncation_info`) e tentativas consumidas pelo `call_with_vertex_retry`.
- **Adicionar telemetria no LangExtract** (`app/tools/langextract_sb7.py`): logar `prepared_input` length, número de passes, e quando `_prepare_input` aplicar head+tail; emitir métrica customizada (`storybrand.langextract.prompt_chars`).
- **Correlacionar com `vertex_retry`**: no `call_with_vertex_retry`, habilitar logs em nível INFO para cada retry (`vertex_call_retry`) com `status_code` 429/503 e `retry_after`. Checar se o semáforo (`VERTEX_CONCURRENCY_LIMIT`) está segurando múltiplas requisições simultâneas.
- **Capturar stack traces do ADK** em modo debug (`STORYBRAND_GATE_DEBUG=true`) para garantir que o travamento não ocorra em outra etapa (ex.: bloqueio no próprio ADK aguardando callback).
- **Testes controlados**: usar duas URLs (uma “pequena” e a problemática) e comparar resultados do `storybrand_timing` salvo no estado (`app/callbacks/landing_page_callbacks.py:151-160`) e do arquivo de falha (`write_failure_meta`).
- **Fallback forçado como controle**: executar com `ENABLE_STORYBRAND_FALLBACK=true` e `force_storybrand_fallback=true` para ver se a mesma página completa o fallback — se sim, confirma que o gargalo é na chamada direta ao LangExtract e não no restante da pipeline.
- **Dump temporário de prompts**: em ambiente dev, persistir o texto enviado ao `StoryBrandExtractor` quando `len(input_text)` ultrapassar um limiar (ex.: 12k) para inspeção offline; remover após diagnóstico.


---

## Notas adicionais (interação recente sobre Makefile e flags)
- `make dev` apenas exporta `GOOGLE_APPLICATION_CREDENTIALS` e chama `make dev-all`; ele não carrega automaticamente variáveis do `.env`. Referência: `Makefile` linhas 17-52.
- `dev-backend-all` invoca `uv run uvicorn app.server:app --reload`, portanto o processo depende das variáveis já presentes no ambiente antes do comando (`Makefile:41-50`).
- A configuração dinâmica das flags (`enable_new_input_fields`, `enable_storybrand_fallback`, `storybrand_gate_debug`) acontece em `app/config.py`: o objeto `config` lê defaults e sobrescreve com valores de `os.getenv` durante a importação (`app/config.py:52-122`). Se elas não estiverem exportadas, o gate nunca habilita o fallback e grava `block_reason="fallback_disabled"`.
- Solução sugerida para carregar `.env` automaticamente no target `dev`:
  ```make
  dev: check-and-kill-ports
  	@set -a; \
  	  if [ -f .env ]; then source .env; fi; \
  	  export GOOGLE_APPLICATION_CREDENTIALS=$${GOOGLE_APPLICATION_CREDENTIALS:-./sa-key.json}; \
  	  echo "Using GOOGLE_APPLICATION_CREDENTIALS=$${GOOGLE_APPLICATION_CREDENTIALS}"; \
  	  if [ ! -f "$${GOOGLE_APPLICATION_CREDENTIALS}" ]; then \
  	    echo "⚠️  Service account key not found at $${GOOGLE_APPLICATION_CREDENTIALS}. Continuing with ADC credentials (Signed URLs may fail)."; \
  	  fi; \
  	  make dev-all
  ```
- Com `set -a`, todas as variáveis do `.env` ficam exportadas para o subshell que chama `make dev-all`, garantindo que `config.enable_new_input_fields`, `config.enable_storybrand_fallback` e `config.storybrand_gate_debug` recebam os valores desejados.
- Após alterar o Makefile e reiniciar, verificar no log do backend se `fallback_enabled=True` aparece no evento `storybrand_gate_decision` para confirmar que o fallback está efetivamente ativo.

