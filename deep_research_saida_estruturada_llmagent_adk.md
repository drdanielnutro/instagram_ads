# Análise Técnica e Guia de Implementação para Saída Estruturada com Gemini no Google ADK

Este documento apresenta uma investigação detalhada e um guia de implementação para a adoção da saída estruturada (controlled generation) da API Gemini no pipeline de geração de anúncios. O objetivo é resolver problemas de validação de JSON no agente `final_assembler_llm`, garantindo que a sua saída adira estritamente a um esquema Pydantic predefinido, incluindo a validação de campos obrigatórios e enums.

## I. Dominando a Saída Estruturada no Google Agent Development Kit

A análise do Google Agent Development Kit (ADK) revela que o framework foi projetado com mecanismos nativos para a geração de saídas estruturadas, abstraindo grande parte da complexidade da API Gemini subjacente. A compreensão correta desses mecanismos é fundamental para uma implementação robusta e livre de erros.

### O Parâmetro `output_schema`: O Gateway do ADK para a Geração Controlada

O principal mecanismo fornecido pelo ADK para impor uma estrutura de saída é o parâmetro `output_schema` na classe `LlmAgent`.¹ Este parâmetro funciona como a interface de alto nível para a funcionalidade de geração controlada do Gemini, projetada para se integrar diretamente com modelos Pydantic em ambientes Python.

A funcionalidade central reside na sua capacidade de aceitar uma classe que herda de `pydantic.BaseModel` como seu valor. Quando um agente é instanciado com este parâmetro, o framework ADK executa várias ações internamente:

1.  Converte o modelo Pydantic fornecido em uma representação de Esquema JSON compatível com a especificação OpenAPI 3.0, que a API Gemini entende.²
2.  Configura a chamada para a API Gemini, definindo o parâmetro `response_mime_type` como `$application/json$` e passando o esquema gerado no campo `response_schema` do objeto de configuração da geração.³
3.  Após receber a resposta do modelo, o ADK tenta analisar a string JSON retornada e validá-la contra o modelo Pydantic original.

Esta integração nativa com Pydantic é um recurso poderoso, pois simplifica drasticamente o desenvolvimento. Em vez de construir manualmente dicionários de Esquema JSON, os desenvolvedores podem usar a sintaxe declarativa e expressiva do Pydantic, que é amplamente utilizada em ecossistemas Python, especialmente com frameworks como FastAPI.⁵ O próprio SDK subjacente `google-genai`, que o ADK utiliza, suporta nativamente o uso de classes Pydantic para o parâmetro `response_schema`, garantindo uma base sólida para esta funcionalidade.²

Para tornar a saída estruturada útil em um pipeline multiagente, o ADK fornece o parâmetro `output_key`. Quando `output_key` é definido em conjunto com `output_schema`, o resultado da geração não é apenas validado, mas o objeto Pydantic instanciado é automaticamente armazenado no dicionário de estado da sessão (`session.state`) sob a chave especificada.¹ Por exemplo, se `output_key` for definido como `'final_ads'`, os agentes subsequentes no fluxo de trabalho podem acessar um objeto Python totalmente tipado e validado através de `session.state['final_ads']`, eliminando a necessidade de análise e validação manuais de JSON em etapas posteriores.⁹

### Esclarecendo o Papel de `generate_content_config`

É crucial distinguir a função do parâmetro `output_schema` daquela do `generate_content_config`. Uma fonte comum de confusão é a tentativa de configurar o esquema de resposta através do `generate_content_config`. No entanto, este parâmetro serve a um propósito diferente: ele é projetado para ajustar o comportamento de geração do LLM, não a sua estrutura de saída.¹

O `generate_content_config` aceita uma instância do objeto `google.genai.types.GenerateContentConfig`.¹¹ Através deste objeto, os desenvolvedores podem controlar parâmetros de inferência do modelo, como:

*   `temperature`: Controla a aleatoriedade da saída. Valores mais baixos (próximos de 0.0) tornam a saída mais determinística.
*   `max_output_tokens`: Define o comprimento máximo da resposta em tokens.
*   `top_p` / `top_k`: Métodos de amostragem para controlar a diversidade do vocabulário.
*   `safety_settings`: Configura os limiares para o bloqueio de conteúdo potencialmente prejudicial.¹²

