# Playbook – Referências Visuais (Auditoria, Monitoramento e Rollout)

## 1. Visão Geral
- A funcionalidade de referências visuais é controlada pela flag `ENABLE_REFERENCE_IMAGES` (default `False`). O valor pode ser sobrescrito via variável de ambiente e lido em `app/config.py`. 【F:app/config.py†L82-L207】
- Quando ativada, expõe o endpoint `POST /upload/reference-image`, enriquece o `/run_preflight` com `reference_images` e faz com que o `ImageAssetsAgent` injete `visual.reference_assets` no JSON final. 【F:app/server.py†L181-L417】【F:app/agent.py†L428-L910】【F:app/callbacks/persist_outputs.py†L58-L215】
- O termo operacional **`image_generation_audit`** referencia o conjunto de sinais armazenados em `state['image_assets']`, `state['reference_images']` e nos eventos do `delivery_audit_trail`. Esses campos já são persistidos no `meta.json` sanitizado e podem ser consultados após cada execução. 【F:app/agent.py†L428-L910】【F:app/utils/audit.py†L1-L40】【F:app/callbacks/persist_outputs.py†L58-L215】

## 2. Auditoria (state & artefatos)
1. **Resumo estruturado (`state['image_assets']`)**
   - Preenchido pelo `ImageAssetsAgent` com status por variação, uso de referências e notas de SafeSearch. 【F:app/agent.py†L828-L910】
   - Persistido em `meta.json` como `image_assets`/`reference_images` e enriquecido com TTL/expiração calculados. 【F:app/callbacks/persist_outputs.py†L58-L215】
2. **Trilha de auditoria (`delivery_audit_trail`)**
   - Cada etapa do agente gera um evento via `append_delivery_audit_event` indicando sucesso, falhas ou motivos de reprovação. 【F:app/utils/audit.py†L1-L40】【F:app/agent.py†L430-L910】
   - Para reconstruir o histórico, busque pelo evento `image_assets_agent` no audit trail; este é o insumo base para dashboards internos.
3. **Logs estruturados**
   - Upload: `reference_image_upload_start|success|failed|rejected` com metadata (usuário, tamanho, tipo). 【F:app/server.py†L181-L272】
   - Preflight: `preflight_reference_images_resolved` (ou `..._ignored` quando a flag está off). 【F:app/server.py†L569-L659】
   - Execução: `image_assets_generation_start` e `image_assets_generation_complete`, com resumos de referências usadas e erros críticos. 【F:app/agent.py†L582-L910】
4. **Artefatos persistidos**
   - `artifacts/ads_final/*.json` recebem `visual.reference_assets` sanitizados; URLs assinadas expiram conforme `image_signed_url_ttl`. 【F:app/callbacks/persist_outputs.py†L101-L215】

> **Consulta rápida**: para investigar uma sessão, abra `meta.json` correspondente e verifique `reference_images_present`, `reference_images`, `image_assets` e os eventos do audit trail.

## 3. Monitoramento Contínuo
- **Métricas recomendadas**
  - Contar uploads aprovados vs. rejeitados (`reference_image_upload_*`).
  - Percentual de execuções com `reference_images_present=true` e `grade=pass` no evento `image_assets_generation_complete`.
  - Falhas críticas (`critical_errors`) e motivos agregados de reprovação (`reference_parse_errors`).
- **Alertas sugeridos**
  - Taxa de erro do endpoint >3% (HTTP 4xx/5xx) em 5 minutos.
  - Erros de Vision (`vision_analysis_error`) consecutivos em 3 uploads.
  - `image_assets_review_failed` sinalizado no estado em mais de 5% das execuções por hora. 【F:app/agent.py†L840-L910】
- **Política de retenção**
  - Cache local: TTL de 1 h configurado em `reference_cache_ttl_seconds`. Ajuste conforme capacidade de memória. 【F:app/config.py†L82-L108】
  - URLs assinadas: padrão 24 h (`image_signed_url_ttl`). Considere reduzir em ambientes sensíveis. 【F:app/config.py†L85-L181】【F:app/callbacks/persist_outputs.py†L58-L137】
  - Buckets: configure rotinas externas de limpeza usando o campo `signed_url_expires_at` persistido no meta.

## 4. Plano de Rollout (`ENABLE_REFERENCE_IMAGES`)
1. **Preparação**
   - Garantir variáveis `REFERENCE_IMAGES_BUCKET` (GCS) e `ENABLE_REFERENCE_IMAGES=false` em todos os ambientes.
   - Validar uploads com flag desligada para confirmar respostas `403`. 【F:app/server.py†L181-L215】
2. **Canário interno**
   - Habilitar `ENABLE_REFERENCE_IMAGES=true` apenas em um ambiente de QA.
   - Executar os quatro cenários (sem referência, personagem, produto, ambos) e revisar `meta.json`/audit trail.
3. **Expansão gradual**
   - Promover para staging com monitoramento dos eventos `reference_image_upload_*` e `image_assets_generation_complete`.
   - Ativar progressivamente em produção (ex.: 10% → 50% → 100%), ajustando o frontend para exibir upload somente quando o flag SSE indicar disponibilidade.
4. **Comunicação**
   - Informar times de atendimento sobre o limite de 5 MB e formatos suportados.
   - Atualizar documentação externa/FAQ com prazo de expiração das URLs assinadas.

## 5. Plano de Rollback
1. **Desativar flag**: redefinir `ENABLE_REFERENCE_IMAGES=false` e reiniciar os pods/serviços para limpar o cache em memória. 【F:app/config.py†L82-L207】【F:app/utils/reference_cache.py†L18-L123】
2. **Limpeza de cache**: invalidar manualmente quaisquer entradas remanescentes (reinício do serviço ou limpeza explícita do backend compartilhado futuro).
3. **Sanear GCS**: executar job de remoção para arquivos enviados durante a janela problemática usando `signed_url_expires_at` como corte.
4. **Auditar sessões**: revisar `delivery_audit_trail` e `meta.json` das execuções impactadas para garantir que nenhuma referência rejeitada foi aplicada.
5. **Comunicação**: registrar incidente e avisar o time de produto/QA sobre o retorno ao comportamento legado (3 variações sem referências).

## 6. Checklist Operacional
- [ ] Flag e variáveis revisadas em todos os ambientes.
- [ ] Buckets e TTL documentados para SRE.
- [ ] Painéis configurados para eventos `reference_image_*` e `image_assets_generation_*`.
- [ ] Processo de limpeza periódica acordado com Data/SRE.
- [ ] Canal de comunicação pronto para avisar stakeholders durante rollout/rollback.
