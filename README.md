# Sistema de Geração de Anúncios Instagram com Google ADK

## Visão Geral

Este projeto é um sistema multiagente baseado no Google ADK (Agent Development Kit) para gerar anúncios do Instagram em formato JSON. O objetivo principal é automatizar todo o fluxo de criação de anúncios (texto e imagem) a partir de informações fornecidas pelo usuário.

**Status**: ✅ Funcional. Análise StoryBrand com mitigação de latência (truncagem + parâmetros). Ver Solução de Problemas para env vars e logs de timing (2025-09-15)

## ✅ Problema Resolvido - TRAVAMENTO

### Diagnóstico (2025-09-14) - CORRIGIDO
~~O sistema estava travando ao processar requisições com o campo `foco`. O travamento ocorria especificamente em:~~
- ~~**Arquivo**: `app/tools/langextract_sb7.py` (linha ~309)~~
- ~~**Momento**: Durante análise StoryBrand com LangExtract + Vertex AI~~
- ~~**Sintoma**: Requisição travava indefinidamente (timeout após 5+ minutos)~~
- ~~**Causa**: Timeout na API Vertex AI/Gemini ou HTML muito grande~~

**STATUS: PROBLEMA CORRIGIDO** - Implementadas mitigações com truncagem adaptativa, retry exponencial e limite de concorrência

## 📝 Como Fazer Requisições ao Sistema

### Opção 1: Via Frontend (Interface Web) - RECOMENDADO

1. **Acesse**: http://localhost:5173/app/
2. **Digite no campo de texto**:
```
landing_page_url: https://seusite.com.br/pagina
nome_empresa: Clínica Bem Viver
o_que_a_empresa_faz: Clínica de nutrição e emagrecimento saudável
objetivo_final: agendamentos
formato_anuncio: Reels
perfil_cliente: descrição da persona e suas dores
sexo_cliente_alvo: masculino
foco: liquidação de inverno
```

3. **Frontend gerencia automaticamente**:
   - Session ID (UUID único)
   - User ID (fixo: "u_999")
   - App Name (fixo: "app")
   - Conversão para formato JSON da API
   - Preflight (valida/normaliza) antes de criar sessão; se inválido, retorna 422 e não dispara o ADK

### Opção 2: Via API Direta (curl)

#### Passo 1: Criar uma sessão
```bash
SESSION_ID="session_$(date +%s)"
curl -X POST "http://localhost:8000/apps/app/users/user1/sessions/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Passo 2: Fazer a requisição
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "app",
    "userId": "user1",
    "sessionId": "'$SESSION_ID'",
    "newMessage": {
      "role": "user",
      "parts": [
        {
          "text": "landing_page_url: https://nutrologodivinopolis.com.br/masculino/\nobjetivo_final: agendamentos de consulta via WhatsApp\nperfil_cliente: homens 35-50 anos, executivos com sobrepeso, querem emagrecer sem perder massa muscular\nformato_anuncio: Reels\nfoco: não engordar no inverno"
        }
      ]
    }
  }'
```

### Opção 3: Via API com Streaming (SSE)

Use o endpoint `/run_sse` ao invés de `/run` para receber eventos em tempo real:
```bash
curl -X POST http://localhost:8000/run_sse \
  -H "Content-Type: application/json" \
  -d '{...mesmo payload...}'
```

## 📊 Comparação entre Frontend e API Direta

| Aspecto                | Frontend                         | API Direta                         |
| ---------------------- | -------------------------------- | ---------------------------------- |
| **Session ID**         | UUID gerado automaticamente      | Você cria manualmente              |
| **User ID**            | Fixo: "u_999"                    | Você define (ex: "user1")          |
| **Formato de Entrada** | Texto simples (chave: valor)     | JSON complexo                      |
| **Endpoint**           | Frontend escolhe automaticamente | Você especifica (/run ou /run_sse) |
| **Streaming**          | Automático (SSE)                 | Você controla                      |
| **Complexidade**       | Baixa (só digitar)               | Alta (gerenciar sessões)           |

## 🔐 Autenticação Local (Vertex AI)

- Use **Application Default Credentials (ADC)** com sua conta do gcloud:
  ```bash
  gcloud auth application-default login
  gcloud auth application-default set-quota-project instagram-ads-472021
  ```
- **Não configure** `GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json` no ambiente de desenvolvimento local; isso força o uso da service account e pode falhar caso a chave não tenha permissões completas de Vertex AI.
- Se optar por uma service account no futuro, garanta que ela tenha `roles/aiplatform.user` (ou equivalente) no projeto antes de reutilizar o arquivo.

## Refatorações Recentes

