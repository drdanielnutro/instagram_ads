# Plano de Correção: Instruções dos Agentes para Garantir 3 Prompts Obrigatórios

## 1. Resumo Executivo

### Problema Identificado

Quando o pipeline de fallback do StoryBrand está ativo, o JSON final apresenta variações com campos `prompt_estado_atual` e `prompt_estado_intermediario` como `null`, deixando apenas `prompt_estado_aspiracional` preenchido. Isso impede a geração das imagens.

### Causa Raiz

As instruções dos agentes `code_generator`, `code_reviewer`, `code_refiner` e `final_assembler` não são suficientemente explícitas e rigorosas sobre a **obrigatoriedade** dos 3 prompts de imagem. Especificamente:

1. **`code_generator`**: Usa `...` que pode ser interpretado como opcional; não enfatiza "OBRIGATÓRIO"
2. **`code_reviewer`**: Usa "Incluir" (fraco); não valida explicitamente se campos são `null`
3. **`code_refiner`**: Não tem instrução específica sobre VISUAL_DRAFT
4. **`final_assembler`**: Instrução ambígua "Complete faltantes de forma conservadora" incentiva manter `null`

### Objetivo da Correção

Modificar **apenas as instruções (strings)** dos 4 agentes para tornar **absolutamente explícito e obrigatório** que:

1. A `descricao_imagem` DEVE descrever uma **sequência de 3 imagens distintas**
2. Os 3 prompts (`prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional`) são **OBRIGATÓRIOS e NUNCA devem ser null**
3. O `code_reviewer` DEVE reprovar qualquer VISUAL_DRAFT com prompts ausentes ou `null`
4. O `final_assembler` DEVE completar obrigatoriamente qualquer prompt ausente

### Escopo

**Incluído**:
- ✅ Modificação de 4 strings de instrução em `app/agent.py`
- ✅ Testes manuais para validar comportamento

**Excluído**:
- ❌ Mudanças em código Python (lógica, estruturas, callbacks)
- ❌ Mudanças em schemas Pydantic
- ❌ Mudanças no pipeline de fallback

---

## 2. Modificações Necessárias

### Localização: `app/agent.py`

Todos os 4 agentes estão definidos no arquivo `app/agent.py`. As modificações serão feitas nas strings `instruction` de cada agente.

---

## 3. Modificação 1: `code_generator` (Linhas 1056-1138)

### 3.1. Localização Exata

**Arquivo**: `app/agent.py`
**Agente**: `code_generator`
**Linhas**: 1108-1118 (seção VISUAL_DRAFT dentro da instrução completa)

### 3.2. Instrução Atual (Antes)

```python
- VISUAL_DRAFT:
  {
    "visual": {
      "descricao_imagem": "Descrição em pt-BR narrando a sequência: estado_atual (dor) → estado_intermediario (decisão imediata) → estado_aspiracional (transformação)...",
      "prompt_estado_atual": "Prompt técnico em inglês descrevendo o estado de dor (emoções, postura, cenário)...",
      "prompt_estado_intermediario": "Prompt técnico em inglês mantendo cenário/vestuário e mostrando a ação imediata de mudança...",
      "prompt_estado_aspiracional": "Prompt técnico em inglês descrevendo o estado transformado (emoções positivas, resultados visíveis, cenário)...",
      "aspect_ratio": "definido conforme especificação do formato"
    },
    "formato": "{formato_anuncio}"  # Usar o especificado pelo usuário
  }
```

### 3.3. Problemas Identificados

1. ❌ Usa `...` ao final de cada campo, que pode ser interpretado como "exemplo" ou "opcional"
2. ❌ Não usa a palavra **"OBRIGATÓRIO"** em nenhum momento
3. ❌ Não proíbe explicitamente deixar campos como `null`
4. ❌ Não enfatiza que `descricao_imagem` deve mencionar **"sequência de 3 imagens/cenas"**
5. ❌ Não explica claramente a narrativa esperada (jornada StoryBrand)

### 3.4. Instrução Nova (Depois)