Dentro do contexto do `LlmAgent` do ADK, os parâmetros `response_mime_type` e `response_schema` não devem ser definidos manualmente dentro de um objeto `GenerateContentConfig`. O ADK gerencia essa configuração automaticamente quando o parâmetro `output_schema` é utilizado. Tentar configurá-los manualmente pode levar a um comportamento inesperado ou a erros de configuração. A abordagem correta é usar `output_schema` para a estrutura e, separadamente, `generate_content_config` para o comportamento da geração.

### Tabela de Referência de APIs e Parâmetros

Para consolidar o entendimento, a tabela a seguir detalha os parâmetros do `LlmAgent` mais relevantes para a implementação da saída estruturada.

| Parâmetro                 | Tipo                        | Descrição                                                                       | Papel nesta Solução                                                                              |
| :------------------------ | :-------------------------- | :------------------------------------------------------------------------------ | :----------------------------------------------------------------------------------------------- |
| `name`                    | str                         | Um identificador único e descritivo para o agente.                              | Identifica o `final_assembler_llm` no pipeline.                                                  |
| `model`                   | str ou BaseLlm              | O identificador do modelo Gemini a ser utilizado (ex: 'gemini-1.5-flash').      | Define o motor de IA que realizará a montagem do JSON.                                           |
| `instruction`             | str                         | O prompt de sistema que guia o comportamento e a tarefa do agente.              | Orienta o modelo a preencher o esquema com base nos dados de entrada.                            |
| `output_schema`           | type                        | Parâmetro central. A classe Pydantic que define a estrutura JSON desejada.      | Garante que a saída do LLM seja um JSON válido que corresponda ao `AdVariationsPayload`.         |
| `output_key`              | str                         | A chave sob a qual o objeto Pydantic analisado é armazenado em `session.state`. | Permite que agentes downstream acessem os dados validados de forma programática.                 |
| `generate_content_config` | types.GenerateContentConfig | Configurações para o comportamento de geração do LLM (ex: temperatura).         | Usado para ajustar a criatividade ou o determinismo da montagem do anúncio, não a sua estrutura. |

A arquitetura do ADK, ao fornecer uma abstração como `output_schema`, oferece uma experiência de desenvolvimento simplificada. No entanto, é importante reconhecer que essa conveniência vem com uma troca. O desenvolvedor está dependendo da implementação do ADK para traduzir corretamente o modelo Pydantic para o Esquema JSON e para configurar a chamada da API. Quaisquer limitações na capacidade de conversão do ADK ou um atraso na adoção de novos recursos da API Gemini de geração controlada poderiam se tornar um ponto de restrição. Esta abstração, embora poderosa, significa que o controle sobre a chamada exata da API é delegado ao framework.

## II. Arquitetando o Esquema Canônico para Variações de Anúncios do Instagram

A base de uma saída estruturada confiável é um esquema bem definido. Utilizando Pydantic, podemos criar um contrato de dados que não apenas valida a saída do LLM, mas também serve como um guia claro para o modelo sobre a estrutura esperada. O esquema a seguir é projetado para ser robusto, modular e alinhado com os requisitos do `final_assembler_llm`.

### Design do Modelo Pydantic para `StrictAdItem`

Para garantir a clareza e a manutenibilidade, a estrutura do anúncio será dividida em modelos Pydantic aninhados. Esta abordagem modular é totalmente suportada pela geração de Esquema JSON do Pydantic e facilita a compreensão tanto para os desenvolvedores quanto para o LLM.¹⁴ Cada campo será anotado com uma descrição usando `pydantic.Field`, uma prática recomendada que melhora a capacidade do modelo Gemini de compreender a intenção de cada campo e preenchê-lo corretamente.¹⁵

### Impondo Restrições com Enums

Uma das principais fontes de falha de validação é a geração de valores de string que não pertencem a um conjunto predefinido. Para resolver isso, utilizaremos a classe `Enum` do Python, que se integra perfeitamente com Pydantic e é suportada pela funcionalidade de esquema do Gemini.²

