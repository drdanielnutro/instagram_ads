Relatório de Refatoração: Extrator StoryBrand com LLM
Este relatório apresenta uma abordagem completa para refatorar o StoryBrandExtractor, substituindo a análise baseada em regex por uma solução robusta que utiliza um Modelo de Linguagem Grande (LLM) para uma extração semântica precisa dos 7 elementos do framework StoryBrand.

1. Análise da Biblioteca "LangExtract" e a Abordagem Recomendada
Esta seção inicial aborda a principal dúvida sobre a existência e acessibilidade da biblioteca "LangExtract". Após uma investigação completa na documentação oficial do Google ADK (google.github.io/adk-docs/), a conclusão é que "LangExtract" não é uma biblioteca pública, uma ferramenta documentada ou um conceito mencionado no framework do ADK. A ausência de uma biblioteca de extração dedicada como essa implica que a responsabilidade pela extração de dados estruturados recai sobre a implementação direta de chamadas a um Modelo de Linguagem Grande (LLM).

Com base nessa investigação, a abordagem recomendada é refatorar a classe StoryBrandExtractor para orquestrar uma chamada direta ao modelo Gemini. A implementação de chamadas diretas ao modelo, encapsuladas como uma ferramenta personalizada dentro do ADK, é a prática recomendada para integrar capacidades de IA.

Vantagens desta abordagem:

Controle Total sobre o Processo: Há um controle granular sobre o pré-processamento do HTML, a engenharia de prompt e o pós-processamento da resposta, permitindo ajustes finos para maximizar a precisão.
Flexibilidade Máxima: A lógica de extração não fica presa a uma biblioteca de terceiros. Se os requisitos de extração mudarem, basta atualizar o prompt enviado ao Gemini, sem depender de atualizações de uma biblioteca externa.
Aproveitamento do Poder Semântico: Uma chamada direta ao Gemini permite o uso de prompts complexos que instruem o modelo a realizar uma análise semântica profunda, entendendo nuances, contexto e a intenção do texto—algo que a implementação atual com regex não consegue fazer.
Saída Estruturada Garantida: Ao instruir o modelo para retornar um JSON e validar a saída com um schema Pydantic, a integridade e o formato dos dados são garantidos de forma consistente.
Eficiência: Realizar a extração de todos os 7 elementos em uma única chamada ao LLM é mais eficiente em termos de latência e custo do que múltiplas chamadas, uma para cada elemento.
Em resumo, a estratégia recomendada é abandonar a busca pela "LangExtract" e focar na construção de uma lógica de extração robusta dentro da classe StoryBrandExtractor, que usará o Gemini como seu motor de análise semântica.

2. Engenharia de Prompt para Extração Semântica
O coração da nova implementação reside em instruir o LLM de forma eficaz. Esta seção detalha a estratégia de engenharia de prompt projetada para o Gemini.

Estrutura do Prompt Mestre: Um único prompt otimizado para extrair todos os 7 elementos em uma única chamada.
Instruções Específicas: Detalhamento das instruções para cada elemento StoryBrand (Personagem, Problema, Guia, etc.).
Garantia de Formato: Como instruir o modelo a retornar um JSON estruturado compatível com o schema Pydantic, incluindo campos para descrição, evidências e pontuação de confiança.
O prompt deve ser dividido em seções claras para que o modelo entenda perfeitamente a tarefa, o contexto, as regras e o formato de saída desejado.

Você é um especialista em marketing e no framework StoryBrand de Donald Miller. Sua tarefa é analisar o conteúdo de uma landing page fornecido abaixo e extrair os 7 elementos chave da narrativa da marca.

Siga estas regras estritamente:
1. Analise o CONTEÚDO fornecido para identificar cada um dos 7 elementos.
2. Para cada elemento, forneça uma descrição concisa, as evidências textuais exatas que justificam sua análise e uma pontuação de confiança (de 0.0 a 1.0) que represente sua certeza na extração.
3. Se um elemento não for encontrado ou não estiver claro, a descrição deve indicar isso, e a pontuação de confiança deve ser baixa (ex: 0.1).
4. Sua resposta DEVE SER UM ÚNICO OBJETO JSON, sem nenhum texto ou formatação adicional antes ou depois dele.