```python
- VISUAL_DRAFT:

  **IMPORTANTE**: Este é o fragmento mais crítico. Você DEVE gerar EXATAMENTE 3 prompts de imagem distintos e completos.
  NUNCA crie apenas 1 ou 2 prompts. NUNCA deixe campos como null, vazios ou omitidos.

  A narrativa visual DEVE seguir a jornada do cliente através do framework StoryBrand:
  1. **Estado Atual (Dor)**: O cliente enfrentando o problema/frustração específica
  2. **Estado Intermediário (Decisão)**: O momento de mudança/decisão de buscar a solução
  3. **Estado Aspiracional (Transformação)**: O cliente transformado após alcançar o resultado desejado

  {
    "visual": {
      "descricao_imagem": "OBRIGATÓRIO - Descrição em pt-BR narrando uma SEQUÊNCIA DE 3 IMAGENS/CENAS DISTINTAS que mostram a jornada do cliente: 1) Estado Atual (dor/frustração: descreva a cena específica mostrando o problema), 2) Estado Intermediário (decisão/mudança: descreva a cena mostrando o momento de ação/esperança), 3) Estado Aspiracional (transformação: descreva a cena mostrando o resultado alcançado). Use palavras como 'sequência', 'jornada', 'três imagens', '3 cenas' para deixar claro que são múltiplas imagens. NUNCA use 'imagem única' ou 'single image'.",

      "prompt_estado_atual": "OBRIGATÓRIO - Prompt técnico em inglês descrevendo APENAS o Estado Atual (dor). Descreva uma pessoa específica (idade, expressão facial de frustração/cansaço/desânimo, postura corporal derrotada ou tensa) em um cenário que reflita o problema (ambiente doméstico com elementos que simbolizam a luta, iluminação suave/dim que transmite dificuldade). Foque nas emoções negativas e na situação problemática. Nunca deixe este campo vazio ou null.",

      "prompt_estado_intermediario": "OBRIGATÓRIO - Prompt técnico em inglês descrevendo APENAS o Estado Intermediário (decisão/mudança). Mostre a MESMA PESSOA do estado anterior (mantendo idade, vestuário similar para continuidade visual) agora com expressão de determinação, esperança ou foco. A cena deve mostrar a ação imediata de mudança: pesquisando soluções, em consulta médica, conversando com profissional, ou tomando uma decisão clara. Iluminação mais clara/natural simbolizando a virada. Nunca deixe este campo vazio ou null.",

      "prompt_estado_aspiracional": "OBRIGATÓRIO - Prompt técnico em inglês descrevendo APENAS o Estado Aspiracional (transformação alcançada). Mostre a MESMA PESSOA dos estados anteriores (continuidade visual) agora radiante, confiante, com expressão genuína de alegria/satisfação. Postura ereta, energia visível. Cenário que reflita o sucesso alcançado (ambiente luminoso, externo com natureza, ou interno moderno e acolhedor). Foque nas emoções positivas e nos resultados visíveis da transformação. Nunca deixe este campo vazio ou null.",

      "aspect_ratio": "definido conforme especificação do formato (ex.: '4:5' para Feed, '9:16' para Reels/Stories)"
    },
    "formato": "{formato_anuncio}"
  }

  **VALIDAÇÃO INTERNA**: Antes de retornar o JSON, verifique:
  - [ ] `descricao_imagem` menciona "sequência", "jornada", "três imagens" ou "3 cenas"?
  - [ ] `prompt_estado_atual` está preenchido com descrição completa em inglês?
  - [ ] `prompt_estado_intermediario` está preenchido com descrição completa em inglês?
  - [ ] `prompt_estado_aspiracional` está preenchido com descrição completa em inglês?
  - [ ] Todos os 3 prompts descrevem a MESMA PESSOA em diferentes momentos da jornada?

  Se qualquer item acima for "não", CORRIJA antes de retornar o JSON.
```

### 3.5. Racional das Mudanças

| Mudança | Justificativa |
|---------|---------------|
| Adicionar bloco **"IMPORTANTE"** no início | Chama atenção para a criticidade deste fragmento |
| Usar **"OBRIGATÓRIO"** em todos os campos | Remove qualquer ambiguidade sobre opcionalidade |
| Explicar a jornada StoryBrand (1, 2, 3) | Contextualiza o modelo sobre o que representar em cada estado |
| Detalhar cada prompt (pessoa, expressão, postura, cenário, iluminação) | Fornece template claro do que incluir, reduzindo chance de omissão |
| Proibir explicitamente "imagem única" | Previne o padrão problemático identificado no fallback |
| Adicionar checklist de validação interna | Incentiva auto-correção antes de retornar o JSON |
| Remover `...` | Elimina interpretação de "exemplo" ou "continuar..." |

### 3.6. Impacto Esperado

✅ O modelo sempre gerará `descricao_imagem` com "sequência de 3 imagens"
✅ Os 3 prompts serão sempre preenchidos, mesmo com contexto desequilibrado
✅ Redução de 66% para 0% nas variações com prompts ausentes

---

## 4. Modificação 2: `code_reviewer` (Linhas 1140-1201)

### 4.1. Localização Exata

**Arquivo**: `app/agent.py`
**Agente**: `code_reviewer`
**Linhas**: 1179-1187 (seção VISUAL_DRAFT dentro da instrução completa)

### 4.2. Instrução Atual (Antes)

```python
- VISUAL_DRAFT:
  * Descrição visual com gancho, contexto e elementos on-screen
  * Narrativa deve mostrar a sequência: estado_atual (dor) → estado_intermediario (decisão imediata/mudança) → estado_aspiracional (transformação) mantendo coerência com a persona/contexto
  * Incluir prompts técnicos em inglês (`prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional`) alinhados à narrativa e mostrando evolução honesta
  * Aspect ratio coerente com o formato (conforme {format_specs_json}); aparência nativa do posicionamento
```

### 4.3. Problemas Identificados

1. ❌ Usa palavra fraca "Incluir" (não é imperativo)
2. ❌ Não valida explicitamente se os campos são `null` ou vazios
3. ❌ Não tem regra de reprovação automática para campos ausentes
4. ❌ Não verifica se `descricao_imagem` menciona "imagem única"

### 4.4. Instrução Nova (Depois)

