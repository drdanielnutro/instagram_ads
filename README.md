# Instagram Ads - Sistema de Geração Automatizada

Sistema de geração automatizada de anúncios para Instagram baseado em Google ADK (Agent Development Kit), que cria conteúdo de anúncios (texto e imagens) em formato JSON para campanhas.

## 🚀 Início Rápido

```bash
# Iniciar ambiente de desenvolvimento completo
make dev

# Executar testes
pytest tests/ -v

# Verificar qualidade de código
make lint
```

**Acesso**:
- Frontend: http://localhost:5173/app/
- Backend API: http://localhost:8000/docs

## 📋 Visão Geral

### Arquitetura Multi-Agente

O sistema utiliza agentes ADK sequenciais organizados em pipeline:

```
input_processor → landing_page_analyzer → planning_pipeline →
execution_pipeline → final_assembly → validation
```

### Componentes Principais

1. **Sistema Preflight** (`/run_preflight`)
   - Valida e normaliza entrada do usuário
   - Seleciona planos fixos baseados no formato (Reels/Stories/Feed)
   - Retorna estado inicial com plano de implementação

2. **Análise de Landing Page**
   - Extrai conteúdo HTML via `web_fetch_tool`
   - Análise StoryBrand via LangExtract/Vertex AI
   - Extrai 7 elementos StoryBrand para contexto do anúncio

3. **Execução de Planos**
   - Planos fixos por formato em `app/plan_models/fixed_plans.py`
   - 8 categorias de tarefas: STRATEGY, RESEARCH, COPY_DRAFT, VISUAL_DRAFT, etc.
   - Cada tarefa gera fragmentos JSON que são montados

4. **Persistência**
   - **Local**: `artifacts/ads_final/<timestamp>_<session>_<formato>.json`
   - **GCS**: Upload opcional para `gs://<bucket>/ads/final/`
   - **StoryBrand Sections**: `artifacts/storybrand/<session_id>.json` (quando fallback ativo)

## 📁 Persistência de Dados

### JSON Final de Entrega

O sistema persiste o resultado final em formato JSON contendo:
- Conteúdo dos anúncios (texto, imagens, formato)
- Metadados da sessão
- Análise StoryBrand
- Plano de execução utilizado

**Localização**:
- Local: `artifacts/ads_final/<timestamp>_<session_id>_<formato>.json`
- GCS (opcional): `gs://<DELIVERIES_BUCKET>/deliveries/<user_id>/<session_id>/final_code_delivery.json`

### Persistência de Seções StoryBrand (Fallback)

Quando o **fallback StoryBrand** é ativado, o sistema salva as **16 seções completas** da narrativa antes da consolidação:

**Arquivo gerado**: `artifacts/storybrand/<session_id>.json`

**Estrutura**:
```json
{
  "sections": {
    "storybrand_hero": "Texto da seção...",
    "storybrand_problema_externo": "Texto da seção...",
    "storybrand_problema_interno": "Texto da seção...",
    // ... 16 seções completas (ver SECTION_CONFIGS)
  },
  "audit": [...],
  "enriched_inputs": {...},
  "timestamp_utc": "2025-10-12T15:00:00Z"
}
```

**Referência no meta.json**:
O arquivo `meta.json` (gerado junto com o JSON final) contém referências às seções:
```json
{
  "storybrand_sections_saved_path": "artifacts/storybrand/<session_id>.json",
  "storybrand_sections_gcs_uri": "gs://bucket/deliveries/<user>/<session>/storybrand_sections.json",
  "storybrand_sections_present": true
}
```

**Quando é gerado**:
- Flag `PERSIST_STORYBRAND_SECTIONS=true` habilitada
- Flag `ENABLE_STORYBRAND_FALLBACK=true` habilitada
- Fallback StoryBrand ativado (score < threshold ou erro)

**Implementação**: `app/agents/storybrand_fallback.py:69-161` (`PersistStorybrandSectionsAgent`)

**Uso**: Auditorias, reconstrução de narrativa completa, análise detalhada por seção.

### Endpoints de Recuperação

