# 🔬 Deep Research: Arquitetura ADK com StoryBrand + LangExtract

## CONTEXTO CRÍTICO
Você está analisando um projeto **existente e funcional** em Google ADK que já:
- ✅ Usa `LlmAgent`, `LoopAgent`, `SequentialAgent`, `BaseAgent`
- ✅ Tem pipeline completo: `input_processor → landing_page_analyzer → planning → execution → assembly → validation`
- ✅ Usa `google_search` como única tool para "analisar" URLs (limitado)
- ✅ Gera anúncios Instagram em JSON com callbacks funcionais

**PROBLEMA ATUAL**: O `landing_page_analyzer` não extrai conteúdo real da URL, apenas usa `google_search` (superficial).

## OBJETIVO DA PESQUISA
Descobrir **exatamente** como implementar no ADK:
1. **Extração real de HTML** (fetch HTTP completo)
2. **Parsing estruturado** (texto, headings, CTAs, metadata)
3. **Framework StoryBrand** com evidências rastreáveis
4. **Integração sem quebrar** o pipeline existente

## PERGUNTAS ESPECÍFICAS DO ADK

### 1. TOOLS NATIVAS vs CUSTOM
```python
# O ADK tem alguma dessas tools nativas?
- http_fetch / web_fetch / url_fetch?
- html_parser / text_extractor?
- Ou APENAS google_search?

# Se NÃO existir, qual é o padrão correto?
from google.adk.tools import Tool  # Esta é a classe base?

class WebFetchTool(Tool):
    async def run(self, url: str) -> dict:
        # Como implementar corretamente?
        pass

# Como registrar uma tool custom?
tools=[google_search, web_fetch_tool]  # Assim?
```

### 2. CALLBACKS - PONTOS EXATOS NO ADK
```python
# CONFIRME os nomes exatos e assinaturas:
def my_callback(callback_context: CallbackContext) -> None:
    # callback_context.state[key] = value  # Correto?
    # callback_context.session.state[key] = value  # Ou assim?

# Quais callbacks existem EXATAMENTE no ADK?
before_agent_callback=?
after_agent_callback=?
before_tools_callback=?
after_tools_callback=?
before_model_callback=?
after_model_callback=?

# Em que ordem executam num LlmAgent com tools?
1. before_agent → 2. ? → 3. ? → 4. after_agent
```

### 3. ESTADO E CONTEXTO
```python
# Como acessar o estado em diferentes pontos?

# Dentro de um LlmAgent instruction:
"Analise {landing_page_url}"  # Funciona?

# Dentro de uma callback:
callback_context.state["key"]  # Correto?
callback_context.session.state["key"]  # Ou este?

# Dentro de uma Tool custom:
async def run(self, ctx: InvocationContext):
    ctx.session.state["key"]  # Assim?

# Como passar estado entre agentes num SequentialAgent?
```

### 4. INTEGRAÇÃO DO LANGEXTRACT

**Opção A - Como Tool:**
```python
class LangExtractTool(Tool):
    async def run(self, text: str, schema: dict) -> dict:
        # Chamar LangExtract aqui
        return storybrand_json
```

**Opção B - Como Agent:**
```python
langextract_agent = LlmAgent(
    instruction="Use LangExtract para...",
    tools=[langextract_tool]
)
```

**Opção C - Dentro de callback:**
```python
def after_tools_callback(ctx: CallbackContext):
    html = ctx.state["fetch_result"]
    # Chamar LangExtract aqui?
    storybrand = langextract.extract(html, schema)
    ctx.state["storybrand"] = storybrand
```

**Qual é a melhor prática no ADK?**

### 5. SCHEMA E MODELOS
```python
# Pydantic models funcionam como output_schema?
class StoryBrandSchema(BaseModel):
    personagem: dict
    problema: dict
    # ...

landing_analyzer = LlmAgent(
    output_schema=StoryBrandSchema,  # Suportado?
    output_key="storybrand"
)

# Ou precisa ser dict/JSON?
```