```python
- VISUAL_DRAFT:

  **CRITÉRIOS DE REPROVAÇÃO AUTOMÁTICA** (grade = "fail"):

  1. **Campos Obrigatórios Ausentes**:
     - Se `prompt_estado_atual` é null, vazio, ou ausente → REPROVAR
     - Se `prompt_estado_intermediario` é null, vazio, ou ausente → REPROVAR
     - Se `prompt_estado_aspiracional` é null, vazio, ou ausente → REPROVAR
     - Se `descricao_imagem` é null, vazia, ou ausente → REPROVAR
     - Comentário: "VISUAL_DRAFT reprovado: campo(s) obrigatório(s) ausente(s) ou null. Todos os 3 prompts (estado_atual, estado_intermediario, estado_aspiracional) devem estar preenchidos."

  2. **Descrição Incorreta**:
     - Se `descricao_imagem` contém "imagem única", "single image", "uma imagem" (singular) → REPROVAR
     - Se `descricao_imagem` NÃO menciona "sequência", "jornada", "três imagens", "3 cenas" ou equivalente → REPROVAR
     - Comentário: "VISUAL_DRAFT reprovado: descricao_imagem deve descrever uma SEQUÊNCIA de 3 imagens distintas (estado atual → intermediário → aspiracional), não uma imagem única."

  3. **Narrativa Incompleta**:
     - Se os 3 prompts não representam claramente uma progressão (dor → decisão → transformação) → REPROVAR
     - Se os 3 prompts não descrevem a MESMA PESSOA em momentos diferentes → REPROVAR
     - Comentário: "VISUAL_DRAFT reprovado: os 3 prompts devem mostrar a jornada da mesma pessoa através dos 3 estados do StoryBrand (dor atual → decisão de mudar → transformação alcançada)."

  **CRITÉRIOS DE APROVAÇÃO** (grade = "pass"):

  Somente aprovar se TODOS os itens abaixo forem verdadeiros:

  * ✅ `descricao_imagem` menciona explicitamente "sequência", "jornada", "três imagens/cenas" ou "3 imagens/cenas"
  * ✅ `descricao_imagem` descreve claramente 3 momentos distintos: 1) dor/frustração, 2) decisão/mudança, 3) transformação/sucesso
  * ✅ `prompt_estado_atual` está preenchido com descrição completa em inglês mostrando dor/problema
  * ✅ `prompt_estado_intermediario` está preenchido com descrição completa em inglês mostrando decisão/ação
  * ✅ `prompt_estado_aspiracional` está preenchido com descrição completa em inglês mostrando transformação
  * ✅ Os 3 prompts mantêm continuidade visual (mesma pessoa, idade consistente, vestuário similar)
  * ✅ Os 3 prompts são tecnicamente acionáveis para IA de geração de imagens (descrevem pessoa, expressão, postura, cenário, iluminação)
  * ✅ `aspect_ratio` está correto conforme {format_specs_json}
  * ✅ Conteúdo visual alinhado com {landing_page_context} (persona, dores, benefícios)

  **IMPORTANTE**: Este agente é a última linha de defesa antes da aprovação do snippet. Seja rigoroso. Se houver QUALQUER dúvida sobre a completude dos prompts, reprove e solicite correção.
```

### 4.5. Racional das Mudanças

| Mudança | Justificativa |
|---------|---------------|
| Criar seção **"CRITÉRIOS DE REPROVAÇÃO AUTOMÁTICA"** | Torna as regras de validação explícitas e não-ambíguas |
| Listar cada campo obrigatório individualmente | Permite validação field-by-field, sem interpretação |
| Adicionar validação de palavras-chave ("imagem única") | Previne o padrão problemático identificado no fallback |
| Exigir menção de "sequência" ou equivalente | Garante que o conceito de múltiplas imagens está presente |
| Criar seção **"CRITÉRIOS DE APROVAÇÃO"** com checklist | Fornece template claro do que verificar antes de aprovar |
| Adicionar nota "última linha de defesa" | Reforça a responsabilidade crítica deste agente |

### 4.6. Impacto Esperado

✅ Snippets com prompts `null` serão **sempre reprovados**
✅ `code_refiner` será invocado para corrigir
✅ Nenhum snippet incompleto chegará ao `final_assembler`

---

## 5. Modificação 3: `code_refiner` (Linhas 1203-1217)

### 5.1. Localização Exata

**Arquivo**: `app/agent.py`
**Agente**: `code_refiner`
**Linhas**: 1207-1214 (instrução completa)

### 5.2. Instrução Atual (Antes)

```python
## IDENTIDADE: Ads Refinement Specialist

Tarefas:
1) Aplique TODAS as correções do review {code_review_result} ao fragmento {generated_code}.
2) Se houver `follow_up_queries`, execute-as via `google_search` e incorpore boas práticas.
3) Retorne o **mesmo fragmento** corrigido em **JSON válido**.
```

### 5.3. Problemas Identificados

1. ❌ Não tem instrução específica sobre VISUAL_DRAFT
2. ❌ Depende 100% do comentário do `code_review_result` para saber o que corrigir
3. ❌ Não tem orientação sobre onde buscar informação para completar campos ausentes

### 5.4. Instrução Nova (Depois)

