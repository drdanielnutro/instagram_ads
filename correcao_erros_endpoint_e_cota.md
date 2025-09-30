# Correção — Erros de Endpoint e de Cota

## Contexto do incidente
- Execução do fallback StoryBrand abortada com `google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED` ao chamar `generate_content_async`.
- Após a interrupção, o frontend continuou consultando `GET /delivery/final/meta`, recebendo `404 Not Found`.
- Logs apontaram `INFO:root:Span ... exceeds limit` e `AFC is enabled with max remote calls: 10`, sugerindo uso excessivo de tokens por requisição.

## Sintomas observados
- Tarefas com landing pages curtas completam; páginas mais longas falham durante o fallback.
- Não há arquivo sidecar de falha em `artifacts/ads_final/meta/` quando o erro ocorre no fallback, logo o endpoint não possui estado para responder 503.
- A pilha de chamadas mostra o fallback executando `LoopAgent` de seções (`app/agents/storybrand_fallback.py`).

## Análise técnica
1. **Entrada grande nos prompts do fallback**
   - Cada seção monta `writer_instruction` incluindo `landing_page_context` completo e um dump JSON de todas as seções aprovadas (`approved_sections`). Referência: `app/agents/storybrand_fallback.py:546-588`.
   - Conforme mais seções são aprovadas, o dump cresce quase linearmente. Para páginas extensas, o prompt pode exceder limites de tokens do modelo `gemini-2.5-flash`, gerando 429.
2. **Limites já aplicados na análise inicial**
   - O extrator `StoryBrandExtractor` trunca a entrada HTML para ~20 k caracteres e usa cache, backoff e semáforo (`app/tools/langextract_sb7.py:447-520`). Isso protege a fase de análise, mas não evita que o fallback expanda o prompt novamente.
3. **Retry e controle de concorrência**
   - `call_with_vertex_retry` (`app/utils/vertex_retry.py:32-160`) limita a concorrência das chamadas do LangExtract a `VERTEX_CONCURRENCY_LIMIT` (padrão 3) e aplica até 5 tentativas com exponencial + jitter.
   - As chamadas de `LlmAgent` no fallback dependem do retry automático do ADK; ao estourar tokens, as tentativas esgotam e o erro propaga.
4. **Endpoint `/delivery/final/meta`**
   - Implementado em `app/routers/delivery.py:99-116`. Retorna:
     - `200` + meta quando existe arquivo.<br>
     - `503` com detalhe salvo por `write_failure_meta` (`app/utils/delivery_status.py`) quando há sidecar de falha.<br>
     - `404` quando nenhum arquivo está presente. Como o 429 ocorreu pós-análise, nenhum sidecar foi gravado e o frontend recebeu 404.

## Recomendações
1. **Reduzir tamanho dos prompts**
   - Resumir ou truncar `approved_sections` antes de serializar. Ex.: limitar cada seção a N caracteres ou extrair apenas pontos principais.
   - Avaliar remoção de campos redundantes do `landing_page_context` no prompt do escritor.
2. **Ajustar parâmetros de ambiente**
   - `FALLBACK_STORYBRAND_MODEL`: trocar para modelo com throughput maior quando disponível.
   - `STORYBRAND_SOFT_CHAR_LIMIT` / `STORYBRAND_HARD_CHAR_LIMIT`: diminuir valores para enviar menos contexto ao fallback.
   - `VERTEX_RETRY_MAX_ATTEMPTS`, `VERTEX_RETRY_BACKOFF_*`: calibrar caso insistência adicional faça sentido operacional.
3. **Propagar falhas ao delivery**
   - Adicionar handler no fallback (ex.: no `LoopAgent` de seções) que, ao capturar exceções definitivas, chame `write_failure_meta`. Isso permitirá ao endpoint retornar 503 com payload explicativo e bloquear polling infinito.
4. **Telemetria**
   - Logar comprimento dos prompts para monitorar aproximações ao limite.
   - Registrar métricas quando o fallback acionar `EventActions(escalate=True)` por causa de 429.

## Próximos passos sugeridos
1. Implementar truncagem/resumo de `approved_sections` e validar `make lint && make test`.
2. Realizar teste com landing page “grande” monitorando tamanho de prompt, consumo e sucesso.
3. Ajustar frontend para tratar `503` com detalhes de falha, evitando tentativas infinitas.

---
Documento elaborado a partir da inspeção dos arquivos `app/agents/storybrand_fallback.py`, `app/tools/langextract_sb7.py`, `app/utils/vertex_retry.py`, `app/routers/delivery.py` e logs de execução recentes.
