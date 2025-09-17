1. Arquitetura e Estrutura Fundamental do Agente ADK
Esta seção aborda os componentes centrais que definem a estrutura e o comportamento de um agente no Google ADK. Serão analisados os tipos de agentes disponíveis, como o estado é gerenciado e os mecanismos de controle de fluxo.

Tipos de Agentes Nativos: Análise dos construtores de agentes fornecidos pelo ADK, investigando a existência do LoopAgent e a metodologia para conectar múltiplos agentes.
O Google ADK fornece tipos de agentes nativos para orquestrar fluxos de trabalho complexos. Estes se dividem em três categorias principais: LlmAgent (agentes baseados em LLM para raciocínio), Workflow Agents (agentes determinísticos para controle de fluxo) e Custom Agents (agentes com lógica personalizada).

Dentro dos agentes de fluxo de trabalho, o ADK oferece nativamente o LoopAgent, projetado para tarefas que requerem repetição ou refinamento iterativo. Ele executa sub-agentes sequencialmente em um loop por um número definido de iterações ou até que uma condição de término seja atendida. A conexão de múltiplos agentes é realizada através da composição, onde um agente de fluxo de trabalho gerencia uma lista de sub-agentes, como demonstrado na sintaxe abaixo:

from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.adk.tools import FunctionTool

# Ferramenta para sair do loop
def exit_loop_if_done(tool_context: ToolContext, critique: str):
    """Chame esta função para sair do loop se a crítica for satisfatória."""
    if "no further changes are needed" in critique.lower():
        tool_context.actions.escalate = True
        return {"status": "Loop terminado"}
    return {"status": "Continuando loop"}

exit_tool = FunctionTool(func=exit_loop_if_done)

# Agentes especializados
proposer_agent = LlmAgent(
    name="ProposerAgent",
    instruction="Proponha uma solução inicial.",
    output_key="current_solution"
)
critic_agent = LlmAgent(
    name="CriticAgent",
    instruction="Critique a solução fornecida em {{current_solution}} e sugira melhorias. Se estiver bom, diga 'no further changes are needed'.",
    tools=[exit_tool],
    output_key="critique"
)
refiner_agent = LlmAgent(
    name="RefinerAgent",
    instruction="Refine a {{current_solution}} com base na seguinte crítica: {{critique}}.",
    output_key="current_solution"
)

# Agente de Loop para o ciclo de refinamento
refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[critic_agent, refiner_agent],
    max_iterations=5
)

# Agente Sequencial principal para orquestrar o fluxo completo
main_workflow_agent = SequentialAgent(
    name="MainWorkflow",
    sub_agents=[proposer_agent, refinement_loop]
)
Gerenciamento de Estado: Exploração do sistema de estado do ADK, comparando o uso do output_key com a manipulação direta do objeto de state para persistência e compartilhamento de dados.
O ADK possui um sistema de estado nativo robusto, centrado no objeto session.state, que funciona como um dicionário para persistir e compartilhar dados entre agentes e turnos de conversação.

O parâmetro output_key é uma funcionalidade de conveniência do LlmAgent que automatiza o processo de salvar a resposta final de texto de um agente no estado. Por exemplo, output_key="cidade_capital" irá salvar a saída do agente em session.state['cidade_capital'].

Enquanto output_key é ideal para fluxos de trabalho lineares simples, a manipulação direta do objeto de estado (ex: context.state['minha_chave'] = 'valor') oferece controle granular, permitindo que ferramentas, callbacks ou agentes customizados leiam e escrevam múltiplos valores intermediários, sendo essencial para cenários mais complexos. A sintaxe a seguir demonstra o compartilhamento de dados usando output_key e a leitura implícita do estado na instrução de um agente subsequente.

from google.adk.agents import LlmAgent, SequentialAgent

# Agente A salva sua saída na chave 'cidade_capital'
agente_A = LlmAgent(
    name="AgenteA",
    instruction="Qual é a capital da França?",
    output_key="cidade_capital"
)

# Agente B usa a informação salva pelo Agente A em sua instrução
# O ADK substitui automaticamente {cidade_capital} pelo valor em state['cidade_capital']
agente_B = LlmAgent(
    name="AgenteB",
    instruction="Fale-me sobre a cidade de {cidade_capital}."
)

# O SequentialAgent garante que o Agente A rode antes do Agente B
pipeline = SequentialAgent(
    name="PipelineDeInformacao",
    sub_agents=[agente_A, agente_B]
)
Controle de Fluxo e Contexto: Verificação da existência e funcionalidade do objeto tool_context.actions e do atributo escalate como mecanismo nativo para direcionar o fluxo de execução do agente.
O ADK fornece o objeto tool_context.actions como um mecanismo nativo para controlar o fluxo de execução a partir de uma ferramenta. Quando uma função de ferramenta inclui tool_context: ToolContext em sua assinatura, o ADK injeta automaticamente este objeto, que dá acesso a ações de controle.