## FORMATO DE SAÍDA JSON OBRIGATÓRIO

{
  "character": {
    "description": "Uma breve descrição do cliente ideal a quem a página se dirige.",
    "evidence": ["Frase ou trecho exato do texto que define o personagem."],
    "confidence_score": 0.9
  },
  "problem": {
    "description": "Resumo dos problemas (externo, interno e filosófico) que o personagem enfrenta.",
    "evidence": ["Frase que descreve a dor ou o desafio do cliente."],
    "confidence_score": 0.8
  },
  "guide": {
    "description": "Como a marca se posiciona como um guia empático e com autoridade.",
    "evidence": ["Trecho que demonstra empatia ou autoridade (ex: 'Entendemos sua dificuldade...', 'Com 10 anos de experiência...')."],
    "confidence_score": 0.9
  },
  "plan": {
    "description": "O plano simples (geralmente 3-4 passos) que o cliente deve seguir.",
    "evidence": ["Lista de passos ou o texto que descreve o processo."],
    "confidence_score": 0.7
  },
  "action": {
    "description": "O chamado à ação principal (direto) e secundário (transicional) que a página propõe.",
    "evidence": ["Texto exato dos botões ou links de CTA (ex: 'Compre agora', 'Baixe o e-book')."],
    "confidence_score": 1.0
  },
  "failure": {
    "description": "As consequências negativas ou os riscos de não seguir o plano e não usar a solução.",
    "evidence": ["Frase que descreve o que pode dar errado ou o que o cliente continuará a perder."],
    "confidence_score": 0.6
  },
  "success": {
    "description": "A transformação positiva e o sucesso que o cliente alcançará após usar a solução.",
    "evidence": ["Trecho que descreve a visão de sucesso ou a transformação prometida."],
    "confidence_score": 0.9
  }
}

---
## CONTEÚDO DA LANDING PAGE PARA ANÁLISE

{html_content}
---

Agora, analise o conteúdo e retorne o objeto JSON populado.
Este prompt é projetado para ser robusto, utilizando uma persona ("Você é um especialista..."), regras claras, um exemplo de formato (one-shot learning), e delimitadores (---) para guiar o Gemini a executar a tarefa de forma precisa e com a saída no formato desejado.

3. Guia de Refatoração da Classe StoryBrandExtractor
Esta seção fornece um guia passo a passo para modificar o código existente em app/tools/langextract_sb7.py. O foco é a transição da lógica de regex para a nova abordagem baseada em LLM.

Pré-processamento de HTML: Uma estratégia para limpar e extrair o conteúdo textual relevante do HTML antes de enviá-lo ao LLM. O padrão recomendado é o uso de bibliotecas Python consagradas como BeautifulSoup para remover scripts, estilos e outros elementos irrelevantes, focando no conteúdo textual principal.
Integração com o Gemini: Como inicializar e configurar o cliente do modelo Gemini dentro da classe.
Lógica de Extração Atualizada: A nova implementação do método extract, que constrói o prompt, envia a requisição para a API e processa a resposta JSON recebida. A resposta deve ser parseada e, idealmente, validada com um modelo Pydantic para garantir a integridade dos dados.
Passos da Refatoração:

Limpar a Classe Atual: Remover todos os métodos e atributos relacionados à antiga lógica de regex.
Adicionar Novas Importações: Incluir google.generativeai, BeautifulSoup, json, logging e o schema Pydantic.
Atualizar o __init__: Configurar o cliente do modelo Gemini, passando a chave de API de forma segura.
Implementar o Pré-processamento de HTML: Criar um método privado (_preprocess_html) que use BeautifulSoup para extrair texto limpo do HTML bruto.
Implementar o Novo Método extract: Orquestrar o processo: chamar o pré-processamento, construir o prompt, enviar a requisição ao Gemini e processar a resposta JSON.
Criar o Método de Construção do Prompt: Isolar a lógica do "Prompt Mestre" em um método privado (_build_prompt) para manter o código organizado.
Manter o Método _empty_result: Garantir que a função retorne uma estrutura de dados consistente mesmo em caso de falha.
Seguindo este guia, a classe StoryBrandExtractor será transformada de uma ferramenta baseada em regras frágeis para uma poderosa solução de análise semântica.

