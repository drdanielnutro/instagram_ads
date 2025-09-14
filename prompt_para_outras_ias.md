# Pesquisa Definitiva: Capacidades Nativas e Estrutura do Google ADK

## Contexto
Estou desenvolvendo um sistema com o Google Assistant Development Kit (ADK) e recebi duas pesquisas contraditórias sobre as capacidades nativas da plataforma. Preciso de respostas definitivas baseadas exclusivamente na documentação oficial do ADK sobre o que é nativo da plataforma e o que precisa ser implementado customizado.

## Inconsistências a Resolver

### 1. Ferramenta de Fetch Nativa do ADK
**Conflito:**
- Pesquisa 1 afirma que NÃO existe ferramenta nativa de fetch (como `web_fetch` ou `http_fetch`) no ADK e sugere criar uma Function Tool customizada.
- Pesquisa 2 afirma que EXISTE `load_web_page(url)` nativa importável de `google.adk.tools`.

**Pergunta:** O Google ADK possui alguma ferramenta nativa para fazer fetch/download de páginas web? Se sim, qual é o nome exato, como importá-la e qual sua sintaxe de uso? Se não, qual a abordagem recomendada pela documentação oficial?

### 2. Callbacks e Processamento de Tools
**Conflito:**
- Pesquisa 1 sugere usar `before_tool_callback` e `after_tool_callback` para processar dados.
- Pesquisa 2 também menciona callbacks mas com abordagem diferente de seleção de tools.

**Pergunta:** Como funcionam os callbacks no ADK? Qual a sintaxe correta para `before_tool_callback` e `after_tool_callback`? É possível usar callbacks para escolher dinamicamente qual tool executar?

### 3. Tool `google_search` Nativa
**Conflito:**
- Pesquisa 1 substitui `google_search` por tool custom.
- Pesquisa 2 mantém `google_search` junto com outras tools.

**Pergunta:** A `google_search` é uma tool nativa do ADK? Como importá-la corretamente? Ela pode coexistir com outras tools customizadas no mesmo agente?

### 4. LoopAgent e Tipos de Agentes
**Conflito:**
- Pesquisa 1 usa um único agente com `output_key`.
- Pesquisa 2 menciona `LoopAgent` para conectar múltiplos agentes.

**Pergunta:** O ADK possui `LoopAgent` como tipo nativo de agente? Quais tipos de agentes existem nativamente no ADK? Como é a sintaxe correta para criar e conectar múltiplos agentes?

### 5. Tool Context e Actions
**Conflito:**
- Pesquisa 1 menciona `tool_context.actions.escalate = True` para controlar fluxo.
- Pesquisa 2 usa manipulação direta do `state` para controle.

**Pergunta:** O objeto `tool_context.actions` existe no ADK? O que é `escalate` e como funciona? Qual a estrutura correta do contexto de ferramentas no ADK?

### 6. Modelos LLM Disponíveis
**Conflito:**
- Pesquisa 1 usa `model="gemini-1.5-flash"`.
- Pesquisa 2 menciona `gemini-2.5-flash` e `gemini-2.5-pro`.

**Pergunta:** Quais modelos Gemini estão atualmente disponíveis no ADK? Existem modelos "2.5"? Qual a nomenclatura correta e capabilities de cada modelo?

### 7. Estado e Output Key
**Conflito:**
- Pesquisa 1 usa `output_key` para persistir resultados.
- Pesquisa 2 manipula diretamente múltiplas chaves no `state`.

**Pergunta:** Como funciona o sistema de estado no ADK? O que é `output_key` e como difere da manipulação direta do `state`? Qual a sintaxe correta para compartilhar dados entre agentes?

### 8. Estrutura de Projeto ADK
**Conflito:**
- Pesquisa 1 sugere estrutura simples com `agent.py` e pasta `.tools`.
- Pesquisa 2 sugere estrutura com `tools/`, `callbacks/`, `schemas/`, `agents/`.

**Pergunta:** O ADK define uma estrutura de diretórios padrão? Onde devem ficar tools customizadas, callbacks e schemas segundo a documentação oficial?

### 9. Output Schema e Validação
**Conflito:**
- Pesquisa 1 processa dados no `after_tool_callback`.
- Pesquisa 2 menciona uso de `output_schema` para validação estruturada.

**Pergunta:** O ADK suporta `output_schema` para validar outputs de agentes? Como funciona? Qual a sintaxe para definir schemas de saída estruturada?

### 10. Function Tools Customizadas
**Questão adicional:**
Como criar Function Tools customizadas no ADK? Qual a estrutura e sintaxe correta? Como registrar e usar tools customizadas em agentes?

## Requisitos da Resposta

Para CADA ponto acima, preciso:

1. **Resposta SIM/NÃO definitiva** - Se é nativo do ADK ou não
2. **Sintaxe correta** - Se for nativo, como importar e usar
3. **Código exemplo** - Mostrando a implementação correta segundo a documentação oficial
4. **Referência da documentação** - Link ou seção específica da documentação ADK que confirma a resposta

## Instruções Importantes

- **FOQUE APENAS** nas capacidades nativas do ADK
- **NÃO** sugira implementações ou soluções para análise de conteúdo
- **NÃO** discuta frameworks de análise como StoryBrand
- **RESPONDA APENAS** o que é ou não é nativo do ADK
- Se algo não existir na documentação oficial, diga claramente "NÃO É NATIVO DO ADK"
- Use a documentação oficial mais recente do Google ADK (2024/2025)

Por favor, seja extremamente preciso e baseie-se EXCLUSIVAMENTE na documentação oficial do Google ADK.