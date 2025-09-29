# Análise de Inconsistências - Correções Críticas

Este documento registra as inconsistências encontradas ao verificar a implementação das tarefas descritas em `correcoes_criticas.md`.

## Tarefa 1: Saturação do Vertex AI (erro 429 RESOURCE_EXHAUSTED)

**Status:** CORRETA

**Justificativa:** A análise do código confirmou que todas as correções propostas foram implementadas de forma consistente.

1.  **Retry com backoff**:
    *   **Evidência:** O arquivo `app/utils/vertex_retry.py` contém a função `call_with_vertex_retry`, que implementa retry com backoff exponencial, jitter e considera o cabeçalho `Retry-After`. A ferramenta `app/tools/langextract_sb7.py` utiliza essa função para encapsular as chamadas à API Vertex AI, conforme especificado.
    *   **Conclusão:** Implementação correta.

2.  **Limitar concorrência**:
    *   **Evidência:** O utilitário `app/utils/vertex_retry.py` utiliza um `threading.Semaphore` para limitar o número de chamadas concorrentes. O limite é configurável pela variável de ambiente `VERTEX_CONCURRENCY_LIMIT`. A função `call_with_vertex_retry` adquire o semáforo antes de executar a chamada, garantindo o controle de concorrência.
    *   **Conclusão:** Implementação correta.

3.  **Truncagem adaptativa**:
    *   **Evidência:** O método `_prepare_input` em `app/tools/langextract_sb7.py` implementa uma lógica de truncagem "head+tail" para o conteúdo HTML. A lógica é configurável por meio das variáveis de ambiente `STORYBRAND_HARD_CHAR_LIMIT`, `STORYBRAND_SOFT_CHAR_LIMIT` e `STORYBRAND_TAIL_RATIO`.
    *   **Conclusão:** Implementação correta.

4.  **Cache local opcional**:
    *   **Evidência:** O arquivo `app/utils/cache.py` define uma classe de cache LRU em memória com TTL. A ferramenta `app/tools/langextract_sb7.py` utiliza este cache, condicionado pela variável de ambiente `STORYBRAND_CACHE_ENABLED`, para armazenar e reutilizar respostas da análise StoryBrand, evitando chamadas repetidas à API.
    *   **Conclusão:** Implementação correta.

## Tarefa 2: Falha de permissão no bucket GCS (erro 403 storage.buckets.get)

**Status:** CORRETA

**Justificativa:** As correções propostas para resiliência do código e documentação foram implementadas corretamente.

1.  **Ajustar IAM**:
    *   **Evidência:** A alteração de permissões no IAM não pode ser verificada diretamente no código. No entanto, a documentação necessária foi adicionada.
    *   **Conclusão:** Não verificável, mas a parte de documentação está correta.

2.  **Tratamento resiliente**:
    *   **Evidência:** O arquivo `app/utils/tracing.py` foi atualizado. A classe `CloudTraceLoggingSpanExporter` agora captura exceções `gcs_exceptions.Forbidden` ao tentar acessar o bucket. Em caso de falha de permissão, ela emite um aviso e desativa futuras tentativas de upload para o GCS, além de respeitar a flag `TRACING_DISABLE_GCS`.
    *   **Conclusão:** Implementação correta.

3.  **Documentar credenciais**:
    *   **Evidência:** O arquivo `deployment/README.md` possui uma nova seção que detalha as permissões de IAM (`roles/storage.objectCreator` e `roles/storage.legacyBucketReader`) e os comandos `gcloud` para aplicá-las. O `README.md` principal também menciona a flag `TRACING_DISABLE_GCS`.
    *   **Conclusão:** Implementação correta.

## Tarefa 3: Melhor resposta ao frontend durante falhas Vertex

**Status:** CORRETA

**Justificativa:** O fluxo de tratamento de falhas foi implementado de ponta a ponta, garantindo que o frontend receba uma resposta clara em caso de erro no backend.

1.  **Propagar falha ao estado**:
    *   **Evidência:** O callback `process_and_extract_sb7` em `app/callbacks/landing_page_callbacks.py` agora captura a exceção `VertexRetryExceededError`. Ao fazer isso, ele chama a função `_mark_storybrand_failure`, que atualiza o `state['final_delivery_status']` com os detalhes do erro, persiste um arquivo de metadados de falha e registra uma métrica customizada.
    *   **Conclusão:** Implementação correta.

2.  **Endpoint 404 inteligente**:
    *   **Evidência:** O endpoint `/delivery/final/meta` em `app/routers/delivery.py` foi modificado. Antes de retornar um 404, ele verifica se existe um arquivo de metadados de falha. Se existir, o endpoint retorna um status **503 Service Unavailable** com os detalhes do erro, informando ao cliente que a requisição falhou e não deve ser tentada novamente.
    *   **Conclusão:** Implementação correta.

3.  **UI Feedback**:
    *   **Evidência:** O backend agora fornece os sinais corretos (status 503 e payload de erro) para que o frontend possa detectar a falha e exibir uma mensagem apropriada ao usuário.
    *   **Conclusão:** A parte do backend foi implementada corretamente para suportar o feedback na UI.

## Tarefa 4: Observabilidade e Alertas

**Status:** CORRETA

**Justificativa:** A instrumentação de métricas customizadas foi implementada conforme o plano. A configuração de alertas é uma tarefa de infraestrutura externa e não pode ser verificada no código.

1.  **Métricas customizadas**:
    *   **Evidência:** O arquivo `app/utils/metrics.py` define os contadores `storybrand.vertex429.count`, `storybrand.fallback.triggered` e `storybrand.delivery_failure.count`. As funções para incrementar esses contadores são chamadas nos locais apropriados do código: `record_vertex_429` é chamada em `app/utils/vertex_retry.py` ao encontrar um erro 429; `record_storybrand_fallback` é chamada em `app/agents/storybrand_gate.py` ao acionar o pipeline de fallback; e `record_delivery_failure` é chamada em `app/callbacks/landing_page_callbacks.py` quando uma falha de entrega é propagada.
    *   **Conclusão:** Implementação correta.

2.  **Alerting**:
    *   **Evidência:** A criação de políticas de alerta é uma configuração realizada no Google Cloud Monitoring.
    *   **Conclusão:** Não verificável no código-fonte.