Primeiro, definimos os enums para os textos de Call-To-Action (CTA) e para as proporções de aspecto, conforme os requisitos.

```python
import enum
from pydantic import BaseModel, Field
from typing import List

class CtaEnum(str, enum.Enum):
    """Enumeração dos textos de Call-To-Action permitidos."""
    SAIBA_MAIS = "Saiba mais"
    ENVIAR_MENSAGEM = "Enviar mensagem"
    LIGAR = "Ligar"
    COMPRAR_AGORA = "Comprar agora"
    CADASTRE_SE = "Cadastre-se"

class AspectRatioEnum(str, enum.Enum):
    """Enumeração das proporções de aspecto permitidas com base nas especificações de formato."""
    SQUARE = "1:1"
    VERTICAL = "4:5"
    STORY = "9:16"
```

Com os enums definidos, podemos construir os modelos Pydantic aninhados.

```python
class CopyContent(BaseModel):
    """Define o conteúdo de texto de uma variação de anúncio."""
    headline: str = Field(description="O título principal do anúncio. Deve ser curto e impactante.")
    body: str = Field(description="O texto do corpo do anúncio, detalhando a oferta ou mensagem.")
    cta_texto: CtaEnum = Field(description="O texto exibido no botão principal de call-to-action.")

class VisualContent(BaseModel):
    """Define o conteúdo visual de uma variação de anúncio."""
    asset_url: str = Field(description="A URL do ativo de imagem ou vídeo a ser usado.")
    aspect_ratio: AspectRatioEnum = Field(description="A proporção de aspecto do visual, conforme as especificações.")

class StrictAdItem(BaseModel):
    """Define a estrutura completa e estrita de uma única variação de anúncio."""
    landing_page_url: str = Field(description="A URL de destino para a qual o usuário será redirecionado.")
    formato: str = Field(default="INSTAGRAM_FEED", description="O formato de posicionamento do anúncio.")
    copy: CopyContent = Field(description="O conteúdo de texto do anúncio.")
    visual: VisualContent = Field(description="O conteúdo visual do anúncio.")
    cta_instagram: CtaEnum = Field(description="O tipo de botão de CTA nativo do Instagram a ser usado.")
```

### O Esquema Completo `AdVariationsPayload`

Finalmente, o modelo de nível superior encapsula a saída completa esperada do `final_assembler_llm`. O requisito é que o agente produza três variações. O esquema garantirá que a saída seja uma lista e que cada item dentro dessa lista adira à estrutura `StrictAdItem`.

```python
class AdVariationsPayload(BaseModel):
    """O payload final contendo uma lista de variações de anúncios geradas."""
    variations: List[StrictAdItem] = Field(
        description="Uma lista contendo exatamente três variações de anúncio completas e validadas.",
        min_length=3,
        max_length=3
    )
```

Nota: Embora `min_length` e `max_length` sejam úteis para a validação Pydantic pós-geração, a API Gemini pode não impor estritamente a cardinalidade da lista com a mesma confiabilidade que impõe a estrutura do objeto. Portanto, a instrução do prompt ainda deve enfatizar a necessidade de gerar exatamente três itens.

Este processo de design de esquema transcende a mera modelagem de dados; ele se torna uma forma de engenharia de prompt. A clareza dos nomes dos campos, o uso de enums e as descrições detalhadas fornecem um contexto rico para o LLM. Um esquema bem projetado reduz a ambiguidade e a carga cognitiva sobre o modelo, diminuindo a necessidade de instruções de prompt excessivamente complexas e aumentando drasticamente a probabilidade de uma saída compatível e de alta qualidade na primeira tentativa.

## III. Guia de Implementação Passo a Passo para o `final_assembler_llm`

Com o esquema canônico definido, a próxima fase é integrá-lo ao agente `final_assembler_llm` existente. Este processo envolve a refatoração da instanciação do agente, a revisão do seu prompt de instrução e a adaptação dos agentes consumidores downstream para aproveitar a saída já validada.