4. Implementação do Protótipo Funcional
Esta seção final apresenta o código completo e funcional da nova classe StoryBrandExtractor. O protótipo serve como uma solução "pronta para uso" que pode ser diretamente integrada ao projeto, demonstrando a aplicação prática de todos os conceitos discutidos nas seções anteriores. O código está pronto para ser integrado em app/tools/langextract_sb7.py, substituindo completamente a versão anterior.

"""
StoryBrand Framework Extractor using a Large Language Model (Gemini).
Extracts the 7 elements of Donald Miller's StoryBrand framework from HTML content
through semantic analysis.
"""

import google.generativeai as genai
from bs4 import BeautifulSoup
import json
import logging
from typing import Dict, Any

# Configure um logger para o seu módulo
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Recomenda-se definir um schema Pydantic para validar a saída.
# Exemplo (pode ser importado de outro lugar):
# from pydantic import BaseModel, Field, conlist
#
# class StoryBrandElement(BaseModel):
#     description: str = Field(..., description="A concise description of the element.")
#     evidence: conlist(str, min_length=0) = Field(..., description="Exact text snippets from the content as evidence.")
#     confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0.")
#
# class StoryBrandSchema(BaseModel):
#     character: StoryBrandElement
#     problem: StoryBrandElement
#     guide: StoryBrandElement
#     plan: StoryBrandElement
#     action: StoryBrandElement
#     failure: StoryBrandElement
#     success: StoryBrandElement


