# 🎯 Instagram Ads Generator - Sistema Multi-Agente com Google ADK

## 📋 Visão Geral do Projeto

**Instagram Ads Generator** é um sistema avançado de multi-agentes construído sobre o Google ADK (Agent Development Kit) v1.4.2 que automatiza a geração de anúncios para Instagram em formato JSON estruturado.

**Tecnologia Core**: Python 3.10+ | FastAPI | Google ADK | Gemini 2.5 | GCP

**Missão**: Automatizar completamente o fluxo de criação de anúncios (texto e imagem) a partir de informações fornecidas pelo usuário, gerando sempre 3 variações otimizadas.

**Status**: ✅ Funcional com refatorações recentes (2025-09-12)

## 🏗️ Arquitetura do Sistema

### Pipeline Principal de 8 Agentes

O sistema utiliza um pipeline sequencial de agentes ADK organizados em 8 etapas:

```
input_processor → landing_page_analyzer → context_synthesizer → feature_planner
     ↓                                                                    ↓
validation ← final_assembly ← task_execution ← plan_review
```

### Detalhamento dos Agentes

#### 1. **Input Processor** (`input_processor`)
- **Função**: Extrai e valida campos estruturados da entrada do usuário
- **Campos Obrigatórios**:
  - `landing_page_url`: URL da página de destino
  - `objetivo_final`: Ex: agendamentos, leads, vendas
  - `perfil_cliente`: Persona/storybrand do público-alvo
  - `formato_anuncio`: "Reels", "Stories" ou "Feed" (controlado pelo usuário)
- **Output**: Dados estruturados para próximos agentes

#### 2. **Landing Page Analyzer** (`landing_page_analyzer`)
- **Função**: Analisa a landing page para extrair contexto
- **⚠️ LIMITAÇÃO CRÍTICA**: Usa apenas `google_search` (não faz fetch real do HTML)
- **Tenta Extrair**:
  - Título principal e proposta de valor
  - Benefícios e CTAs
  - Ofertas e provas sociais
  - Tom de voz e palavras-chave
- **Output**: Contexto extraído (superficial)

#### 3. **Context Synthesizer** (`context_synthesizer`)
- **Função**: Consolida todas as entradas em briefing estruturado
- **Processa**:
  - Persona e dores/benefícios
  - Formato definido pelo usuário
  - Mensagens-chave (tentativa de alinhamento com landing)
  - Restrições (políticas Instagram/saúde)
- **Output**: Briefing completo para planejamento

#### 4. **Feature Planner** (`feature_planner`)
- **Função**: Gera plano detalhado com tarefas categorizadas
- **Categorias de Tarefas**:
  - `STRATEGY`: Diretrizes estratégicas
  - `RESEARCH`: Referências e padrões
  - `COPY_DRAFT`: Texto do anúncio
  - `VISUAL_DRAFT`: Descrição de imagem estática
  - `COPY_QA` / `VISUAL_QA`: Validações
  - `COMPLIANCE_QA`: Conformidade
  - `ASSEMBLY`: Montagem JSON
- **Output**: Lista estruturada de tarefas

#### 5. **Plan Review Loop** (`plan_review`)
- **Função**: Loop de revisão e refinamento do plano
- **Iterações**: Até 7 ciclos
- **Valida**: Coerência, completude, alinhamento com objetivo
- **Output**: Plano aprovado

#### 6. **Task Execution** (`task_execution`)
- **Função**: Executa cada tarefa do plano aprovado
- **Sub-agentes**:
  1. `code_generator`: Gera fragmento JSON
  2. `code_reviewer`: Valida alinhamento e qualidade
  3. `code_refiner`: Aplica correções se necessário
  4. `code_approver`: Registra fragmento aprovado
- **Iterações**: Até 8 por tarefa
- **Output**: Fragmentos JSON aprovados

#### 7. **Final Assembly** (`final_assembly`)
- **Função**: Combina fragmentos em 3 variações de anúncio
- **Garante**:
  - Estrutura JSON válida
  - Todas as chaves obrigatórias presentes
  - Variações diferentes entre si
- **Output**: Array com 3 anúncios completos