```python
## IDENTIDADE: Ads Refinement Specialist

Tarefas:
1) Aplique TODAS as correções do review {code_review_result} ao fragmento {generated_code}.
2) Se houver `follow_up_queries`, execute-as via `google_search` e incorpore boas práticas.
3) Retorne o **mesmo fragmento** corrigido em **JSON válido**.

**ATENÇÃO ESPECIAL PARA VISUAL_DRAFT**:

Se {current_task_info} indica categoria "VISUAL_DRAFT" e o review reprovou por campos ausentes ou null:

A) **Complete os prompts ausentes** usando as seguintes fontes do estado:
   - `prompt_estado_atual`: Baseie-se em {landing_page_context}.storybrand_dores (descreva a frustração/dor específica)
   - `prompt_estado_intermediario`: Baseie-se em {landing_page_context}.storybrand_proposta e storybrand_cta_principal (mostre decisão/ação)
   - `prompt_estado_aspiracional`: Baseie-se em {landing_page_context}.storybrand_beneficios e storybrand_transformacao (mostre resultado)

B) **Corrija a descricao_imagem** se necessário:
   - Se contém "imagem única" ou similar, reescreva para "SEQUÊNCIA de 3 imagens mostrando: 1) [estado atual com dor], 2) [decisão de mudar], 3) [transformação alcançada]"
   - Garanta que menciona "sequência", "jornada" ou "três imagens/cenas"

C) **Mantenha continuidade visual**:
   - Os 3 prompts devem descrever a MESMA PESSOA (use "the same woman/man" nos prompts intermediário e aspiracional)
   - Mantenha idade, tipo físico e vestuário similar entre os 3 estados

D) **Formato dos prompts em inglês**:
   - Use descrições técnicas adequadas para image generation AI (person description, facial expression, body posture, setting, lighting, mood, aspect ratio)
   - Exemplo: "A middle-aged woman, 40s, with a frustrated expression, sitting at home looking at clothes that don't fit. Dim lighting, subdued colors. Aspect ratio 4:5."

E) **Validação antes de retornar**:
   - NUNCA retorne um fragmento VISUAL_DRAFT com qualquer campo null ou vazio
   - Se não conseguir completar algum prompt com informação suficiente do contexto, use placeholder genérico mas SEMPRE preencha

**IMPORTANTE**: Este agente é responsável por garantir que nenhum VISUAL_DRAFT incompleto seja aprovado. Complete obrigatoriamente todos os campos.
```

### 5.5. Racional das Mudanças

| Mudança | Justificativa |
|---------|---------------|
| Adicionar seção **"ATENÇÃO ESPECIAL PARA VISUAL_DRAFT"** | Fornece instruções específicas para este caso crítico |
| Mapear cada prompt para fonte de dados | Orienta onde buscar informação para completar campos |
| Fornecer template de correção de `descricao_imagem` | Remove ambiguidade sobre como corrigir |
| Instruir sobre continuidade visual | Garante coerência entre os 3 prompts |
| Fornecer exemplo de formato de prompt em inglês | Mostra o padrão esperado |
| Proibir explicitamente retornar campos null | Torna a responsabilidade absoluta |

### 5.6. Impacto Esperado

✅ Todos os prompts ausentes serão completados na etapa de refinamento
✅ Snippets reprovados pelo reviewer serão corrigidos de forma determinística
✅ Nenhum snippet com campos `null` passará do loop de revisão

---

## 6. Modificação 4: `final_assembler` (Linhas 1572-1592)

### 6.1. Localização Exata

**Arquivo**: `app/agent.py`
**Variável**: `final_assembler_instruction`
**Linhas**: 1572-1592

### 6.2. Instrução Atual (Antes)

```python
final_assembler_instruction = """
## IDENTIDADE: Final Ads Assembler

Monte **3 variações** de anúncio combinando `approved_code_snippets`.

Campos obrigatórios (saída deve ser uma LISTA com 3 OBJETOS):
- "landing_page_url": usar {landing_page_url} (se vazio, inferir do briefing coerentemente)
- "formato": usar {formato_anuncio} especificado pelo usuário
- "copy": { "headline", "corpo", "cta_texto" } (COPY_DRAFT refinado - CRIAR 3 VARIAÇÕES)
- "visual": { "descricao_imagem", "prompt_estado_atual", "prompt_estado_intermediario", "prompt_estado_aspiracional", "aspect_ratio" } (sem duração - apenas imagens)
- "cta_instagram": do COPY_DRAFT
- "fluxo": coerente com {objetivo_final}, por padrão "Instagram Ad → Landing Page → Botão WhatsApp"
- "referencia_padroes": do RESEARCH
- "contexto_landing": resumo do {landing_page_context}

Regras:
- Criar 3 variações diferentes de copy e visual reutilizando os snippets aprovados sempre que possível.
- Complete faltantes de forma conservadora.
- Se um "foco" foi definido, garanta que as variações respeitam e comunicam o tema.
- **Saída**: apenas JSON válido (sem markdown).
"""
```

### 6.3. Problemas Identificados

1. ❌ Instrução ambígua "Complete faltantes de forma conservadora" pode ser interpretada como "manter null"
2. ❌ Não enfatiza que prompts null são **inaceitáveis** na saída final
3. ❌ Não instrui sobre como completar campos ausentes se o snippet aprovado estiver incompleto (cenário improvável após as correções anteriores, mas importante como última linha de defesa)

### 6.4. Instrução Nova (Depois)

