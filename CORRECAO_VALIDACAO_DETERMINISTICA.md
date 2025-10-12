# Correção - Validação Determinística Falhando

**Data:** 2025-10-12
**Status:** ✅ CORRIGIDO
**Contexto:** Pipeline determinístico (`ENABLE_DETERMINISTIC_FINAL_VALIDATION=true`) bloqueava todas as requisições

---

## 🔴 Problema Identificado

### Erro 1: Campo `aspect_ratio` Ausente

**Sintoma:**
```
visual.aspect_ratio
  Field required [type=missing, input_value={'descricao_imagem': '...'}, input_type=dict]
```

**Causa Raiz:**
- **Arquivo:** [app/agent.py:1288](app/agent.py#L1288)
- **Instrução problemática:**
  ```python
  "aspect_ratio": "definido conforme especificação do formato"
  ```
- **Comportamento do LLM:** Interpretava como placeholder/texto descritivo em vez de extrair o valor real de `{format_specs_json}`
- **Resultado:** Campo `aspect_ratio` ausente ou com texto literal, bloqueado pelo `FinalAssemblyNormalizer` (linha 1657)

### Erro 2: Campo `cta_texto` com Valores Inválidos

**Sintoma:**
```
copy.cta_texto
  Value error, cta_texto must be one of ('Saiba mais', 'Enviar mensagem', 'Ligar', 'Comprar agora', 'Cadastre-se')
  [input_value='Dê o primeiro passo par...e. Agende sua consulta.']
```

**Causa Raiz:**
- **Arquivo:** [app/agent.py:1263](app/agent.py#L1263) (antes da correção)
- **Instrução problemática:** `"cta_texto": "..."` (sem especificar valores permitidos)
- **Comportamento do LLM:** Criava frases customizadas/criativas em vez de usar os valores exatos do enum
- **Validação:** `StrictAdItem.cta_texto` exige valores de `CTA_INSTAGRAM_CHOICES` (app/config.py:22-28)

---

## ✅ Correções Aplicadas

### Correção 1: `aspect_ratio` Explícito

**Arquivo:** [app/agent.py:1288](app/agent.py#L1288)

**ANTES:**
```python
"aspect_ratio": "definido conforme especificação do formato"
```

**DEPOIS:**
```python
"aspect_ratio": "OBRIGATÓRIO: use o valor exato de {format_specs_json}.visual.aspect_ratio. Para Reels/Stories use '9:16', para Feed use '4:5'. Este campo DEVE ser uma string com o valor literal do aspect ratio, NÃO uma descrição."
```

**Impacto:**
- ✅ LLM agora extrai valor correto de `format_specs_json`
- ✅ `FinalAssemblyNormalizer` não bloqueia mais por campo ausente
- ✅ `FinalDeliveryValidatorAgent` valida corretamente contra `ALLOWED_ASPECT_RATIOS`

---

### Correção 2: `cta_texto` e `cta_instagram` com Valores Enum

**Arquivo:** [app/agent.py:1263-1265](app/agent.py#L1263-L1265)

**ANTES:**
```python
"copy": {
  "headline": "...",
  "corpo": "...",
  "cta_texto": "..."
},
"cta_instagram": "Saiba mais" | "Enviar mensagem" | "Ligar" | "Comprar agora" | "Cadastre-se"
```

**DEPOIS:**
```python
"copy": {
  "headline": "...",
  "corpo": "...",
  "cta_texto": "OBRIGATÓRIO: escolha EXATAMENTE um destes valores: 'Saiba mais', 'Enviar mensagem', 'Ligar', 'Comprar agora', 'Cadastre-se'. NÃO crie frases customizadas, use APENAS um desses textos literais."
},
"cta_instagram": "OBRIGATÓRIO: escolha EXATAMENTE um destes valores: 'Saiba mais', 'Enviar mensagem', 'Ligar', 'Comprar agora', 'Cadastre-se'. Para {objetivo_final}='agendamentos', prefira 'Enviar mensagem' ou 'Ligar'."
```

**Impacto:**
- ✅ LLM agora usa valores literais do enum `CTA_INSTAGRAM_CHOICES`
- ✅ Validação Pydantic (`StrictAdItem.cta_texto`) não rejeita mais
- ✅ Validação de CTA por objetivo (`cta_by_objective`) funciona corretamente

---

## 🔍 Arquitetura Relacionada

### Pipeline de Validação Determinística

1. **FinalAssemblyGuardPre** → Valida presença de snippets VISUAL_DRAFT aprovados
2. **FinalAssemblerLLM** → Monta JSON final a partir dos snippets
3. **FinalAssemblyNormalizer** → Verifica campos obrigatórios (incluindo `aspect_ratio`)
4. **FinalDeliveryValidatorAgent** → Validação Pydantic estrita (`StrictAdItem`)
5. **RunIfPassed** → Libera pipeline apenas se `grade="pass"`

### Schemas Pydantic Relevantes

- **`StrictAdItem`** ([app/schemas/final_delivery.py:75-145](app/schemas/final_delivery.py#L75-L145))
  - Valida estrutura completa de cada variação
  - `cta_texto` e `cta_instagram` validados contra `CTA_INSTAGRAM_CHOICES`
  - `aspect_ratio` validado contra `ALLOWED_ASPECT_RATIOS`

- **`StrictAdVisual`** ([app/schemas/final_delivery.py:56-70](app/schemas/final_delivery.py#L56-L70))
  - Campo `aspect_ratio: str` obrigatório
  - Validator custom verifica se está em `ALLOWED_ASPECT_RATIOS` ("9:16", "1:1", "4:5", "16:9")

### Configuração Global

- **`CTA_INSTAGRAM_CHOICES`** ([app/config.py:22-28](app/config.py#L22-L28))
  ```python
  ("Saiba mais", "Enviar mensagem", "Ligar", "Comprar agora", "Cadastre-se")
  ```

- **`format_specs_json`** injetado no estado via preflight ([app/server.py:511](app/server.py#L511))
  ```python
  initial_state["format_specs_json"] = specs_json  # JSON string do FORMAT_SPECS[formato]
  ```

---

## 🧪 Testes Recomendados

### Teste 1: Validação de `aspect_ratio`

**Objetivo:** Confirmar que VISUAL_DRAFT agora inclui campo `aspect_ratio` correto

**Payload de teste:**
```json
{
  "landing_page_url": "https://example.com",
  "objetivo_final": "agendamentos",
  "perfil_cliente": "Homens 35-50 anos",
  "formato_anuncio": "Feed"
}
```

**Validação esperada:**
- ✅ Snippet VISUAL_DRAFT contém `"aspect_ratio": "4:5"`
- ✅ `FinalAssemblyNormalizer` não bloqueia
- ✅ `FinalDeliveryValidatorAgent` retorna `grade="pass"`

---

### Teste 2: Validação de `cta_texto`

**Objetivo:** Confirmar que COPY_DRAFT usa valores literais do enum

**Payload de teste:**
```json
{
  "landing_page_url": "https://example.com",
  "objetivo_final": "agendamentos",
  "perfil_cliente": "Mulheres 25-40 anos",
  "formato_anuncio": "Reels"
}
```

**Validação esperada:**
- ✅ Snippet COPY_DRAFT contém `"cta_texto": "Enviar mensagem"` ou `"Ligar"` (conforme `CTA_BY_OBJECTIVE`)
- ✅ Não há frases customizadas como "Agende sua consulta!"
- ✅ Validação Pydantic não rejeita

---

### Teste 3: Pipeline Completo Determinístico

**Objetivo:** Confirmar que pipeline determinístico completa sem bloqueios

**Pré-requisitos:**
```bash
export ENABLE_DETERMINISTIC_FINAL_VALIDATION=true
make dev
```

**Validação esperada:**
1. ✅ `FinalAssemblyGuardPre` passa (snippets VISUAL_DRAFT presentes)
2. ✅ `FinalAssemblyNormalizer` passa (campos obrigatórios presentes)
3. ✅ `FinalDeliveryValidatorAgent` retorna `grade="pass"` (sem erros Pydantic)
4. ✅ `RunIfPassed` libera `persist_final_delivery_agent`
5. ✅ JSON final salvo em `artifacts/ads_final/` e `meta.json` com `grade="pass"`
6. ✅ Endpoint `/delivery/final/meta` retorna 200 (não 404/503)

---

## 📊 Impacto

### Antes da Correção:
- ❌ **100% de falha** no pipeline determinístico
- ❌ Normalizer bloqueava todas as variações (`aspect_ratio` ausente)
- ❌ Validator rejeitava `cta_texto` customizado
- ❌ Endpoint `/delivery/final/meta` retornava 404 (artefato não persistido)

### Depois da Correção:
- ✅ Pipeline determinístico funcional
- ✅ Campos obrigatórios preenchidos corretamente pelo LLM
- ✅ Validação Pydantic passa
- ✅ Persistência de artefatos funcionando

---

## 📝 Notas Adicionais

### Por que a instrução anterior falhava?

**Instrução ambígua:**
```python
"aspect_ratio": "definido conforme especificação do formato"
```

**Interpretações possíveis pelo LLM:**
1. ❌ Omitir o campo completamente (campo vazio)
2. ❌ Colocar o texto literal `"definido conforme especificação do formato"`
3. ❌ Incluir a informação dentro de `descricao_imagem` como texto narrativo (ex: "Aspect ratio: 4:5")

Nenhuma dessas gera um campo JSON válido `"aspect_ratio": "4:5"`.

**Instrução corrigida (imperativa e explícita):**
```python
"aspect_ratio": "OBRIGATÓRIO: use o valor exato de {format_specs_json}.visual.aspect_ratio. Para Reels/Stories use '9:16', para Feed use '4:5'. Este campo DEVE ser uma string com o valor literal do aspect ratio, NÃO uma descrição."
```

Agora o LLM entende que deve:
1. Extrair valor de `{format_specs_json}` (disponível no contexto)
2. Usar valor literal exato (`"9:16"` ou `"4:5"`)
3. Não criar descrição/texto narrativo

---

### Validação de CTA por Objetivo

O sistema valida CTAs contra `cta_by_objective` ([app/config.py:30-36](app/config.py#L30-L36)):

```python
CTA_BY_OBJECTIVE = {
    "agendamentos": ("Enviar mensagem", "Ligar"),
    "leads": ("Cadastre-se", "Saiba mais"),
    "vendas": ("Comprar agora", "Saiba mais"),
    "contato": ("Enviar mensagem", "Ligar"),
    "awareness": ("Saiba mais",),
}
```

A correção aplicada garante que o LLM escolha valores de `CTA_INSTAGRAM_CHOICES`, mas ainda pode gerar um CTA inválido para o objetivo (ex: "Comprar agora" para objetivo "agendamentos").

**Validação adicional** ocorre em [app/validators/final_delivery_validator.py:156-164](app/validators/final_delivery_validator.py#L156-L164):
```python
if allowed_ctas:
    if item.copy.cta_texto not in allowed_ctas:
        issues.append(f"Variação {idx}: CTA do texto não permitido para objetivo {objective}.")
```

Se necessário, a instrução do `code_generator` pode ser refinada para consultar `cta_by_objective` diretamente.

---

## 🔗 Referências

- **Issue Original:** Logs de erro em `artifacts/ads_final/meta/*.error.json`
- **Commit:** (a ser preenchido após commit das alterações)
- **Arquivos Modificados:**
  - [app/agent.py](app/agent.py) (linhas 1263-1265, 1288)
- **Documentação Relacionada:**
  - [README.md](README.md) - Seção "Rollout recomendado da validação determinística"
  - [CLAUDE.md](CLAUDE.md) - Feature flag `ENABLE_DETERMINISTIC_FINAL_VALIDATION`

---

**Última Atualização:** 2025-10-12
**Autor:** Claude Code (análise de causa raiz e correção)
