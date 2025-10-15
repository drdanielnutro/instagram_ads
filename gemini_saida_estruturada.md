Saída estruturada

Você pode configurar o Gemini para gerar uma saída estruturada em vez de texto não estruturado, permitindo a extração e padronização precisas de informações para processamento posterior. Por exemplo, você pode usar a saída estruturada para extrair informações de currículos e padronizá-los para criar um banco de dados estruturado.

O Gemini pode gerar JSON ou valores de enumeração como saída estruturada.

Gerar JSON
Para restringir o modelo a gerar JSON, configure um responseSchema. O modelo vai responder a qualquer comando com uma saída formatada em JSON.

Python
JavaScript
Go
REST

from google import genai
from pydantic import BaseModel

class Recipe(BaseModel):
    recipe_name: str
    ingredients: list[str]

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="List a few popular cookie recipes, and include the amounts of ingredients.",
    config={
        "response_mime_type": "application/json",
        "response_schema": list[Recipe],
    },
)
# Use the response as a JSON string.
print(response.text)

# Use instantiated objects.
my_recipes: list[Recipe] = response.parsed
Observação: validadores do Pydantic ainda não são compatíveis. Se ocorrer um pydantic.ValidationError, ele será suprimido, e .parsed poderá estar vazio/nulo.
A saída pode ser semelhante a esta:


[
  {
    "recipeName": "Chocolate Chip Cookies",
    "ingredients": [
      "1 cup (2 sticks) unsalted butter, softened",
      "3/4 cup granulated sugar",
      "3/4 cup packed brown sugar",
      "1 teaspoon vanilla extract",
      "2 large eggs",
      "2 1/4 cups all-purpose flour",
      "1 teaspoon baking soda",
      "1 teaspoon salt",
      "2 cups chocolate chips"
    ]
  },
  ...
]
Gerar valores de tipo enumerado
Em alguns casos, talvez você queira que o modelo escolha uma única opção em uma lista. Para implementar esse comportamento, transmita um enum no seu esquema. É possível usar uma opção de enumeração em qualquer lugar em que um string possa ser usado no responseSchema, porque uma enumeração é uma matriz de strings. Assim como um esquema JSON, uma enumeração permite restringir a saída do modelo para atender aos requisitos do seu aplicativo.

Por exemplo, suponha que você esteja desenvolvendo um aplicativo para classificar instrumentos musicais em uma de cinco categorias: "Percussion", "String", "Woodwind", "Brass" ou ""Keyboard"". Você pode criar uma enumeração para ajudar nessa tarefa.

No exemplo a seguir, você transmite uma enumeração como responseSchema, restringindo o modelo a escolher a opção mais adequada.

Python
JavaScript
REST

from google import genai
import enum

class Instrument(enum.Enum):
  PERCUSSION = "Percussion"
  STRING = "String"
  WOODWIND = "Woodwind"
  BRASS = "Brass"
  KEYBOARD = "Keyboard"

client = genai.Client()
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What type of instrument is an oboe?',
    config={
        'response_mime_type': 'text/x.enum',
        'response_schema': Instrument,
    },
)

print(response.text)
# Woodwind
A biblioteca Python vai traduzir as declarações de tipo da API. No entanto, a API aceita um subconjunto do esquema OpenAPI 3.0 (Schema).