```python
final_assembler_instruction = """
## IDENTIDADE: Final Ads Assembler

Monte **3 variações** de anúncio combinando `approved_code_snippets`.

Campos obrigatórios (saída deve ser uma LISTA com 3 OBJETOS):
- "landing_page_url": usar {landing_page_url} (se vazio, inferir do briefing coerentemente)
- "formato": usar {formato_anuncio} especificado pelo usuário
- "copy": { "headline", "corpo", "cta_texto" } (COPY_DRAFT refinado - CRIAR 3 VARIAÇÕES)
- "visual": { "descricao_imagem", "prompt_estado_atual", "prompt_estado_intermediario", "prompt_estado_aspiracional", "aspect_ratio" }

  **IMPORTANTE SOBRE VISUAL**: TODOS os 5 campos de visual são OBRIGATÓRIOS e NUNCA podem ser null ou vazios nas 3 variações.
  - "descricao_imagem": DEVE descrever uma sequência de 3 imagens mostrando a jornada do cliente
  - "prompt_estado_atual": DEVE descrever o estado de dor/frustração em inglês
  - "prompt_estado_intermediario": DEVE descrever o momento de decisão/mudança em inglês
  - "prompt_estado_aspiracional": DEVE descrever o estado transformado em inglês
  - "aspect_ratio": DEVE ser coerente com o formato (ex.: "4:5" para Feed, "9:16" para Reels/Stories)

- "cta_instagram": do COPY_DRAFT
- "fluxo": coerente com {objetivo_final}, por padrão "Instagram Ad → Landing Page → Botão WhatsApp"
- "referencia_padroes": do RESEARCH
- "contexto_landing": resumo do {landing_page_context}

Regras:
- Criar 3 variações diferentes de copy e visual reutilizando os snippets VISUAL_DRAFT aprovados sempre que possível.

- **TRATAMENTO DE CAMPOS VISUAL AUSENTES** (última linha de defesa):

  Se algum snippet VISUAL_DRAFT aprovado tiver campos null ou vazios (cenário improvável, mas possível), você DEVE completá-los obrigatoriamente:

  * `prompt_estado_atual`: Gere baseado em {landing_page_context}.storybrand_dores
    Exemplo: "A frustrated [target persona], [age], with tired expression, sitting at home struggling with [specific problem]. Dim lighting, subdued mood. Aspect ratio [format]."

  * `prompt_estado_intermediario`: Gere baseado em {landing_page_context}.storybrand_proposta e storybrand_cta_principal
    Exemplo: "The same person, now with determined expression, taking action: [specific action like consulting doctor, researching solutions]. Brighter lighting, hopeful mood. Aspect ratio [format]."

  * `prompt_estado_aspiracional`: Gere baseado em {landing_page_context}.storybrand_beneficios e storybrand_transformacao
    Exemplo: "The same person, now radiant and confident, [specific result achieved]. Bright, joyful setting. Full of energy and self-assurance. Aspect ratio [format]."

  * `descricao_imagem`: Se ausente ou mencionar "imagem única", reescreva como:
    "Sequência de 3 imagens mostrando a jornada: 1) [pessoa] enfrentando [dor específica], 2) [pessoa] decidindo buscar [solução], 3) [pessoa] transformada com [resultado alcançado]."

- **VALIDAÇÃO OBRIGATÓRIA ANTES DE RETORNAR**:

  Para CADA uma das 3 variações, verifique:
  - [ ] `visual.descricao_imagem` está preenchida e menciona "sequência" ou equivalente?
  - [ ] `visual.prompt_estado_atual` está preenchido (não null, não vazio)?
  - [ ] `visual.prompt_estado_intermediario` está preenchido (não null, não vazio)?
  - [ ] `visual.prompt_estado_aspiracional` está preenchido (não null, não vazio)?
  - [ ] `visual.aspect_ratio` está preenchido e correto?

  Se QUALQUER checklist falhar para QUALQUER variação, COMPLETE obrigatoriamente antes de retornar o JSON.

- Se um "foco" foi definido, garanta que as variações respeitam e comunicam o tema.

- **Saída**: apenas JSON válido (sem markdown). Array com exatamente 3 objetos. NUNCA retorne menos de 3 variações completas.

**COMPROMISSO DE QUALIDADE**: Este é o último agente antes da persistência. A saída DEVE ser perfeita. Nenhuma variação pode ter campos visual ausentes ou null.
"""
```

### 6.5. Racional das Mudanças

| Mudança | Justificativa |
|---------|---------------|
| Adicionar bloco **"IMPORTANTE SOBRE VISUAL"** | Enfatiza a criticidade dos campos visuais |
| Listar os 5 campos de visual individualmente | Remove ambiguidade sobre o que é obrigatório |
| Criar seção **"TRATAMENTO DE CAMPOS VISUAL AUSENTES"** | Fornece última linha de defesa caso algo passe pelos agentes anteriores |
| Mapear cada prompt ausente para fonte de dados | Orienta geração de conteúdo quando necessário |
| Fornecer templates/exemplos de prompts | Remove ambiguidade sobre formato esperado |
| Adicionar **"VALIDAÇÃO OBRIGATÓRIA"** com checklist | Força auto-verificação antes de retornar |
| Remover "Complete faltantes de forma conservadora" | Elimina instrução ambígua que incentivava manter null |
| Adicionar **"COMPROMISSO DE QUALIDADE"** | Reforça responsabilidade final deste agente |

### 6.6. Impacto Esperado

✅ Mesmo se snippets incompletos chegarem (improvável), serão completados aqui
✅ 100% das variações terão todos os 5 campos de visual preenchidos
✅ Garantia absoluta de que nenhum JSON final terá prompts `null`

---

## 7. Resumo das Modificações

### Arquivos Afetados

| Arquivo | Linhas Modificadas | Tipo de Mudança |
|---------|-------------------|-----------------|
| `app/agent.py` | 1108-1118 (dentro de 1056-1138) | Substituição da instrução VISUAL_DRAFT do `code_generator` |
| `app/agent.py` | 1179-1187 (dentro de 1140-1201) | Substituição da instrução VISUAL_DRAFT do `code_reviewer` |
| `app/agent.py` | 1207-1214 (dentro de 1203-1217) | Expansão da instrução do `code_refiner` |
| `app/agent.py` | 1572-1592 | Substituição completa de `final_assembler_instruction` |

**Total**: 1 arquivo, 4 modificações de strings de instrução

---

## 8. Estratégia de Implementação

### 8.1. Ordem de Modificação (Sequencial)

**Fase 1: Gerador**
1. Modificar `code_generator` (linhas 1108-1118)
2. Testar isoladamente: forçar fallback e verificar se gera os 3 prompts

**Fase 2: Revisor**
3. Modificar `code_reviewer` (linhas 1179-1187)
4. Testar: verificar se reprova snippets com null