### 2025-09-20 - Validação determinística e rollout controlado
- ✅ `build_execution_pipeline` agora separa caminhos determinístico e legado, encadeando `RunIfPassed` para revisão semântica, geração de imagens e persistência. 【F:app/agent.py†L1834-L1883】
- ✅ Guard, normalizer e validador alimentam `state['deterministic_final_validation']`/`state['deterministic_final_blocked']`, bloqueando o pipeline quando `grade != "pass"`. 【F:app/agent.py†L1293-L1352】【F:app/validators/final_delivery_validator.py†L71-L93】
- ✅ Persistência e sidecar `meta.json` passaram a incluir `deterministic_final_validation`, `semantic_visual_review` e `image_assets_review`, além dos blocos StoryBrand para observabilidade unificada. 【F:app/callbacks/persist_outputs.py†L31-L185】
- ✅ `FeatureOrchestrator` e SSE expõem mensagens específicas para falhas determinísticas, revisão semântica e imagens, mantendo compatibilidade com o fallback legado. 【F:app/agent.py†L1937-L1955】
- ✅ Flag `ENABLE_DETERMINISTIC_FINAL_VALIDATION` documentada para ativar o novo caminho por ambiente, com rollback simples via `.env`. 【F:app/config.py†L44-L85】

### 2025-09-18 - Estabilização Vertex AI e observabilidade
- ✅ Retry exponencial com respeito ao cabeçalho `Retry-After` (`VERTEX_RETRY_*`) e limite de concorrência configurável (`VERTEX_CONCURRENCY_LIMIT`).
- ✅ Truncagem adaptativa (head+tail) para inputs grandes (`STORYBRAND_SOFT_CHAR_LIMIT`, `STORYBRAND_HARD_CHAR_LIMIT`, `STORYBRAND_TAIL_RATIO`).
- ✅ Cache local opcional para resultados repetidos (`STORYBRAND_CACHE_ENABLED`, `STORYBRAND_CACHE_MAXSIZE`, `STORYBRAND_CACHE_TTL`).
- ✅ Persistência de falhas StoryBrand com retorno 503 para o frontend e métrica `storybrand.vertex429.count`/`storybrand.delivery_failure.count`.
- ✅ Exportador de spans resiliente: use `TRACING_DISABLE_GCS=true` em ambientes sem permissão de GCS.

### 2025-09-17 - StoryBrand fallback enforcement
- ✅ `nome_empresa` e `o_que_a_empresa_faz` passam a ser tratados como obrigatórios quando `ENABLE_NEW_INPUT_FIELDS=true`.
- ✅ `sexo_cliente_alvo` deve ser `masculino` ou `feminino`; o fallback tenta inferir via `landing_page_context` antes de abortar.
- ✅ Auditoria/logs ampliados (`preparer`, `checker`, `compiler` e `storybrand_fallback_section`).

### 2025-09-16 - Campos opcionais no preflight/wizard
- ✅ Novos campos opcionais `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` no extractor, preflight e wizard
- ✅ Normalização de gênero com default `neutro`
- ✅ Validações e testes cobrindo os novos passos do formulário e payloads

### 2025-09-15 - Preflight + Planos fixos + Persistência JSON
- ✅ Preflight no servidor (LangExtract/Vertex) valida/normaliza entrada e injeta plano fixo por formato
- ✅ Bypass do planejamento dinâmico; `context_synthesizer` ainda roda para gerar `{feature_briefing}`
- ✅ Prompts consideram `{format_specs_json}` (regras por formato)
- ✅ Persistência do JSON final: local em `artifacts/ads_final/…json` e upload opcional ao GCS `ads/final/…json`
- ✅ Logs essenciais (preflight) e métricas de StoryBrand (parâmetros e timing)

### 2025-09-14 - Campo "foco" e Makefile
- ✅ **Novo campo `foco`**: Campo opcional para temas/ganchos de campanha
- ✅ **Makefile melhorado**: Auto-kill de portas 8000 e 5173 antes de iniciar

### 2025-09-13 - Integração LangExtract
- ✅ **Web fetch real**: Implementado download completo de HTML
- ✅ **Framework StoryBrand**: Análise dos 7 elementos via LangExtract
- ✅ **Callbacks ADK**: Processamento via `after_tool_callback`
- ✅ ~~**Bug**: Sistema trava ao processar com LangExtract~~ **CORRIGIDO**

### 2025-09-12 - Melhorias Core
- ✅ **Campo `formato_anuncio` obrigatório**: Usuário controla o formato (Reels/Stories/Feed)
- ✅ **Gera 3 variações**: Sistema sempre produz 3 versões diferentes do anúncio
- ✅ **Apenas imagens**: Removido suporte a vídeos (campo `duracao` eliminado)
- ✅ **Loops de qualidade aumentados**: 7-10 iterações (antes eram 3-5)
- ✅ **Novo campo `contexto_landing`**: Armazena contexto extraído da landing page

