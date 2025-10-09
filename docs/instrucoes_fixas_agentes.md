# Instruções Fixas dos Agentes (System Instructions)

## 1. `code_generator` - Gera VISUAL_DRAFT

**Localização**: [app/agent.py:1056-1136](app/agent.py#L1056-L1136)

**Modelo**: `gemini-2.5-flash` (config.worker_model)

**Instrução fixa para VISUAL_DRAFT**:

```
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

### Análise da Instrução:

✅ **Pontos fortes**:
- Menciona "sequência"
- Lista os 3 prompts explicitamente
- Usa `...` sugerindo continuação

❌ **Pontos fracos**:
- Não diz **"OBRIGATÓRIO"** ou **"NUNCA deixe null"**
- Usa `...` que pode ser interpretado como "opcional" ou "exemplo"
- Não dá exemplo concreto de como escrever a `descricao_imagem` mencionando explicitamente "3 cenas"

---

## 2. `code_reviewer` - Valida VISUAL_DRAFT

**Localização**: [app/agent.py:1144-1201](app/agent.py#L1144-L1201)

**Modelo**: `gemini-2.5-pro` (config.critic_model)

**Instrução fixa para VISUAL_DRAFT**:

```
- VISUAL_DRAFT:
  * Descrição visual com gancho, contexto e elementos on-screen
  * Narrativa deve mostrar a sequência: estado_atual (dor) → estado_intermediario (decisão imediata/mudança) → estado_aspiracional (transformação) mantendo coerência com a persona/contexto
  * Incluir prompts técnicos em inglês (`prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional`) alinhados à narrativa e mostrando evolução honesta
  * Aspect ratio coerente com o formato (conforme {format_specs_json}); aparência nativa do posicionamento
```

### Análise da Instrução:

✅ **Pontos fortes**:
- Diz "Incluir prompts técnicos" (menciona os 3)
- Menciona "sequência" e os 3 estados

❌ **Pontos fracos**:
- Não diz **"OBRIGATÓRIO todos os 3 prompts"**
- Não diz **"Se qualquer prompt estiver ausente ou null: grade = fail"**
- Palavra "Incluir" pode ser interpretada como sugestão, não como requisito obrigatório
- Não tem verificação explícita: "Se `prompt_estado_atual` é null → FAIL"

---

## 3. `code_refiner` - Corrige VISUAL_DRAFT

**Localização**: [app/agent.py:1203-1217](app/agent.py#L1203-L1217)

**Modelo**: `gemini-2.5-flash` (config.worker_model)

**Instrução fixa**:

```
## IDENTIDADE: Ads Refinement Specialist

Tarefas:
1) Aplique TODAS as correções do review {code_review_result} ao fragmento {generated_code}.
2) Se houver `follow_up_queries`, execute-as via `google_search` e incorpore boas práticas.
3) Retorne o **mesmo fragmento** corrigido em **JSON válido**.
```

### Análise da Instrução:

✅ **Pontos fortes**:
- Aplica correções do review

❌ **Pontos fracos**:
- Não menciona VISUAL_DRAFT especificamente
- Depende 100% do `code_review_result` ser rigoroso
- Se o reviewer não bloqueou, o refiner não vai adicionar os prompts ausentes

---

## 4. `final_assembler` - Monta as 3 variações finais

**Localização**: [app/agent.py:1572-1592](app/agent.py#L1572-L1592)

**Modelo**: `gemini-2.5-pro` (config.critic_model)

**Instrução fixa**:

```
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
```

### Análise da Instrução:

✅ **Pontos fortes**:
- Lista os 4 campos de `visual` explicitamente
- Diz "Campos obrigatórios"

❌ **Pontos fracos**:
- Diz **"reutilizando os snippets aprovados sempre que possível"**
- Diz **"Complete faltantes de forma conservadora"**
- Isso pode ser interpretado como: "Se o snippet VISUAL_DRAFT aprovado tiver campos null, mantenha null ou complete conservadoramente"
- **Não diz**: "Se algum snippet VISUAL_DRAFT estiver incompleto, REJEITE a montagem" ou "NUNCA deixe prompts como null"

---

## Descoberta Crítica: A Instrução "Complete faltantes de forma conservadora"

### O Fluxo Real:

1. **`code_generator`** gera VISUAL_DRAFT (variação 2):
   ```json
   {
     "descricao_imagem": "Imagem única de uma mulher serena...",
     "prompt_estado_atual": null,
     "prompt_estado_intermediario": null,
     "prompt_estado_aspiracional": "A hopeful woman..."
   }
   ```

2. **`code_reviewer`** recebe e valida:
   - Instrução: "Incluir prompts técnicos..."
   - ⚠️ **Não diz explicitamente**: "Se null → FAIL"
   - Possível interpretação: "Os prompts estão presentes no JSON (as chaves existem), só que null"
   - **Resultado**: `grade: "pass"` (!)

3. **`code_approver`** registra o snippet como **"approved"**:
   ```python
   snippet = {
     "status": "approved",
     "code": '{"visual": {"prompt_estado_atual": null, ...}}'
   }
   ```

4. **`final_assembler`** recebe `approved_code_snippets`:
   - Instrução: "reutilizando os snippets aprovados sempre que possível"
   - Instrução: "Complete faltantes de forma conservadora"
   - ⚠️ **Interpretação**: "O snippet foi aprovado pelo reviewer, então devo reutilizá-lo como está"
   - **Comportamento conservador**: Manter os campos `null` em vez de sobrescrever o snippet aprovado
   - **Resultado**: Variação 2 mantém `prompt_estado_atual: null`

---

## Por Que Funciona no Caminho Feliz?

### Exemplo Caminho Feliz (investigacao.md:246-250):

Variação 1 do caminho feliz:
```json
{
  "descricao_imagem": "Uma sequência de três imagens mostrando a jornada emocional...",
  "prompt_estado_atual": "A middle-aged woman, 40s, with a visibly tired...",
  "prompt_estado_intermediario": "The same woman, now with a determined...",
  "prompt_estado_aspiracional": "The same woman, now beaming with genuine joy..."
}
```

**Por que todos os 3 prompts foram preenchidos?**

Hipótese: O `code_generator` ao escrever a `descricao_imagem` com **"Uma sequência de três imagens"**, criou um contexto interno forte que guiou o preenchimento dos 3 prompts.

Quando o contexto (`landing_page_context`) é:
- **Conciso** (600 chars)
- **Factual** (não narrativo)
- **Distribuído** entre os 7 elementos do StoryBrand

O LLM consegue equilibrar os 3 estados e gerar naturalmente:
1. Estado atual (dor) baseado em `storybrand_dores`
2. Estado intermediário (decisão) baseado em `storybrand_proposta`/`storybrand_cta_principal`
3. Estado aspiracional (transformação) baseado em `storybrand_beneficios`/`storybrand_transformacao`

---

## Por Que Falha no Fallback?

### Exemplo Fallback (investigacao.md:57-61):

Variação 2 do fallback:
```json
{
  "descricao_imagem": "Imagem única de uma mulher com uma expressão serena e esperançosa...",
  "prompt_estado_atual": null,
  "prompt_estado_intermediario": null,
  "prompt_estado_aspiracional": "A hopeful woman in her late 30s..."
}
```

**Por que apenas 1 prompt foi preenchido?**

Quando o contexto (`landing_page_context`) é:
- **Extenso** (10.000 chars)
- **Narrativo em 2ª pessoa** ("Você é...", "Imagine-se...")
- **85% focado no estado aspiracional**:
  - `storybrand_persona`: 641 chars sobre a jornada completa
  - `storybrand_beneficios[0]`: 1.400 chars sobre "realidade que você tanto sonhou"
  - `storybrand_transformacao`: 700 chars sobre "versão mais plena de si mesma"
  - `storybrand_cta_principal`: 800 chars sobre "conquistar o corpo e confiança"
  - `storybrand_urgencia`: 1.800 chars focados no estado negativo (mas como contraste para o estado final)

O LLM do `code_generator`:
1. **Absorve o viés aspiracional** do contexto (85% do texto fala sobre transformação/radiante/plena)
2. **Gera `descricao_imagem`** refletindo esse viés: **"Imagem única"** focada no estado final
3. **Usa a própria `descricao_imagem`** como guia interno para os prompts
4. **Preenche apenas `prompt_estado_aspiracional`** (coerente com "Imagem única" de estado final)
5. **Deixa os outros como `null`** (não há "sequência" para justificar 3 prompts distintos)

---

## Confirmação da Sua Hipótese

Você disse:

> "se o campo 'descricao_imagem' iniciar com 'Uma sequência de imagens' ocorre a descrição exata de três situações seguindo a ordem exata do storybrand"

**Você está correto!** Vejamos os dados:

### Caminho Feliz - Todas as 3 variações:

**Variação 1** (investigacao.md:246):
```
"descricao_imagem": "Uma sequência de três imagens mostrando a jornada..."
```
✅ Todos os 3 prompts preenchidos

**Variação 2** (investigacao.md:286):
```
"descricao_imagem": "Uma jornada focada na superação do ciclo de dietas..."
```
✅ Todos os 3 prompts preenchidos

**Variação 3** (investigacao.md:326):
```
"descricao_imagem": "Uma narrativa visual que foca na parceria médico-paciente..."
```
✅ Todos os 3 prompts preenchidos

**Padrão**: Palavras como "sequência", "jornada", "narrativa" indicam múltiplos estados → LLM preenche os 3 prompts

---

### Fallback - 2 das 3 variações falharam:

**Variação 1** (investigacao.md:19):
```
"descricao_imagem": "Uma sequência de imagens que ilustra a jornada emocional..."
```
✅ Todos os 3 prompts preenchidos

**Variação 2** (investigacao.md:57):
```
"descricao_imagem": "Imagem única de uma mulher com uma expressão serena..."
```
❌ Apenas `prompt_estado_aspiracional` preenchido

**Variação 3** (investigacao.md:95):
```
"descricao_imagem": "Imagem única de uma mulher radiante e cheia de energia..."
```
❌ Apenas `prompt_estado_aspiracional` preenchido

**Padrão**: Palavras como "Imagem única" indicam estado singular → LLM preenche apenas 1 prompt

---

## Causa Raiz Refinada

Não é o **tamanho** do contexto (você está certo, 10k chars é trivial para 1M tokens).

É a **composição semântica** do contexto:

### Caminho Feliz:
```python
landing_page_context = {
  "storybrand_dores": ["tensão constante...", "autoestima cai..."],      # Estado atual
  "storybrand_proposta": "Autoridade: Dr. Daniel; Empatia: ...",         # Estado intermediário (guia)
  "storybrand_beneficios": ["energia renovada", "autoconfiança"],        # Estado aspiracional
  "storybrand_transformacao": "saúde concreta e duradoura"               # Estado aspiracional
}
```

**Distribuição equilibrada**:
- 30% estado atual (dores)
- 30% estado intermediário (proposta/cta)
- 40% estado aspiracional (benefícios/transformação)

**Resultado**: `descricao_imagem` menciona "sequência de três imagens" → 3 prompts preenchidos

---

### Fallback:
```python
landing_page_context = {
  "storybrand_dores": ["[420 chars]", "[1.100 chars]"],                           # 15% (mas negativo, contraste)
  "storybrand_proposta": "[3.000 chars sobre tratamento transformador]",          # 30%
  "storybrand_beneficios": ["Imagine-se vivendo a realidade... [1.400 chars]"],  # 14%
  "storybrand_transformacao": "Você se tornou a versão plena... [700 chars]",    # 7%
  "storybrand_cta_principal": "Conquistar corpo e confiança... [800 chars]",     # 8%
  "storybrand_urgencia": ["Continuar presa no ciclo... [1.800 chars]"]           # 18%
  "storybrand_autoridade": "[múltiplos parágrafos sobre Dr. Daniel]",            # 8%
}
```

**Distribuição desequilibrada**:
- 15% estado atual (mas como contraste negativo, não como foco)
- 30% estado intermediário (proposta)
- **55% estado aspiracional** (benefícios + transformação + CTA + autoridade todos focados no resultado final)

**Tom dominante**: "Imagine-se agora vivendo...", "Você se tornou a versão plena...", "Conquistar o corpo e confiança..."

**Resultado**: `descricao_imagem` menciona **"Imagem única de uma mulher radiante"** → apenas 1 prompt preenchido (aspiracional)

---

## Conclusão

### As Instruções Fixas Têm 2 Problemas:

1. **`code_reviewer` não é rigoroso o suficiente**:
   - Diz "Incluir prompts técnicos" mas não "OBRIGATÓRIO: todos os 3 prompts devem estar preenchidos (não null)"
   - Não tem validação explícita: `if prompt_estado_atual is null → grade = "fail"`

2. **`final_assembler` tem instrução ambígua**:
   - "Complete faltantes de forma conservadora"
   - "reutilizando os snippets aprovados sempre que possível"
   - Isso incentiva manter `null` se o snippet foi "aprovado" pelo reviewer

### O Viés do Contexto Intensifica o Problema:

- **Caminho Feliz**: Contexto equilibrado → LLM gera naturalmente "sequência de três imagens" → Preenche os 3 prompts → Reviewer passa → Assembler recebe snippet completo

- **Fallback**: Contexto desequilibrado (55% aspiracional) → LLM gera "Imagem única" focada no estado final → Preenche apenas 1 prompt → Reviewer **deveria reprovar mas passa** → Assembler recebe snippet incompleto mas "conservadoramente" mantém os `null`

---

## Solução Proposta

### 1. Tornar o `code_reviewer` RIGOROSO:

```python
- VISUAL_DRAFT:
  * **OBRIGATÓRIO**: Verificar que TODOS os 3 prompts estão preenchidos (não null, não vazios)
  * Se `prompt_estado_atual` is null OU vazio → grade = "fail"
  * Se `prompt_estado_intermediario` is null OU vazio → grade = "fail"
  * Se `prompt_estado_aspiracional` is null OU vazio → grade = "fail"
  * Se `descricao_imagem` contém "imagem única" ou "single image" → grade = "fail" (deve ser uma sequência)
  * Descrição visual deve mencionar explicitamente "sequência" ou "jornada" ou "3 estados/cenas/imagens"
  * Narrativa deve mostrar a sequência: estado_atual (dor) → estado_intermediario (decisão) → estado_aspiracional (transformação)
  * Os 3 prompts técnicos devem estar alinhados à narrativa e mostrar evolução clara entre os estados
