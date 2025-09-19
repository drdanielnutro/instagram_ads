# Plano de Integração da Geração de Imagens com Transformação Consistente (Gemini 2.5 Flash Image Preview) no Pipeline ADK

## 1. Objetivo
Adicionar a geração de nove imagens com transformação consistente (três por variação: estado atual, estado intermediário e estado aspiracional) logo após a produção do JSON final pelo pipeline ADK, garantindo que as seis URLs (3 GCS + 3 Signed URLs) por variação fiquem disponíveis no `final_code_delivery` entregue ao frontend e persistido no GCS.

## 2. Estado Atual
- `final_assembler` grava o JSON final em `final_code_delivery` (incluindo `descricao_imagem`, `prompt_estado_atual`, `prompt_estado_intermediario` e `prompt_estado_aspiracional`) e aciona `persist_final_delivery` (callback) para salvar o artefato.
- O `execution_pipeline` encerra com `EscalationBarrier(name="final_validation_stage", ...)` seguido de `EnhancedStatusReporter(name="status_reporter_final")`.
- Ainda não há geração de imagens nem campos de artefatos visuais (URIs) anexados às variações.
- Cada variação contém três prompts técnicos (`prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional`) conforme plano `PLAN_THREE_STAGE_IMAGE_TRANSFORMATION.md`.

## 3. Proposta de Arquitetura
1. **Agente dedicado** (`ImageAssetsAgent`) adicionado ao `execution_pipeline` entre `final_validation_stage` e `status_reporter_final`.
2. **Ferramenta de transformação** (`generate_transformation_images_tool`) que:
   - Recebe `prompt_estado_atual`, `prompt_estado_intermediario` e `prompt_estado_aspiracional` para cada variação.
   - Primeira chamada: gera imagem base apenas com `prompt_estado_atual` usando Gemini 2.5 Flash Image Preview.
   - Segunda chamada: usa a imagem base (PIL Image) + prompt intermediário para representar a decisão imediata mantendo cenário/vestuário.
   - Terceira chamada: usa a imagem intermediária + prompt aspiracional para representar o resultado de médio prazo, permitindo mudanças de cenário/roupa.
   - Salva TRÊS imagens por variação no bucket configurado (`DELIVERIES_BUCKET`) em `deliveries/{user_id}/{session_id}/images/`.
   - Retorna 6 URIs por variação (3 GCS + 3 Signed URLs de 24h).
3. **Atualização de estado**: o agente lê `final_code_delivery`, adiciona 6 campos de URIs em cada variação e regrava no estado.
4. **Persistência pós-atualização**: reexecutar `persist_final_delivery` após a atualização para garantir que o JSON com imagens seja persistido.
5. **Eventos de progresso**: o agente emite eventos SSE informando o status ("Gerando imagens 1/3…", "Gerando imagens 2/3…", "Gerando imagens 3/3…") para manter a conexão viva.

## 4. Detalhamento das Alterações Necessárias
### 4.1. Configuração
- `app/config.py`: adicionar parâmetros para timeout, número máximo de retries, quantidade de etapas (`image_transformation_steps=3`) e templates distintos para prompts intermediário/aspiracional.
- Definir env vars esperadas (`VERTEX_PROJECT`, `VERTEX_LOCATION`, `DELIVERIES_BUCKET` já existente).
- Adicionar configuração do template de prompt de transformação.
- Adicionar ao `.env`:
  ```
  GOOGLE_CLOUD_PROJECT=instagram-ads-472021
  GOOGLE_CLOUD_LOCATION=us-central1
  DELIVERIES_BUCKET=project-facilitador-logs-data
  GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json
  IMAGE_GENERATION_TIMEOUT=60
  IMAGE_GENERATION_MAX_RETRIES=3
  IMAGE_TRANSFORMATION_STEPS=3
  IMAGE_INTERMEDIATE_PROMPT_TEMPLATE="...same outfit, same scene..."
  ```