- `GET /final/meta` - Metadados do JSON final (inclui referências StoryBrand)
- `GET /final/download` - Download do JSON final de entrega

## 🔧 Comandos de Desenvolvimento

### Ambiente de Desenvolvimento

```bash
# Iniciar todos os serviços (mata portas automaticamente)
make dev

# Iniciar com logging reduzido
make dev-quiet

# Apenas backend (inclui /run_preflight)
make dev-backend-all

# Apenas frontend
make dev-frontend
```

### Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Com relatório de cobertura
pytest tests/ --cov=app --cov-report=html

# Categorias específicas
pytest tests/unit
pytest tests/integration
```

### Qualidade de Código

```bash
# Executar todos os linters
make lint

# Comandos individuais
uv run ruff check . --diff
uv run ruff format . --check --diff
uv run mypy .
uv run codespell
```

### Deploy

```bash
# Deploy para Google Cloud Run
make backend

# Configurar ambiente de desenvolvimento no GCP
make setup-dev-env
```

## 📥 Formato de Entrada

### Campos Base (Sempre Disponíveis)

**Obrigatórios**:
- `landing_page_url`: URL da página de destino
- `objetivo_final`: Objetivo da campanha (ex: agendamentos, leads)
- `perfil_cliente`: Persona do público-alvo
- `formato_anuncio`: "Reels", "Stories" ou "Feed"

**Opcional**:
- `foco`: Tema ou gancho da campanha

### Campos Condicionais (Quando `ENABLE_NEW_INPUT_FIELDS=true`)

Campos adicionais obrigatórios para pipeline de fallback StoryBrand:
- `nome_empresa`: Nome da empresa como deve aparecer nos criativos
- `o_que_a_empresa_faz`: Proposta de valor/resumo do serviço
- `sexo_cliente_alvo`: Gênero do público-alvo - deve ser exatamente `"masculino"` ou `"feminino"`

**Nota**: Estes campos são extraídos em modo shadow quando `PREFLIGHT_SHADOW_MODE=true` mas só incluídos em `initial_state` quando `ENABLE_NEW_INPUT_FIELDS=true`.

## 🎛️ Feature Flags

### Flags Disponíveis

- `ENABLE_STORYBRAND_FALLBACK`: Pipeline de fallback quando análise StoryBrand é fraca ou falha (padrão: `false`)
- `ENABLE_NEW_INPUT_FIELDS`: Campos experimentais de entrada (padrão: `false`)
- `PERSIST_STORYBRAND_SECTIONS`: Salvar 16 seções StoryBrand em artefato separado (padrão: `false`)
- `STORYBRAND_GATE_DEBUG`: Forçar caminho de fallback para testes (padrão: `false`)
- `ENABLE_IMAGE_GENERATION`: Geração de imagens com Gemini (padrão: `true`)
- `PREFLIGHT_SHADOW_MODE`: Extrair novos campos sem incluir em initial_state (padrão: `true`)
- `ENABLE_DETERMINISTIC_FINAL_VALIDATION`: Pipeline de validação determinística para JSON final (padrão: `false`)

### Lógica de Ativação do Fallback

O pipeline de fallback StoryBrand só executa quando:
1. `ENABLE_STORYBRAND_FALLBACK=true` **E** `ENABLE_NEW_INPUT_FIELDS=true` (ambos obrigatórios)
2. **E** um dos seguintes:
   - `STORYBRAND_GATE_DEBUG=true` (força fallback)
   - `force_storybrand_fallback=true` no state (definido por error handlers)
   - Score StoryBrand < `min_storybrand_completeness` (padrão 0.6)

Ver `app/agents/storybrand_gate.py:47-75` para lógica do gate.

### Configurando Flags Localmente

Flags são carregadas de `app/.env` via Makefile:
1. Editar `app/.env`
2. Reiniciar com `make dev` (exporta variáveis automaticamente)
3. Verificar logs de startup para "Feature flags loaded on startup"
4. Procurar entrada de log `storybrand_gate_decision` com `fallback_enabled=True`

### Troubleshooting

Se flags não estão sendo carregadas:
- Verificar que `app/.env` existe e contém as flags
- Reiniciar backend completamente (`make check-and-kill-ports`)
- Verificar logs de startup imediatamente após `make dev`
- Testar: `uv run python -c "import os; from app.config import config; print(config.enable_storybrand_fallback)"`

## 🌐 Variáveis de Ambiente

Configurações principais em `app/.env`:

```bash
GOOGLE_CLOUD_PROJECT=instagram-ads-472021
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
ARTIFACTS_BUCKET=gs://project-facilitador-logs-data  # Opcional
LANGEXTRACT_API_KEY=your-gemini-key  # Opcional
DELIVERIES_BUCKET=gs://bucket-name  # Para upload GCS