O atributo booleano escalate é um desses controles. Quando uma ferramenta define tool_context.actions.escalate = True, ela envia um sinal de interrupção para cima na hierarquia de agentes. Em um LoopAgent, isso causa o término imediato do loop. Se esse LoopAgent estiver dentro de um SequentialAgent, o sinal se propaga, interrompendo também a execução do agente sequencial pai. Este é o mecanismo correto e nativo para que uma ferramenta sinalize a interrupção de um processo iterativo.

2. Ecossistema de Ferramentas (Tools) Nativas e Customizadas
Esta seção foca nas ferramentas que um agente pode utilizar para interagir com dados e serviços externos. Abrange tanto as ferramentas pré-construídas oferecidas pelo framework quanto o processo para desenvolver ferramentas personalizadas.

Ferramentas de Busca e Acesso à Web: Investigação sobre a existência de ferramentas nativas como google_search e uma função de fetch para download de conteúdo web (ex: load_web_page).
A pesquisa na documentação do ADK não encontrou nenhuma ferramenta nativa integrada para download de conteúdo web, como web_fetch ou http_fetch. As referências a APIs de "fetch" encontradas se aplicam a outros contextos de desenvolvimento, como Node. npmjs.com logrocket.comjs, React Native reactnative.dev reddit.com, e a API Fetch padrão da web mozilla.org mozilla.org, mas não ao ADK. Uma referência a load_web_page aparece no contexto de expor ferramentas do ADK através de um servidor MCP (Model Context Protocol), indicando que pode ser uma ferramenta customizada ou de exemplo usada para demonstrar a integração, e não uma ferramenta nativa diretamente importável no ADK. youtube.com

Em contraste, a ferramenta google_search é uma ferramenta nativa do Google ADK. github.io Ela é importada de google.adk.tools e adicionada à lista de ferramentas de um agente. github.io A documentação confirma que as ferramentas nativas, como google_search, podem ser usadas em conjunto com outras ferramentas. github.io É importante notar que a documentação especifica que a ferramenta google_search é compatível apenas com modelos Gemini 2. github.io reddit.com Para modelos Gemini 1.5, uma ferramenta legada chamada google_search_retrieval era utilizada. google.dev O uso da ferramenta é faturado por solicitação de API que a inclui. Mesmo que o modelo decida executar múltiplas consultas de busca para responder a um único prompt, isso conta como um único uso faturável da ferramenta para aquela solicitação. google.dev

from google.adk.agents import Agent
from google.adk.tools import google_search

# Criar um agente que utiliza a ferramenta google_search
search_agent = Agent(
    model="gemini-2.0-flash",
    tools=[google_search]
)
Criação de Function Tools Customizadas: Detalhamento do processo oficial para definir, registrar e implementar ferramentas customizadas dentro de um agente ADK, incluindo a sintaxe e a estrutura necessárias.
A criação de ferramentas customizadas (Function Tools) é uma capacidade central e nativa do ADK. O processo envolve escrever uma função Python padrão com anotações de tipo (type hints) e uma docstring descritiva, que o LLM utiliza para entender a funcionalidade e os parâmetros da ferramenta. A função é então transformada em um objeto de ferramenta, seja pelo decorador @function_tool ou instanciando a classe FunctionTool, e registrada na lista de tools do agente.

from google.adk.agents import Agent
from google.adk.tools import function_tool, FunctionTool
import random

# Definir e decorar a função da ferramenta
@function_tool
def obter_cotacao_acao(simbolo_acao: str) -> float:
    """
    Obtém o preço atual de uma ação para um determinado símbolo.

    Args:
        simbolo_acao: O símbolo da ação no mercado de ações (ex: 'GOOGL').

    Returns:
        O preço atual da ação como um float.
    """
    # Em um cenário real, esta função chamaria uma API de mercado de ações.
    print(f"--> Chamando API para obter o preço de {simbolo_acao}...")
    preco_simulado = round(random.uniform(100, 500), 2)
    return preco_simulado

# Registrar e usar a ferramenta em um agente
agente_financeiro = Agent(
    model="gemini-1.5-flash",
    instruction="Você é um assistente financeiro. Use a ferramenta obter_cotacao_acao para responder a perguntas sobre preços de ações.",
    tools=[obter_cotacao_acao] # Passa a função decorada diretamente
)
3. Execução, Callbacks e Validação de Saída
Esta seção explora os mecanismos avançados para monitorar, intervir e validar o ciclo de vida da execução de um agente. O foco está nos "hooks" (callbacks) e na definição de esquemas de dados.

