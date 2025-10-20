# Relatório Técnico: Erro `RESOURCE_EXHAUSTED` no Vertex AI

## 1. Possíveis causas do erro RESOURCE_EXHAUSTED

Documentação oficial confirma que _diversos limites de quota_ podem disparar um erro 429 “Resource exhausted” em Vertex AI generativo. Em especial, incluem-se limites de **taxa de requisições** e **de tokens**, tais como: **RPM** (requests per minute), **TPM** (tokens per minute de entrada) e **RPD** (requests per day). Por exemplo, as quotas padrão para modelos Gemini são especificadas em RPM/TPM/RPD – p. ex. _Gemini 2.5 Flash_ tem 10 RPM e 250 000 TPM [1]. Ultrapassar qualquer um desses limites tipicamente gera um erro de quota. Outros fatores válidos incluem limites de **tamanho da carga (payload)**: cada requisição multimodal tem **input limitado a 500 MB** e cada arquivo de documento a **50 MB** [2][3]. Também há **limites de tokens por requisição** (tamanho da “context window” do modelo): p. ex., Gemini 2.5 Flash suporta até **1 048 576 tokens de entrada** [4]. Se uma requisição exceder esse limite de contexto, a API deverá rejeitar a chamada (possivelmente com erro de entrada inválida) – por isso recomenda-se usar a API _CountTokens_ para evitar esse caso [5]. Finalmente, limitações de **concorrência** podem gerar falhas: modelos não-Gemini têm cotas baixas de jobs simultâneos (ex. apenas 4 jobs de batch em paralelo para _textembedding_) [6][7], enquanto modelos Gemini usam um pool compartilhado sem limite fixo [6] (ver seção seguinte).

Em resumo, as causas confirmadas incluem quotas de _taxa_ (RPM/TPM/RPD), tamanho de payload (500 MB/50 MB), limite de tokens por requisição e cotas de concorrência [1][4][2][6]. Todas essas são documentadas nas páginas oficiais de quotas e modelos. (Em contraste, o erro **413 Request Entity Too Large** seria retornado se o payload for maior que o limite HTTP, em vez de 429 [8].)

## 2. Cotas por projeto vs. **DSQ** (Gemini 2.x) e interpretação do erro 429

Para _Gemini 2.0+_ (Flash, Pro, Flash-Lite, etc.), o Google utiliza **Dynamic Shared Quota (DSQ)** por padrão [9]. Isso significa que **não há uma cota fixa por projeto**: as requisições usam um pool global de capacidade. Nesse caso, um erro 429 “Resource exhausted” indica geralmente **saturação temporária desse pool compartilhado** (por alta demanda global), e não uma limitação absoluta do projeto. Conforme explicado pela Google: “com DSQ, 429 indica que o pool compartilhado para aquele modelo/região está em alta demanda… Não é um limite fixo no seu projeto” [10][11]. De fato, apoio oficial nota que em um 429 sem cota excedida aparente “os recursos na região podem estar temporariamente esgotados por alta demanda” [12]. Nesses casos recomenda-se re-tentativa com backoff ou usar outro endpoint/região.

Por outro lado, para modelos **não-DSQ** (antes de Gemini 2.0 ou em modos não-DSQ) ou tráfego excedendo a cota fixa, o erro 429 de quota também ocorre, mas reflete seu limite por projeto (RPM, TPM, etc). Nessa situação, deve-se consultar as quotas do projeto e possivelmente pedir aumento. Em resumo: **error 429 com modelo Gemini 2.x = provável saturação global (DSQ)** [10]; **error 429 com modelo não-DSQ = provavelmente limite de cota do projeto**. Ambos aparecem com o mesmo código HTTP, portanto é preciso diferenciar pelo contexto do modelo e região.

## 3. Validação dos procedimentos de diagnóstico

A sugestão de usar **gcloud e Cloud Monitoring** para diagnosticar é válida. É possível listar as cotas via linha de comando (usando o componente “alpha quotas” do gcloud) – por exemplo, após gcloud components install alpha e definindo o projeto de cota, roda-se gcloud alpha quotas list para exibir limites de API [8][13]. Em paralelo, o **Cloud Monitoring** permite consultar métricas de uso de quota. A API Monitoring (timeSeries.list) ou o _Metrics Explorer_ podem buscar métricas do recurso _Generative AI Model_, como _concurrent_requests_, _request_count_ (taxa de requisições) e _token_count_ (taxa de tokens) para região e base model específicos [14][15]. De fato, suporte Google recomenda filtrar esses indicadores em Monitoring para identificar qual cota foi atingida [14].