### 4.2. Ferramenta de Transformação de Imagens
- Criar `app/tools/generate_transformation_images.py` com:
  - Cliente Gemini configurado: `client = genai.Client()`.
  - Método assíncrono `generate_transformation_images(
        prompt_atual: str,
        prompt_intermediario: str,
        prompt_aspiracional: str,
        variation_idx: int,
        metadata: dict
    )`.
  - Fluxo de três chamadas encadeadas:
    1. Gerar estado atual (texto → imagem): `client.models.generate_content(model="gemini-2.5-flash-image-preview", contents=[prompt_atual])`.
    2. Transformar para estado intermediário reutilizando a primeira imagem: `client.models.generate_content(model="gemini-2.5-flash-image-preview", contents=[transform_prompt_intermediario, image_atual])`.
    3. Transformar para estado aspiracional reutilizando a imagem intermediária: `client.models.generate_content(model="gemini-2.5-flash-image-preview", contents=[transform_prompt_aspiracional, image_intermediaria])`.
  - Upload de TRÊS imagens ao GCS:
    - `deliveries/{user_id}/{session_id}/images/estado_atual_{idx}.png`
    - `deliveries/{user_id}/{session_id}/images/estado_intermediario_{idx}.png`
    - `deliveries/{user_id}/{session_id}/images/estado_aspiracional_{idx}.png`
  - Retorno estruturado com 6 URLs por variação:
    ```json
    {
      "estado_atual": {"gcs_uri": "gs://...", "signed_url": "https://..."},
      "estado_intermediario": {"gcs_uri": "gs://...", "signed_url": "https://..."},
      "estado_aspiracional": {"gcs_uri": "gs://...", "signed_url": "https://..."}
    }
    ```
  - Tratamento de erros com retries preservando consistência visual e registrando etapa que falhou.
  - As chamadas síncronas do cliente Gemini devem ser executadas via `asyncio.to_thread(...)` para manter o agente não bloqueante em todas as etapas.

### 4.2.1. Detalhamento da Lógica de Transformação
- **Consistência Visual**: A segunda chamada recebe a imagem gerada na primeira e a terceira chamada recebe a imagem intermediária, garantindo mesma persona e evolução natural.
- **Template Intermediário**: "Show the same person, same outfit, same environment taking the first confident step: {prompt_intermediario}. Keep lighting and framing consistent." (configurável via `IMAGE_INTERMEDIATE_PROMPT_TEMPLATE`).
- **Template Aspiracional**: "Show the same person after some time has passed: {prompt_aspiracional}. Preserve facial features and identity while allowing environment/wardrobe upgrades.".
- **Paralelização**: Processar as 3 variações em paralelo com `asyncio.gather()` para manter performance (~30s total para 3 variações).


### 4.2.2. Importações e Inicialização dos Clientes
- **Importações necessárias**:
  ```python
  # Cliente Gemini via Vertex AI
  from google import genai
  from google.genai import types

  # Manipulação de imagens
  from PIL import Image
  from io import BytesIO

  # Google Cloud Storage
  from google.cloud import storage
  from datetime import timedelta

  # Assíncrono e tipos
  import asyncio
  from typing import Dict, Any, Tuple, Optional

  # Resiliência e logging
  import logging
  from tenacity import retry, stop_after_attempt, wait_exponential

  # Configuração do projeto
  import os
  import json
  from app.config import config
  ```

- **Inicialização do Cliente Gemini**:
  ```python
  # Cliente Gemini (usa ADC configurado via sa-key.json)
  client = genai.Client(
      # O cliente detecta automaticamente projeto/location do ADC
      # Caso necessário, pode-se especificar explicitamente:
      # project=os.getenv("GOOGLE_CLOUD_PROJECT", "instagram-ads-472021"),
      # location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
  )
  ```

- **Inicialização do Cliente GCS**:
  ```python
  # Cliente para Google Cloud Storage
  storage_client = storage.Client()
  bucket_name = os.getenv("DELIVERIES_BUCKET", "project-facilitador-logs-data")
  bucket = storage_client.bucket(bucket_name)
  ```

- **Configuração de Retry com Tenacity**:
  ```python
  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential(multiplier=1, min=4, max=10)
  )
  async def generate_with_retry(client, model, contents):
      """Wrapper para chamadas ao Gemini com retry automático"""
      return await asyncio.to_thread(
          client.models.generate_content,
          model=model,
          contents=contents
      )
  ```

