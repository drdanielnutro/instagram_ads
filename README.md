# Sistema de Geração de Anúncios Instagram com Google ADK

## Visão Geral

Este projeto é um sistema multiagente baseado no Google ADK (Agent Development Kit) para gerar anúncios do Instagram em formato JSON. O objetivo principal é automatizar todo o fluxo de criação de anúncios (texto e imagem) a partir de informações fornecidas pelo usuário.

**Status**: ✅ Funcional com refatorações recentes (2025-09-12)

## Refatorações Recentes

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

### 1. Input Processor
Extrai campos estruturados da entrada do usuário:

**Campos obrigatórios**:
- `landing_page_url`: URL da página de destino
- `objetivo_final`: Ex: agendamentos, leads, vendas
- `perfil_cliente`: Persona/storybrand do público-alvo
- `formato_anuncio`: **"Reels", "Stories" ou "Feed"** (controlado pelo usuário)

### 2. Landing Page Analyzer
**⚠️ LIMITAÇÃO CRÍTICA**: Usa apenas `google_search` para buscar informações públicas. **NÃO faz fetch real do HTML**.

Tenta extrair:
- Título principal e proposta de valor
- Benefícios e CTAs
- Ofertas e provas sociais
- Tom de voz e palavras-chave

### 3. Context Synthesizer
Consolida entradas em briefing estruturado:
- Persona e dores/benefícios
- Formato definido pelo usuário
- Mensagens-chave (tentativa de alinhamento com landing page)
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
1. `code_generator`: Gera fragmento JSON
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
- `contexto_landing`: Resumo do contexto extraído

### 8. Final Validation
Valida:
- JSON válido com 3 objetos
- Todas chaves obrigatórias presentes
- Enums corretos (formato, aspect_ratio, CTA)
- Coerência com objetivo
- Variações diferentes entre si

## Modelos de Dados

```python
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
    contexto_landing: str  # Novo campo
```

## Limitações Conhecidas

### 🔴 Críticas
1. **Não extrai conteúdo real da landing page**: Usa apenas `google_search` (superficial)
2. **Sem fetch HTTP**: Não acessa HTML/conteúdo real das páginas
3. **Sem framework estruturado**: Não implementa StoryBrand ou similar

### 🟡 Moderadas
1. **Contexto limitado**: Depende de informações públicas indexadas
2. **Alinhamento parcial**: Copy pode divergir do conteúdo real da landing
3. **Sem rastreabilidade**: Não há evidências/offsets do conteúdo extraído

## Configuração

### Modelos LLM
- **Worker**: `gemini-2.5-flash`
- **Critic**: `gemini-2.5-pro`

### Iterações Máximas
```python
max_code_review_iterations: 8
max_plan_review_iterations: 7
final_validation_loop: 10
max_task_iterations: 20
```

### Estrutura de Arquivos
```
app/
├── agent.py          # Pipeline completo (881 linhas)
├── config.py         # Configurações
├── server.py         # API FastAPI
└── utils/
    ├── gcs.py       # Google Cloud Storage
    └── tracing.py   # Telemetria
```

## API

### POST /feedback
Recebe feedback sobre anúncios gerados:
```json
{
  "grade": "pass|fail",
  "comment": "...",
  "follow_up_queries": [...]
}
```

## Execução

```bash
# Backend
make dev-backend-all

# Frontend (se disponível)
npm run dev
```

Acesso: http://localhost:8000

## Próximos Passos Sugeridos

1. **Implementar fetch real de HTML** (web_fetch tool)
2. **Adicionar parser estruturado** (Trafilatura/BeautifulSoup)
3. **Integrar framework StoryBrand** com evidências
4. **Melhorar rastreabilidade** (offsets/quotes)
5. **Adicionar cache** para URLs já processadas

## Observações

- O bucket de logs usa nome `{project_id}-facilitador-logs-data` (herança do projeto original)
- Sistema funcional mas com limitações na extração de conteúdo
- Refatorações recentes melhoraram qualidade e controle do usuário

---

**Última atualização**: 2025-09-13