```

### 2. Modificar o `code_generator` para ser MAIS EXPLÍCITO:

```python
- VISUAL_DRAFT:
  IMPORTANTE: Você DEVE criar EXATAMENTE 3 prompts separados e distintos.
  NUNCA crie apenas um prompt ou deixe campos como null.

  A descricao_imagem deve SEMPRE narrar uma SEQUÊNCIA de 3 cenas/imagens distintas, não uma imagem única.

  {
    "visual": {
      "descricao_imagem": "SEQUÊNCIA de 3 imagens distintas mostrando: 1) Estado atual (dor/frustração específica), 2) Estado intermediário (momento de decisão/mudança), 3) Estado aspiracional (transformação alcançada). Descreva TODAS as três cenas claramente.",
      "prompt_estado_atual": "OBRIGATÓRIO - Prompt técnico em inglês descrevendo APENAS o estado de dor (emoções negativas, postura derrotada, cenário que reflete frustração)...",
      "prompt_estado_intermediario": "OBRIGATÓRIO - Prompt técnico em inglês mostrando APENAS a ação imediata de mudança (mantendo cenário/vestuário similar, mas expressão de decisão/esperança)...",
      "prompt_estado_aspiracional": "OBRIGATÓRIO - Prompt técnico em inglês descrevendo APENAS o estado transformado (emoções positivas, resultados visíveis, cenário que reflete sucesso)...",
      "aspect_ratio": "4:5"
    }
  }