**Fase 3: Refinador**
5. Modificar `code_refiner` (linhas 1207-1214)
6. Testar: verificar se completa prompts reprovados

**Fase 4: Montador**
7. Modificar `final_assembler_instruction` (linhas 1572-1592)
8. Testar: verificar JSON final completo

### 8.2. Validação de Cada Fase

Após cada modificação:
1. Executar `make dev`
2. Testar com mesma landing page: `https://nutrologodivinopolis.com.br/feminino/`
3. Forçar fallback: `STORYBRAND_GATE_DEBUG=true`
4. Verificar JSON final: todos os 3 prompts preenchidos nas 3 variações

---

## 9. Critérios de Sucesso

### 9.1. Testes de Validação

**Teste 1: Caminho Feliz (sem fallback)**
- Input: Landing page real
- Fallback: Desativado
- Expectativa: 3 variações, cada uma com 3 prompts preenchidos (mantém comportamento atual)

**Teste 2: Fallback Forçado**
- Input: Mesma landing page
- Fallback: Forçado (`STORYBRAND_GATE_DEBUG=true`)
- Expectativa: 3 variações, cada uma com 3 prompts preenchidos (NOVO comportamento)

**Teste 3: Fallback Real (score baixo)**
- Input: Landing page com StoryBrand fraco
- Fallback: Ativado automaticamente (score < 0.6)
- Expectativa: 3 variações, cada uma com 3 prompts preenchidos

### 9.2. Métricas de Sucesso

| Métrica | Antes | Depois (Meta) |
|---------|-------|---------------|
| % de variações com 3 prompts preenchidos (caminho feliz) | 100% | 100% ✅ |
| % de variações com 3 prompts preenchidos (fallback) | 33% (1/3) | 100% ✅ |
| % de `descricao_imagem` com "imagem única" (fallback) | 66% (2/3) | 0% ✅ |
| % de snippets VISUAL_DRAFT reprovados pelo reviewer (fallback) | ~0% | ~50% → 0% após refiner ✅ |

### 9.3. Definição de "Pronto"

✅ Todas as 4 instruções modificadas
✅ Teste 1 passa (caminho feliz mantido)
✅ Teste 2 passa (fallback corrigido)
✅ Teste 3 passa (fallback real corrigido)
✅ 100% das variações têm 3 prompts preenchidos em todos os cenários
✅ 0% de "imagem única" em `descricao_imagem`

---

## 10. Riscos e Mitigações

### 10.1. Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| **R1**: Instruções muito longas aumentam latência do LLM | Baixa | Médio | Instruções são texto puro, impacto mínimo; benefício compensa |
| **R2**: `code_reviewer` muito rigoroso reprova casos válidos | Baixa | Alto | Testar extensivamente; ajustar critérios se necessário |
| **R3**: `code_refiner` não consegue completar prompts ausentes | Baixa | Médio | Instrução fornece templates e fontes de dados claras |
| **R4**: Mudanças afetam comportamento do caminho feliz | Baixa | Alto | Testar caminho feliz ANTES de modificar; garantir compatibilidade |
| **R5**: LLM ignora instruções longas | Média | Alto | Usar formatação clara (**bold**, listas, exemplos); validar empiricamente |

### 10.2. Plano de Rollback

Se após implementação os testes falharem:

1. **Rollback Imediato**: Reverter para instruções originais (git revert)
2. **Análise de Falha**: Identificar qual agente causou o problema
3. **Correção Incremental**: Re-implementar um agente por vez com testes

### 10.3. Monitoramento Pós-Implementação

Após implementação, monitorar por 1 semana:
- Taxa de reprovação do `code_reviewer` para VISUAL_DRAFT
- Taxa de sucesso do `code_refiner` em completar prompts
- Quantidade de variações com prompts `null` no JSON final (meta: 0)
- Latência média do pipeline (não deve aumentar >10%)

---

## 11. Implementação Técnica

### 11.1. Passos de Modificação

Para cada modificação:

1. **Localizar o trecho exato**:
   ```bash
   # Abrir arquivo
   vim app/agent.py

   # Buscar linha
   :1108  # Para code_generator
   :1179  # Para code_reviewer
   :1207  # Para code_refiner
   :1572  # Para final_assembler_instruction
   ```

2. **Selecionar o bloco da instrução**:
   - Para `code_generator`: Selecionar linhas 1108-1118 (seção VISUAL_DRAFT)
   - Para `code_reviewer`: Selecionar linhas 1179-1187 (seção VISUAL_DRAFT)
   - Para `code_refiner`: Selecionar linhas 1207-1214 (instrução completa)
   - Para `final_assembler_instruction`: Selecionar linhas 1572-1592 (variável completa)

3. **Substituir pela nova instrução**:
   - Copiar o texto "Instrução Nova (Depois)" da seção correspondente deste plano
   - Colar no lugar do texto original
   - Manter a indentação correta (3 espaços para strings dentro de `instruction="""`)

4. **Validar sintaxe**:
   ```bash
   # Verificar se o arquivo Python é válido
   python -m py_compile app/agent.py
   ```

5. **Reiniciar o servidor**:
   ```bash
   make dev
   ```

6. **Testar a modificação**:
   - Executar teste específico para o agente modificado
   - Verificar logs para confirmar nova instrução está sendo usada

### 11.2. Ordem de Implementação Recomendada

1. ✅ `code_generator` (mais crítico - previne geração incorreta)
2. ✅ `code_reviewer` (segunda camada - reprova geração incorreta)
3. ✅ `code_refiner` (terceira camada - corrige reprovações)
4. ✅ `final_assembler` (última camada - garante saída final correta)