#### 8. **Final Validation** (`final_validation`)
- **Função**: Validação final rigorosa
- **Iterações**: Até 10 ciclos
- **Valida**:
  - JSON válido com exatamente 3 objetos
  - Enums corretos (formato, aspect_ratio, CTA)
  - Coerência com objetivo
  - Conformidade com políticas Instagram
- **Output**: JSON final aprovado

## 📊 Modelos de Dados

### Estrutura Principal do Anúncio

```python
from pydantic import BaseModel
from typing import Literal

class AdCopy(BaseModel):
    """Textos do anúncio"""
    headline: str           # Título principal (máx 40 caracteres)
    corpo: str             # Texto do corpo (máx 125 caracteres)
    cta_texto: str         # Texto do botão CTA

class AdVisual(BaseModel):
    """Visual do anúncio - apenas imagens"""
    descricao_imagem: str  # Descrição detalhada da imagem
    aspect_ratio: Literal["9:16", "1:1", "4:5", "16:9"]

class AdItem(BaseModel):
    """Estrutura completa de um anúncio"""
    landing_page_url: str
    formato: Literal["Reels", "Stories", "Feed"]
    copy: AdCopy
    visual: AdVisual
    cta_instagram: Literal[
        "Saiba mais",
        "Enviar mensagem",
        "Ligar",
        "Comprar agora",
        "Cadastre-se"
    ]
    fluxo: str                # Ex: "Instagram Ad → Landing Page → WhatsApp"
    referencia_padroes: str   # Padrões de mercado utilizados
    contexto_landing: str     # Contexto extraído da landing page
```

### Exemplo de Output Final

```json
[
  {
    "landing_page_url": "https://exemplo.com/produto",
    "formato": "Feed",
    "copy": {
      "headline": "Transforme sua rotina hoje",
      "corpo": "Descubra o método comprovado que já ajudou +5000 pessoas",
      "cta_texto": "Quero começar agora"
    },
    "visual": {
      "descricao_imagem": "Mulher sorridente usando o produto em ambiente moderno",
      "aspect_ratio": "1:1"
    },
    "cta_instagram": "Saiba mais",
    "fluxo": "Instagram Ad → Landing Page → Formulário → Email",
    "referencia_padroes": "Hook emocional + prova social + urgência",
    "contexto_landing": "Página sobre método de produtividade com depoimentos"
  },
  // ... mais 2 variações
]
```

## ⚡ Comandos Essenciais

### Desenvolvimento
```bash
# Ativar ambiente virtual
source .venv/bin/activate           # Linux/Mac
.venv\Scripts\activate              # Windows

# Instalar/atualizar dependências
uv sync                            # Gerenciador de pacotes uv
pip install -r requirements.txt    # Alternativa com pip

# Executar servidor de desenvolvimento
make dev-backend-all               # Backend + Frontend
uvicorn app.server:app --reload --port 8000  # Apenas backend

# Frontend (se disponível)
npm run dev                        # Interface web
```

### Testes
```bash
# Executar todos os testes
pytest tests/ -v

# Teste específico
pytest tests/unit/test_agent.py -k "test_pipeline"

# Com cobertura
pytest tests/ --cov=app --cov-report=html
```

### Validação de Código
```bash
# Lint e formatação
make lint                          # Executa ruff e mypy
ruff check app/                    # Apenas verificação
ruff format app/                   # Formatação automática

# Type checking
mypy app/
```

### Google Cloud
```bash
# Autenticação
gcloud auth login
gcloud config set project [PROJECT_ID]
export GOOGLE_CLOUD_PROJECT=[PROJECT_ID]

# Deploy
gcloud run deploy instagram-ads-generator \
  --source . \
  --region us-central1
```

## 🔒 Regras Críticas

### ⛔ NUNCA FAÇA
- **NUNCA** modifique arquivos em `.venv/`, `uv.lock`, ou `__pycache__/`
- **NUNCA** altere a estrutura do pipeline de 8 agentes sem aprovação
- **NUNCA** remova validações de campos obrigatórios
- **NUNCA** reduza as iterações de loop (mínimo 7-10)
- **NUNCA** commite API keys ou credenciais
- **NUNCA** gere vídeos (apenas imagens são suportadas)
- **NUNCA** ignore o formato escolhido pelo usuário