### Refatorando o `LlmAgent` para Imposição de Esquema

A modificação principal no código existente é na instanciação do `LlmAgent`. O agente deve ser atualizado para incluir os parâmetros `output_schema` e `output_key`.

#### Exemplo de Código: Antes e Depois

Supondo que a definição original do agente fosse semelhante a esta:

```python
# --- ANTES ---
from google.adk.agents import LlmAgent

# Snippets de código aprovados são passados no contexto/prompt
instruction_prompt_antiga = """
Você é um montador de anúncios especialista.
Com base nos snippets de código aprovados fornecidos, gere três variações de anúncio completas.
Sua resposta deve ser APENAS um objeto JSON válido contendo uma lista de três anúncios.
"""

final_assembler_llm_antigo = LlmAgent(
    name="final_assembler_llm",
    model="gemini-1.5-flash",
    instruction=instruction_prompt_antiga,
)
```

A versão refatorada integrará o esquema Pydantic `AdVariationsPayload` definido anteriormente:

```python
# --- DEPOIS ---
from google.adk.agents import LlmAgent
# Importar o modelo Pydantic definido na Seção II
from .schemas import AdVariationsPayload

# O prompt é revisado para trabalhar em conjunto com o esquema
instruction_prompt_nova = """
Você é um montador de anúncios especialista em IA. Sua tarefa é usar os 'approved_code_snippets'
fornecidos para construir um payload de anúncio completo.
Sua resposta final DEVE ser um objeto JSON que se ajuste perfeitamente ao esquema AdVariationsPayload.
Gere exatamente três variações de anúncio. Não inclua nenhum texto, explicações ou
formatação markdown em torno do objeto JSON.
"""

final_assembler_llm_novo = LlmAgent(
    name="final_assembler_llm",
    model="gemini-1.5-flash",
    instruction=instruction_prompt_nova,
    output_schema=AdVariationsPayload,
    output_key="final_ad_variations"
)
```

Nesta nova configuração, o ADK garantirá que a saída do `final_assembler_llm_novo` seja uma string JSON que possa ser validada com sucesso pelo modelo `AdVariationsPayload`. Além disso, o objeto Pydantic resultante será acessível em `session.state['final_ad_variations']` para os próximos agentes no pipeline.⁵

### Revisando o Prompt para Ótima Conformidade com o Esquema

Embora o `output_schema` imponha a estrutura, o prompt de instrução (`instruction`) continua a ser um componente vital para o sucesso. A documentação e as melhores práticas indicam que o modelo tem um desempenho melhor quando o prompt e o esquema trabalham em sinergia.¹

A instrução revisada deve:

*   **Reconhecer o Esquema:** Mencionar explicitamente que a saída deve estar em conformidade com o esquema fornecido.
*   **Ser Direto:** Instruir o modelo a retornar apenas o objeto JSON, sem texto ou formatação adicionais, como blocos de código markdown (```json...```). Este é um problema comum que a geração controlada ajuda a resolver, mas um prompt claro reforça o comportamento desejado.⁴
*   **Reforçar a Cardinalidade:** Repetir o requisito de gerar "exatamente três variações", pois, como mencionado, a imposição do comprimento da lista pelo esquema pode ser menos rigorosa do que a imposição da estrutura do objeto.

A combinação de um esquema estrito e um prompt claro e sinérgico é a abordagem mais eficaz para alcançar uma conformidade de saída consistente e confiável.³

### Adaptando os Consumidores Downstream

A implementação da saída estruturada no agente de montagem gera um benefício arquitetônico significativo: a simplificação dos agentes subsequentes. Os agentes `FinalAssemblyNormalizer` e `FinalDeliveryValidatorAgent` podem ter sua complexidade drasticamente reduzida.

O `FinalDeliveryValidatorAgent`, em particular, transforma-se de um agente de análise e validação complexo em um simples verificador de estado.

#### Exemplo de Lógica do Validador: Antes e Depois

A lógica anterior provavelmente envolvia a captura de uma string de texto, análise de JSON e um bloco `try-except` para capturar `ValidationError`.

