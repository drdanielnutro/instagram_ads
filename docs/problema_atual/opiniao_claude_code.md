ANÁLISE ULTRATHINK: ANATOMIA DO ERRO RESOURCE_EXHAUSTED

1. NATUREZA MULTIDIMENSIONAL DO ERRO
   O erro RESOURCE_EXHAUSTED é ambíguo por design - não informa diretamente qual dimensão de cota foi violada. Segundo a documentação e código do projeto, existem pelo menos 7 dimensões diferentes que podem causar este erro:
   A. Rate Limits (Limites de Taxa)
   RPM (Requisições Por Minuto) - Ex: 120 RPM para Gemini 2.5 Flash no tier padrão
   TPM (Tokens Por Minuto) - Ex: 4.000.000 TPM para Gemini 2.0 Flash
   RPD (Requisições Por Dia) - Ex: 100 RPD para Gemini 2.5 Pro no tier Free
   B. Limites de Throughput
   Pages Per Minute (Páginas/min) - Document AI: 120 páginas/minuto
   Concurrent Requests (Requisições Simultâneas) - Ex: 5 batch jobs concorrentes
   Payload Size (Tamanho da Requisição) - 20 MB inline, 2 GB via File API
   Token Count Per Request - Input + Output tokens dentro da janela de contexto

2. DISTINÇÃO CRÍTICA: DOIS SISTEMAS DE COTAS
   A documentação vertex_doc_limites.md:14-35 revela uma armadilha fundamental:
   Sistema de Cota Padrão (Tradicional):
   429 RESOURCE_EXHAUSTED → SEU projeto excedeu SUA cota específica
   Solução: Verificar consumo + solicitar aumento de cota
   Dynamic Shared Quota (DSQ) - Gemini 2.x:
   429 RESOURCE_EXHAUSTED → Pool GLOBAL saturado (TODOS os clientes)
   Solução: Retry com backoff exponencial (aumento de cota NÃO resolve!)
   Esta distinção é crucial porque:
   Gemini 2.5 Pro/Flash/Flash-Lite usam DSQ
   Text-bison, modelos AutoML usam Cota Padrão
   O mesmo código de erro tem causas e soluções opostas!

3. METODOLOGIA DE DIAGNÓSTICO
   Read metrics.py
   PASSO 1: Identificar a Exceção e Contexto
   Segundo vertex_retry.py:83-97, o código já detecta:

```
def _is_retryable_exception(exc: BaseException) -> bool:
    status = _extract_status_code(exc)
    if status in {408, 429, 500, 503}:  # 429 = RESOURCE_EXHAUSTED
        return True
    if gcloud_exceptions and isinstance(exc, gcloud_exceptions.ResourceExhausted):
        return True
```

Informações coletáveis da exceção:
status_code: 429 ou 503
exc.**class**.**name**: "ResourceExhausted", "ClientError", etc.
retry_after header (se presente): indica tempo de espera sugerido
Mensagem de erro pode conter pistas sobre o limite específico

PASSO 2: Consultar Cloud Monitoring (Única Fonte de Verdade)
Segundo vertex_doc_limites.md:236-248, as métricas essenciais são:
Consumer Quota metrics:

* quota/{service}/allocation/usage (uso atual)
* quota/{service}/allocation/limit (limite configurado)
* quota/{service}/exceeded (tentativas de exceder)
  Exemplo de query MQL (Monitoring Query Language):

```
fetch consumed_api
| filter service = 'aiplatform.googleapis.com'
| filter quota_metric = 'aiplatform.googleapis.com/generate_content_requests_per_minute_per_project_per_base_model'
| { group_by [quota_metric], .sum() ; .limit() }
| ratio
```

PASSO 3: Inspecionar Logs Estruturados
Segundo correcao_erros_endpoint_e_cota.md:6, os logs fornecem pistas:
INFO:root:Span ... exceeds limit
AFC is enabled with max remote calls: 10
Isso indica limite de tokens por span (AFC = Automatic Function Calling), não limite de requisições.