Mecanismo de Callbacks: Análise aprofundada da sintaxe e funcionalidade dos before_tool_callback e after_tool_callback, esclarecendo seu propósito e capacidade de influenciar a seleção de ferramentas.
O Google ADK possui um sistema de callbacks nativo que permite aos desenvolvedores intervir em pontos específicos do ciclo de execução do agente. Os principais callbacks relacionados a ferramentas são:

before_tool_callback: Executado antes da invocação de uma ferramenta. É ideal para validar ou modificar argumentos, aplicar políticas ou retornar resultados de um cache, evitando a execução da ferramenta.
after_tool_callback: Executado após a conclusão bem-sucedida de uma ferramenta. É útil para pós-processar, formatar ou padronizar os resultados antes de serem enviados de volta ao LLM.
Os callbacks são ganchos para intervir antes e depois da execução de uma ferramenta já selecionada pelo LLM, e não um mecanismo para substituir a lógica de seleção de ferramentas do modelo.

Sintaxe before_tool_callback:

def my_before_tool_callback(tool_context, tool, args, llm_request):
    print(f"Antes de executar a ferramenta: {tool.name}")
    # Modificar argumentos, se necessário
    if 'country' in args and args['country'] == 'USA':
        args['country'] = 'United States'
    return None # Retornar None para continuar a execução normal
Sintaxe after_tool_callback:

def my_after_tool_callback(tool_context, tool, result):
    print(f"Depois de executar a ferramenta: {tool.name}")
    # Modificar o resultado
    if isinstance(result, dict) and 'data' in result:
        result['processed'] = True
    return result # Retornar o resultado modificado ou original
Validação com Output Schema: Investigação do suporte nativo a output_schema como método para validar e estruturar os dados de saída gerados por um agente.
O ADK suporta nativamente o uso do parâmetro output_schema no LlmAgent para forçar a geração de uma resposta que seja uma string JSON em conformidade com um schema Pydantic BaseModel fornecido. Isso garante que a saída do agente seja consistente, estruturada e programaticamente utilizável por outros sistemas. O ADK valida a saída gerada pelo LLM em relação ao schema definido.

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import List

# 1. Definir o schema de saída usando Pydantic
class AnaliseDeSentimento(BaseModel):
    sentimento: str = Field(description="O sentimento geral, como 'positivo', 'negativo' ou 'neutro'.")
    palavras_chave: List[str] = Field(description="Uma lista de palavras-chave que influenciaram a análise.")
    pontuacao_confianca: float = Field(description="Um score de confiança entre 0.0 e 1.0.")

# 2. Criar o agente e passar o schema para o parâmetro output_schema
agente_analisador = LlmAgent(
    model="gemini-1.5-flash",
    instruction="Analise o texto fornecido e retorne o sentimento, palavras-chave e sua confiança.",
    output_schema=AnaliseDeSentimento
)
4. Configuração de Projeto e Modelos de LLM
Esta seção aborda os aspectos de configuração do ambiente de desenvolvimento e os recursos de modelagem de linguagem disponíveis. Serão discutidas as melhores práticas para estruturação de projetos e as opções de modelos Gemini.

Estrutura de Projeto Recomendada: Esclarecimento sobre se o ADK define uma estrutura de diretórios padrão para organizar arquivos como tools, schemas e callbacks.
A documentação oficial do ADK não impõe uma estrutura de diretórios obrigatória para projetos. A organização do código fica a critério do desenvolvedor. No entanto, as melhores práticas de engenharia de software sugerem uma estrutura modular que separa as responsabilidades. É uma prática comum e recomendada organizar o código em diretórios dedicados, como tools/ para ferramentas customizadas, callbacks/ para funções de callback, e schemas/ para definições de Pydantic, a fim de melhorar a clareza, a reutilização e a manutenção do projeto.

Modelos Gemini Disponíveis: Apresentação da lista oficial de modelos de LLM da família Gemini suportados nativamente pelo ADK, incluindo sua nomenclatura correta e capacidades.
A família de modelos Gemini disponível no ADK é extensa e inclui as versões "2.5". Os modelos são nativamente multimodais, capazes de processar texto, código, PDFs, imagens, vídeo e áudio. A nomenclatura correta para as versões estáveis geralmente não possui sufixo (ex: gemini-2.5-pro). Os modelos disponíveis incluem, mas não se limitam a:

Gemini 2.5 Pro: O modelo mais avançado para raciocínio complexo.
Gemini 2.5 Flash: Apresenta um equilíbrio entre preço e desempenho, adequado para tarefas de grande escala e casos de uso de agentes.
Gemini 2.5 Flash-Lite: A versão mais rápida e econômica, otimizada para casos de uso de baixa latência.
Gemini 2.0 Flash / Flash-Lite: Versões anteriores que também são multimodais e eficientes.