# Plano de Integração da Geração Determinística de Imagens (Vertex AI) no Pipeline ADK

## 1. Objetivo
Adicionar a geração determinística de três imagens (uma por variação do anúncio) logo após a produção do JSON final pelo pipeline ADK, garantindo que as URLs das imagens fiquem disponíveis no `final_code_delivery` entregue ao frontend e persistido no GCS.

## 2. Estado Atual
- `final_assembler` grava o JSON final em `final_code_delivery` (incluindo `descricao_imagem` e o novo `prompt_imagem`) e aciona `persist_final_delivery` (callback) para salvar o artefato.
- O `execution_pipeline` encerra com `EscalationBarrier(name="final_validation_stage", ...)` seguido de `EnhancedStatusReporter(name="status_reporter_final")`.
- Ainda não há geração de imagens nem campos de artefatos visuais (URIs) anexados às variações.

## 3. Proposta de Arquitetura
1. **Agente dedicado** (`ImageAssetsAgent`) adicionado ao `execution_pipeline` entre `final_validation_stage` e `status_reporter_final`.
2. **Ferramenta determinística** (`generate_vertex_image_tool`) que:
   - Recebe `prompt_imagem` (como texto técnico principal), `descricao_imagem` para contexto complementar, `seed` fixa (configurável) e metadados (ex.: `formato`, `variação`).
   - Invoca a Vertex AI (modelo `gemini-2.5-flash-image-preview`) usando ADC.
   - Salva a imagem produzida no bucket configurado (`DELIVERIES_BUCKET` ou variação) em `deliveries/{user_id}/{session_id}/images/`.
   - Retorna URIs (`gs://...`) e, opcionalmente, Signed URL (curta duração) para uso imediato.
3. **Atualização de estado**: o agente lê `final_code_delivery`, adiciona campos `image_gcs_uri` (e opcionalmente `image_signed_url`, `image_seed`) em cada variação e regrava a lista no estado.
4. **Persistência pós-atualização**: reexecutar `persist_final_delivery` (ou mover o callback) após a atualização para garantir que o JSON com imagens seja o conteúdo final salvo/entregue.
5. **Eventos de progresso**: o agente emite eventos SSE informando o status (“Gerando imagem 1/3…”, “Upload concluído”, etc.) para manter a conexão viva.

## 4. Detalhamento das Alterações Necessárias
### 4.1. Configuração
- `app/config.py`: adicionar parâmetros para seed determinística (`image_generation_seed`), timeout, número máximo de retries e modelo Vertex.
- Definir env vars esperadas (`VERTEX_PROJECT`, `VERTEX_LOCATION`, `DELIVERIES_BUCKET` já existente). Documentar em `README.md`/`.env`.

### 4.2. Ferramenta Vertex AI
- Criar `app/tools/generate_vertex_image.py` (ou similar) com:
  - Cliente Vertex configurado via ADC (`google.genai.Client` ou Vertex SDK).
  - Método assíncrono `generate_vertex_image(prompt: str, seed: int, **metadata)`.
  - Upload ao GCS usando `google.cloud.storage.Blob.upload_from_string` (content-type adequado, ex.: `image/png`).
  - Retorno estruturado `{ "status": "ok", "gcs_uri": ..., "signed_url": ..., "variation_index": ... }`.
  - Tratamento de erros com retries (ex.: `tenacity` ou estratégia manual) preservando seed fixo.

### 4.3. Novo agente sequencial
- Implementar `ImageAssetsAgent(BaseAgent)` em `app/agent.py` ou arquivo dedicado:
  - Localizar `final_code_delivery` no estado; abortar com evento de erro se ausente.
  - Converter para `list[dict]` (usar `json.loads` se string).
  - Iterar sobre variações (3 previstas):
    - Emitir evento de status.
    - Chamar `generate_vertex_image_tool` (com `prompt_imagem` como prompt principal, `descricao_imagem` como referência adicional, seed, info do formato, user/session). Seed pode ser derivada de `seed_base + idx` para diferenciar variações mantendo determinismo.
    - Em caso de sucesso: anexar URIs aos campos da variação.
    - Em caso de falha não recuperável: registrar campo `image_generation_error` mantendo estrutura do JSON; continuar com próximas variações.
  - Atualizar `final_code_delivery` no estado (string JSON) com campos novos.
  - Reexecutar `persist_final_delivery(callback_context)` manualmente para sobrescrever JSON e metadados com a versão final.
  - Registrar caminhos (`state["image_assets"]=...`) para uso posterior ou auditoria.

### 4.4. Ajustes no pipeline
- Atualizar `execution_pipeline.sub_agents` para incluir `ImageAssetsAgent` antes do `status_reporter_final`.
- Garantir que o `EnhancedStatusReporter` final continue funcionando com novos campos; se necessário, atualizar mensagem para sinalizar “Imagens geradas e salvas”.

### 4.5. Persistência e delivery
- Conferir `persist_final_delivery` para confirmar idempotência e permitir múltiplas execuções (possivelmente sobrescrevendo o arquivo anterior no mesmo timestamp ou registrando novo).
- Opcional: estender `app/routers/delivery.py` para expor lista das imagens (ex.: nova rota `/delivery/final/images` ou inclusão das URIs em `meta`).

### 4.6. Observabilidade e Testes
- Logging detalhado no agente e na tool (sucesso/falha, URIs gerados, tempo de geração).
- Métricas/contadores simples (ex.: número de retries) via logging estruturado.
- Testes:
  - Unit: mock da tool para validar atualização do JSON e chamadas ao persist.
  - Integração: cenário end-to-end com geração mockada (substituindo Vertex por stub). Validar que `final_code_delivery` persistido inclui URIs.
  - Verificação manual: rodar `make dev`, executar pipeline, verificar SSE e arquivos em `artifacts/ads_final` + GCS.

### 4.7. Documentação
- Atualizar `README.md` ou docs específicos explicando:
  - Como configurar credenciais Vertex.
  - Como os URIs de imagens aparecem no JSON final.
  - Políticas de expiração (Signed URLs 24h, retention em GCS etc.).

## 5. Riscos e Mitigações
- **Timeout SSE**: mitigado com eventos de progresso.
- **Quota/erros Vertex**: implementar retries + fallback de erro no JSON.
- **Determinismo**: seed fixa documentada; evitar parâmetros aleatórios.
- **Persistência duplicada**: confirmar idempotência de `persist_final_delivery` ou mover persistência para o novo agente.

## 6. Próximos Passos
1. Validar plano com stakeholders.
2. Implementar tool + agente, ajustar pipeline e persistência.
3. Escrever testes e atualizar documentação.
4. Executar validação manual end-to-end.
