🔎 Confirmações do ADK
•	Ferramenta nativa load_web_page(url): A documentação oficial confirma a existência da função load_web_page, que “busca o conteúdo na URL e retorna o texto”[1]. Ou seja, basta fazer from google.adk.tools import load_web_page e registrar esta função na lista de tools do agente.
•	Callbacks do ADK: Há tipos de callbacks em cada estágio (agente, modelo, ferramenta). Em Python, as assinaturas são:
•	Before Agent: recebe callback_context: CallbackContext e retorna opcionalmente um Content para sobrescrever o resultado. Ex.:

    def before_agent_cb(ctx: CallbackContext) -> Optional[Content]:
    # ler ctx.state, possivelmente retornar Content para pular o agente
    (documentação de exemplo [30†L235-L244] mostra def check_if_agent_should_run(callback_context: CallbackContext) -> Optional[types.Content] lendo callback_context.state).
•	After Agent: recebe callback_context: CallbackContext e pode retornar Content ou None. Exemplo:

    def after_agent_cb(ctx: CallbackContext) -> Optional[Content]:
    # ler/modificar ctx.state ou a resposta final do agente
    (ver [33†L550-L558] para assinatura e uso em validação).
•	Before Model: recebe (callback_context: CallbackContext, llm_request: LlmRequest) e retorna opcionalmente um LlmResponse para bloquear/alterar a chamada. Exemplo [34†L920-L929]:

    def before_model_cb(ctx: CallbackContext, request: LlmRequest) -> Optional[LlmResponse]:
    # inspeciona/modifica request, retorna LlmResponse para pular LLM
•	After Model: recebe (callback_context: CallbackContext, llm_response: LlmResponse). Exemplo [39†L1217-L1220]:

    def after_model_cb(ctx: CallbackContext, response: LlmResponse) -> Optional[LlmResponse]:
    # inspeciona/modifica response antes de passar ao próximo estágio
•	Before Tool: recebe (tool: BaseTool, args: Dict, tool_context: ToolContext). Pode retornar None (prosseguir) ou um dict para pular a execução do tool (usando este dict como resposta). Exemplo [26†L1580-L1588]:

    def before_tool_cb(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
    # ex.: ajusta args ou retorna {'result': ...} para pular execução do tool
    return None
•	After Tool: recebe (tool: BaseTool, args: Dict, tool_context: ToolContext, tool_response: Dict). Pode retornar None ou novo dict para modificar o resultado. Exemplo [28†L1845-L1854]:

    def after_tool_cb(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, response: Dict) -> Optional[Dict]:
    # ex.: inspeciona response e retorna novo dict ou None
    return None
•	Estado (state): Dentro de callbacks de agente/modelo usa-se callback_context.state, e dentro de callbacks de tool usa-se tool_context.state, ambos agindo como dicionários persistentes[2][3]. Por exemplo, num Tool:

    def my_tool(tool_context: ToolContext) -> dict:
    state = tool_context.state
    state['alguma_chave'] = valor  # gravando no estado
    return {"resposta": algo}
    (O Google ADK demonstra acesso a tool_context.state para ler e escrever dados do estado da sessão[3][4].)
•	output_schema (Pydantic): Se definido em um LlmAgent, o ADK força o agente a gerar exatamente JSON no formato do schema e desativa o uso de tools por aquele agente[5][6]. Em especial, “using output_schema prevents tool use” (sem tools no agente)[7]. Logo, o agente que faz fetch não deve usar output_schema, mas agentes somente de validação (como QA) podem usar schemas para validar saídas.
🛠️ Esqueleto de Código (exemplos)
# app/tools/langextract_sb7.py
import langextract as lx
from langextract.data import ExampleData, Extraction

def langextract_sb7(text: str, prompt: str, examples: list) -> dict:
    """
    Extrai campos SB7 de texto não-estruturado usando LangExtract.
    Retorna dict com extrações e evidências (offsets/spans).
    """
    # Chama o LangExtract
    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt,
        examples=examples,
        model_id="gemini-2.5-flash"
    )
    # formata resultado para JSON simples (exemplo de estrutura):
    output = {
        "extractions": []
    }
    for extr in result.extractions:
        # Cada 'extr' tem atributos: class, text, attributes, span_offsets, etc.
        output["extractions"].append({
            "field": extr.extraction_class, 
            "value": extr.extraction_text,
            "start_offset": extr.start_idx,  # posição inicial no texto
            "end_offset": extr.end_idx      # posição final no texto
            # ... outros detalhes ou evidências ...
        })
    return output