### ✅ SEMPRE FAÇA
- **SEMPRE** gere exatamente 3 variações de anúncio
- **SEMPRE** valide formato JSON antes de retornar
- **SEMPRE** use `uv` para gerenciar dependências
- **SEMPRE** mantenha o campo `formato_anuncio` como obrigatório
- **SEMPRE** execute testes antes de fazer alterações em `app/agent.py`
- **SEMPRE** documente limitações conhecidas
- **SEMPRE** valide conformidade com políticas do Instagram

## 📁 Estrutura de Arquivos

```
instagram_ads/
├── app/                          # [CORE - Modificar com cuidado]
│   ├── agent.py                 # ⚡ Pipeline principal (881 linhas)
│   ├── config.py                # Configurações e modelos
│   ├── server.py                # API FastAPI
│   └── utils/                   # Utilitários
│       ├── gcs.py              # Google Cloud Storage
│       └── tracing.py          # OpenTelemetry
├── frontend/                    # [PODE MODIFICAR] Interface web (se existir)
├── deployment/                  # [PODE MODIFICAR] Scripts de deploy
├── tests/                       # [PODE MODIFICAR] Testes
│   ├── unit/                   # Testes unitários
│   ├── integration/            # Testes de integração
│   └── load_test/              # Testes de carga (Locust)
├── .env                        # [NUNCA COMMITAR] Credenciais
├── Makefile                    # Comandos automatizados
├── pyproject.toml              # [CUIDADO] Configuração do projeto
├── requirements.txt            # Dependências Python
├── README.md                   # Documentação principal
├── AGENTS.md                   # Guia de desenvolvimento
└── contexto.md                # Este arquivo
```

### Modificação de Arquivos
```yaml
PODE_MODIFICAR:
  - frontend/**/*          # Interface web
  - tests/**/*            # Adicionar testes
  - deployment/**/*       # Scripts de deploy
  - docs/**/*            # Documentação

MODIFICAR_COM_CUIDADO:
  - app/agent.py         # Pipeline principal - testar sempre
  - app/server.py        # API - manter compatibilidade
  - app/config.py        # Configurações - validar mudanças
  - pyproject.toml       # Usar 'uv add', não editar manual

NUNCA_MODIFICAR:
  - .venv/**/*           # Ambiente virtual
  - uv.lock              # Lock file do uv
  - __pycache__/**/*     # Cache Python
  - .git/**/*            # Controle de versão
```

## 🎨 Padrões de Código

### Python/ADK
```python
# ✅ BOM: Seguindo padrões ADK
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
import logging

logger = logging.getLogger(__name__)

class AdGenerator:
    """Gerador de anúncios seguindo padrões ADK."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validate_config()

    async def generate_ads(
        self,
        input_data: Dict[str, Any]
    ) -> List[AdItem]:
        """Gera 3 variações de anúncio."""
        try:
            validated = self._validate_input(input_data)
            ads = await self._process_pipeline(validated)
            return self._ensure_three_variations(ads)
        except Exception as e:
            logger.error(f"Erro na geração: {e}")
            raise

# ❌ RUIM: Não seguindo padrões
class generator:
    def make_ad(self, data):
        # Sem tipos, sem validação, sem tratamento de erro
        return data
```

### Configuração de Modelos LLM
```python
# Modelos por tarefa (em config.py)
MODEL_CONFIG = {
    "worker": "gemini-2.5-flash",     # Tarefas rápidas
    "critic": "gemini-2.5-pro",       # Revisões críticas
    "max_tokens": 1024,
    "temperature": 0.7,
    "top_p": 0.9
}

# Iterações máximas
ITERATION_LIMITS = {
    "code_review": 8,
    "plan_review": 7,
    "final_validation": 10,
    "max_tasks": 20
}
```

## 🧪 Estratégia de Testes

