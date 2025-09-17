# Análise de Refatoração: Especificações Dinâmicas por Formato de Anúncio

## Contexto do Sistema Atual

Estamos trabalhando em um sistema de geração de anúncios Instagram baseado em Google ADK (Agent Development Kit) que processa requisições através de múltiplos agentes em pipeline. O sistema atualmente gera 3 variações de anúncios em formato JSON.

## Problema Identificado

Atualmente, o sistema trata todos os formatos de anúncio (Reels, Stories, Feed) de forma praticamente idêntica, alterando apenas o `aspect_ratio` das imagens. Isso resulta em:

1. **Conteúdo genérico**: Headlines, copy e CTAs iguais para Reels (vídeo dinâmico) e Feed (posts estáticos)
2. **Desperdício de potencial**: Stories não aproveitam elementos de urgência/escassez
3. **Validações inadequadas**: Limites de caracteres iguais para todos os formatos
4. **Estratégias uniformes**: Ignora que cada formato funciona melhor em diferentes etapas do funil

## Nossa Proposta de Solução

### Abordagem: Injeção de Especificações via State

Queremos manter o schema JSON de saída fixo, mas injetar especificações dinâmicas baseadas no formato escolhido. A proposta é:

1. **Criar arquivo de especificações** (`app/format_specifications.py`):
```python
FORMAT_SPECS = {
    "Reels": {
        "copy": {
            "headline_max_chars": 40,
            "corpo_style": "bullets rápidos, verbos de ação",
            "estrutura_narrativa": "gancho-desenvolvimento-cta"
        },
        "visual": {
            "tipo_midia": ["video", "foto_sequencial"],
            "aspect_ratio": "9:16"
        },
        "strategy": {
            "etapa_funil": ["topo", "meio"],
            "cta_preferencial": "Saiba mais"
        }
    },
    # Similar para Stories e Feed...
}
```

2. **Modificar o callback existente** (`unpack_extracted_input_callback`) ou criar novo para:
   - Detectar o campo `formato_anuncio` extraído pelo `input_processor`
   - Buscar as especificações correspondentes
   - Adicionar ao state como `state["format_specs"]`

3. **Atualizar prompts dos agentes** para usar `{format_specs}`:
   - `context_synthesizer`: Criar briefing específico
   - `code_generator`: Seguir limites e estilos
   - `code_reviewer`: Validar contra specs
   - `final_assembler`: Gerar variações adequadas

### Fluxo Proposto:
```
Usuário envia "formato_anuncio: Reels"
    ↓
input_processor extrai campo
    ↓
callback injeta FORMAT_SPECS["Reels"] no state
    ↓
Todos agentes têm acesso via {format_specs} nos prompts
```

## Questões para o Codex Analisar

### 1. Viabilidade Técnica
Por favor, analise o código real em `app/agent.py` e confirme:
- O state é realmente compartilhado entre todos os agentes durante a execução?
- Os placeholders como `{formato_anuncio}` nos prompts são substituídos automaticamente pelo ADK?
- É possível adicionar novos campos ao state via callback e acessá-los nos agentes subsequentes?

### 2. Ponto de Injeção Correto
Verifique se nossa proposta de usar `after_agent_callback` no `input_processor` é adequada:
- Linha 778: `after_agent_callback=unpack_extracted_input_callback`
- Este é o melhor lugar para injetar as especificações?
- Ou seria melhor em outro ponto do pipeline?

### 3. Propagação do State
Confirme como o state se propaga:
- O `callback_context.state` modificado em um callback fica disponível para todos os agentes seguintes?
- Exemplo nas linhas 146-147 onde campos são adicionados ao state

### 4. Alternativas de Implementação

Por favor, sugira se há uma abordagem melhor/mais segura:

a) **Alternativa 1**: Usar `before_agent_callback` em vez de `after_agent_callback`?

b) **Alternativa 2**: Criar um agente intermediário dedicado apenas para injetar specs?
```python
format_spec_injector = LlmAgent(
    name="format_spec_injector",
    instruction="Injete especificações baseadas em {formato_anuncio}"
    # ...
)
```

c) **Alternativa 3**: Modificar diretamente os prompts com condicionais?
```python
instruction = """
{% if formato_anuncio == "Reels" %}
  Use limite de 40 caracteres...
{% elif formato_anuncio == "Stories" %}
  Use urgência e escassez...
{% endif %}
"""
```

d) **Alternativa 4**: Usar um FunctionTool customizado para buscar specs?

### 5. Riscos e Considerações

Identifique potenciais problemas:
- Risco de sobrescrever campos importantes do state?
- Impacto na performance com dicionários grandes no state?
- Compatibilidade com callbacks existentes como `process_and_extract_sb7`?
- Melhor formato para passar specs (JSON string vs dict vs objeto)?

## Resultado Esperado da Análise

Precisamos que o Codex:

1. **Valide** se nossa compreensão do fluxo ADK está correta
2. **Confirme** se a abordagem de injeção via state funcionará
3. **Sugira** a implementação mais limpa e maintível
4. **Identifique** riscos que não consideramos
5. **Recomende** padrões ADK best practices para este caso

## Arquivos Relevantes para Análise

- `app/agent.py` - Pipeline principal e agentes
- `app/config.py` - Configurações do sistema
- `app/callbacks/landing_page_callbacks.py` - Exemplo de callbacks existentes
- Documentação ADK sobre state management e callbacks

Por favor, forneça uma análise técnica detalhada com exemplos de código quando apropriado.