**Racional**: Implementar em ordem de execução no pipeline garante que cada camada protege a seguinte.

---

## 12. Validação e Testes

### 12.1. Script de Teste Automatizado

Criar script `test_visual_prompts_completeness.py`:

```python
import json
import sys

def validate_visual_completeness(json_path: str) -> bool:
    """Valida se todas as variações têm os 3 prompts preenchidos."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) != 3:
        print(f"❌ Erro: JSON deve ser uma lista com 3 variações. Encontrado: {type(data)}, len={len(data) if isinstance(data, list) else 'N/A'}")
        return False

    all_valid = True
    for idx, variation in enumerate(data, 1):
        visual = variation.get('visual', {})

        # Validar campos obrigatórios
        required_fields = [
            'descricao_imagem',
            'prompt_estado_atual',
            'prompt_estado_intermediario',
            'prompt_estado_aspiracional',
            'aspect_ratio'
        ]

        missing = []
        null_or_empty = []

        for field in required_fields:
            if field not in visual:
                missing.append(field)
            elif visual[field] is None or visual[field] == '':
                null_or_empty.append(field)

        if missing:
            print(f"❌ Variação {idx}: campos ausentes: {', '.join(missing)}")
            all_valid = False

        if null_or_empty:
            print(f"❌ Variação {idx}: campos null ou vazios: {', '.join(null_or_empty)}")
            all_valid = False

        # Validar descricao_imagem
        descricao = visual.get('descricao_imagem', '')
        if descricao:
            keywords_bad = ['imagem única', 'single image', 'uma imagem']
            keywords_good = ['sequência', 'jornada', 'três imagens', '3 imagens', '3 cenas', 'três cenas']

            has_bad = any(bad in descricao.lower() for bad in keywords_bad)
            has_good = any(good in descricao.lower() for good in keywords_good)

            if has_bad:
                print(f"⚠️ Variação {idx}: descricao_imagem menciona 'imagem única' ou similar")
                all_valid = False

            if not has_good:
                print(f"⚠️ Variação {idx}: descricao_imagem NÃO menciona 'sequência', 'jornada' ou equivalente")
                all_valid = False

        if not missing and not null_or_empty:
            print(f"✅ Variação {idx}: Todos os campos preenchidos")

    return all_valid

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python test_visual_prompts_completeness.py <caminho_json>")
        sys.exit(1)

    json_path = sys.argv[1]
    success = validate_visual_completeness(json_path)

    if success:
        print("\n✅ SUCESSO: Todas as variações estão completas!")
        sys.exit(0)
    else:
        print("\n❌ FALHA: Algumas variações estão incompletas.")
        sys.exit(1)
```

Uso:
```bash
python test_visual_prompts_completeness.py artifacts/ads_final/TIMESTAMP_SESSION_Feed.json
```

### 12.2. Checklist de Testes Manuais

**Antes da Implementação**:
- [ ] Executar teste com fallback forçado e documentar taxa de falha atual (baseline)
- [ ] Salvar JSON de exemplo com prompts ausentes como referência

**Após Modificar `code_generator`**:
- [ ] Testar geração de VISUAL_DRAFT isoladamente
- [ ] Verificar se `descricao_imagem` sempre menciona "sequência"
- [ ] Verificar se todos os 3 prompts são gerados (não null)

**Após Modificar `code_reviewer`**:
- [ ] Criar snippet VISUAL_DRAFT com prompt null manualmente
- [ ] Verificar se reviewer reprova (grade = "fail")
- [ ] Verificar mensagem de erro no comentário

**Após Modificar `code_refiner`**:
- [ ] Forçar reprovação de VISUAL_DRAFT
- [ ] Verificar se refiner completa os prompts ausentes
- [ ] Verificar se snippet corrigido é aprovado na segunda iteração

**Após Modificar `final_assembler`**:
- [ ] Testar pipeline completo com fallback forçado
- [ ] Executar script de validação automático
- [ ] Verificar que 100% das variações têm 3 prompts preenchidos

**Testes de Regressão**:
- [ ] Testar caminho feliz (sem fallback) - garantir que mantém 100%
- [ ] Testar com diferentes landing pages
- [ ] Testar com diferentes formatos (Feed, Reels, Stories)

---

## 13. Cronograma Estimado

| Fase | Atividade | Duração Estimada | Responsável |
|------|-----------|------------------|-------------|
| **Fase 1** | Modificar instrução do `code_generator` | 15 min | Dev |
| | Testar isoladamente | 10 min | Dev |
| **Fase 2** | Modificar instrução do `code_reviewer` | 15 min | Dev |
| | Testar isoladamente | 10 min | Dev |
| **Fase 3** | Modificar instrução do `code_refiner` | 15 min | Dev |
| | Testar isoladamente | 10 min | Dev |
| **Fase 4** | Modificar instrução do `final_assembler` | 15 min | Dev |
| | Testar isoladamente | 10 min | Dev |
| **Fase 5** | Testes integrados | 30 min | Dev |
| | Criar script de validação | 20 min | Dev |
| | Executar bateria de testes | 30 min | Dev |
| **Fase 6** | Documentação e commit | 15 min | Dev |
| **Total** | | **3h 15min** | |

---

## 14. Documentação de Mudanças

### 14.1. Commit Message Template