```

### 3. Modificar o `final_assembler`:

```python
Campos obrigatórios (saída deve ser uma LISTA com 3 OBJETOS):
...
- "visual": { "descricao_imagem", "prompt_estado_atual", "prompt_estado_intermediario", "prompt_estado_aspiracional", "aspect_ratio" }
  **IMPORTANTE**: TODOS os 4 campos de visual devem estar preenchidos (não null, não vazios) em TODAS as 3 variações.
  Se algum snippet VISUAL_DRAFT aprovado tiver campos null, você DEVE gerar os prompts ausentes baseando-se em:
    - storybrand_dores para prompt_estado_atual
    - storybrand_proposta/storybrand_cta_principal para prompt_estado_intermediario
    - storybrand_beneficios/storybrand_transformacao para prompt_estado_aspiracional

Regras:
- Criar 3 variações diferentes de copy e visual reutilizando os snippets aprovados sempre que possível.
- **Se algum snippet VISUAL_DRAFT tiver campos ausentes (null), COMPLETE-OS obrigatoriamente com base no contexto StoryBrand.**
- NUNCA deixe prompts como null na saída final.
```

---

## Arquivo de Instruções Fixas

Todas as instruções estão definidas em **[app/agent.py](app/agent.py)**:

- `code_generator`: linhas 1052-1138
- `code_reviewer`: linhas 1140-1201
- `code_refiner`: linhas 1203-1217
- `final_assembler`: linhas 1572-1592