### Rollout recomendado dos novos campos
- **Fase 1 – Backend**: publicar o extractor atualizado mantendo `ENABLE_NEW_INPUT_FIELDS=false` e observar o log estruturado `preflight_new_fields`.
- **Fase 2 – Frontend**: disponibilizar o wizard com os novos passos em ambientes internos com `VITE_ENABLE_NEW_FIELDS=false` para validação.
- **Fase 3 – Liberação total**: ativar `VITE_ENABLE_NEW_FIELDS=true` e `ENABLE_NEW_INPUT_FIELDS=true` após o período de monitoramento.

### Rollout recomendado da validação determinística
1. **Preparação (flag desligada)** – manter `ENABLE_DETERMINISTIC_FINAL_VALIDATION=false` para preservar o fluxo legado e limpar chaves determinísticas automaticamente via `ResetDeterministicValidationState`. 【F:app/agent.py†L1874-L1883】【F:app/agents/gating.py†L83-L124】
2. **Canário** – habilitar a flag apenas em um ambiente controlado, monitorando `deterministic_final_validation`, `semantic_visual_review` e `image_assets_review` via SSE/`meta.json` para confirmar grades esperadas. 【F:app/config.py†L44-L85】【F:app/agent.py†L1917-L1955】【F:app/callbacks/persist_outputs.py†L98-L185】
3. **Expansão gradual** – após estabilidade do canário, promover a flag para staging e depois produção acompanhando dashboards/alertas (ver playbook) e confirmando que `RunIfPassed` libera apenas execuções aprovadas. 【F:app/agent.py†L1850-L1883】【F:app/agents/gating.py†L19-L81】
4. **Rollback** – em caso de anomalias, retornar a `ENABLE_DETERMINISTIC_FINAL_VALIDATION=false` e reiniciar o processo; o primeiro agente do caminho legado limpará resíduos determinísticos antes de retomar o `final_validation_loop`. 【F:app/agent.py†L1874-L1883】【F:app/agents/gating.py†L83-L124】

## Arquitetura do Sistema

O sistema utiliza múltiplos agentes ADK organizados em pipeline sequencial:

```
input_processor → landing_page_analyzer → planning_pipeline → execution_pipeline → final_assembly → validation
```

### Modo “Plano Fixo” (Preflight)
- O servidor executa um “preflight” para extrair/validar a entrada do usuário (LangExtract via Vertex/ADC) e seleciona um de 3 planos fixos (Reels/Stories/Feed).
- Quando o plano fixo está presente no estado (`planning_mode=fixed` + `implementation_plan`), o pipeline:
  - Executa o `context_synthesizer` (gera `{feature_briefing}`)
  - Pula o `planning_pipeline` (revisão/geração dinâmica de plano)
  - Segue direto para `execution_pipeline` com as 8 tarefas do plano fixo
- Os prompts consideram `{format_specs_json}` (regras por formato como aspect_ratio, estilo/limites de copy etc.).
 
### Persistência do JSON Final
- Ao final do pipeline, o JSON é salvo localmente em `artifacts/ads_final/<timestamp>_<session>_<formato>.json`.
- Em produção, use um bucket dedicado para entregas finais: `DELIVERIES_BUCKET=gs://…`. O upload vai para `gs://<deliveries_bucket>/deliveries/<user_id>/<session_id>/<arquivo>.json` e um sidecar `meta.json` é salvo no mesmo prefixo.
- Os caminhos ficam no state da sessão: `final_delivery_local_path` e (se houver upload) `final_delivery_gcs_uri`. O sidecar facilita o lookup por sessão.

### Ordem de validação determinística (flag ON)
1. **FinalAssemblyGuardPre** garante que existem snippets `VISUAL_DRAFT` aprovados, normaliza os conteúdos e bloqueia o pipeline quando encontra problemas, registrando `deterministic_final_validation.grade = "fail"` e `deterministic_final_blocked=True`. 【F:app/agent.py†L1288-L1316】
2. **FinalAssemblyNormalizer** reserializa o JSON do assembler, verifica campos obrigatórios e sinaliza `grade="pending"` até que o validador processe o payload. Falhas estruturais mantêm `deterministic_final_blocked=True`. 【F:app/agent.py†L1343-L1524】
3. **FinalDeliveryValidatorAgent** aplica o schema estrito e atualiza `state['deterministic_final_validation']`, limpando `deterministic_final_blocked` somente quando `grade="pass"`; reprovações mantêm `issues`/`failure_reason` no estado. 【F:app/validators/final_delivery_validator.py†L71-L93】
4. **RunIfPassed** libera o restante do pipeline apenas quando os reviews estão aprovados (`deterministic_final_validation`, `semantic_visual_review`, `image_assets_review`), tratando `grade="skipped"` como sucesso aceitável para imagens. 【F:app/agent.py†L1850-L1883】
5. **PersistFinalDeliveryAgent** chama `persist_final_delivery` uma única vez, garantindo que o sidecar `meta.json` reflita os estados de revisão (`deterministic_final_validation`, `semantic_visual_review`, `image_assets_review`) e agregue métricas StoryBrand. 【F:app/agent.py†L1537-L1569】【F:app/callbacks/persist_outputs.py†L31-L185】