```python
# --- LÓGICA DO VALIDADOR ANTES ---
from pydantic import ValidationError
import json

# Dentro do método de execução do agente validador...
raw_json_output = session.state.get('raw_assembler_output')
if not raw_json_output:
    # Lidar com erro: sem saída
    return

try:
    # Análise manual e validação
    data = json.loads(raw_json_output)
    payload = AdVariationsPayload.model_validate(data)
    if len(payload.variations) != 3:
        # Lidar com erro: contagem incorreta
        return
    #... Lógica de entrega bem-sucedida...
except (json.JSONDecodeError, ValidationError) as e:
    # Lidar com erro: JSON malformado ou esquema inválido
    return
```

Com a nova abordagem, a validação já foi realizada pelo ADK no momento em que a saída do `final_assembler_llm` foi gerada. O agente validador simplesmente precisa verificar se o objeto esperado existe no estado da sessão.

```python
# --- LÓGICA DO VALIDADOR DEPOIS ---

# Dentro do método de execução do agente validador...
validated_payload: AdVariationsPayload = session.state.get('final_ad_variations')

if validated_payload and isinstance(validated_payload, AdVariationsPayload):
    # A análise e a validação do esquema já foram feitas pelo ADK.
    # A validação de cardinalidade do Pydantic (min/max_length) também foi aplicada.
    #... Lógica de entrega bem-sucedida...
else:
    # Lidar com erro: o agente montador falhou em produzir uma saída válida.
    # O objeto não está no estado ou é do tipo errado.
    return
```

Esta mudança representa uma melhoria arquitetônica fundamental. A responsabilidade pela validação é deslocada para o ponto de geração de dados, tornando o resto do pipeline mais enxuto, robusto e menos suscetível a erros de dados em cascata. O custo total de propriedade do sistema diminui, pois há menos código personalizado de tratamento de erros e validação para manter.

## IV. Análise de Impacto, Mitigação de Riscos e Desempenho

A transição para a saída estruturada é uma mudança arquitetônica significativa com implicações que vão além da simples validação de JSON. Uma avaliação completa dos trade-offs, riscos e perfil de desempenho é essencial para uma implementação bem-sucedida em um ambiente de produção.

### O Trade-Off Crítico: Incompatibilidade com Ferramentas e Transferências de Agentes

A limitação mais significativa do uso do parâmetro `output_schema` no ADK é sua exclusividade mútua com outras funcionalidades de agência dinâmica. A documentação do ADK e discussões da comunidade confirmam que, quando `output_schema` é ativado, o `LlmAgent` perde a capacidade de:

*   **Utilizar Ferramentas (`tools`):** O agente não pode mais invocar `FunctionTool` ou outras ferramentas para interagir com sistemas externos ou realizar cálculos.
*   **Transferir Controle:** O agente não pode delegar a tarefa a outros agentes (subagentes ou pares) dinamicamente.⁹

A razão para esta restrição reside provavelmente na forma como a API Gemini opera em nível fundamental. A "geração controlada" (`JSON mode`) e a "chamada de função" (`function calling`) são modos de operação distintos e mutuamente exclusivos. No modo de geração controlada, a saída do modelo é rigorosamente restringida a cada token para se conformar à gramática do esquema fornecido. No modo de chamada de função, o modelo tem a liberdade de gerar texto livre ou um token especial que sinaliza uma chamada de ferramenta. A alternância entre esses dois modos em uma única chamada de API não é suportada atualmente.

Para o caso de uso específico do `final_assembler_llm`, esta limitação é perfeitamente aceitável. A função deste agente é terminal dentro do seu escopo: ele recebe dados pré-aprovados e os formata. Ele não precisa realizar pesquisas externas, consultar APIs ou delegar tarefas adicionais. Sua única responsabilidade é a montagem, tornando-o um candidato ideal para a geração controlada.

### Estratégia de Mitigação Arquitetônica: O Padrão Pesquisador-Formatador

