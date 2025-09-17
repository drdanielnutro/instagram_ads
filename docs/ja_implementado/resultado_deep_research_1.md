Relatório de Implementação Avançada: Arquitetura ADK com Extração de Conteúdo e Framework StoryBrandIntrodução: Arquitetando um Pipeline de Análise de Conteúdo de Alta Fidelidade no ADKEste relatório detalha uma arquitetura robusta e idiomática para aprimorar um pipeline existente do Google Agent Development Kit (ADK). O ponto de partida é um sistema funcional que gera anúncios para o Instagram, mas que depende de uma análise superficial de URLs através da ferramenta google_search. O objetivo é substituir este componente por um motor de análise de conteúdo profundo, capaz de realizar a extração real de HTML, parsing estruturado e a aplicação do framework de marketing StoryBrand (SB7) de forma rastreável e eficiente.O desafio central não é corrigir um defeito, mas sim executar uma atualização estratégica. A transição de uma análise baseada em busca para uma análise baseada em extração direta de conteúdo requer uma compreensão nuançada dos padrões de design do ADK. A arquitetura proposta aqui se baseia em uma sinergia entre Ferramentas Customizadas (Custom Tools) para ações de I/O e Callbacks para lógica de processamento determinístico. Esta abordagem maximiza a eficiência, a manutenibilidade e a aderência às melhores práticas do ADK, resultando em um sistema mais poderoso, econômico e de menor latência.PARTE 1: Capacidades e Restrições Arquiteturais do ADK: O que Existe vs. O que ConstruirAntes de implementar a solução, é fundamental estabelecer um entendimento claro do cenário de ferramentas e funcionalidades do ADK. Esta seção fornece respostas definitivas às questões fundamentais sobre os componentes nativos, as limitações da plataforma e os padrões corretos para a extensão do f
ramework.1.1. Ferramentas Nativas vs. Customizadas: Um Inventário DefinitivoUma análise da documentação oficial do ADK revela um conjunto de ferramentas nativas poderosas, porém focadas em serviços específicos do ecossistema Google.Confirmação do google_search: A ferramenta google_search é um componente nativo e poderoso, mas seu propósito é realizar buscas na web e fornecer "grounding" (contextualização) para as respostas do LLM, não a extração direta e completa do conteúdo HTML de uma URL.1 Usá-la para análise de conteúdo é uma aproximação que não atende aos requisitos de profundidade do projeto.A Ausência de Ferramentas Nativas de Fetch/Parse: O ADK não possui ferramentas nativas como http_fetch, web_fetch ou html_parser. O conjunto de ferramentas "built-in" está focado em serviços como Google Search, Code Execution, Vertex AI Search e BigQuery.1 Esta constatação estabelece a necessidade inequívoca de construir uma ferramenta customizada para a extração de conteúdo.O Caminho Correto: Ferramentas de Função Customizadas (Custom Function Tools): A abordagem idiomática e recomendada pelo ADK para esta tarefa é a criação de uma "Function Tool".2 Este padrão consiste em escrever uma função Python padrão, com anotações de tipo (type hints) e uma docstring clara, e registrá-la na lista de tools de um agente. O ADK se encarrega de inspecionar a assinatura da função e a docstring para gerar o esquema necessário para que o LLM entenda como e quando utilizá-la.3 Embora seja possível herdar da classe base google.adk.tools.BaseTool para cenários mais complexos, a simplicidade de usar uma função Python pura é preferível na maioria dos casos.21.2. Esquemas Pydantic: Poder e uma Limitação CríticaA capacidade de gerar saídas estruturadas é vital para sistemas de agentes que interagem com outros componentes de software.Confirmação do Suporte a Pydantic: O LlmAgent do ADK suporta totalmente modelos Pydantic através do parâmetro output_schema. Isso força o LLM a gerar uma resposta em formato JSON que adere estritamente à estrutura do modelo Pydantic fornecido, incluindo validação de tipos e campos.8A Restrição Fundamental: output_schema e tools são Mutuamente Exclusivos: Este é o ponto de maior impacto arquitetural para este projeto. A documentação oficial e discussões na comunidade confirmam que um LlmAgent configurado com um output_schema não pode, simultaneamente, utilizar ferramentas (tools).10 Esta limitação invalida qualquer arquitetura que tente usar um único agente para, em uma mesma etapa, buscar conteúdo de uma URL (que requer uma ferramenta) e formatar esse conteúdo em um JSON estruturado (que idealmente usaria output_schema).Essa restrição força a adoção de padrões de design mais sofisticados. A solução comum para contornar essa limitação é usar um SequentialAgent com dois LlmAgents: o primeiro usa ferramentas para coletar dados e o segundo, sem ferramentas, usa output_schema para formatar a saída do primeiro. No entanto, para o caso específico de aplicar o LangExtract, a transformação de texto para o JSON do StoryBrand é um processo determinístico que não requer o raciocínio de um LLM. Portanto, uma arquitetura ainda mais eficiente e elegante consiste em realizar essa transformação dentro de um callback, eliminando a necessidade de um segundo agente e uma chamada adicional ao LLM. Esta será a base da solução implementada.1.3. Tabela de Referência: Componentes e Padrões do ADKA tabela a seguir resume os principais pontos sobre as capacidades do ADK relevantes para este projeto, servindo como um guia de referência rápida.Componente/Funcionalidade ADKStatus e Nome OficialObservação Chave e ReferênciaClasse Base para Ferramenta Customizada✅ google.adk.tools.BaseToolEmbora exista, o padrão mais simples é fornecer uma função Python, que o ADK envolve automaticamente.2Ferramenta de HTTP Fetch❌ Não NativaDeve ser implementada como uma ferramenta customizada. google_search é a única ferramenta web nativa.1Ferramenta de HTML Parser❌ Não NativaA lógica de parsing deve ser parte da ferramenta customizada ou de um callback subsequente.Callbacks de Agente✅ before_agent_callback, after_agent_callbackExecutados no início e no fim do ciclo de vida completo de um agente.11Callbacks de Modelo✅ before_model_callback, after_model_callbackInterceptam a requisição e a resposta da chamada ao LLM.11Callbacks de Ferramenta✅ before_tool_callback, after_tool_callbackEnvolvem a execução de uma ferramenta específica, permitindo pré e pós-processamento.11Objeto de Contexto de Callback✅ CallbackContextFornece acesso ao nome do agente, contexto de invocação e estado da sessão (state).13Objeto de Contexto de Ferramenta✅ ToolContextInjetado em ferramentas; fornece acesso ao estado da sessão (state) e ações de invocação.4Suporte a Schema Pydantic✅ Suportado em output_schemaO ADK pode forçar a saída do LLM a se conformar com um modelo Pydantic.9Uso Simultâneo de tools e output_schema❌ Mutuamente ExclusivoLimitação crítica. Um agente não pode ter ambos os parâmetros configurados.10Terminação de Loop✅ via tool_context.actions.escalate = TrueMecanismo padrão para um sub-agente/ferramenta sinalizar a parada de um LoopAgent.15PARTE 2: A Arquitetura Ótima: Sinergia entre Ferramentas Customizadas e CallbacksCom base nas capacidades e limitações do ADK, a arquitetura mais eficiente e idiomática para resolver o problema proposto é o padrão "Fetch-then-Process". Este padrão utiliza uma Ferramenta Customizada para a ação externa (buscar dados) e um Callback para a lógica interna (processar dados).2.1. O Padrão "Fetch-then-Process": Ferramenta para Ação, Callback para LógicaEste padrão se baseia no princípio de separação de responsabilidades, um pilar da engenharia de software que o design do ADK incentiva.O Papel da Ferramenta (WebFetchTool): A responsabilidade da ferramenta é singular: realizar a operação de I/O externa de buscar dados de uma URL. Ela deve receber uma string de URL e retornar o conteúdo bruto ou semi-processado. Isso torna a ferramenta simples, reutilizável e fácil de testar em isolamento.4O Papel do Callback (after_tool_callback): A responsabilidade do callback é lidar com a transformação de dados interna e determinística. Ele é acionado após a ferramenta retornar os dados com sucesso. Este é o local perfeito para executar lógica como parsing de HTML, extração de texto com trafilatura e a aplicação do LangExtract para gerar a análise StoryBrand.11Superioridade da Abordagem: Este padrão evita chamadas desnecessárias ao LLM. O modelo é invocado uma única vez para decidir chamar a ferramenta web_fetch. O processamento subsequente, que é determinístico, ocorre em código Python puro (no callback), sem a necessidade de um segundo LlmAgent apenas para formatação. Isso economiza custos de API, reduz a latência da resposta e aumenta a robustez do sistema, pois elimina a não-deterministicidade do LLM de uma tarefa que não a requer.2.2. O Ciclo de Vida de Execução do LlmAgent com Ferramentas e CallbacksPara integrar essa arquitetura corretamente, é essencial compreender a ordem precisa em que o ADK executa cada componente. A sequência de eventos para um LlmAgent que utiliza uma ferramenta é a seguinte:before_agent_callback Dispara: A execução do agente landing_page_analyzer começa.12before_model_callback Dispara: O agente prepara o prompt (instrução + entrada do usuário) para ser enviado ao LLM.12Invocação do LLM: O LLM recebe o prompt e, com base em sua instrução, decide que a melhor ação é chamar a ferramenta web_fetch_tool com a URL fornecida.after_model_callback Dispara: A resposta do LLM, que é a requisição de chamada da ferramenta (tool call), é recebida pelo framework ADK.12before_tool_callback Dispara: O framework está prestes a executar a ferramenta web_fetch_tool. Neste ponto, o callback prepare_fetch_analysis é executado, permitindo a validação da URL ou a verificação de um cache.11Execução da Ferramenta: A função da ferramenta web_fetch_tool é executada, realizando a requisição HTTP para a URL especificada.after_tool_callback Dispara: A ferramenta retorna seu resultado (o conteúdo da página). Este é o ponto de integração chave. O callback process_and_extract_sb7 recebe este resultado, executa o parsing, aplica o LangExtract e salva a análise StoryBrand estruturada no estado da sessão (callback_context.state).Segunda Invocação do LLM ( sumarização): O resultado da ferramenta (e quaisquer modificações feitas pelo callback) é enviado de volta ao LLM. O modelo agora tem o contexto do conteúdo da página e da análise realizada, e pode cumprir a parte final de sua instrução: gerar um resumo para o usuário.after_agent_callback Dispara: A execução do agente está completa. A resposta final (o resumo gerado pelo LLM) está pronta para ser retornada e, potencialmente, passada para o próximo agente no pipeline SequentialAgent.12PARTE 3: Implementação I: A Ferramenta WebFetchTool para Extração Profunda de ConteúdoEsta seção fornece o código completo e pronto para produção da ferramenta customizada responsável por buscar e extrair o conteúdo textual de uma página web.3.1. Estrutura de Projeto RecomendadaA sugestão de criar um diretório app/tools/ é validada como uma boa prática para organizar ferramentas customizadas em projetos ADK, promovendo a modularidade e a manutenibilidade.16 A estrutura final recomendada é:app/
├── agent.py
├── config.py
├── __init__.py
└── tools/
    ├── __init__.py
    ├── web_fetch_tool.py  # <-- Nova Ferramenta
    └── langextract_sb7.py # <-- Lógica do LangExtract