> Quando `ENABLE_DETERMINISTIC_FINAL_VALIDATION=false`, o pipeline legado usa `ResetDeterministicValidationState` e mantém o `final_validation_loop` original antes de persistir. 【F:app/agent.py†L1874-L1883】

## 🎨 Geração de Imagens com Referências Visuais

O pipeline de imagens aceita **uploads opcionais** de referências de personagem e produto quando a flag `ENABLE_REFERENCE_IMAGES=true`. O fluxo completo envolve upload, cache temporário, consumo no preflight e propagação até a persistência final:

1. **Upload** (`POST /upload/reference-image`)
   - Disponível apenas quando a flag está ativa; caso contrário, responde `403` imediatamente.
   - Aceita formatos `PNG`, `JPEG/JPG` e `WebP` com limite de **5 MB** por arquivo. Rejeições retornam `415` (tipo inválido) ou `413` (tamanho excedido). 【F:app/server.py†L41-L115】【F:app/server.py†L181-L272】
   - Antes de devolver `{ id, signed_url, labels }`, o backend armazena o arquivo no GCS via `upload_reference_image_to_gcs`, executa análise do Vertex AI Vision e guarda os metadados aprovados no cache em memória. 【F:app/server.py†L235-L271】【F:app/utils/gcs.py†L55-L155】【F:app/utils/reference_cache.py†L18-L123】

2. **Cache & TTL**
   - Metadados ficam disponíveis via cache em memória com TTL configurável (`config.reference_cache_ttl_seconds`, padrão 1 h). Use `REFERENCE_CACHE_TTL_SECONDS` para ajustar em produção. 【F:app/config.py†L82-L108】【F:app/utils/reference_cache.py†L21-L122】
   - URLs assinadas geradas durante o upload respeitam `config.image_signed_url_ttl` (padrão 24 h) e têm a expiração calculada automaticamente durante a sanitização. Ajuste com `IMAGE_SIGNED_URL_TTL`. 【F:app/config.py†L85-L181】【F:app/callbacks/persist_outputs.py†L58-L137】

3. **Preflight & Pipeline**
   - O `/run_preflight` injeta `reference_images` e resumos (`reference_image_*`) no `initial_state`, garantindo que prompts e agentes usem obrigatoriamente as referências aprovadas. Logs estruturados sinalizam quando referências são resolvidas ou ignoradas por flag. 【F:app/server.py†L333-L417】【F:app/server.py†L569-L659】
   - `ImageAssetsAgent` reidrata os metadados, registra uso/emoções e adiciona `visual.reference_assets` no JSON final, enquanto `persist_final_delivery` remove campos sensíveis antes de salvar. 【F:app/agent.py†L428-L910】【F:app/callbacks/persist_outputs.py†L58-L215】

4. **Política de Limpeza**
   - A sanitização persiste somente `id`, `gcs_uri`, `labels`, `user_description` e informações de expiração, evitando exposição de tokens ou URLs long-lived. Recomenda-se rodar jobs periódicos de limpeza no bucket (`reference_images_bucket`) para remover uploads expirados. 【F:app/callbacks/persist_outputs.py†L58-L215】【F:app/utils/gcs.py†L55-L155】

> **Flag desligada?** O upload retorna erro e o preflight ignora qualquer payload `reference_images`, mantendo o comportamento legado de geração sem referências.

### 1. Input Processor
Extrai campos estruturados da entrada do usuário:

**Campos obrigatórios** (quando `ENABLE_NEW_INPUT_FIELDS=true` e fallback habilitado):
- `landing_page_url`: URL da página de destino
- `objetivo_final`: Ex: agendamentos, leads, vendas
- `perfil_cliente`: Persona/storybrand do público-alvo
- `formato_anuncio`: **"Reels", "Stories" ou "Feed"** (controlado pelo usuário)
- `nome_empresa`: Como a marca deve ser citada nos criativos (obrigatório, sem default)
- `o_que_a_empresa_faz`: Resumo da proposta de valor/serviços da empresa (obrigatório)
- `sexo_cliente_alvo`: **apenas** `masculino` ou `feminino` (valores vazios/"neutro" bloqueiam o fallback)

**Campos opcionais**:
- `foco`: Tema ou gancho da campanha (ex: "liquidação de inverno")

Observação: No modo “preflight”, a extração/normalização ocorre no servidor antes do ADK. Se inválido, o servidor responde 422 com os erros e o ADK não é acionado.