Embora a limitação não afete o `final_assembler_llm`, ela tem implicações importantes para o design de futuros agentes mais complexos. Para cenários onde um agente precisa tanto interagir com o mundo externo (via ferramentas) quanto produzir uma saída final estritamente formatada, a melhor prática arquitetônica é adotar um padrão de dois agentes, conforme sugerido por soluções da comunidade.¹⁶

*   **Agente Pesquisador (`Researcher Agent`):** Um `LlmAgent` configurado com um conjunto de ferramentas (`tools`), mas sem um `output_schema`. Sua responsabilidade é interagir com APIs, bancos de dados ou outras fontes de informação para coletar todos os dados necessários. Ele então armazena esses dados, possivelmente em um formato de texto semiestruturado ou como múltiplos valores, no estado da sessão.
*   **Agente Formatador (`Formatter Agent`):** Um segundo `LlmAgent`, sem ferramentas, cujo único propósito é ler os dados brutos deixados pelo Pesquisador no estado da sessão e usar um `output_schema` para formatá-los no JSON final e validado.

Este padrão, embora pareça uma solução alternativa para uma limitação, na verdade promove um design de software robusto ao aderir ao Princípio da Responsabilidade Única. Ele separa as preocupações de "interação e raciocínio dinâmico" das de "transformação e formatação de dados". Em vez de criar um agente monolítico complexo, o sistema é composto por especialistas modulares e mais fáceis de testar. A limitação do framework, portanto, atua como um "guardrail" de design que guia os desenvolvedores para uma arquitetura multiagente mais sustentável.

### Perfil de Desempenho e Latência

A implementação da saída estruturada introduz novas considerações de desempenho:

*   **Custo de Tokens:** O próprio Esquema JSON, gerado a partir do modelo Pydantic, é enviado como parte do prompt para a API Gemini. Isso consome tokens de entrada.¹⁵ Para o esquema `AdVariationsPayload`, esse custo será relativamente baixo, mas para esquemas muito grandes e detalhados, pode se tornar um fator a ser monitorado.
*   **Latência de Geração:** Pode haver um aumento na latência, especialmente na primeira vez que um novo esquema é usado. O backend da API pode precisar processar, validar e armazenar em cache a gramática do esquema antes da geração.¹⁸ As solicitações subsequentes com o mesmo esquema devem ser significativamente mais rápidas. Em geral, a latência da geração estruturada é comparável à geração de texto livre, mas esquemas excessivamente complexos podem adicionar uma sobrecarga computacional.²⁰
*   **Impacto no Sistema:** O impacto mais importante é a melhoria na latência e confiabilidade de ponta a ponta. Ao eliminar a necessidade de laços de repetição (retry loops) causados por falhas de validação de JSON, o sistema se torna mais rápido e previsível em geral. O ganho em confiabilidade e a redução de falhas em cascata superam em muito qualquer pequena sobrecarga de latência na chamada individual da API.

### Compatibilidade e Melhores Práticas com Pydantic

A API Gemini suporta um subconjunto da especificação OpenAPI 3.0 para esquemas.² Embora a integração com Pydantic seja excelente, existem algumas limitações e melhores práticas a serem consideradas para garantir a máxima confiabilidade:

*   **Evitar Tipos Complexos:** Tipos Pydantic muito complexos, como modelos recursivos, ou tipos Python abstratos como `Union` ou `Any`, podem não ser traduzidos corretamente para o Esquema JSON suportado e podem levar a erros ou saídas inesperadas.²¹
*   **Manter a Simplicidade:** Prefira esquemas mais planos em vez de estruturas profundamente aninhadas.
*   **Validadores Pydantic:** Os validadores personalizados definidos nos modelos Pydantic não são executados pelo LLM durante a geração. Eles só são aplicados pelo ADK após o recebimento da resposta. A validação deve ser imposta através de tipos e estruturas, não de lógica de validação personalizada.
*   **Nomenclatura:** Use nomes de propriedades e de enums curtos e descritivos para reduzir a contagem de tokens e a complexidade do esquema.²

### Tabela de Comparação de Estratégias de Implementação

A tabela a seguir resume a análise das diferentes abordagens para alcançar a saída estruturada, justificando a recomendação principal.

