# 🧠 PROMPT DE VALIDAÇÃO TÉCNICA – ERRO `RESOURCE_EXHAUSTED` (Vertex AI / Gemini)

## 🎯 OBJETIVO

Validar (ou refutar) tecnicamente a análise fornecida sobre o erro `RESOURCE_EXHAUSTED` no Vertex AI, confirmando ou desmentindo cada uma das afirmações com base em documentação **oficial e atualizada da Google Cloud (Vertex AI, Generative AI Studio, Gemini)** e **fontes confiáveis (support.google.com, developers.google.com, cloud.google.com/docs, etc.)**.

---

## 🧩 CONTEXTO GERAL (Resumo do Caso)

O modelo Gemini (2.x) apresentou o erro `RESOURCE_EXHAUSTED` (HTTP 429).
A hipótese é que o erro não decorreu de excesso de requisições no projeto, mas sim de **limite de tokens por requisição (context window)** ou de **saturação global do pool DSQ (Dynamic Shared Quota)**.
O usuário suspeita que o prompt tenha crescido linearmente em tamanho, excedendo o limite de tokens permitido pelo modelo.

---

## 🧱 INSTRUÇÕES PARA A IA ANALISADORA

### 1. MISSÃO

Você é um **validador técnico sênior**.
Seu trabalho é **confirmar ou refutar cada afirmação abaixo**, explicando o que é verdadeiro, parcialmente verdadeiro ou incorreto, **citando a fonte exata** (link oficial da Google Cloud, documentação de API, etc.).

---

### 2. AFIRMAÇÕES A VALIDAR

A. O erro `RESOURCE_EXHAUSTED` (HTTP 429) no Vertex AI pode ocorrer por múltiplas dimensões de quota:

* RPM (Requests per Minute)
* TPM (Tokens per Minute)
* RPD (Requests per Day)
* Payload Size (inline e File API)
* Token Count Per Request (context window)
* Concurrent Jobs
* DSQ Pool Saturation (Dynamic Shared Quota)

B. Modelos **Gemini 2.x (Pro, Flash, Flash-Lite)** utilizam **Dynamic Shared Quota (DSQ)**, ou seja, um pool global de recursos.
Um erro 429 nesses modelos **não indica que o projeto excedeu sua própria quota**, e sim que o pool global está temporariamente saturado.

C. Modelos **não-DSQ** (como Text-Bison ou AutoML) ainda usam quotas fixas por projeto.
Nesses casos, o erro 429 significa **exceder cota própria**, e o aumento de quota pode resolver.

D. O erro `RESOURCE_EXHAUSTED` é ambíguo por design — o mesmo código (429) é usado tanto para DSQ quanto para cotas fixas, portanto deve-se verificar:

* Logs e métricas em Cloud Monitoring (`aiplatform.googleapis.com/publisher/online_serving/token_count`)
* Comando `gcloud alpha quotas list`
* API `countTokens`
  para diagnosticar corretamente o tipo de limitação.

E. É válida a recomendação de usar **CountTokens API** para medir o tamanho do prompt e evitar exceder a *context window*.

F. Os limites documentados para Gemini 2.x incluem até **1.048.576 tokens de entrada** e **65.536 tokens de saída** (Flash) e até **500 MB de payload total por requisição**.

G. A hipótese de que o erro foi causado por **crescimento progressivo de prompts concatenados** (com JSON de seções aprovadas) é coerente tecnicamente — pois aumentaria linearmente o número de tokens, podendo ultrapassar o limite máximo de contexto.

H. O comportamento de **retry/backoff exponencial** é a resposta recomendada pela Google para DSQ saturado — aumentar a cota **não resolve** nesse caso.

---

### 3. INSTRUÇÕES ADICIONAIS

* Para cada item (A–H), classifique em uma destas categorias:

  * ✅ **Confirmado** (correto segundo documentação oficial)
  * ⚠️ **Parcialmente correto** (há detalhes ou exceções)
  * ❌ **Incorreto** (não consta ou foi modificado)
* Em cada caso, **cite links diretos** para a fonte (Google Cloud docs, release notes, quotas, support, etc.).
* Ao final, produza uma **síntese executiva** com:

  * Diagnóstico mais provável do erro.
  * Medidas recomendadas de mitigação e instrumentação.

---

## 📂 INSIRA AQUI SEUS LOGS E DETALHES ESPECÍFICOS

*(cole aqui as linhas de log, stack trace, status_code, mensagens ou headers do erro)*

```
Timestamp (UTC): 2024-10-14T22:41:08Z
Projeto: projects/instagram-ads-472021/locations/us-central1
Modelo: publishers/google/models/gemini-2.5-flash
Endpoint: generateContent (fallback StoryBrand writer)
Seção em execução: storybrand_vitoria (12ª de 16)
Exception: google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED
Mensagem completa:
  google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED:
  Span storybrand_fallback_section_writer exceeds limit;
  AFC is enabled with max remote calls: 10

Stack trace relevante:
  File "app/agents/storybrand_fallback.py", line 582, in _run_section_writer
    section_response = await storybrand_writer_agent.arun(...)
  File ".../google/genai/_genai.py", line 412, in generate_content_async
    raise ClientError("429 RESOURCE_EXHAUSTED", response=response)

Contexto adicional da requisição falha:
  - `landing_page_context` (texto bruto): 18.742 caracteres após limpeza.
  - `approved_sections` passado ao prompt: 11 seções StoryBrand já aprovadas
    serializadas em JSON (~64 kB, 7.9 k tokens estimados via tiktoken).
  - `writer_instruction` final concatenado no prompt: 86.531 caracteres
    (registrado em log DEBUG interno).
  - Flags de execução: ENABLE_STORYBRAND_FALLBACK=true,
    ENABLE_NEW_INPUT_FIELDS=true, PERSIST_STORYBRAND_SECTIONS=true.
  - Concurrency: VERTEX_CONCURRENCY_LIMIT=3 (retry helper).
  - Tentativas realizadas pelo retry wrapper: 5 (todas com 429 e Retry-After ausente).
  - Após o 429 o pipeline abortou e nenhum `meta.json` foi persistido,
    resultando em 404 no endpoint `/delivery/final/meta`.
```

---

## 💡 SAÍDA ESPERADA

O resultado deve ser estruturado assim:

```
### Validação Técnica do Erro RESOURCE_EXHAUSTED

#### A. Múltiplas dimensões de quota
✅ Confirmado. [fonte: link]

#### B. Dynamic Shared Quota (DSQ)
⚠️ Parcialmente correto. [fonte: link]

... (demais itens)

---

### Síntese executiva
Resumo das causas prováveis, medidas recomendadas e grau de veracidade das informações.
```

---