### 2. Landing Page Analyzer
**✅ ATUALIZADO**: Agora usa `web_fetch_tool` para extrair HTML real + análise StoryBrand

Extrai:
- Título principal (H1) do HTML real
- Proposta de valor baseada no StoryBrand Guide
- Benefícios do StoryBrand Success
- CTAs do StoryBrand Action
- Ofertas e provas sociais
- Tom de voz e palavras-chave
- Persona do StoryBrand Character
- Problemas/dores do StoryBrand Problem
- Transformação do StoryBrand Success

### 3. Context Synthesizer
Consolida entradas em briefing estruturado:
- Persona e dores/benefícios
- Formato definido pelo usuário
- Mensagens-chave alinhadas com landing page real
- Integração com análise StoryBrand
- Consideração do campo "foco" quando presente
- Restrições (políticas Instagram/saúde)

### 4. Feature Planner
Gera plano com tarefas categorizadas:
- **STRATEGY**: Diretrizes estratégicas
- **RESEARCH**: Referências e padrões
- **COPY_DRAFT**: Texto do anúncio
- **VISUAL_DRAFT**: Descrição de imagem estática
- **COPY_QA / VISUAL_QA**: Validações
- **COMPLIANCE_QA**: Conformidade
- **ASSEMBLY**: Montagem JSON

### 5. Loops de Revisão
- **Plan Review**: Até 7 iterações
- **Code Review**: Até 8 iterações
- **Final Validation**: Até 10 iterações

### 6. Task Execution
Para cada tarefa do plano:
1. `code_generator`: Gera fragmento JSON (considera "foco")
2. `code_reviewer`: Valida alinhamento e qualidade
3. `code_refiner`: Aplica correções se necessário
4. `code_approver`: Registra fragmento aprovado

### 7. Final Assembly
Combina fragmentos em **3 variações** de anúncio com:
- `landing_page_url`
- `formato` (definido pelo usuário)
- `copy`: headline, corpo, cta_texto
- `visual`: descricao_imagem, aspect_ratio
- `cta_instagram`: Saiba mais, Enviar mensagem, etc.
- `fluxo`: Ex: "Instagram Ad → Landing Page → WhatsApp"
- `contexto_landing`: Resumo do contexto extraído com StoryBrand
- `referencia_padroes`: Padrões de alta performance utilizados

### 8. Final Validation
Valida:
- JSON válido com exatamente 3 objetos
- Todas chaves obrigatórias presentes
- Enums corretos (formato, aspect_ratio, CTA)
- Coerência com objetivo e "foco" (se fornecido)
- Variações diferentes entre si
- Conformidade com políticas Instagram

## Modelos de Dados

```python
class AdCopy(BaseModel):
    headline: str           # Título principal (máx 40 caracteres)
    corpo: str             # Texto do corpo (máx 125 caracteres)
    cta_texto: str         # Texto do botão CTA

class AdVisual(BaseModel):
    descricao_imagem: str  # Apenas imagens, sem vídeos
    prompt_estado_atual: str
    prompt_estado_intermediario: str
    prompt_estado_aspiracional: str
    aspect_ratio: Literal["9:16", "1:1", "4:5", "16:9"]

class AdItem(BaseModel):
    landing_page_url: str
    formato: Literal["Reels", "Stories", "Feed"]
    copy: AdCopy
    visual: AdVisual
    cta_instagram: Literal["Saiba mais", "Enviar mensagem", "Ligar", "Comprar agora", "Cadastre-se"]
    fluxo: str
    referencia_padroes: str
    contexto_landing: str  # Inclui análise StoryBrand
```

## Estrutura de Arquivos

```
app/
├── agent.py              # Pipeline completo (881 linhas)
├── config.py             # Configurações e modelos
├── server.py             # API FastAPI
├── tools/                # Ferramentas customizadas
│   ├── web_fetch.py      # Fetch HTTP real
│   └── langextract_sb7.py # Análise StoryBrand com LangExtract
├── callbacks/            # Callbacks ADK
│   └── landing_page_callbacks.py
├── schemas/              # Schemas Pydantic
│   └── storybrand.py
└── utils/
    ├── gcs.py           # Google Cloud Storage
    └── tracing.py       # Telemetria
```

## Configuração

### Modelos LLM
- **Worker**: `gemini-2.5-flash`
- **Critic**: `gemini-2.5-pro`
- **LangExtract**: `gemini-2.5-flash` (via Vertex AI)

### Iterações Máximas
```python
max_code_review_iterations: 3
max_plan_review_iterations: 1
final_validation_loop: 3
max_task_iterations: 20
```

