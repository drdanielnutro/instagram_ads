# Sistema de Geração de Anúncios Instagram com Google ADK

## Visão Geral

Este projeto é um sistema multiagente baseado no Google ADK (Agent Development Kit) para gerar anúncios do Instagram em formato JSON. O objetivo principal é automatizar todo o fluxo de criação de anúncios (texto e imagem) a partir de informações fornecidas pelo usuário.

**Status**: ✅ Funcional. Análise StoryBrand com mitigação de latência (truncagem + parâmetros). Ver Solução de Problemas para env vars e logs de timing (2025-09-15)

## 🚨 Problema Atual - TRAVAMENTO

### Diagnóstico (2025-09-14)
O sistema está travando ao processar requisições com o campo `foco`. O travamento ocorre especificamente em:
- **Arquivo**: `app/tools/langextract_sb7.py` (linha ~309)
- **Momento**: Durante análise StoryBrand com LangExtract + Vertex AI
- **Sintoma**: Requisição trava indefinidamente (timeout após 5+ minutos)
- **Causa provável**: Timeout na API Vertex AI/Gemini ou HTML muito grande

## 📝 Como Fazer Requisições ao Sistema

### Opção 1: Via Frontend (Interface Web) - RECOMENDADO

1. **Acesse**: http://localhost:5173/app/
2. **Digite no campo de texto**:
```
landing_page_url: https://seusite.com.br/pagina
objetivo_final: agendamentos
perfil_cliente: descrição da persona e suas dores
formato_anuncio: Reels
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

| Aspecto | Frontend | API Direta |
|---------|----------|------------|
| **Session ID** | UUID gerado automaticamente | Você cria manualmente |
| **User ID** | Fixo: "u_999" | Você define (ex: "user1") |
| **Formato de Entrada** | Texto simples (chave: valor) | JSON complexo |
| **Endpoint** | Frontend escolhe automaticamente | Você especifica (/run ou /run_sse) |
| **Streaming** | Automático (SSE) | Você controla |
| **Complexidade** | Baixa (só digitar) | Alta (gerenciar sessões) |

## 🔐 Autenticação Local (Vertex AI)

- Use **Application Default Credentials (ADC)** com sua conta do gcloud:
  ```bash
  gcloud auth application-default login
  gcloud auth application-default set-quota-project instagram-ads-472021
  ```
- **Não configure** `GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json` no ambiente de desenvolvimento local; isso força o uso da service account e pode falhar caso a chave não tenha permissões completas de Vertex AI.
- Se optar por uma service account no futuro, garanta que ela tenha `roles/aiplatform.user` (ou equivalente) no projeto antes de reutilizar o arquivo.

## Refatorações Recentes

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
- ⚠️ **Bug**: Sistema trava ao processar com LangExtract

### 2025-09-12 - Melhorias Core
- ✅ **Campo `formato_anuncio` obrigatório**: Usuário controla o formato (Reels/Stories/Feed)
- ✅ **Gera 3 variações**: Sistema sempre produz 3 versões diferentes do anúncio
- ✅ **Apenas imagens**: Removido suporte a vídeos (campo `duracao` eliminado)
- ✅ **Loops de qualidade aumentados**: 7-10 iterações (antes eram 3-5)
- ✅ **Novo campo `contexto_landing`**: Armazena contexto extraído da landing page

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

### 1. Input Processor
Extrai campos estruturados da entrada do usuário:

**Campos obrigatórios**:
- `landing_page_url`: URL da página de destino
- `objetivo_final`: Ex: agendamentos, leads, vendas
- `perfil_cliente`: Persona/storybrand do público-alvo
- `formato_anuncio`: **"Reels", "Stories" ou "Feed"** (controlado pelo usuário)

**Campo opcional**:
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
```

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
- Resposta: `{ ok: true, filename, formato, timestamp, size_bytes, final_delivery_local_path, final_delivery_gcs_uri, user_id, session_id }`
- 404 quando o artefato ainda não estiver disponível

### GET /delivery/final/download
- Parâmetros: `user_id`, `session_id`
- Produção (GCS): retorna `{ signed_url: "...", expires_in: 600 }` (v4, GET, 10 min, com `Content-Disposition` e `Content-Type` para download)
- Desenvolvimento: stream do arquivo local (`application/json`)

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

### 🔴 Crítica - Travamento com LangExtract
1. **Sistema trava ao processar**: Especificamente em `langextract_sb7.py`
2. **Timeout indefinido**: Requisições ficam pendentes por 5+ minutos
3. **Afeta campo "foco"**: Problema aparece ao usar o novo campo opcional

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

### Problema: Sistema trava ao processar
**Sintoma**: Requisição fica pendente indefinidamente
**Causa**: LangExtract travando com Vertex AI
**Solução temporária**:
1. Remover campo "foco" da requisição
2. Ou desabilitar análise StoryBrand em `landing_page_callbacks.py`

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

1. **URGENTE: Corrigir travamento do LangExtract**
   - Adicionar timeout na chamada Vertex AI
   - Limitar tamanho do HTML processado
   - Implementar fallback sem StoryBrand

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

**Última atualização**: 2025-09-14
**Versão**: 2.1.0 (com campo "foco" e diagnóstico de travamento)