# app/callbacks/landing_fetch_callbacks.py
from google.adk.tools import load_web_page, google_search
from google.adk.tools.tool_context import ToolContext
from langextract_sb7 import langextract_sb7
from schemas.storybrand_schema import StoryBrandSchema

def landing_before_tool(tool, args: dict, tool_context: ToolContext):
    # Decide se vai buscar diretamente ou usar google_search
    url = tool_context.state.get("landing_page_url")
    if url:
        print(f"[Callback] Usando ferramenta: {tool.name}")
        # args já vem contendo 'url'
        return None  # prossegue normalmente
    else:
        return {"error": "URL não encontrada no estado"}

def landing_after_tool(tool, args: dict, tool_context: ToolContext, tool_response):
    """
    Após obter o conteúdo da página, parsear e extrair SB7.
    """
    html = tool_response.get("text") if isinstance(tool_response, dict) else str(tool_response)
    # Parsing simples (placeholder - usar parser real, e.g. BeautifulSoup):
    parsed = {
        "text": html, 
        "headings": [], 
        "links": [],
        "open_graph": {}, 
        "json_ld": {}
    }
    # Exemplo de preenchimento (omitido detalhes do parsing real):
    # parsed["text"] = extrair_texto_principal(html)
    # parsed["headings"] = extrair_headings(html) etc.
    # Salvar no estado de ferramenta
    tool_context.state["parsed_page"] = parsed

    # Preparar LangExtract (prompt e exemplos):
    prompt = "Extrair elementos StoryBrand (SB7) da página: herói, problema, guia, plano, chamada-ação, evitar falha, alcançar sucesso."
    examples = [
        # ExampleData(text="...", extractions=[Extraction(...), ...])
        # preencher com exemplos SB7 anotados em texto de landing pages conhecidas
    ]
    storybrand_result = langextract_sb7(parsed["text"], prompt, examples)
    tool_context.state["storybrand_json"] = storybrand_result

    # Verificar lacunas (exemplo simplificado):
    required_fields = {"hero", "problem", "guide", "plan", "cta", "failure", "success"}
    found = {e["field"] for e in storybrand_result["extractions"]}
    missing = required_fields - found
    tool_context.state["lacunas_detectadas"] = list(missing or [])
# app/agents/input_processor.py
from google.adk.agents import LlmAgent

input_processor = LlmAgent(
    name="InputProcessor",
    model="gemini-2.5-flash",
    instruction="Extraia 'landing_page_url', 'objetivo_final', 'perfil_cliente', 'formato_anuncio' da entrada do usuário.",
    description="Processador de entrada: normaliza e valida campos",
)
# Exemplo de callback para normalizar:
async def after_input(ctx: CallbackContext):
    state = ctx.state
    # padronizar URL (garantir esquema etc)
    if "landing_page_url" in state:
        url = state["landing_page_url"]
        # ex.: garantir formato, adicionar http se faltar
        state["landing_page_url"] = url
input_processor.after_agent_callback = after_input
# app/agents/landing_fetcher.py
from google.adk.agents import LlmAgent
from google.adk.tools import load_web_page, google_search, FunctionTool
from callbacks.landing_fetch_callbacks import landing_before_tool, landing_after_tool
from tools.langextract_sb7 import langextract_sb7
from schemas.storybrand_schema import StoryBrandSchema

landing_fetcher = LlmAgent(
    name="LandingFetcher",
    model="gemini-2.5-flash",
    instruction="Use a ferramenta para obter e analisar o conteúdo da landing page.",
    description="Obtem e extrai info da landing page",
    tools=[load_web_page, google_search],  # ferramentas disponíveis
    before_tool_callback=landing_before_tool,
    after_tool_callback=landing_after_tool
)
# app/agents/sb7_qa.py
from google.adk.agents import LlmAgent
from schemas.storybrand_schema import StoryBrandSchema

sb7_qa = LlmAgent(
    name="SB7QA",
    model="gemini-2.5-pro",
    instruction="Verifique e valide o JSON SB7, identifique campos faltantes e gere 'qa_report'.",
    description="Validações dos campos SB7",
    output_schema=StoryBrandSchema,  # Pydantic: enforces JSON structure
)
async def after_sb7(ctx: CallbackContext):
    sb7 = ctx.state.get("storybrand_json", {})
    # Verificar campos do schema, anotar lacunas no estado
    # (por exemplo, qual campo do schema está None ou vazio)
    missing = []  # lógica de verificação...
    if missing:
        # sinaliza para re-executar LandingFetcher via loop
        ctx.state["retry_fetch"] = True
    ctx.state["qa_report"] = f"Campos faltantes: {missing}"