### 6. LOOPS E VALIDAÇÃO
```python
# Como implementar retry com condição?
loop = LoopAgent(
    max_iterations=5,
    sub_agents=[extractor, validator],
    # Como definir condição de parada?
    # Ex: "pare quando storybrand.problema.interno != []"
)

# EscalationChecker - como funciona exatamente?
EscalationChecker(
    name="checker",
    review_key="validation_result"  # O que isso faz?
)
```

### 7. ARQUIVOS DO PROJETO ATUAL
Analise a estrutura existente:
```
app/
├── agent.py (881 linhas)
├── config.py
├── __init__.py
└── tools/  # CRIAR AQUI?
    ├── web_fetch.py
    └── langextract_sb7.py
```

**O padrão ADK recomenda tools em que pasta?**

## ENTREGÁVEIS ESPERADOS

### 1. CÓDIGO EXATO DA TOOL
```python
# web_fetch_tool.py completo e funcional
from google.adk.tools import ???
import requests
from trafilatura import extract

class WebFetchTool(???):
    name = "web_fetch"
    description = "..."

    async def run(self, url: str) -> dict:
        # IMPLEMENTAÇÃO COMPLETA
        pass

# Como registrar?
```

### 2. MODIFICAÇÃO DO landing_page_analyzer
```python
# ANTES (linha 294-338 do agent.py):
landing_page_analyzer = LlmAgent(
    tools=[google_search],
    ...
)

# DEPOIS:
landing_page_analyzer = LlmAgent(
    tools=[web_fetch_tool, google_search],  # Ordem importa?
    before_tools_callback=prepare_fetch,
    after_tools_callback=process_and_extract_sb7,
    ...
)
```

### 3. CALLBACKS NECESSÁRIAS
```python
def prepare_fetch(ctx: CallbackContext):
    # Normalizar URL
    # Verificar cache
    # Decidir tool (fetch vs search)
    pass

def process_and_extract_sb7(ctx: CallbackContext):
    # Parsear HTML
    # Extrair texto, headings, CTAs
    # Chamar LangExtract
    # Salvar no estado
    pass
```

### 4. SCHEMA STORYBRAND PARA ADK
```python
# Como estruturar para máxima compatibilidade ADK?
STORYBRAND_SCHEMA = {
    "personagem": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}}
        }
    },
    # ... resto do schema
}
```

## DADOS DO NOSSO CASO
- **URL teste**: `https://nutrologodivinopolis.com.br/masculino/`
- **Ferramentas disponíveis**: `google_search` (já integrada)
- **LLMs**: `gemini-2.5-flash` (worker), `gemini-2.5-pro` (critic)
- **Estado atual**: Pipeline funcional mas sem extração real de conteúdo

## CRITÉRIOS DE SUCESSO
1. **Código que FUNCIONA no ADK real** (não pseudocódigo)
2. **Reutiliza máximo do ADK** (não reinventa)
3. **Callbacks nos pontos CERTOS** (não em qualquer lugar)
4. **Estado compartilhado CORRETAMENTE** entre agentes
5. **LangExtract integrado SEM quebrar** o fluxo

## FORMATO DA RESPOSTA

### PARTE 1: O que o ADK TEM
```markdown
✅ CONFIRMADO no ADK:
- Tool X (doc: link)
- Callback Y (exemplo: link)
- Padrão Z (referência: link)

❌ NÃO EXISTE no ADK:
- Feature A (precisa implementar)
- Tool B (criar custom)
```

### PARTE 2: Implementação EXATA
```python
# Código 100% funcional, não pseudo
# Com imports corretos do ADK
# Com tratamento de erros
```

### PARTE 3: Integração no agent.py
```python
# Linha exata onde modificar
# Diff do antes/depois
```

### PARTE 4: Testes
```python
# Como testar isoladamente
# Como validar no pipeline
```

---

**IMPORTANTE**:
- Foque em **descobrir o que EXISTE** no ADK antes de criar
- Priorize **reutilizar** componentes nativos
- Garanta **compatibilidade** com pipeline existente
- Forneça **código real**, não conceitual