A análise de **logs estruturados** do Vertex AI (por exemplo, audit logs ou logs de requisição) também ajuda. Embora não haja citação direta na documentação pública, é prudente habilitar o _request-response logging_ das previsões do Vertex (via _PredictionService_) e verificar mensagens de erro ou campos como “quotaExceeded” nos logs JSON de falha, semelhante ao exemplo genérico de QUOTA_EXCEEDED visto em tráfegos Google Cloud [16][17]. Ademais, a própria API Vertex AI oferece o método _CountTokens_, que conta tokens do input sem custo e sem restrição de quota (até 3000 req/min) [18]. Isso valida o uso de tal API para evitar context overflow. Em síntese, usar gcloud alpha quotas list, consultar métricas de _request_count/token_count_ em Monitoring e examinar logs de erro são práticas recomendadas de diagnóstico [14][13].

## 4. Árvore de decisão para identificar a causa exata

Um fluxo lógico de diagnóstico pode ser:

1. **Verificar o tipo de erro**: se o código for **413**, indica payload muito grande (excedeu limites de size, e não quota) [8]. Se for **429**, prosseguir.
2. **Determinar se o modelo está em DSQ** (Gemini 2.x). Se sim, 429 aponta saturação global do pool DSQ [10][12]; a ação é reduzir picos de tráfego ou aguardar/re-tentar, talvez usar endpoint global ou provisioned throughput.
3. **Se não for DSQ**, 429 sugere cota específica do projeto. Então:
    a. Use gcloud alpha quotas list (ou console) filtrando pelo serviço Vertex AI e região exata para ver limites por base_model [13].
    b. Compare com métricas de uso: em Metrics Explorer, analise _request_count (rate)_ vs. _requests per minute_ permitidos e _token_count (rate)_ vs. _TPM_ [14].
    c. Identifique se foi excedido RPM, TPM, RPD ou concorrência e ajuste (ex: throttling ou pedir aumento de cota).
4. **Verificar payload e tokens**: confirmar que nem o tamanho de payload nem o número de tokens no request ultrapassaram os limites do modelo (ver seção 1). Usar API _CountTokens_ para garantir que a entrada esteja dentro da _context window_ antes de enviar [5].
5. **Outras cotas**: considerar cotas adicionais (ex. RPD) olhando nos dashboards de quota. Um dashboard de monitoramento pode alertar proximidade de limites [19].

Essa árvore ajuda a isolar se o problema é quota regional (DSQ) ou quotas fixas do projeto ou erro de payload.

## 5. Cenários práticos e crescimento do prompt

Não existe documentação oficial indicando que prompts sucessivos “cresçam linearmente” de modo a acumular tokens entre requisições no Vertex AI. Cada chamada ao modelo é tratada independentemente, com seu próprio limite de tokens. O documentado é que **cada requisição não deve exceder a capacidade de contexto do modelo** (por ex. ~1 M tokens para Gemini 2.x) [4]. Para evitar excesso de contexto, recomenda-se usar a API _CountTokens_ antes de enviar o prompt [5].

Casos publicados na comunidade mostram que um único prompt muito grande (centenas de milhares de tokens) pode gerar **ResourceExhausted 429** por sobrecarga do sistema (como em _Gemini 1.5 Pro_ com 600K tokens) [20] – ou seja, o próprio envio de prompt tão grande é problemático. A prática aceita é _não_ manter prompts crescentes indefinidamente: se houver história de diálogo, cabe ao cliente truncar ou resumir tokens históricos. Métodos de divisão de documentos (chunking) ou RAG são recomendados para grandes entradas [21]. Em suma, não há “acúmulo automático” de tokens entre chamadas; exceder o limite de tokens em uma chamada única seria tratado como entrada inválida ou recusada, não como quota. Documentos oficiais focam em evitar esse caso antecipadamente (via _CountTokens_) [5], e não relatam comportamento inesperado de _crescimento_ de contextos.