### Testes Unitários
```python
# tests/unit/test_models.py
import pytest
from app.config import AdItem, AdCopy, AdVisual

def test_ad_item_validation():
    """Testa validação do modelo AdItem."""
    valid_data = {
        "landing_page_url": "https://example.com",
        "formato": "Feed",
        "copy": {
            "headline": "Teste",
            "corpo": "Corpo do anúncio",
            "cta_texto": "Saiba mais"
        },
        "visual": {
            "descricao_imagem": "Imagem teste",
            "aspect_ratio": "1:1"
        },
        "cta_instagram": "Saiba mais",
        "fluxo": "Instagram → Landing",
        "referencia_padroes": "Padrão X",
        "contexto_landing": "Contexto Y"
    }

    ad = AdItem(**valid_data)
    assert ad.formato == "Feed"
    assert ad.visual.aspect_ratio == "1:1"

def test_invalid_formato():
    """Testa rejeição de formato inválido."""
    with pytest.raises(ValueError):
        AdItem(formato="TikTok", ...)  # Deve falhar
```

### Testes de Integração
```python
# tests/integration/test_pipeline.py
async def test_full_pipeline():
    """Testa pipeline completo de geração."""
    input_data = {
        "landing_page_url": "https://test.com",
        "objetivo_final": "vendas",
        "perfil_cliente": "Empreendedores 25-40 anos",
        "formato_anuncio": "Feed"
    }

    result = await run_pipeline(input_data)

    assert len(result) == 3  # Sempre 3 variações
    assert all(ad["formato"] == "Feed" for ad in result)
    assert all("landing_page_url" in ad for ad in result)
```

## ⚠️ Limitações Conhecidas

### 🔴 Críticas
1. **Não extrai conteúdo real da landing page**
   - Usa apenas `google_search` (resultados superficiais)
   - Não acessa HTML/conteúdo real das páginas
   - **Impacto**: Copy pode não alinhar com landing page real

2. **Sem framework estruturado de copywriting**
   - Não implementa StoryBrand ou metodologias similares
   - **Impacto**: Qualidade do copy depende do modelo LLM

3. **Sem fetch HTTP real**
   - Não pode verificar se landing page existe
   - **Impacto**: Pode gerar anúncios para páginas inválidas

### 🟡 Moderadas
1. **Contexto limitado a informações públicas indexadas**
   - Depende do que o Google já indexou
   - **Workaround**: Fornecer descrição detalhada manualmente

2. **Alinhamento parcial com conteúdo da landing**
   - Copy pode divergir do real conteúdo
   - **Workaround**: Revisar e ajustar manualmente

3. **Sem rastreabilidade de fonte**
   - Não há evidências do conteúdo extraído
   - **Workaround**: Logs detalhados do processo

### 🟢 Melhorias Planejadas
1. Implementar `web_fetch` para acesso real a páginas
2. Adicionar parser HTML estruturado (BeautifulSoup)
3. Integrar framework StoryBrand
4. Adicionar cache para URLs já processadas
5. Melhorar rastreabilidade com offsets/quotes

## 🔧 Solução de Problemas

### Problema: Pipeline trava na geração
```bash
# Verificar logs
tail -f logs/app.log

# Aumentar timeout
export PIPELINE_TIMEOUT=600

# Verificar limites de iteração em config.py
grep -n "max_iterations" app/config.py
```

### Problema: Validação final falhando repetidamente
```python
# Debugar validação
import json

# Verificar JSON gerado
with open("debug_output.json", "w") as f:
    json.dump(generated_ads, f, indent=2)

# Validar estrutura
for ad in generated_ads:
    assert all(key in ad for key in REQUIRED_KEYS)
```

### Problema: Erro de API (Gemini/OpenAI)
```bash
# Verificar credenciais
echo $GOOGLE_API_KEY
echo $OPENAI_API_KEY

# Testar conexão
curl -H "Authorization: Bearer $GOOGLE_API_KEY" \
  https://generativelanguage.googleapis.com/v1/models

# Verificar quota
# Acessar console.cloud.google.com
```

### Problema: Memória/Performance
```bash
# Monitorar uso de memória
htop

# Profile do código
python -m cProfile -o profile.stats app/agent.py

# Analisar profile
python -m pstats profile.stats
```

## 🚀 Workflows de Desenvolvimento

### Workflow 1: Adicionar Nova Validação
```bash
# 1. Criar teste primeiro (TDD)
echo "def test_new_validation():" >> tests/unit/test_validations.py

# 2. Implementar validação
vim app/agent.py  # Adicionar lógica

# 3. Executar testes
pytest tests/unit/test_validations.py -v

# 4. Integrar ao pipeline
# Adicionar ao final_validation agent
```