```
fix(agent-instructions): tornar obrigatória sequência de 3 prompts visuais

Problema: Quando o fallback StoryBrand está ativo, 66% das variações
geradas têm apenas prompt_estado_aspiracional preenchido, deixando
prompt_estado_atual e prompt_estado_intermediario como null.

Causa: Instruções dos agentes não eram explícitas sobre a obrigatoriedade
dos 3 prompts e não validavam campos null.

Solução: Modificar instruções de 4 agentes em app/agent.py:

1. code_generator (L1108-1118):
   - Adicionar "OBRIGATÓRIO" em cada campo
   - Proibir explicitamente "imagem única"
   - Fornecer template detalhado de cada prompt
   - Adicionar checklist de validação interna

2. code_reviewer (L1179-1187):
   - Criar seção "CRITÉRIOS DE REPROVAÇÃO AUTOMÁTICA"
   - Validar explicitamente se campos são null
   - Reprovar se descricao_imagem menciona "imagem única"

3. code_refiner (L1207-1214):
   - Adicionar seção "ATENÇÃO ESPECIAL PARA VISUAL_DRAFT"
   - Mapear cada prompt ausente para fonte de dados
   - Instruir sobre como completar campos null

4. final_assembler_instruction (L1572-1592):
   - Adicionar seção "TRATAMENTO DE CAMPOS VISUAL AUSENTES"
   - Remover instrução ambígua "Complete conservadoramente"
   - Adicionar checklist de validação obrigatória

Resultado esperado:
- 100% das variações com 3 prompts preenchidos (vs 33% atual no fallback)
- 0% de descricao_imagem com "imagem única" (vs 66% atual)

Refs: #ISSUE_NUMBER
```

### 14.2. Atualização do CLAUDE.md

Adicionar seção ao `CLAUDE.md`:

```markdown
## Instruções dos Agentes: Obrigatoriedade de 3 Prompts Visuais

**Data da Modificação**: [DATA]

**Contexto**: As instruções dos agentes `code_generator`, `code_reviewer`, `code_refiner` e `final_assembler` foram modificadas para garantir que **TODAS as variações** de anúncios gerados contenham **EXATAMENTE 3 prompts de imagem distintos**:

1. `prompt_estado_atual`: Estado de dor/frustração
2. `prompt_estado_intermediario`: Momento de decisão/mudança
3. `prompt_estado_aspiracional`: Transformação alcançada

**Comportamento Esperado**:
- ✅ `descricao_imagem` sempre menciona "sequência", "jornada" ou "3 imagens"
- ✅ Todos os 3 prompts preenchidos (nunca null ou vazio)
- ✅ Continuidade visual entre os 3 estados (mesma pessoa)

**Validação**:
- `code_reviewer` reprova automaticamente se qualquer prompt é null
- `code_refiner` completa prompts ausentes usando landing_page_context
- `final_assembler` valida obrigatoriamente antes de retornar JSON final

**Localização das Instruções**: `app/agent.py`
- `code_generator`: L1108-1118 (dentro de L1056-1138)
- `code_reviewer`: L1179-1187 (dentro de L1140-1201)
- `code_refiner`: L1207-1214 (dentro de L1203-1217)
- `final_assembler_instruction`: L1572-1592

**Validação de Saída**:
```bash
python test_visual_prompts_completeness.py artifacts/ads_final/JSON_FILE.json
```
```

---

## 15. Conclusão

### 15.1. Resumo das Mudanças

Este plano modifica **apenas as instruções (strings)** de 4 agentes em `app/agent.py` para tornar **absolutamente explícito e obrigatório** que:

1. A `descricao_imagem` descreve uma **sequência de 3 imagens**
2. Os 3 prompts são **OBRIGATÓRIOS e NUNCA null**
3. O `code_reviewer` **reprova automaticamente** campos ausentes
4. O `code_refiner` **completa obrigatoriamente** prompts ausentes
5. O `final_assembler` **valida e completa** como última linha de defesa

### 15.2. Impacto Esperado

**Antes**:
- Fallback: 33% das variações com 3 prompts (1/3)
- Fallback: 66% das variações com "imagem única" (2/3)

**Depois**:
- Fallback: **100% das variações com 3 prompts** (3/3)
- Fallback: **0% com "imagem única"** (0/3)
- Caminho feliz: Mantém 100% (sem regressão)

### 15.3. Garantias de Qualidade

✅ **Camada 1 (Geração)**: `code_generator` gera sempre os 3 prompts
✅ **Camada 2 (Revisão)**: `code_reviewer` reprova se null
✅ **Camada 3 (Refinamento)**: `code_refiner` completa ausentes
✅ **Camada 4 (Montagem)**: `final_assembler` valida e garante saída perfeita

### 15.4. Próximos Passos

1. ✅ Revisar e aprovar este plano
2. ⏳ Implementar modificações seguindo a ordem recomendada
3. ⏳ Executar testes de validação após cada fase
4. ⏳ Executar testes integrados finais
5. ⏳ Documentar e commitar mudanças
6. ⏳ Monitorar comportamento em produção por 1 semana

---

## 16. Aprovação e Sign-off

**Plano Criado Por**: Claude (Agent)
**Data de Criação**: [DATA_ATUAL]
**Versão do Plano**: 1.0

**Aprovação Necessária**:
- [ ] Desenvolvedor/Product Owner
- [ ] Validação técnica das instruções
- [ ] Aprovação para implementação

**Notas Finais**:

Este plano foi criado após análise detalhada do comportamento atual do sistema e das causas raiz dos prompts ausentes. As modificações propostas são **não-invasivas** (apenas instruções), **testáveis** (script de validação) e **reversíveis** (git revert). O impacto esperado é **eliminação completa** do problema identificado sem afetar o caminho feliz.