3.2. Código: tools/web_fetch_tool.pyO código a seguir deve ser colocado no arquivo app/tools/web_fetch_tool.py. Ele define a função que realiza a busca do conteúdo e a exporta como uma FunctionTool do ADK.Python# app/tools/web_fetch_tool.py

import requests
import trafilatura
from google.adk.tools import FunctionTool
import logging

# Configuração do logger para esta ferramenta
logger = logging.getLogger(__name__)

def fetch_and_extract_text(url: str) -> dict:
    """
    Fetches the full HTML content from a given URL and extracts the main text content.
    This tool is designed to retrieve the core article or body text from a webpage,
    stripping away boilerplate like navigation, ads, and footers.
    Use this tool when you need to analyze the actual content of a landing page or article.

    Args:
        url: The complete URL of the webpage to fetch (e.g., 'https://example.com/page').

    Returns:
        A dictionary containing the status of the operation and the results.
        On success: {"status": "success", "raw_html": "...", "extracted_text": "..."}
        On failure: {"status": "error", "message": "Error description"}
    """
    logger.info(f"Executing fetch_and_extract_text for URL: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # Lança uma exceção para status de erro HTTP (4xx ou 5xx)

        html_content = response.text
        
        # Usa trafilatura para uma extração de texto limpa e robusta
        extracted_text = trafilatura.extract(html_content, include_comments=False, include_tables=True)

        if not extracted_text:
            logger.warning(f"Trafilatura extracted no main text from {url}. Returning empty text.")
            return {
                "status": "success",
                "raw_html": html_content,
                "extracted_text": ""
            }

        logger.info(f"Successfully fetched and extracted text from {url}.")
        return {
            "status": "success",
            "raw_html": html_content,
            "extracted_text": extracted_text
        }

    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error fetching URL {url}: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    except requests.exceptions.RequestException as e:
        error_message = f"Request failed for URL {url}: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}
    except Exception as e:
        error_message = f"An unexpected error occurred while processing {url}: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}

# Envolve a função Python em um objeto FunctionTool do ADK para ser usado pelo agente.
web_fetch_tool = FunctionTool(func=fetch_and_extract_text)
PARTE 4: Implementação II: Orquestração e Extração StoryBrand via CallbacksCom a ferramenta de extração de dados pronta, o próximo passo é implementar a lógica de processamento que será acionada pelos callbacks. Estes callbacks orquestrarão a aplicação do framework StoryBrand e a atualização do estado da sessão.4.1. O Papel do LangExtractAssume-se que existe uma função auxiliar no arquivo app/tools/langextract_sb7.py. Esta função encapsula a lógica de interação com a biblioteca LangExtract, recebendo o texto extraído e o esquema StoryBrand, e retornando um dicionário JSON com a análise.Python# app/tools/langextract_sb7.py (Exemplo de estrutura)

# Supondo que LangExtract é uma biblioteca ou módulo disponível
# import langextract 

STORYBRAND_SCHEMA = {
    "type": "object",
    "properties": {
        "character": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Who is the hero of the story?"},
                "wants": {"type": "string", "description": "What does the character want?"},
                "evidence": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["description", "wants"]
        },
        "problem": {
            "type": "object",
            "properties": {
                "external": {"type": "string", "description": "The external problem the character faces."},
                "internal": {"type": "string", "description": "The internal feeling the external problem causes."},
                "philosophical": {"type": "string", "description": "Why this problem is just plain wrong."},
                "evidence": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["external", "internal"]
        },
        #... resto do schema SB7
    }
}

def apply_storybrand_framework(text: str, schema: dict) -> dict:
    """
    Aplica o framework StoryBrand ao texto fornecido usando LangExtract.
    """
    # Esta é uma implementação hipotética. Substitua pela chamada real ao LangExtract.
    # storybrand_json = langextract.extract(text=text, schema=schema)
    # return storybrand_json
    
    # Exemplo de retorno para fins de demonstração:
    return {
        "character": {"description": "Um homem buscando melhorar sua saúde.", "wants": "Perder peso e ganhar massa muscular.", "evidence": ["...evidência do texto..."]},
        "problem": {"external": "Dificuldade em seguir dietas e rotinas de treino.", "internal": "Frustração e baixa autoestima.", "evidence": ["...evidência do texto..."]}
    }

4.2. Código: Funções de Callback em agent.pyAs funções de callback a seguir devem ser adicionadas ao arquivo principal agent.py. Elas servem como os "ganchos" que executam a lógica de processamento nos momentos certos do ciclo de vida do agente.Python# Adicionar ao agent.py

from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import ToolRequest
import logging

# Supondo que a função e o schema estão no módulo vizinho
from.tools.langextract_sb7 import apply_storybrand_framework, STORYBRAND_SCHEMA

logger = logging.getLogger(__name__)

def prepare_fetch_analysis(
    callback_context: CallbackContext, tool_request: ToolRequest
) -> Optional[dict]:
    """
    Callback executado ANTES da chamada da ferramenta.
    Ideal para logging, normalização de argumentos ou implementação de cache.
    """
    if tool_request.name == "fetch_and_extract_text":
        url = tool_request.args.get("url")
        logger.info(f"[Callback: before_tool] Preparing to fetch URL: {url} for agent '{callback_context.agent_name}'.")
        
        # Ponto de extensão futuro: Lógica de cache
        # cache_key = f"cache:html:{url}"
        # cached_result = callback_context.state.get(cache_key)
        # if cached_result:
        #     logger.info(f"Cache hit for {url}. Skipping tool execution.")
        #     return cached_result  # Retorna o resultado do cache, pulando a ferramenta

    return None  # Retornar None permite que a execução da ferramenta prossiga normalmente

def process_and_extract_sb7(
    callback_context: CallbackContext, tool_result: dict
) -> Optional[dict]:
    """
    Callback executado DEPOIS que a ferramenta retorna um resultado.
    Este é o ponto central para processar os dados brutos, aplicar o LangExtract
    e salvar a análise estruturada no estado da sessão.
    """
    # O ADK não fornece o nome da ferramenta que rodou neste contexto,
    # então verificamos a estrutura do resultado para inferir.
    if "status" in tool_result and "extracted_text" in tool_result:
        logger.info(f"[Callback: after_tool] Processing result for agent '{callback_context.agent_name}'.")

        if tool_result["status"] == "success":
            extracted_text = tool_result.get("extracted_text")
            if extracted_text:
                try:
                    # Aplica o framework StoryBrand usando a função auxiliar
                    storybrand_analysis = apply_storybrand_framework(
                        text=extracted_text, schema=STORYBRAND_SCHEMA
                    )
                    
                    # AÇÃO CRÍTICA: Salva a análise estruturada no estado da sessão.
                    # Isso torna os dados acessíveis para agentes subsequentes.
                    callback_context.state["storybrand_analysis"] = storybrand_analysis
                    logger.info("StoryBrand analysis completed and saved to session state.")

                    # Opcional: Adiciona um resumo ao resultado da ferramenta para o LLM
                    tool_result["analysis_summary"] = "StoryBrand analysis was successfully performed and stored in the session state."

                except Exception as e:
                    logger.error(f"Error during StoryBrand analysis: {e}")
                    tool_result["analysis_summary"] = f"StoryBrand analysis failed with error: {e}"
            else:
                logger.warning("No text was extracted, skipping StoryBrand analysis.")
                callback_context.state["storybrand_analysis"] = {"error": "No text content found on page."}
        else:
            # Se a ferramenta falhou, propaga o erro para o estado
            callback_context.state["storybrand_analysis"] = {"error": tool_result.get("message")}
            logger.error(f"Tool execution failed: {tool_result.get('message')}")

    return None # Retornar None permite que o fluxo padrão continue (enviar resultado ao LLM)
PARTE 5: Integração e Modificação do agent.py PrincipalCom a ferramenta e os callbacks implementados, o passo final é integrá-los ao LlmAgent existente, o landing_page_analyzer, e garantir que o estado seja gerenciado corretamente para comunicação com os outros agentes no pipeline.5.1. Gerenciamento de Estado: A Fonte Única da VerdadeO objeto state é o mecanismo central do ADK para manter o contexto e passar dados entre os componentes de um pipeline durante uma única conversa (sessão).18 É fundamental utilizá-lo corretamente.Padrões de Acesso:Em Callbacks: O acesso é feito através de callback_context.state["minha_chave"]. Este é o método correto e seguro para ler e escrever no estado durante a execução dos callbacks.13Em Ferramentas: O acesso é feito através de tool_context.state["minha_chave"]. As ferramentas recebem seu próprio objeto de contexto com acesso ao mesmo estado da sessão.4Em Instruções de Agente: O valor de uma chave no estado pode ser injetado diretamente no prompt de um agente usando a sintaxe de chaves: "{minha_chave}". É assim que o resultado da análise será consumido pelo próximo agente no SequentialAgent.20callback_context.state vs. session.state: É importante notar que callback_context.state é um proxy gerenciado pelo runtime do ADK para o session.state subjacente. Usar o objeto de contexto (callback_context ou tool_context) é a maneira canônica de interagir com o estado, pois garante que as alterações sejam rastreadas e persistidas corretamente pelo framework.145.2. Agente landing_page_analyzer: Antes e DepoisA seguir, uma comparação direta das modificações necessárias no arquivo agent.py para a definição do landing_page_analyzer.ANTES:Python# Definição original no agent.py (linha 294-338)
landing_page_analyzer = LlmAgent(
    name="landing_page_analyzer",
    tools=[google_search],
    instruction="Analise o conteúdo de {landing_page_url} usando o Google Search para entender a proposta de valor, público-alvo e chamada para ação. Resuma suas descobertas."
    #... outros parâmetros
)
DEPOIS:Python# No topo do agent.py, adicione os imports
from.tools.web_fetch_tool import web_fetch_tool
# As definições das funções de callback (prepare_fetch_analysis, process_and_extract_sb7)
# devem estar neste arquivo, antes da definição do agente.

#... (definições de outros agentes)...

# Modificação do landing_page_analyzer
landing_page_analyzer = LlmAgent(
    name="landing_page_analyzer",
    model="gemini-1.5-flash", # ou o modelo de sua escolha
    tools=[web_fetch_tool],  # Substitui google_search pela nossa nova ferramenta
    instruction=(
        "Você é um analista de conteúdo de websites. Seu objetivo é extrair a mensagem central de uma landing page. "
        "Dada uma URL do usuário, você DEVE OBRIGATORIAMENTE usar a ferramenta `fetch_and_extract_text` para obter o conteúdo da página. "
        "Após a execução da ferramenta, uma análise detalhada do StoryBrand estará disponível internamente. "
        "Sua tarefa final é fornecer um resumo conciso, em um único parágrafo, da análise realizada, destacando o personagem, o problema e a solução propostos na página."
    ),
    before_tool_callback=prepare_fetch_analysis,
    after_tool_callback=process_and_extract_sb7,
    output_key="landing_page_analysis_summary" # Armazena o resumo final para o próximo agente
)

#... (resto do pipeline SequentialAgent)...
Justificativa das Mudanças:tools=[web_fetch_tool]: A ferramenta google_search foi substituída pela nossa ferramenta customizada, que realiza a extração direta do conteúdo.instruction: A instrução foi reescrita para ser muito mais específica, guiando o LLM a usar a ferramenta correta (fetch_and_extract_text) e definindo sua tarefa final (sumarizar a análise que será feita pelos callbacks).before_tool_callback e after_tool_callback: Os callbacks que implementamos foram registrados no agente, garantindo que a lógica de processamento seja executada nos momentos corretos.output_key="landing_page_analysis_summary": Este parâmetro instrui o ADK a pegar a resposta final deste agente (o resumo em texto) e armazená-la no estado da sessão com a chave landing_page_analysis_summary. Isso permite que o próximo agente no SequentialAgent (por exemplo, o execution_agent) acesse facilmente este resumo em sua própria instrução usando {landing_page_analysis_summary}.23PARTE 6: Conceitos Avançados: Dominando Loops e Lógica CondicionalEsta seção aborda as questões específicas sobre LoopAgent e como implementar validação e condições de parada, que são cruciais para fluxos de trabalho iterativos e de refinamento.6.1. Terminação Condicional de Loop: O Mecanismo escalateO LoopAgent do ADK é projetado para repetição, mas a lógica de quando parar o loop não é declarativa.O Padrão Padrão: Não existe um parâmetro como stop_condition no LoopAgent. A maneira idiomática e oficial de sair de um loop com base em uma condição é ter um sub-agente (ou uma ferramenta chamada por um sub-agente) que, ao avaliar que a condição de parada foi atingida, sinaliza uma "escalada".15Implementação da Condição: Para implementar a condição "pare quando storybrand.problema.interno!=", o fluxo seria:Dentro do LoopAgent, inclua um agente validator_agent.A instrução do validator_agent deve acessar a análise do estado: "Analise a estrutura JSON em {storybrand_analysis}. Se o campo 'problem.internal' não estiver vazio e contiver uma descrição válida, você DEVE OBRIGATORIAMENTE chamar a ferramenta exit_loop. Caso contrário, forneça feedback para uma nova iteração."Crie uma ferramenta simples exit_loop_tool cuja única função é acionar o sinal de escalada.Código de Exemplo para a Ferramenta exit_loop:Python# Pode ser adicionado a um novo arquivo em app/tools/ ou diretamente em agent.py

from google.adk.tools import ToolContext, FunctionTool

def exit_loop(tool_context: ToolContext) -> dict:
    """
    Signals that the iterative process is complete and the loop should terminate immediately.
    Call this tool when a validation condition has been met.
    """
    # A linha a seguir é o mecanismo oficial do ADK para parar um LoopAgent.
    tool_context.actions.escalate = True
    return {"status": "Loop termination signaled successfully."}

# Instancia a ferramenta para ser usada pelo validator_agent
exit_loop_tool = FunctionTool(func=exit_loop)
6.2. O EscalationChecker: Um Equívoco ComumO termo EscalationChecker não corresponde a um componente padrão do framework ADK. É provável que seja uma referência a um nome de agente customizado visto em algum exemplo específico. A lógica de verificação (analisar o review_key ou, neste caso, o storybrand_analysis do estado) deve ser implementada dentro de um LlmAgent padrão (o validator_agent descrito acima), que então toma a decisão de chamar ou não a ferramenta exit_loop_tool.PARTE 7: Estrutura do Projeto e Estratégia de TestesA organização do projeto e uma estratégia de testes robusta são essenciais para garantir a qualidade e a manutenibilidade da nova funcionalidade.7.1. Confirmação Final da Estrutura do ProjetoA estrutura com o diretório app/tools/ é confirmada como a melhor prática para projetos ADK que crescem em complexidade. Ela separa as ferramentas, que são componentes reutilizáveis, da lógica de orquestração dos agentes, que reside em agent.py.177.2. Uma Estratégia de Testes PragmáticaUma abordagem de testes em duas camadas é recomendada para validar a nova implementação de forma eficaz.Testes de Unidade (Isolamento):Ferramenta: Crie um script de teste com pytest para web_fetch_tool.py. Chame a função fetch_and_extract_text diretamente com uma URL de teste conhecida e verifique se a estrutura e o conteúdo do dicionário de retorno estão corretos. Use mocks (ex: unittest.mock.patch) para simular a resposta de requests.get, permitindo testar cenários de sucesso e de erro (ex: status 404, timeout) sem fazer chamadas de rede reais.Callbacks: Escreva testes para as funções prepare_fetch_analysis e process_and_extract_sb7. Crie objetos MagicMock para simular o CallbackContext e o tool_result. Chame os callbacks com esses mocks e verifique se o estado (callback_context.state) é modificado como esperado.Testes de Integração (Pipeline):Agente Isolado: Utilize a interface de desenvolvimento adk web. Inicie o serviço e interaja diretamente com o agente landing_page_analyzer. Forneça a URL de teste (https://nutrologodivinopolis.com.br/masculino/) e, após a execução, inspecione o painel "Session State" na UI. Confirme que a chave storybrand_analysis foi criada e contém o JSON estruturado esperado.26Pipeline Completo: Execute o pipeline SequentialAgent completo a partir da UI. Envie uma requisição que acione todo o fluxo. Verifique se o agente que sucede o landing_page_analyzer (por exemplo, planning_agent ou execution_agent) recebe corretamente o resumo através da chave landing_page_analysis_summary e se comporta como esperado com base nessa nova entrada.Conclusão: De Análise Superficial para Insight AcionávelA arquitetura implementada transforma o agente landing_page_analyzer de um componente superficial para um motor de análise de conteúdo robusto e de alta fidelidade. A solução, baseada na sinergia entre uma ferramenta customizada para extração de dados e callbacks para processamento determinístico, representa um padrão de design idiomático e eficiente dentro do ecossistema ADK.Os benefícios desta nova abordagem são significativos:Robustez: A extração direta de HTML com trafilatura é muito mais confiável e completa do que inferir conteúdo a partir de resultados de busca.Eficiência: A aplicação do LangExtract em um callback, em vez de um segundo LLM, reduz custos, diminui a latência e aumenta a previsibilidade do resultado.Qualidade dos Dados: O pipeline agora opera com dados estruturados (o JSON do StoryBrand), o que melhora drasticamente a qualidade e a consistência das entradas para os agentes subsequentes, resultando em uma geração de anúncios mais precisa e eficaz.A separação de responsabilidades — I/O em Ferramentas, lógica determinística em Callbacks e raciocínio em Agentes — é um princípio fundamental que, quando aplicado corretamente, permite a construção de sistemas de agentes complexos, escaláveis e de fácil manutenção com o Google ADK.