### Variáveis de Ambiente (.env)
```bash
GOOGLE_CLOUD_PROJECT=instagram-ads-472021
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
LANGEXTRACT_API_KEY=sua-chave-gemini  # Opcional
ARTIFACTS_BUCKET=gs://instagram-ads-472021-facilitador-logs-data   # uso interno do ADK
DELIVERIES_BUCKET=gs://instagram-ads-472021-deliveries             # JSON final (frontend via Signed URL)
# Flags de novos campos (backend)
ENABLE_NEW_INPUT_FIELDS=false
ENABLE_STORYBRAND_FALLBACK=false
ENABLE_DETERMINISTIC_FINAL_VALIDATION=false
FALLBACK_STORYBRAND_MAX_ITERATIONS=3
FALLBACK_STORYBRAND_MODEL=
STORYBRAND_GATE_DEBUG=false
PREFLIGHT_SHADOW_MODE=true
```

## Sistema de Flags (Frontend e Backend)

### Backend (runtime, .env)
- **ENABLE_NEW_INPUT_FIELDS** (default: false)
  - false: /run_preflight não inclui novos campos no initial_state (retrocompatível).
  - true: inclui `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo` no initial_state **e exige valores válidos** (`sexo_cliente_alvo` limitado a `masculino`/`feminino`).
- **ENABLE_STORYBRAND_FALLBACK** (default: false)
  - false: o gate monitora métricas, mas nunca executa o fallback.
  - true: o gate pode acionar o `fallback_storybrand_pipeline` (requer ENABLE_NEW_INPUT_FIELDS=true).
- **ENABLE_DETERMINISTIC_FINAL_VALIDATION** (default: false)
  - false: usa o pipeline legado (`final_validation_loop` + callbacks do `ImageAssetsAgent`).
  - true: ativa guard → normalizer → validador determinístico + `RunIfPassed` para revisão semântica, imagens e persistência.
- **FALLBACK_STORYBRAND_MAX_ITERATIONS** (default: 3)
  - Controla o número máximo de ciclos writer→reviewer→corrector por seção.
- **FALLBACK_STORYBRAND_MODEL** (opcional)
  - Permite usar um modelo mais potente (ex.: `gemini-2.5-pro`) apenas no fallback.
- **STORYBRAND_GATE_DEBUG** (default: false)
  - true: força o fallback independentemente do score para depuração/QA.
- **PREFLIGHT_SHADOW_MODE** (default: true)
  - true: extrai/loga novos campos sem incluí-los no initial_state (observação segura).
  - false: ignora completamente a extração dos novos campos quando ENABLE_NEW_INPUT_FIELDS=false.

Fases sugeridas:
1) Segurança: ENABLE_NEW_INPUT_FIELDS=false, PREFLIGHT_SHADOW_MODE=true.
2) Ativar inclusão: ENABLE_NEW_INPUT_FIELDS=true (após validar métricas), manter SHADOW por alguns dias.
3) Estabilizado: PREFLIGHT_SHADOW_MODE=false (opcional, reduz custo).

### Frontend (build-time, frontend/.env.local)
- **VITE_ENABLE_WIZARD**
  - false: Wizard oculto.
  - true: Wizard visível.
- **VITE_ENABLE_NEW_FIELDS**
  - false: novos steps/campos ocultos (payload não inclui linhas novas).
  - true: steps/campos visíveis e enviados no payload.

Fases sugeridas:
1) Backend com SHADOW on e NEW_INPUT_FIELDS off; frontend com VITE_ENABLE_NEW_FIELDS=false.
2) Habilitar UI: VITE_ENABLE_NEW_FIELDS=true para subset; observar erros/telemetria.
3) Habilitar fim-a-fim: ENABLE_NEW_INPUT_FIELDS=true; depois avaliar desligar SHADOW.

## StoryBrand Fallback (Alta Fidelidade)

O fallback é ativado pelo agente `StoryBrandQualityGate` quando o score de completude StoryBrand fica abaixo de `config.min_storybrand_completeness`, quando `state['force_storybrand_fallback']` está habilitado ou quando `config.storybrand_gate_debug` está `True`.

- O fallback forçado realmente entrega narrativas mais longas, com contextualização meticulosa (principalmente em `contexto_landing` e nas `copy`). Isso acontece porque o pipeline sintético reconstrói 16 seções do StoryBrand a partir de prompts específicos – ele gera blocos grandes e articulados, mesmo sem ler a landing page.