PASSO 4: Análise de Payload e Tokens
Segundo vertex_doc_limites.md:167-193: Limites multimodais:
Payload inline (Base64): 20 MB (mas pode ser "leniente" se tokens < janela)
File API: 2 GB
Imagens: 3.000 por requisição
Vídeo: 60 min (frames) / 45 min (frames+áudio)
PDFs: 3.000 arquivos, 1.000 páginas/arquivo
Armadilha detectada no projeto: correcao_erros_endpoint_e_cota.md:14-17 mostra que o erro não foi por número de requisições, mas por tamanho do prompt:
Cada seção monta `writer_instruction` incluindo `landing_page_context` completo e um dump JSON de todas as seções aprovadas. Conforme mais seções são aprovadas, o dump cresce quase linearmente, excedendo limites de tokens do gemini-2.5-flash.

4. TIPOS DE EXAUSTÃO E SUAS CAUSAS
   Tipo 1: Taxa de Requisições (RPM/RPD)
   Sintoma: Erro aparece em padrão temporal regular (ex: a cada minuto)
   Causa: Múltiplas requisições concorrentes ou burst de tráfego
   Diagnóstico:

```
gcloud alpha quotas list \
  --service=aiplatform.googleapis.com \
  --filter="metric:generate_content_requests_per_minute"
```

Tipo 2: Taxa de Tokens (TPM)
Sintoma: Erro ocorre mesmo com poucas requisições, mas prompts grandes
Causa: Soma de input + output tokens excede TPM
Diagnóstico:

```
from google.cloud import aiplatform
response = aiplatform.gapic.PredictionServiceClient().count_tokens(
    endpoint=f"projects/{project}/locations/{location}/publishers/google/models/gemini-2.5-flash",
    contents=[{"text": your_prompt}]
)
print(f"Total tokens: {response.total_tokens}")
```

Tipo 3: Concorrência de Processos
Sintoma: Erros ao submeter batch jobs ou múltiplas operações LRO
Causa: Limite de 5 batch jobs simultâneos (Document AI) ou 1 training job
Diagnóstico:

```
gcloud ai custom-jobs list --region=us-central1 --filter="state=RUNNING"
```

Tipo 4: Janela de Contexto (Context Window)
Sintoma: "exceeds limit" ou "input too long" em logs
Causa: Input + Output tokens > max_context_window
Diagnóstico:
Gemini 2.5 Flash: 1.048.576 tokens input, 65.536 output
Gemini 2.0 Flash: 1.048.576 input, 8.192 output (menor!)

Tipo 5: Payload Size
Sintoma: Erro ao enviar mídia grande (imagens/vídeos)
Causa: Arquivo > 20 MB inline ou > 2 GB via File API
Diagnóstico:

```
import base64
payload_size_mb = len(base64.b64encode(file_bytes)) / (1024 * 1024)
print(f"Payload: {payload_size_mb:.2f} MB")
```

Tipo 6: Recursos Computacionais (GPU/CPU)
Sintoma: Erro ao criar custom training job
Causa: Cota regional de vCPUs/GPUs esgotada
Diagnóstico:

```
gcloud compute regions describe us-central1 | grep -i quota
```

Tipo 7: DSQ Pool Saturation (Gemini 2.x)
Sintoma: Erro intermitente, não correlacionado com uso do SEU projeto
Causa: Pool compartilhado global saturado por TODOS os clientes
Diagnóstico: NÃO TEM - sistema opaco, sem métricas por projeto

5. PROCEDIMENTO OPERACIONAL PARA DIAGNÓSTICO

```
# 1. Verificar cotas atuais
gcloud alpha quotas list \
  --service=aiplatform.googleapis.com \
  --filter="quota_id:*gemini*" \
  --format="table(name, quota_id, dimensions, usage, limit)"

# 2. Verificar métricas de uso (últimos 7 dias)
gcloud monitoring time-series list \
  --filter='metric.type="serviceruntime.googleapis.com/quota/rate/net_usage" AND 
            resource.service="aiplatform.googleapis.com"' \
  --format="table(metric.labels.quota_metric, points[0].value)"

# 3. Verificar erros de cota (últimos 1 dia)
gcloud logging read 'severity>=ERROR AND 
  (protoPayload.status.code=8 OR protoPayload.status.code=429)' \
  --limit=50 \
  --format=json

# 4. Contar tokens de um prompt
curl -X POST "https://us-central1-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/us-central1/publishers/google/models/gemini-2.5-flash:countTokens" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"text":"SEU PROMPT AQUI"}]}'
```

6. DECISÃO: QUAL LIMITE FOI EXCEDIDO?