- **Estrutura da Função Principal**:
  ```python
  async def generate_transformation_images(
      prompt_atual: str,
      prompt_intermediario: str,
      prompt_aspiracional: str,
      variation_idx: int,
      metadata: Dict[str, Any]
  ) -> Dict[str, Any]:
      """
      Gera trio de imagens com transformação consistente.

      Args:
          prompt_atual: Prompt para estado de dor/frustração
          prompt_intermediario: Prompt para ação imediata mantendo cenário/vestuário
          prompt_aspiracional: Prompt para estado transformado
          variation_idx: Índice da variação (0, 1, 2)
          metadata: user_id, session_id, formato, etc.

      Returns:
          Dict com 6 URLs (3 GCS + 3 signed)
      """
      user_id = metadata.get("user_id")
      session_id = metadata.get("session_id")

      # Implementação das três chamadas encadeadas...
  ```

### 4.3. Novo agente sequencial
- Implementar `ImageAssetsAgent(BaseAgent)` em `app/agent.py` ou arquivo dedicado:
  - Localizar `final_code_delivery` no estado; abortar com evento de erro se ausente.
  - Converter para `list[dict]` (usar `json.loads` se string).
  - Iterar sobre variações (3 previstas, gerando 3 imagens cada):
    - Emitir evento de status ("Gerando imagens 1/3...", "Gerando imagens 2/3...", "Gerando imagens 3/3...").
    - Chamar `generate_transformation_images_tool` com `prompt_estado_atual`, `prompt_estado_intermediario` e `prompt_estado_aspiracional`.
    - Em caso de sucesso: anexar 6 URIs aos campos da variação:
      * `image_estado_atual_gcs`
      * `image_estado_atual_url`
      * `image_estado_intermediario_gcs`
      * `image_estado_intermediario_url`
      * `image_estado_aspiracional_gcs`
      * `image_estado_aspiracional_url`
    - Em caso de falha não recuperável: registrar campo `image_generation_error` mantendo estrutura do JSON.
  - Atualizar `final_code_delivery` no estado (string JSON) com campos novos.
  - Reexecutar `persist_final_delivery(callback_context)` manualmente para sobrescrever JSON com a versão final.
  - Registrar caminhos (`state["image_assets"]=...`) para uso posterior ou auditoria.

### 4.4. Ajustes no pipeline
- Atualizar `execution_pipeline.sub_agents` para incluir `ImageAssetsAgent` antes do `status_reporter_final`.
- Garantir que o `EnhancedStatusReporter` final continue funcionando com novos campos.
- Atualizar mensagem final para sinalizar "Imagens geradas e salvas (9 imagens)".

### 4.5. Persistência e delivery
- Conferir `persist_final_delivery` para confirmar idempotência e permitir múltiplas execuções.
- Opcional: estender `app/routers/delivery.py` para expor lista das imagens em nova rota `/delivery/final/images`.

### 4.6. Observabilidade e Testes
- Logging detalhado no agente e na tool (sucesso/falha, URIs gerados, tempo de geração).
- Métricas/contadores simples (ex.: número de retries, tempo por etapa) via logging estruturado.
- Testes:
  - Unit: mock da tool para validar atualização do JSON e chamadas ao persist.
  - Integração: cenário end-to-end com geração mockada. Validar que `final_code_delivery` persistido inclui todos os 6 URIs por variação e respeita a ordem das etapas.
  - Verificação manual: rodar `make dev`, executar pipeline, verificar SSE e arquivos em `artifacts/ads_final` + GCS.

### 4.7. Documentação
- Atualizar `README.md` ou docs específicos explicando:
  - Como configurar credenciais para Gemini 2.5 Flash Image Preview:
    - Configurar service account com permissões adequadas (roles/aiplatform.user)
    - Definir GOOGLE_APPLICATION_CREDENTIALS apontando para sa-key.json
    - Verificar que o projeto tem a API Vertex AI habilitada
  - Como os 6 URIs de imagens aparecem no JSON final (3 por variação).
  - Estrutura de nomenclatura: `estado_atual_{0,1,2}.png`, `estado_intermediario_{0,1,2}.png` e `estado_aspiracional_{0,1,2}.png`.
  - Políticas de expiração (Signed URLs 24h, retention em GCS etc.).
  - Tempo estimado: ~30-40s sequencial, ~20s com paralelização.
  - Referenciar `PLAN_THREE_STAGE_IMAGE_TRANSFORMATION.md` como plano complementar para narrativa em três atos.