Há outras duas maneiras de especificar uma enumeração. Você pode usar um Literal: ```

Python

Literal["Percussion", "String", "Woodwind", "Brass", "Keyboard"]
Também é possível transmitir o esquema como JSON:

Python

from google import genai

client = genai.Client()
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What type of instrument is an oboe?',
    config={
        'response_mime_type': 'text/x.enum',
        'response_schema': {
            "type": "STRING",
            "enum": ["Percussion", "String", "Woodwind", "Brass", "Keyboard"],
        },
    },
)

print(response.text)
# Woodwind
Além de problemas básicos de múltipla escolha, você pode usar uma enumeração em qualquer lugar de um esquema JSON. Por exemplo, você pode pedir ao modelo uma lista de títulos de receitas e usar uma enumeração Grade para dar a cada título uma classificação de popularidade:

Python

from google import genai

import enum
from pydantic import BaseModel

class Grade(enum.Enum):
    A_PLUS = "a+"
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    F = "f"

class Recipe(BaseModel):
  recipe_name: str
  rating: Grade

client = genai.Client()
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='List 10 home-baked cookie recipes and give them grades based on tastiness.',
    config={
        'response_mime_type': 'application/json',
        'response_schema': list[Recipe],
    },
)

print(response.text)
A resposta pode ser semelhante a esta:


[
  {
    "recipe_name": "Chocolate Chip Cookies",
    "rating": "a+"
  },
  {
    "recipe_name": "Peanut Butter Cookies",
    "rating": "a"
  },
  {
    "recipe_name": "Oatmeal Raisin Cookies",
    "rating": "b"
  },
  ...
]
Sobre esquemas JSON
A configuração do modelo para saída JSON usando o parâmetro responseSchema depende do objeto Schema para definir a estrutura. Esse objeto representa um subconjunto selecionado do objeto de esquema da OpenAPI 3.0 e também adiciona um campo propertyOrdering.

Dica: em Python, quando você usa um modelo Pydantic, não precisa trabalhar diretamente com objetos Schema, já que ele é convertido automaticamente para o esquema JSON correspondente. Para saber mais, consulte Esquemas JSON em Python.
Confira uma representação pseudo-JSON de todos os campos Schema:


{
  "type": enum (Type),
  "format": string,
  "description": string,
  "nullable": boolean,
  "enum": [
    string
  ],
  "maxItems": integer,
  "minItems": integer,
  "properties": {
    string: {
      object (Schema)
    },
    ...
  },
  "required": [
    string
  ],
  "propertyOrdering": [
    string
  ],
  "items": {
    object (Schema)
  }
}
O Type do esquema precisa ser um dos tipos de dados da OpenAPI ou uma união desses tipos (usando anyOf). Apenas um subconjunto de campos é válido para cada Type. A lista a seguir mapeia cada Type para um subconjunto dos campos válidos para esse tipo:

string -> enum, format, nullable
integer -> format, minimum, maximum, enum, nullable
number -> format, minimum, maximum, enum, nullable
boolean -> nullable
array -> minItems, maxItems, items, nullable
object -> properties, required, propertyOrdering, nullable
Confira alguns exemplos de esquemas que mostram combinações válidas de tipo e campo:


{ "type": "string", "enum": ["a", "b", "c"] }

{ "type": "string", "format": "date-time" }

{ "type": "integer", "format": "int64" }

{ "type": "number", "format": "double" }

{ "type": "boolean" }

{ "type": "array", "minItems": 3, "maxItems": 3, "items": { "type": ... } }

{ "type": "object",
  "properties": {
    "a": { "type": ... },
    "b": { "type": ... },
    "c": { "type": ... }
  },
  "nullable": true,
  "required": ["c"],
  "propertyOrdering": ["c", "b", "a"]
}
Para a documentação completa dos campos de esquema usados na API Gemini, consulte a referência de esquema.

Ordenação de propriedades
Aviso: ao configurar um esquema JSON, defina propertyOrdering[] e, ao fornecer exemplos, verifique se a ordenação das propriedades nos exemplos corresponde ao esquema.
Ao trabalhar com esquemas JSON na API Gemini, a ordem das propriedades é importante. Por padrão, a API ordena as propriedades em ordem alfabética e não preserva a ordem em que elas são definidas, embora os SDKs de IA generativa do Google possam preservar essa ordem. Se você estiver fornecendo exemplos ao modelo com um esquema configurado e a ordenação de propriedades dos exemplos não for consistente com a ordenação de propriedades do esquema, a saída poderá ser confusa ou inesperada.

Para garantir uma ordenação consistente e previsível de propriedades, use o campo opcional propertyOrdering[].


"propertyOrdering": ["recipeName", "ingredients"]
propertyOrdering[], que não é um campo padrão na especificação OpenAPI, é uma matriz de strings usada para determinar a ordem das propriedades na resposta. Ao especificar a ordem das propriedades e fornecer exemplos com propriedades nessa mesma ordem, você pode melhorar a qualidade dos resultados. propertyOrdering só é compatível quando você cria manualmente types.Schema.

Esquemas em Python
Ao usar a biblioteca Python, o valor de response_schema precisa ser um dos seguintes:

Um tipo, como você usaria em uma anotação de tipo (consulte o módulo typing do Python)
Uma instância de genai.types.Schema
O dict equivalente de genai.types.Schema
A maneira mais fácil de definir um esquema é com um tipo Pydantic, como mostrado no exemplo anterior:

Python

config={'response_mime_type': 'application/json',
        'response_schema': list[Recipe]}
Quando você usa um tipo Pydantic, a biblioteca Python cria um esquema JSON para você e o envia à API. Para mais exemplos, consulte a documentação da biblioteca Python.

A biblioteca Python é compatível com esquemas definidos com os seguintes tipos (em que AllowedType é qualquer tipo permitido):

int
float
bool
str
list[AllowedType]
AllowedType|AllowedType|...
Para tipos estruturados:
dict[str, AllowedType]. Essa anotação declara que todos os valores de dict são do mesmo tipo, mas não especifica quais chaves devem ser incluídas.
Modelos Pydantic definidos pelo usuário. Essa abordagem permite especificar os nomes das chaves e definir diferentes tipos para os valores associados a cada uma delas, incluindo estruturas aninhadas.
Suporte ao JSON Schema
O esquema JSON é uma especificação mais recente do que o OpenAPI 3.0, em que o objeto Schema se baseia. O suporte ao esquema JSON está disponível como uma prévia usando o campo responseJsonSchema, que aceita qualquer esquema JSON com as seguintes limitações:

Ele só funciona com o Gemini 2.5.
Embora todas as propriedades do esquema JSON possam ser transmitidas, nem todas são compatíveis. Consulte a documentação do campo para mais detalhes.
Referências recursivas só podem ser usadas como o valor de uma propriedade de objeto não obrigatória.
As referências recursivas são abertas até um grau finito, com base no tamanho do esquema.
Esquemas que contêm $ref não podem ter outras propriedades além daquelas que começam com $.
Confira um exemplo de como gerar um esquema JSON com Pydantic e enviá-lo ao modelo:


curl "https://generativelanguage.googleapis.com/v1alpha/models/\
gemini-2.5-flash:generateContent" \
    -H "x-goog-api-key: $GEMINI_API_KEY"\
    -H 'Content-Type: application/json' \
    -d @- <<EOF
{
  "contents": [{
    "parts":[{
      "text": "Please give a random example following this schema"
    }]
  }],
  "generationConfig": {
    "response_mime_type": "application/json",
    "response_json_schema": $(python3 - << PYEOF
    from enum import Enum
    from typing import List, Optional, Union, Set
    from pydantic import BaseModel, Field, ConfigDict
    import json

    class UserRole(str, Enum):
        ADMIN = "admin"
        VIEWER = "viewer"

    class Address(BaseModel):
        street: str
        city: str

    class UserProfile(BaseModel):
        username: str = Field(description="User's unique name")
        age: Optional[int] = Field(ge=0, le=120)
        roles: Set[UserRole] = Field(min_items=1)
        contact: Union[Address, str]
        model_config = ConfigDict(title="User Schema")

    # Generate and print the JSON Schema
    print(json.dumps(UserProfile.model_json_schema(), indent=2))
    PYEOF
    )
  }
}
EOF
A transmissão direta de um esquema JSON ainda não é compatível ao usar o SDK.

Práticas recomendadas
Considere as seguintes práticas recomendadas ao usar um esquema de resposta:

O tamanho do esquema de resposta é contabilizado no limite de tokens de entrada.
Por padrão, os campos são opcionais. Isso significa que o modelo pode preencher ou pular os campos. É possível definir campos conforme necessário para forçar o modelo a fornecer um valor. Se não houver contexto suficiente no comando de entrada associado, o modelo gera respostas principalmente com base nos dados em que foi treinado.
Um esquema complexo pode resultar em um erro InvalidArgument: 400. A complexidade pode vir de nomes de propriedades longos, limites de comprimento de matrizes longos, enums com muitos valores, objetos com muitas propriedades opcionais ou uma combinação desses fatores.

Se você receber esse erro com um esquema válido, faça uma ou mais das seguintes mudanças para resolver o problema:

Encurte os nomes de propriedades ou de enumerações.
Nivelar matrizes aninhadas.
Reduza o número de propriedades com restrições, como números com limites mínimo e máximo.
Reduza o número de propriedades com restrições complexas, como propriedades com formatos complexos, como date-time.
Reduza o número de propriedades opcionais.
Reduza o número de valores válidos para enums.
Se você não está vendo os resultados esperados, inclua mais contexto aos comandos de entrada ou revise seu esquema de resposta. Por exemplo, revise a resposta do modelo sem saída estruturada para ver como o modelo responde. Depois, você pode atualizar o esquema de resposta para que ele se ajuste melhor à saída do modelo. Para mais dicas de solução de problemas com saída estruturada, consulte o guia de solução de problemas.

A seguir
Agora que você aprendeu a gerar saída estruturada, talvez queira usar as ferramentas da API Gemini:

Chamadas de função
Execução de código
Embasamento com a Pesquisa Google