```
┌─────────────────────────────────────────────────────────────┐
│ ÁRVORE DE DECISÃO PARA RESOURCE_EXHAUSTED                  │
└─────────────────────────────────────────────────────────────┘

1. Qual modelo gerou o erro?
   ├─ Gemini 2.x (Pro/Flash/Lite) → DSQ (pule para etapa 5)
   └─ Outros (text-bison, AutoML) → Cota Padrão (continue)

2. Cloud Monitoring mostra quota/exceeded > 0?
   ├─ SIM → Identifique quota_metric específica
   │         Ex: "generate_content_requests_per_minute" = RPM
   │             "generate_content_input_tokens_per_minute" = TPM
   └─ NÃO → Pode ser limite não monitorado (continue)

3. Erro contém "exceeds limit" ou "too large"?
   ├─ SIM → Limite de tamanho (tokens ou payload)
   │         → Use countTokens API para medir prompt
   │         → Verifique se input+output < context_window
   └─ NÃO → Continue

4. Erro ocorre em operação batch ou LRO?
   ├─ SIM → Verifique jobs concorrentes (max 5 batch, 1 training)
   └─ NÃO → Verifique RPM/RPD

5. Sistema DSQ (Gemini 2.x):
   → Erro NÃO indica sua cota, mas saturação global
   → Solução: Backoff exponencial + retry (já implementado)
   → Alternativa: Provisioned Throughput ($$$)
```

7. EVIDÊNCIAS NO SEU CÓDIGO
   Analisando correcao_erros_endpoint_e_cota.md, o erro real foi:
   Tipo: Janela de Contexto (Token Count)
   Causa raiz: Prompts crescendo linearmente com approved_sections
   Dimensão violada: Total tokens (input) > capacidade do modelo de processar eficientemente
   NÃO foi: RPM, TPD, ou número de requisições
   NÃO foi: Payload size (20 MB)
   O código em vertex_retry.py:143-147 registra métricas quando detecta 429:

```
if status_code == 429:
    try:
        record_vertex_429({"stage": "storybrand_langextract"})
```

Mas não captura qual dimensão foi excedida, apenas que houve um 429.

8. RECOMENDAÇÕES PARA INSTRUMENTAÇÃO

```
# Adicionar em vertex_retry.py após linha 142:
def _extract_quota_exceeded_metric(exc: BaseException) -> str | None:
    """Tenta extrair qual métrica de cota foi excedida da exceção."""
    message = str(exc).lower()
    
    if "requests per minute" in message or "rpm" in message:
        return "RPM"
    elif "tokens per minute" in message or "tpm" in message:
        return "TPM"
    elif "requests per day" in message or "rpd" in message:
        return "RPD"
    elif "exceeds limit" in message or "too large" in message:
        return "TOKEN_LIMIT"
    elif "concurrent" in message:
        return "CONCURRENCY"
    else:
        return "UNKNOWN"

# Usar no log (linha 149):
log.warning(
    "vertex_call_retry",
    extra={
        "attempt": attempts,
        "quota_dimension": _extract_quota_exceeded_metric(exc),  # NOVO
        "status_code": _extract_status_code(exc),
        # ... resto
    },
)
```

📊 **RESUMO EXECUTIVO**
Para descobrir qual limite você excedeu ao receber RESOURCE_EXHAUSTED:
Cloud Monitoring → quota/{service}/exceeded metrics (fonte primária)
Logs estruturados → Buscar "exceeds limit", "too large", "quota" na mensagem
countTokens API → Medir tamanho real dos prompts
gcloud CLI → gcloud alpha quotas list para ver limites configurados
Contexto do modelo → Gemini 2.x = DSQ (erro global), outros = cota por projeto

Tipos de exaustão que provocam o erro:
✅ RPM (requisições/minuto) - comum
✅ TPM (tokens/minuto) - muito comum em Gemini
✅ RPD (requisições/dia) - tier Free
✅ Token Count (tamanho do prompt) - seu caso real
✅ Concurrent Jobs (processos simultâneos) - batch/training
✅ Payload Size (tamanho da mídia) - multimodal
✅ DSQ Pool Saturation (saturação global) - Gemini 2.x

O erro é ambíguo por design - Google Cloud usa o mesmo código (429/ResourceExhausted) para dimensões completamente diferentes, exigindo análise forense para diagnóstico preciso.