| Estratégia                                    | Prós                                                                                                     | Contras                                                                                              | Caso de Uso Recomendado                                                                                     |
| :-------------------------------------------- | :------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------- |
| Nativo ADK `output_schema`                    | Simples, idiomático, totalmente integrado com Pydantic e estado da sessão.                               | Incompatível com ferramentas e transferências de agentes; menos controle sobre os parâmetros da API. | Ideal para agentes terminais de formatação e montagem, como o `final_assembler_llm`.                        |
| Ferramenta Customizada com SDK `google-genai` | Controle total sobre os parâmetros da API; pode ser combinado com outras ferramentas em um mesmo agente. | Mais código boilerplate; gerenciamento manual do cliente da API e do estado.                         | Quando um controle fino da API é necessário dentro de um agente que também precisa usar outras ferramentas. |
| Estender a Classe `LlmAgent`                  | Controle máximo sobre o ciclo de vida e a lógica interna do agente.                                      | Alta complexidade; código frágil a atualizações do ADK; raramente necessário.                        | Para comportamentos de agente avançados e não padronizados que não podem ser alcançados de outra forma.     |

## V. Planejamento de Contingência: Padrões de Implementação Alternativos

Embora a abordagem nativa do ADK com `output_schema` seja a solução recomendada para o problema apresentado, é prudente considerar estratégias alternativas. Estas opções servem como planos de contingência caso a limitação fundamental da abordagem nativa se torne um bloqueador para futuros requisitos.

### Alternativa 1: Integração Direta do SDK via uma Ferramenta Personalizada

Se a restrição de não poder usar ferramentas e `output_schema` juntos se tornar insustentável, uma alternativa viável é encapsular a chamada de geração controlada dentro de uma `FunctionTool` do ADK.

Neste padrão, o fluxo seria o seguinte:

1.  **Criar uma `FunctionTool`:** Desenvolver uma função Python que será registrada como uma ferramenta do ADK.
2.  **Lógica Interna da Ferramenta:** Dentro desta função, em vez de executar uma lógica de negócios, o código instanciaria o cliente do SDK `google.genai` diretamente. Ele construiria e executaria uma chamada ao método `generate_content`, passando explicitamente o prompt, o modelo Pydantic como `response_schema`, e `response_mime_type` como `$application/json$`.²
3.  **Retorno da Ferramenta:** A função receberia a resposta JSON da API, a analisaria (possivelmente instanciando o objeto Pydantic) e a retornaria como a saída da ferramenta.
4.  **Uso pelo Agente:** Um `LlmAgent` poderia então ser configurado com esta "ferramenta de formatação" ao lado de outras ferramentas (como uma ferramenta de busca). O prompt do agente o instruiria a primeiro usar as ferramentas de pesquisa para coletar dados e, em seguida, passar esses dados para a ferramenta de formatação para obter a saída JSON estruturada.

**Trade-offs:**

*   **Prós:** Esta abordagem contorna a limitação de exclusividade mútua, permitindo que um único agente orquestre tanto a coleta de dados quanto a formatação estruturada. Ela oferece controle granular total sobre cada parâmetro da chamada da API Gemini.
*   **Contras:** A conveniência da abstração do ADK é perdida. O desenvolvedor é responsável por gerenciar o ciclo de vida do cliente da API, construir a solicitação manualmente e lidar com a resposta. Isso introduz mais código boilerplate e move a lógica de formatação de uma configuração declarativa (`output_schema`) para uma implementação imperativa dentro de uma ferramenta.

### Alternativa 2: Estendendo a Classe `LlmAgent`

A opção de maior complexidade e último recurso é estender diretamente as classes base do ADK para criar um comportamento de agente personalizado. Um desenvolvedor poderia criar uma nova classe que herda de `google.adk.agents.LlmAgent`.²³

Nesta abordagem, seria necessário um conhecimento profundo do funcionamento interno do ADK. O desenvolvedor teria que identificar e sobrescrever os métodos internos responsáveis por construir e executar a chamada para o LLM (por exemplo, um método como `_generate_content_async_impl`). Dentro do método sobrescrito, seria possível injetar uma lógica customizada que, por exemplo, tentasse fundir a configuração de ferramentas com a configuração de esquema de resposta, ou que alternasse dinamicamente entre os modos de API com base no contexto.