### Workflow 2: Melhorar Extração de Landing Page
```python
# 1. Avaliar limitação atual
# landing_page_analyzer usa apenas google_search

# 2. Implementar solução
# Opção A: Adicionar web_fetch tool
from tools import web_fetch

async def extract_real_content(url: str):
    html = await web_fetch(url)
    parsed = parse_html(html)
    return extract_key_info(parsed)

# 3. Testar com URLs reais
test_urls = [
    "https://example1.com",
    "https://example2.com"
]

# 4. Comparar resultados
# google_search vs web_fetch
```

### Workflow 3: Debug de Geração
```python
# 1. Ativar modo debug
import logging
logging.basicConfig(level=logging.DEBUG)

# 2. Adicionar checkpoints
def checkpoint(stage: str, data: Any):
    print(f"=== {stage} ===")
    print(json.dumps(data, indent=2))
    input("Press Enter to continue...")

# 3. Rastrear pipeline
checkpoint("After input_processor", processed_input)
checkpoint("After landing_analyzer", landing_context)
# etc...
```

## 📊 Métricas e Monitoramento

### KPIs do Sistema
- **Taxa de Sucesso**: % de gerações sem erro
- **Tempo Médio**: Tempo total do pipeline
- **Iterações por Etapa**: Quantas revisões cada agente faz
- **Qualidade do Output**: Validações passadas na primeira tentativa

### Implementação de Métricas
```python
from dataclasses import dataclass
from time import time

@dataclass
class PipelineMetrics:
    total_time: float
    iterations_per_stage: Dict[str, int]
    validation_passes: int
    errors: List[str]

    def log_metrics(self):
        logger.info(f"Pipeline concluído em {self.total_time}s")
        logger.info(f"Iterações: {self.iterations_per_stage}")
        logger.info(f"Taxa de sucesso: {self.success_rate}%")
```

## 🔄 Processo de Contribuição

### Git Flow
```bash
# 1. Criar branch para feature
git checkout -b feature/melhoria-landing-analyzer

# 2. Fazer mudanças
# ... editar arquivos ...

# 3. Testar
make test

# 4. Lint
make lint

# 5. Commit
git add .
git commit -m "feat: melhoria na extração de landing pages"

# 6. Push
git push origin feature/melhoria-landing-analyzer

# 7. Criar PR
# Via GitHub/GitLab
```

### Checklist para PR
- [ ] Testes passando (`make test`)
- [ ] Lint sem erros (`make lint`)
- [ ] Documentação atualizada
- [ ] Não quebra compatibilidade
- [ ] Segue padrões do projeto
- [ ] Não expõe credenciais

## 📚 Referências

### Documentação Principal
- [README.md](./README.md) - Visão geral e status atual
- [AGENTS.md](./AGENTS.md) - Guidelines de desenvolvimento
- [Google ADK Docs](https://cloud.google.com/adk/docs) - Documentação oficial ADK

### APIs e Serviços
- [Gemini API](https://ai.google.dev/docs) - Documentação Gemini
- [Instagram Ads Policies](https://www.facebook.com/policies/ads/) - Políticas de anúncios
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web

### Ferramentas
- [uv](https://github.com/astral-sh/uv) - Gerenciador de pacotes Python
- [Ruff](https://github.com/astral-sh/ruff) - Linter Python
- [Pytest](https://docs.pytest.org/) - Framework de testes

## 🎯 Regra de Ouro

**Antes de qualquer modificação no pipeline:**

1. **ENTENDA** - Leia o código atual e documentação
2. **TESTE** - Escreva testes para sua mudança
3. **IMPLEMENTE** - Faça a modificação
4. **VALIDE** - Execute todos os testes
5. **DOCUMENTE** - Atualize documentação se necessário
6. **REVISE** - Peça review de código

**LEMBRE-SE**:
- O sistema DEVE sempre gerar 3 variações
- O formato é controlado pelo USUÁRIO, não pelo sistema
- Validações são críticas - não as pule
- Limitações conhecidas devem ser documentadas

---

**Última atualização**: 2025-09-13
**Versão**: 2.0.0 (Reescrito para Instagram Ads Generator)