sb7_qa.after_agent_callback = after_sb7
🗺️ Mapeamento do Estado (state)
•	landing_page_url: definido pelo InputProcessor a partir da entrada do usuário.
•	fetch_result: conteúdo bruto (HTML/texto) retornado por load_web_page; disponível em tool_response e salvado em estado interno.
•	parsed_page: dicionário com partes da página (texto principal, títulos, CTAs, dados OpenGraph/JSON-LD) preenchido em after_tool_callback.
•	storybrand_json: resultado estruturado de SB7 (campo-extracção + evidências) salvo pelo callback do LandingFetcher.
•	lacunas_detectadas: lista de campos SB7 faltantes (identificados após extração).
•	qa_report: relatório de validação da etapa SB7QA (se campos críticos faltam ou não).
Em callbacks, acessamos/atualizamos o estado assim:

tool_context.state["parsed_page"] = parsed_page
tool_context.state["storybrand_json"] = storybrand_result
tool_context.state["lacunas_detectadas"] = missing_fields
E em agente (via CallbackContext):

state = callback_context.state
state["retry_fetch"] = True
🔧 Integração e Diferenças no Código Atual
Supondo que o código existente tinha um agente landing_page_analyzer, faremos:
•	Adicionar load_web_page em tools: No arquivo de configuração/agent (ex: agent.py), ao criar o agente de fetch, incluir load_web_page nas tools:

    - tools=[google_search]
+ tools=[load_web_page, google_search]
•	Registrar callbacks: Definir before_tool_callback=landing_before_tool e after_tool_callback=landing_after_tool ao instanciar LandingFetcher (ver código acima).
•	Agent SB7QA e LoopAgent: Inserir após LandingFetcher um agente de validação sem tools, usando output_schema=StoryBrandSchema, e criar lógica de loop:

    + # Novo agente de validação
+ sb7_qa = LlmAgent(..., output_schema=StoryBrandSchema, ...)
+ sb7_qa.after_agent_callback = after_sb7
    Em agent.py, montar um SequentialAgent ou pipeline assim:

    orchestrator = SequentialAgent(
    name="Orchestrator",
    sub_agents=[input_processor, landing_fetcher, sb7_qa, planning_agent, execution_agent, assembly_agent, validation_agent]
)
    E usar um LoopAgent em torno do segmento LandingFetcher → SB7QA se state["retry_fetch"] ficar True.
•	Exemplo de diff (em agent.py existente):
diff agents = [ - input_processor, - old_landing_analyzer, + input_processor, + landing_fetcher, # novo agente com load_web_page + sb7_qa, # etapa de QA dos resultados SB7 planning_agent, execution_agent, assembly_agent, validation_agent ]
📂 Organização de Arquivos Sugerida
app/
├─ agent.py               # define agentes principais e orquestração
├─ config.py
├─ tools/
│  └─ langextract_sb7.py  # wrapper/FunctionTool para LangExtract SB7
├─ callbacks/
│  └─ landing_fetch_callbacks.py  # antes/depois de tool + parsing + LangExtract
├─ schemas/
│  └─ storybrand_schema.py  # Pydantic schema para SB7
└─ agents/
   ├─ input_processor.py
   ├─ landing_fetcher.py
   └─ sb7_qa.py           # agente de validação (QA) do JSON SB7
Nesse esqueleto, preservamos o pipeline original (planning → execution → assembly → validation) inalterado, apenas consumindo state["storybrand_json"] nas etapas subsequentes. Toda a lógica de fetch e parsing fica encapsulada em LandingFetcher e seus callbacks, reutilizando load_web_page (tool nativa)[1] e processo de extração SB7 com LangExtract. Os callbacks usam tool_context.state para armazenar resultados intermediários[8][3], garantindo rastreabilidade e permitindo que agentes posteriores usem esses dados. O uso de output_schema é restrito ao agente de QA, pois a documentação ADK esclarece que ele desabilita tool-calling (Logo, não deve ser usado no LandingFetcher)[5][6].
Referências: A existência de load_web_page é documentada no ADK[1]; exemplos oficiais ilustram assinaturas de callbacks e uso de tool_context.state[8][9][10][3]. O efeito do output_schema (bloquear uso de tools) também é descrito na documentação ADK[5][6]. Estes trechos confirmam os padrões acima, embasando a implementação sugerida.