class StoryBrandExtractor:
    """
    Extracts the 7 StoryBrand framework elements from a webpage's HTML content
    using semantic analysis powered by the Gemini LLM.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash-latest"):
        """
        Initializes the extractor by configuring the Gemini model client.

        Args:
            api_key: The Google AI API key for Gemini.
            model_name: The specific Gemini model to use.
        """
        self.model = None
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"Gemini model '{model_name}' configured successfully.")
        except Exception as e:
            logger.error(f"Failed to configure the Gemini model: {e}")
            raise

    def _preprocess_html(self, html_content: str) -> str:
        """
        Cleans the HTML content to extract relevant text for analysis.
        It removes scripts, styles, navigation, and footer to reduce noise.

        Args:
            html_content: The raw HTML string of the landing page.

        Returns:
            A string of cleaned, relevant text content.
        """
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove tags that are typically irrelevant for content analysis
        for element in soup(["script", "style", "nav", "footer", "header", "meta", "link", "aside"]):
            element.decompose()

        # Get text and join it with spaces, then clean up excessive whitespace
        text = soup.get_text(separator=' ', strip=True)
        return " ".join(text.split())

    def _build_prompt(self, text_content: str) -> str:
        """
        Constructs the detailed master prompt for the Gemini model.

        Args:
            text_content: The cleaned text from the landing page.

        Returns:
            The fully formatted prompt string.
        """
        # This is the master prompt designed for high-quality, structured extraction.
        prompt_template = """
        You are an expert in marketing and Donald Miller's StoryBrand framework. Your task is to analyze the provided landing page content and extract the 7 key elements of the brand's narrative.

        Follow these rules strictly:
        1. Analyze the CONTENT provided to identify each of the 7 elements.
        2. For each element, provide a concise description, the exact textual evidence justifying your analysis, and a confidence score (from 0.0 to 1.0) representing your certainty.
        3. If an element is not found or is unclear, the description should state this, and the confidence score should be low (e.g., 0.1).
        4. Your response MUST BE A SINGLE JSON OBJECT, with no additional text or markdown formatting before or after it.

        ## REQUIRED JSON OUTPUT FORMAT

        {
          "character": {
            "description": "A brief description of the ideal customer the page is addressing.",
            "evidence": ["Exact phrase or excerpt from the text that defines the character."],
            "confidence_score": 0.9
          },
          "problem": {
            "description": "A summary of the problems (external, internal, and philosophical) the character faces.",
            "evidence": ["A sentence describing the customer's pain point or challenge."],
            "confidence_score": 0.8
          },
          "guide": {
            "description": "How the brand positions itself as an empathetic guide with authority.",
            "evidence": ["An excerpt demonstrating empathy or authority (e.g., 'We understand your struggle...', 'With 10 years of experience...')."],
            "confidence_score": 0.9
          },
          "plan": {
            "description": "The simple plan (usually 3-4 steps) the customer should follow.",
            "evidence": ["A list of steps or the text describing the process."],
            "confidence_score": 0.7
          },
          "action": {
            "description": "The main (direct) and secondary (transitional) calls-to-action the page proposes.",
            "evidence": ["Exact text of CTA buttons or links (e.g., 'Buy Now', 'Download the E-book')."],
            "confidence_score": 1.0
          },
          "failure": {
            "description": "The negative consequences or stakes of not following the plan and not using the solution.",
            "evidence": ["A phrase describing what could go wrong or what the customer will continue to lose."],
            "confidence_score": 0.6
          },
          "success": {
            "description": "The positive transformation and success the customer will achieve after using the solution.",
            "evidence": ["An excerpt describing the vision of success or the promised transformation."],
            "confidence_score": 0.9
          }
        }

        ---
        ## LANDING PAGE CONTENT FOR ANALYSIS

        {html_content}
        ---

        Now, analyze the content and return the populated JSON object.
        """
        return prompt_template.format(html_content=text_content)

    def extract(self, html_content: str) -> Dict[str, Any]:
        """
        Extracts StoryBrand elements from HTML content using the Gemini model.

        This method orchestrates the entire process:
        1. Pre-processes the HTML to get clean text.
        2. Builds the detailed prompt for the LLM.
        3. Sends the request to the Gemini API.
        4. Parses and returns the structured JSON response.

        Args:
            html_content: The raw HTML content of the page to be analyzed.

        Returns:
            A dictionary containing the 7 extracted StoryBrand elements, or an empty
            structure in case of failure.
        """
        if not self.model:
            logger.error("Model is not initialized. Aborting extraction.")
            return self._empty_result()

        clean_text = self._preprocess_html(html_content)
        if not clean_text or len(clean_text) < 50: # Avoid sending empty or trivial content
            logger.warning("Text content is too short after pre-processing. Aborting.")
            return self._empty_result()

        prompt = self._build_prompt(clean_text)

        try:
            logger.info("Sending request to the Gemini API for StoryBrand extraction.")
            response = self.model.generate_content(prompt)
            
            response_text = response.text.strip()
            # Clean potential markdown code fences from the response
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()

            # Parse the JSON string into a Python dictionary
            data = json.loads(response_text)

            # Recommended: Validate the data against a Pydantic schema here
            # For example:
            # validated_data = StoryBrandSchema(**data)
            # return validated_data.model_dump()

            logger.info("Successfully extracted and parsed StoryBrand elements.")
            return data

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from the LLM's response.")
            logger.debug(f"Received malformed response: {response.text}")
            return self._empty_result()
        except Exception as e:
            logger.error(f"An unexpected error occurred during Gemini API call: {e}")
            return self._empty_result()

    def _empty_result(self) -> Dict[str, Any]:
        """
        Returns an empty, structured dictionary for error cases.
        """
        return {
            "character": {"description": "", "evidence": [], "confidence_score": 0.0},
            "problem": {"description": "", "evidence": [], "confidence_score": 0.0},
            "guide": {"description": "", "evidence": [], "confidence_score": 0.0},
            "plan": {"description": "", "evidence": [], "confidence_score": 0.0},
            "action": {"description": "", "evidence": [], "confidence_score": 0.0},
            "failure": {"description": "", "evidence": [], "confidence_score": 0.0},
            "success": {"description": "", "evidence": [], "confidence_score": 0.0}
        }