# Tunning de performance StoryBrand
STORYBRAND_HARD_CHAR_LIMIT=20000
STORYBRAND_SOFT_CHAR_LIMIT=12000
STORYBRAND_TAIL_RATIO=0.2

# Configurações de retry Vertex AI
VERTEX_CONCURRENCY_LIMIT=3
VERTEX_RETRY_MAX_ATTEMPTS=5
VERTEX_RETRY_INITIAL_BACKOFF=1.0
VERTEX_RETRY_MAX_BACKOFF=30.0
```

## 🏗️ Arquivos Críticos

- **Agente principal**: `app/agent.py` - Definição completa do pipeline
- **Servidor**: `app/server.py` - Endpoints FastAPI incluindo preflight
- **LangExtract**: `app/tools/langextract_sb7.py` - Análise StoryBrand
- **Planos Fixos**: `app/plan_models/fixed_plans.py` - Planos pré-definidos
- **Especificações de Formato**: `app/format_specifications.py` - Regras de formato Instagram
- **Persistência**: `app/callbacks/persist_outputs.py` - Salvamento de outputs e metadados

## 📡 Endpoints da API

- `POST /run_preflight` - Validar entrada e obter estado inicial
- `POST /run` - Executar agente sincronamente (provido pelo ADK)
- `POST /run_sse` - Executar com Server-Sent Events streaming (provido pelo ADK)
- `POST /apps/{app_name}/users/{user_id}/sessions/{session_id}` - Criar sessão (provido pelo ADK)
- `POST /feedback` - Enviar feedback
- `GET /final/meta` - Obter metadados do JSON final
- `GET /final/download` - Download do JSON final

**Nota**: Endpoints marcados como "provido pelo ADK" são registrados automaticamente por `get_fast_api_app()`.

## 🎨 Arquitetura Frontend

- React + TypeScript + Vite
- Localização: `frontend/`
- Componentes principais:
  - `App.tsx` - Componente principal da aplicação
  - `InputForm.tsx` - Manipulação de entrada do usuário
  - `ChatMessagesView.tsx` - Exibição de mensagens
  - Componentes UI em `components/ui/`

## 🤖 Modelos Utilizados

- Agentes worker: `gemini-2.5-flash`
- Agentes critic: `gemini-2.5-pro`
- LangExtract: `gemini-2.5-flash` (via Vertex AI)

## 📚 Documentação Adicional

Para instruções detalhadas sobre desenvolvimento com Claude Code, consulte:
- [README_BACKUP.md](README_BACKUP.md) - Instruções completas do Claude Code
- [.claude/CLAUDE.md](.claude/CLAUDE.md) - Configurações do sistema multi-agente

Para playbooks operacionais e procedimentos:
- [docs/playbooks/](docs/playbooks/) - Procedimentos de rollout, validação e troubleshooting
- [docs/changelog_reference_images.md](docs/changelog_reference_images.md) - Histórico de mudanças

## 🐛 Problemas Conhecidos & Soluções

### Performance da Análise StoryBrand

Se experimentar latência na análise de landing page:
1. Ajustar variáveis de ambiente (ver acima)
2. Verificar logs: `make logs-storybrand`
3. Monitorar métricas de timing nos logs

### Conflitos de Porta

O Makefile mata automaticamente processos nas portas 8000 e 5173 antes de iniciar.

## 📄 Licença

[Especificar licença do projeto]

## 🤝 Contribuindo

[Especificar processo de contribuição]