- **Pipeline**: `fallback_storybrand_pipeline` (`app/agents/storybrand_fallback.py`) executa inicialização, coleta/validação de inputs, geração das 16 seções, compilação (`FallbackStorybrandCompiler`) e relatório de qualidade.
- **Coleta**: o coletor reforça `nome_empresa`/`o_que_a_empresa_faz`, tenta inferir `sexo_cliente_alvo` a partir de `landing_page_context` e aborta o pipeline com `EventActions(escalate=True)` quando os campos não podem ser recuperados.
- **Prompts**: ficam em `prompts/storybrand_fallback/` e são carregados pelo utilitário `PromptLoader` (`app/utils/prompt_loader.py`). Faltas disparam `FileNotFoundError`.
- **Métricas/Logs**: o gate popula `state['storybrand_gate_metrics']`; o fallback adiciona eventos (incluindo `preparer`, `checker`, `compiler` com `duration_ms`) em `state['storybrand_audit_trail']`, registra logs estruturados `storybrand_fallback_section` e gera `state['storybrand_recovery_report']`.
- **Configuração**: use `ENABLE_STORYBRAND_FALLBACK=true`, `ENABLE_NEW_INPUT_FIELDS=true` e ajuste `FALLBACK_STORYBRAND_MAX_ITERATIONS`/`FALLBACK_STORYBRAND_MODEL` conforme necessidade.
- **Rollout sugerido**: habilite primeiro o backend (`ENABLE_STORYBRAND_FALLBACK=true`), valide métricas com `STORYBRAND_GATE_DEBUG` em ambiente de QA e só então ligue `VITE_ENABLE_NEW_FIELDS` no frontend.
- **QA**: `tests/unit/agents/test_storybrand_gate.py` e `tests/unit/utils/test_prompt_loader.py` cobrem a lógica crítica do gate e do carregamento de prompts.

## Execução

### Desenvolvimento (com auto-kill de portas)
```bash
# O Makefile agora mata automaticamente processos nas portas 8000 e 5173
make dev

# Ou executar separadamente:
make dev-backend-all  # Backend apenas (uvicorn app.server:app com /run_preflight)
make dev-frontend     # Frontend apenas
```

### Produção
```bash
# Deploy no Google Cloud Run
make backend
```

### Testes
```bash
# Executar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=app --cov-report=html
```

Acesso:
- Frontend: http://localhost:5173/app/
- Backend API: http://localhost:8000/docs

## Mensagens SSE e chaves de estado
- O `FeatureOrchestrator` envia mensagens distintas quando qualquer estágio falha: planejamento, revisão de conteúdo, execução, validação determinística, revisão semântica ou geração de imagens. 【F:app/agent.py†L1917-L1955】
- A sessão expõe `deterministic_final_validation`, `deterministic_final_blocked`, `semantic_visual_review` e `image_assets_review` para que consumidores verifiquem status e motivos (`*_failure_reason`). 【F:app/agent.py†L1293-L1524】【F:app/validators/final_delivery_validator.py†L71-L93】
- `clear_failure_meta` elimina indicadores de falha antigos após persistência bem-sucedida, mantendo `final_delivery_status` alinhado com o pipeline determinístico. 【F:app/callbacks/persist_outputs.py†L167-L185】

## API Endpoints

### POST /run_preflight
Valida e normaliza a entrada do usuário e retorna um estado inicial com plano fixo por formato (Reels/Stories/Feed).

- Body (simples):
```
{ "text": "landing_page_url: https://...\nobjetivo_final: agendamentos\nperfil_cliente: ...\nformato_anuncio: Reels\nfoco: ..." }
```

- Respostas:
  - 200 OK → `{ success: true, initial_state: {...}, plan_summary: {...} }`
  - 422 Unprocessable Entity → `{ message: "Campos mínimos ausentes/invalidos.", errors: [{field, message}], partial: {...} }`

Uso típico: o frontend chama `/run_preflight` antes de criar a sessão; se `success=true`, cria a sessão enviando `initial_state` no body e depois chama `/run_sse` normalmente. Em caso de 422, não dispara o ADK.
Logs úteis: `[preflight] start` → `result` → `blocked` (422) → `plan_selected` → `return`.

### GET /delivery/final/meta
- Parâmetros: `user_id`, `session_id`
- Resposta: `{ ok: true, filename, formato, stage, grade, deterministic_final_validation, semantic_visual_review, image_assets_review, storybrand_audit_trail, storybrand_gate_metrics, storybrand_fallback_meta, delivery_audit_trail, final_delivery_local_path, final_delivery_gcs_uri, user_id, session_id }`
- 503 quando somente `failure_meta` existe (falha determinística/semântica/imagens registrada), 404 se nenhum artefato foi encontrado
- A resposta é abastecida pelo sidecar `meta.json` salvo em disco/GCS pelo callback de persistência. 【F:app/callbacks/persist_outputs.py†L98-L185】【F:app/routers/delivery.py†L63-L92】

### GET /delivery/final/download
- Parâmetros: `user_id`, `session_id`
- Produção (GCS): retorna `{ signed_url: "...", expires_in: 600 }` (v4, GET, 10 min, com `Content-Disposition` e `Content-Type` para download)
- Desenvolvimento: stream do arquivo local (`application/json`)
- Quando `inline=true`, valida que todas as variações possuem URLs de imagem e falha com 424 se algo estiver ausente, reportando quais campos faltam. 【F:app/routers/delivery.py†L93-L173】