## 6. Recomendações de instrumentação e logging

Para identificar métricas excedidas, é crucial habilitar logs e métricas:

- **Cloud Monitoring**: configure dashboards e alertas para as métricas do _PublisherModel_/_Generative AI Model_, especialmente aiplatform.googleapis.com/publisher/online_serving/token_count e model_invocation_count (previsões), e as métricas de _requests_ e _tokens_ do recurso _Generative AI Model_ [19][14]. Isso permite ver rapidamente picos de uso. Google recomenda **monitorar tráfego vs. quotas** e disparar alertas quando estiver próximo do limite [19].
- **Logs estruturados**: ative o _request/response logging_ do Vertex AI (via PredictionService) para capturar falhas detalhadas. Nos logs de erro, procure campos como error.message contendo “Quota exceeded” ou error.details[].quotaExceeded. Embora nem todo erro especifique a cota atingida, o conjunto de logs (tanto de aplicação como de API) ajuda a correlacionar tempo de erro com métricas de uso.
- **Instrumentation adicional**: no código cliente, use a API _CountTokens_ prévia às chamadas para reportar ou rejeitar solicitações que excedam a janela do modelo [5]. Considere medir latência e taxa de sucesso das chamadas, e logar internamente o tipo de limitação suspeita (por exemplo, armazenar localmente o contador de tokens e o resultado da API, para auditar).

Adotando essas práticas – dashboards de monitoramento, alertas pró-ativos e logging de requisições/erros – consegue-se identificar rapidamente se o erro ocorreu por _tokens_, _requisitions/min_, _jobs concorrentes_, etc., facilitando a resposta corretiva conforme cada caso.

**Fontes:** Documentação Google sobre quotas e erros do Vertex AI [1][10][4][14][5] e discussões oficiais de suporte [12][19].

[1] Rate limits | Gemini API | Google AI for Developers  
https://ai.google.dev/gemini-api/docs/rate-limits

[2]  
[3]  
[4] Gemini 2.5 Flash | Generative AI on Vertex AI | Google Cloud  
https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash

[5] CountTokens API | Generative AI on Vertex AI | Google Cloud  
https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/count-tokens

[6]  
[7]  
[9] Vertex AI quotas and limits | Google Cloud  
https://cloud.google.com/vertex-ai/docs/quotas

[8]  
[13]  
[16] Resolver erros de cota | Cloud Quotas | Google Cloud  
https://cloud.google.com/docs/quotas/troubleshoot?hl=pt-br

[10]  
[11] Dynamic shared quota (DSQ) | Generative AI on Vertex AI | Google Cloud  
https://cloud.google.com/vertex-ai/generative-ai/docs/dynamic-shared-quota

[12] Vertex 429 Error: Quota shows 15K tokens/min but still getting "Quota exceeded" - #2 by dawnberdan - Custom ML & MLOps - Google Developer forums  
https://discuss.google.dev/t/vertex-429-error-quota-shows-15k-tokens-min-but-still-getting-quot-quota-exceeded-quot/191758/2

[14]  
[19] How to find which quota i actually hit? - Custom ML & MLOps - Google Developer forums  
https://discuss.google.dev/t/how-to-find-which-quota-i-actually-hit/192540

[15] Retrieve time-series data | Cloud Monitoring | Google Cloud  
https://cloud.google.com/monitoring/custom-metrics/reading-metrics

[17] google cloud platform - Receiving confusing 429 Resource Exhausted Error with Gemini Vertex AI - Stack Overflow  
https://stackoverflow.com/questions/79142037/receiving-confusing-429-resource-exhausted-error-with-gemini-vertex-ai

[18] Use the Count Tokens API | Generative AI on Vertex AI | Google Cloud  
https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/get-token-count

[20] 429 Resource exhausted on VertexAI with just one large request - Custom ML & MLOps - Google Developer forums  
https://discuss.google.dev/t/429-resource-exhausted-on-vertexai-with-just-one-large-request/173310

[21] Gemini 2.5 Pro – Extremely High Latency on Large Prompts (100K–500K Tokens) - Custom ML & MLOps - Google Developer forums  
https://discuss.google.dev/t/gemini-2-5-pro-extremely-high-latency-on-large-prompts-100k-500k-tokens/188489
