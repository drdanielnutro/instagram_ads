# Plano Expandido — Duplo Prompt Visual (Estado Atual x Aspiracional)

## Objetivo
Permitir que cada variação do anúncio traga dois prompts de imagem correlacionados:
- **estado_atual_prompt**: representa o cliente/persona antes de contratar o serviço/produto.
- **estado_aspiracional_prompt**: representa a transformação desejada (identidade aspiracional) após o cliente obter o resultado prometido.

O pipeline deve manter a descrição textual da imagem em pt-BR, mas passar a registrar esses dois prompts técnicos (inglês) no JSON final, garantindo validação automática e prontidão para a futura geração de imagens.

---

## 1. Modelos & Tipagem

### 1.1 `app/agent.py`
- Atualizar `AdVisual` para incluir dois campos adicionais:
  ```python
  class AdVisual(BaseModel):
      descricao_imagem: str
      prompt_estado_atual: str
      prompt_estado_aspiracional: str
      aspect_ratio: Literal["9:16", "1:1", "4:5", "16:9"]
  ```
- Garantir que eventuais referências (ex.: `SessionState`, callbacks) aceitem os novos campos.

### 1.2 `app/utils/session-state.py`
- Se houver tipagem forte (`SessionState`) para snippets/visual, incluir os dois prompts.

### 1.3 `app/utils/typing.py`
- Caso exista `AdVisual` ou estruturas equivalentes, replicar os campos para consistência.

---

## 2. Planos Fixos e Instruções de Agentes

- **VISUAL_DRAFT**
  - Reescrever a descrição em cada plano (Reels/Stories/Feed) para exigir:
    - `descricao_imagem`: texto em pt-BR narrando de forma clara o contraste entre duas cenas com a mesma persona — primeiro a dor atual (antes), depois o estado aspiracional (após a transformação). A descrição deve mencionar explicitamente ambos os momentos (emoções, ambiente, sinais visuais).
    - `prompt_estado_atual`: prompt técnico em inglês derivado da mesma narrativa, detalhando o cenário de dor (emoção negativa, postura, elementos que reforçam o problema não resolvido).
    - `prompt_estado_aspiracional`: prompt técnico em inglês derivado da narrativa, detalhando o cenário transformado (emoção positiva, confiança, sinais de resultado alcançado). Ambos os prompts devem manter consistência visual (mesma persona, contexto evoluindo) e deixar claro o antes/depois sem prometer resultados impossíveis.
  - Remover instruções antigas que mencionavam apenas `descricao_imagem` + `prompt_imagem` genérico.

- **COMPLIANCE_QA**
  - Substituir o texto genérico “sem ‘antes‑depois’…” por uma orientação mais específica, permitindo o uso narrativo do contraste atual/aspiracional desde que não envolva promessas irreais, prazos impossíveis ou alegações médicas proibidas. Exemplo de novo texto: “Checar se o contraste (estado atual vs aspiracional) é honesto, não promete resultados instantâneos/impossíveis e respeita as políticas do Meta para saúde/beleza (sem choque gráfico, sem alegações mágicas).”

### 2.2 `app/agent.py` — Instruções dos agentes LLM
- **code_generator** (`VISUAL_DRAFT` bloco): ajustar o template para solicitar os dois prompts correlacionados, deixando claro que ambos derivam da descrição base e representam momentos distintos (“antes” e “depois”). Exemplo:
  ```json
  {
    "visual": {
      "descricao_imagem": "...",
      "prompt_estado_atual": "...",  // inglês técnico – estado atual (dor)
      "prompt_estado_aspiracional": "...",  // inglês técnico – estado aspiracional (transformação)
      "aspect_ratio": "..."
    },
    "formato": "{formato_anuncio}"
  }
  ```
- **code_reviewer** (`VISUAL_DRAFT` regras): validar a consistência narrativa — a descrição menciona os dois momentos e os prompts de estado atual/aspiracional capturam esse contraste (dor → transformação) sem perder a coerência da persona/contexto.
- **code_reviewer** (`VISUAL_QA`): acrescentar verificação da coerência entre os dois prompts (mesma persona, mesmo ambiente evoluindo) e da clareza na transformação desejada.
- **final_assembler**: garantir que o JSON final traga as novas chaves. Documentar no bloco “Campos obrigatórios”.
- **final_validator**: atualizar critérios para exigir os dois prompts:
  - `visual{descricao_imagem,prompt_estado_atual,prompt_estado_aspiracional,aspect_ratio}`.

### 2.3 `app/format_specifications.py` (se aplicável)
- Incluir notas para `prompt_estado_atual` e `prompt_estado_aspiracional` em cada formato, orientando estilo/emoção/elementos relevantes.

---

## 3. Persistência e Callbacks

### 3.1 `app/callbacks/persist_outputs.py`
- Nenhuma mudança específica se o JSON final simplesmente incluir novos campos. Verificar se a função `json.dump` continua preservando os campos (deve funcionar sem ajuste).

### 3.2 `app/routers/delivery.py`
- Não há alteração necessária (endpoint já devolve JSON completo). Certificar que os novos campos não afetem os metadados.

---

## 4. Validação & Tests

### 4.1 `tests/test_refactored.py`
- Atualizar o script de verificação para checar `prompt_estado_atual` e `prompt_estado_aspiracional` dentro de `visual`.
  ```python
  print(f"  - Tem prompt_estado_atual: {…}")
  print(f"  - Tem prompt_estado_aspiracional: {…}")
  ```

### 4.2 Caso exista suíte `pytest`
- Criar/atualizar testes unitários para validar que o JSON final contém os campos novos e que o validador falha quando ausentes.

### 4.3 Logs e validação manual
- Após implementar, rodar `make dev` → gerar sessão → conferir SSE e JSON final.
- Verificar que `plan_summary` continua consistente e que as novas chaves aparecem nas três variações.

---

## 5. Documentação

### 5.1 `README.md`
- Incluir nota na seção “Arquitetura” ou “Saída do JSON” descrevendo os novos campos em `visual`.

### 5.2 `PLAN_IMAGE_ASSETS_INTEGRATION.md`
- Atualizar para considerar que, ao gerar imagens, haverá dois prompts por variação (podendo resultar em duas imagens distintas ou uma montagem).

### 5.3 Outros docs relevantes (`docs/…`)
- Ajustar guias que mencionem o schema do JSON final para incluir os prompts de transformação.

---

## 6. Visão de Pipeline

1. **Preflight** continua igual (extraindo campos de texto).
2. **Planos fixos** agora orientam `VISUAL_DRAFT` a gerar descrição + dupla de prompts.
3. **code_generator** produz os dados; **code_reviewer** garante coerência e dualidade (atual vs aspiracional).
4. **final_assembler** inclui ambos os prompts no JSON final.
5. **final_validator** exige os campos extras, mantendo controle de qualidade.
6. **Persistência/delivery** salva os novos campos sem alteração na lógica.
7. Quando o agente de geração de imagens for implementado, usará os prompts (pode produzir duas imagens por variação ou um díptico).

---

## 7. Próximos Passos

1. Implementar alterações mínimas (modelos, instruções, planos, validador, testes).
2. Rodar validação manual e automática.
3. Atualizar documentação e planos correlacionados.
4. (Futuro) Estender o agente de imagens para consumir ambos os prompts.