### POST /run
Executa o agente de forma síncrona
- **Body**: AgentRunRequest (veja exemplo acima)
- **Response**: JSON com resultado final

### POST /run_sse
Executa o agente com streaming (Server-Sent Events)
- **Body**: Mesmo que /run
- **Response**: Stream de eventos

### POST /apps/{app_name}/users/{user_id}/sessions/{session_id}
Cria uma nova sessão
- **Body**: `{}` ou estado inicial opcional
- **Response**: Detalhes da sessão criada

### POST /feedback
Recebe feedback sobre anúncios gerados:
```json
{
  "grade": "pass|fail",
  "comment": "...",
  "follow_up_queries": [...]
}
```

## Limitações Conhecidas

### ✅ Corrigidas - ~~Travamento com LangExtract~~
1. ~~**Sistema trava ao processar**: Especificamente em `langextract_sb7.py`~~ **CORRIGIDO**
2. ~~**Timeout indefinido**: Requisições ficam pendentes por 5+ minutos~~ **CORRIGIDO**
3. ~~**Afeta campo "foco"**: Problema aparece ao usar o novo campo opcional~~ **CORRIGIDO**

### 🟢 Resolvidas (eram limitações)
1. ~~Não extrai conteúdo real da landing page~~ ✅ Resolvido com web_fetch_tool
2. ~~Sem framework estruturado~~ ✅ Implementado StoryBrand via LangExtract
3. ~~Sem rastreabilidade~~ ✅ Adicionado com análise StoryBrand

## Solução de Problemas

### Ajuste de desempenho da análise StoryBrand
Se notar latência elevada na análise da landing (LangExtract), ajuste via env vars e verifique logs de timing:
```bash
export STORYBRAND_TRUNCATE_LIMIT_CHARS=12000   # 0 desativa truncagem; 8–12k recomendados
export STORYBRAND_EXTRACTION_PASSES=1          # 1 recomendado
export STORYBRAND_MAX_WORKERS=4                # 2–4
export STORYBRAND_MAX_CHAR_BUFFER=1500         # 1000–2000
```
- Logs úteis:
  - `LangExtract params: passes=…, max_workers=…, max_char_buffer=…`
  - `StoryBrand timing: { duration_s, truncated, truncate_limit }`
- Makefile: gere o extrato com `make logs-storybrand`.

### Preflight retorna 404
Inicie o backend com `uvicorn app.server:app` (o Makefile já faz isso em `make dev` e `make dev-backend-all`). O endpoint `/run_preflight` é definido em `app/server.py`.

### ~~Problema: Sistema trava ao processar~~ **CORRIGIDO**
~~**Sintoma**: Requisição fica pendente indefinidamente~~
~~**Causa**: LangExtract travando com Vertex AI~~
~~**Solução temporária**:~~
~~1. Remover campo "foco" da requisição~~
~~2. Ou desabilitar análise StoryBrand em `landing_page_callbacks.py`~~

**STATUS: PROBLEMA CORRIGIDO** - Implementadas mitigações com truncagem adaptativa e retry exponencial

### Problema: Porta já em uso
**Sintoma**: "address already in use"
**Solução**: Use `make dev` - ele mata automaticamente processos nas portas

### Problema: Erro de autenticação Google Cloud
**Sintoma**: Erros de credenciais
**Solução**:
```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=seu-projeto
```

## Próximos Passos Sugeridos

1. ~~**URGENTE: Corrigir travamento do LangExtract**~~ ✅ **CONCLUÍDO**
   - ✅ Adicionar timeout na chamada Vertex AI
   - ✅ Limitar tamanho do HTML processado
   - ✅ Implementar fallback sem StoryBrand

2. **Melhorias planejadas**:
   - Cache para URLs já processadas
   - Suporte a Selenium para páginas JavaScript-heavy
   - A/B testing de variações
   - Métricas de performance

## Observações

- Buckets:
  - `ARTIFACTS_BUCKET`: uso interno do ADK (agentes/ferramentas). Não é exposto ao frontend.
  - `DELIVERIES_BUCKET`: uso da aplicação para entregas finais (JSON). Acesso via Signed URL (v4) nos endpoints `/delivery/*`.
- Em produção, não crie buckets no startup; provisione via IaC/CLI.
- Sistema funcional com mitigação de latência na análise StoryBrand (use as env vars de desempenho se necessário).
- Frontend gerencia sessões automaticamente e executa preflight por padrão.
- Campo "foco" é opcional mas recomendado para campanhas direcionadas.
- Preflight: no frontend, vem ativado por padrão (toggle no topo). Se desativar (`VITE_ENABLE_PREFLIGHT='false'`), o fluxo segue como antes (apenas ADK).

---

**Última atualização**: 2025-10-03
**Versão**: 2.2.0 (travamento LangExtract corrigido com mitigações)