**Trade-offs:**

*   **Prós:** Oferece o nível máximo de controle sobre o comportamento do agente, permitindo a implementação de lógicas que não são suportadas nativamente pelo framework.
*   **Contras:**
    *   **Alta Complexidade:** Requer a leitura e compreensão do código-fonte do ADK.
    *   **Fragilidade:** A implementação se torna fortemente acoplada à versão atual do ADK. Qualquer atualização futura do framework que altere os métodos internos sobrescritos pode quebrar a funcionalidade, criando um alto custo de manutenção.
    *   **Desnecessário na Maioria dos Casos:** Para a grande maioria dos casos de uso, incluindo a combinação de ferramentas e saída estruturada, o padrão Pesquisador-Formatador ou a abordagem de ferramenta personalizada são soluções muito mais simples e robustas.

Esta alternativa deve ser considerada apenas em cenários extremos onde os padrões existentes são comprovadamente inadequados e o nível de personalização justifica o aumento significativo na complexidade e no risco de manutenção.

## VI. Recomendações Finais

Com base na análise técnica detalhada, as seguintes recomendações são propostas para resolver de forma robusta e escalável o problema de validação de JSON no agente `final_assembler_llm`.

### Recomendação Primária:

Adotar a abordagem nativa do Google Agent Development Kit, utilizando o parâmetro `output_schema` na instanciação do `LlmAgent` `final_assembler_llm`. Esta é a solução mais direta, idiomática e de menor complexidade.

**Justificativa:** O agente `final_assembler_llm` tem uma responsabilidade única e terminal de formatação, não requerendo o uso de ferramentas ou transferência de controle. Portanto, a principal limitação do `output_schema` não se aplica a este caso de uso. Os benefícios de ter a validação de esquema garantida pelo framework, a integração perfeita com Pydantic e a simplificação radical dos agentes consumidores downstream superam em muito qualquer outra consideração.

### Diretriz Arquitetônica para o Futuro:

Para o desenvolvimento de futuros agentes que exijam tanto a interação com ferramentas quanto a produção de uma saída estruturada, adotar o padrão Pesquisador-Formatador.

**Justificativa:** Este padrão promove um design de sistema multiagente mais limpo e modular, separando as responsabilidades de raciocínio/interação e de formatação de dados. Ele representa uma prática de engenharia de software sólida que leva a agentes mais especializados, testáveis e fáceis de manter, alinhando-se com os princípios de design de microsserviços aplicados a sistemas de IA.

### Plano de Ação Sugerido:

1.  **Definir os Esquemas Pydantic:** Implementar as classes `CtaEnum`, `AspectRatioEnum`, `CopyContent`, `VisualContent`, `StrictAdItem` e `AdVariationsPayload` em um módulo de esquemas compartilhado.
2.  **Refatorar o `final_assembler_llm`:** Modificar a instanciação do `LlmAgent` para incluir os parâmetros `output_schema=AdVariationsPayload` e `output_key='final_ad_variations'`.
3.  **Revisar o Prompt do Agente:** Atualizar a instrução (`instruction`) do `final_assembler_llm` para orientar explicitamente o modelo a preencher o esquema e a retornar apenas o objeto JSON.
4.  **Simplificar Agentes Downstream:** Refatorar o `FinalDeliveryValidatorAgent` e outros consumidores para ler o objeto Pydantic validado diretamente de `session.state['final_ad_variations']`, removendo a lógica manual de análise e validação de JSON.
5.  **Testar e Monitorar:** Realizar testes de ponta a ponta, prestando atenção à latência da primeira chamada com o novo esquema e confirmando a melhoria na confiabilidade geral do pipeline.

Seguindo este plano, a equipe de desenvolvimento pode efetivamente eliminar a classe de erros de validação de JSON, aumentar a robustez do pipeline de geração de anúncios e estabelecer uma base arquitetônica sólida para a construção de sistemas multiagente mais complexos e confiáveis.