## 5. Riscos e Mitigações
- **Timeout SSE**: mitigado com eventos de progresso detalhados ("Gerando imagem 1/3...", "Gerando imagem 2/3...").
- **Quota/erros Gemini**: implementar retries + fallback de erro no JSON.
- **Consistência visual**: Mantida pelo uso encadeado das imagens (atual → intermediária → aspiracional) como entrada das chamadas subsequentes.
- **Persistência duplicada**: confirmar idempotência de `persist_final_delivery`.
- **Latência/tempo de geração**: Mitigado com paralelização das 3 variações (asyncio.gather) mesmo com 3 etapas por variação.
- **Custo**: 9 chamadas (3 variações × 3 etapas) vs 3 originais, justificado pela narrativa em três atos; monitorar uso para evitar excesso.

## 6. Próximos Passos
1. Validar plano com stakeholders.
2. Implementar tool de transformação com lógica de três chamadas encadeadas + agente atualizado.
3. Ajustar pipeline e persistência para suportar 9 imagens totais (3 por variação, 6 URIs por variação).
4. Escrever testes unitários e de integração.
5. Executar validação manual end-to-end com todas as variações.

## 7. Exemplos de Output Esperado

### Antes (atual sem imagens):
```json
{
  "visual": {
    "descricao_imagem": "Mulher de 40 anos inicialmente cansada em cozinha desorganizada, depois confiante preparando refeições",
    "prompt_estado_atual": "tired woman, 40yo, stressed expression, cluttered kitchen...",
    "prompt_estado_intermediario": "same tired woman, same cluttered kitchen, determined expression as she throws junk food away...",
    "prompt_estado_aspiracional": "confident woman, 40yo, organized kitchen, healthy meal prep...",
    "aspect_ratio": "9:16"
  }
}
```

### Depois (com imagens geradas):
```json
{
  "visual": {
    "descricao_imagem": "Mulher de 40 anos inicialmente cansada em cozinha desorganizada, depois confiante preparando refeições",
    "prompt_estado_atual": "tired woman, 40yo, stressed expression, cluttered kitchen, overwhelming meal prep, harsh lighting",
    "prompt_estado_intermediario": "same woman, same outfit and kitchen, determined as she throws fries and ice cream into the trash, warm supportive light",
    "prompt_estado_aspiracional": "same woman healthier and energetic, modern gym setting, athletic outfit, confident smile, natural lighting",
    "image_estado_atual_gcs": "gs://project-facilitador-logs-data/deliveries/user123/session456/images/estado_atual_0.png",
    "image_estado_atual_url": "https://storage.googleapis.com/...(signed-24h)",
    "image_estado_intermediario_gcs": "gs://project-facilitador-logs-data/deliveries/user123/session456/images/estado_intermediario_0.png",
    "image_estado_intermediario_url": "https://storage.googleapis.com/...(signed-24h)",
    "image_estado_aspiracional_gcs": "gs://project-facilitador-logs-data/deliveries/user123/session456/images/estado_aspiracional_0.png",
    "image_estado_aspiracional_url": "https://storage.googleapis.com/...(signed-24h)",
    "aspect_ratio": "9:16"
  }
}
```

## 8. Notas de Implementação

1. O campo `prompt_estado_atual` deve sempre mostrar a persona em situação de dor/frustração
2. O campo `prompt_estado_intermediario` deve manter cenário/vestuário e evidenciar a decisão imediata de mudança
3. O campo `prompt_estado_aspiracional` deve mostrar a MESMA persona transformada positivamente
4. A consistência visual é crítica para a credibilidade da narrativa
5. Evitar transformações impossíveis ou milagrosas para manter conformidade com políticas do Meta
6. O template de transformação deve ser ajustável via configuração para diferentes nichos
7. O cliente genai.Client() usa automaticamente Application Default Credentials (ADC)
8. Se ADC não estiver configurado, definir explicitamente project/location na inicialização
9. Todas as chamadas ao Gemini devem usar o wrapper com retry para resiliência
