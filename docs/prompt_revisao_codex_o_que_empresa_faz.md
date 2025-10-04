# Análise Crítica: Campo `o_que_a_empresa_faz` - Falha de Design Estratégico

## CONTEXTO EXECUTIVO

Identificamos uma **falha crítica de design** na implementação atual que compromete a qualidade do sistema de geração de StoryBrand. O campo `o_que_a_empresa_faz` está sendo tratado como dado secundário quando deveria ser o **motor principal de contextualização** de toda a narrativa.

## 1. EVIDÊNCIAS DA FALHA

### 1.1 Código Atual - `helpers/user_extract_data.py`

**Linha 63-66 (Prompt de Extração):**
```python
base_prompt += (
    ", nome_empresa (obrigatório), o_que_a_empresa_faz (obrigatório), "
    "sexo_cliente_alvo (obrigatório; somente masculino ou feminino)"
)
```
**PROBLEMA:** Trata todos os campos com igual importância, sem enfatizar que `o_que_a_empresa_faz` deve capturar a **proposta de valor completa**.

**Linhas 393-409 (Validação):**
```python
if not descricao or len(descricao) < 10:
    errors.append({
        "field": "o_que_a_empresa_faz",
        "message": "Descrição da empresa é obrigatória (mínimo 10 caracteres).",
    })
```
**PROBLEMA:** Validação de apenas 10 caracteres permite descrições inúteis como "Consultoria" ao invés de "Ajudamos executivos a organizar finanças para aposentadoria antecipada".

**Linhas 141-169 (Exemplo 2 em `_examples`):**
```python
lx.data.Extraction(
    extraction_class="o_que_a_empresa_faz",
    extraction_text="Agência de marketing digital para profissionais autônomos",
)
```
**PROBLEMA:** Exemplo mostra extração genérica sem capturar a transformação oferecida ao cliente.

### 1.2 Plano de Fallback - `aprimoramento_plano_storybrand_v2.md`

**Linha 43 (Seção 4, `fallback_input_collector`):**
> "Ele deve priorizar os valores já presentes na raiz do estado [...] Ele não deve inferir 'persona' ou 'tom'"

**PROBLEMA:** O plano não especifica que este agente deve **validar a riqueza semântica** do campo, não apenas sua presença.

**Linhas 45-47 (Seção 4, `section_pipeline_runner`):**
> "Ele carregará a configuração de todas as 16 seções do StoryBrand e executará, em um loop, o bloco de agentes reutilizáveis"

**PROBLEMA:** Não menciona que `o_que_a_empresa_faz` deve ser **injetado como contexto prioritário** em cada ciclo de escrita.

**Linha 76 (Seção 7, Prompts de Escrita):**
> "Cada prompt conterá a 'receita' estrutural para sua respectiva seção, extraída dos modelos storybrand_*.txt originais"

**PROBLEMA:** Não especifica que os prompts devem ser instruídos a **adaptar toda narrativa** baseando-se em `o_que_a_empresa_faz`.

**Linha 77 (Seção 7, Prompts de Revisão):**
> "instruções para atuar como o 'empresário consciente' e os critérios de avaliação da dupla consciência (empatia + estratégia)"

**PROBLEMA:** Os critérios não incluem explicitamente: "O texto está alinhado com a proposta de valor em `o_que_a_empresa_faz`?"

## 2. IMPACTO DA FALHA

### Exemplo Concreto de Falha em Produção:

**Input do usuário:**
```
nome_empresa: FinançasPro
o_que_a_empresa_faz: Consultoria financeira
perfil_cliente: Homens 40-50 anos preocupados com aposentadoria
```

**Resultado ATUAL (problemático):**
- StoryBrand genérico sobre "problemas financeiros"
- Sem conexão específica com a solução da empresa
- Poderia servir para qualquer consultoria financeira

**Resultado ESPERADO:**
- StoryBrand específico sobre como FinançasPro ajuda homens a planejar aposentadoria
- Narrativa conectada à transformação específica oferecida
- Único e relevante para este negócio

## 3. CORREÇÕES NECESSÁRIAS

### 3.1 Em `helpers/user_extract_data.py`

**A. Prompt de Extração (linhas 63-66):**
```python
# PROPOSTA DE CORREÇÃO:
base_prompt += (
    ", nome_empresa (obrigatório), "
    "o_que_a_empresa_faz (CRÍTICO: extraia a FRASE COMPLETA descrevendo "
    "como a empresa transforma a vida dos clientes - ex: 'Ajudamos X a conseguir Y através de Z'), "
    "sexo_cliente_alvo (obrigatório; somente masculino ou feminino)"
)
```

**B. Validação (linhas 393-409):**
```python
# PROPOSTA DE CORREÇÃO:
if not descricao or len(descricao) < 30:
    errors.append({
        "field": "o_que_a_empresa_faz",
        "message": "Descreva COMO sua empresa transforma clientes (mín. 30 caracteres). "
                   "Ex: 'Ajudamos executivos a organizar finanças para aposentadoria'",
    })
elif "ajud" not in descricao.lower() and "oferec" not in descricao.lower() and "transform" not in descricao.lower():
    # Validação semântica adicional
    errors.append({
        "field": "o_que_a_empresa_faz",
        "message": "Descreva a TRANSFORMAÇÃO que sua empresa oferece aos clientes.",
    })
```

**C. Exemplos (linha 169):**
```python
# PROPOSTA DE CORREÇÃO:
lx.data.Extraction(
    extraction_class="o_que_a_empresa_faz",
    extraction_text="Ajudamos profissionais autônomos a conquistar clientes consistentes através de estratégias digitais personalizadas",
)
```

### 3.2 Em `aprimoramento_plano_storybrand_v2.md`

**ADICIONAR nova Seção 4.1:**
```markdown
#### **4.1 Contexto Universal Obrigatório: `o_que_a_empresa_faz`**

- **Status Crítico:** Este campo é o **motor principal de contextualização** de todo o pipeline.
- **Validação Semântica:** O `fallback_input_collector` deve validar que o campo contém:
  - Pelo menos 30 caracteres
  - Verbos de ação (ajudar, transformar, capacitar, etc.)
  - Descrição clara do benefício ao cliente
- **Injeção Universal:** O `section_pipeline_runner` DEVE injetar `state['o_que_a_empresa_faz']` em TODOS os contextos de:
  - Agentes escritores (16 seções)
  - Agentes revisores
  - Agente compilador
- **Falha Crítica:** Se após validação o campo não contiver proposta de valor clara, abortar pipeline com erro:
  ```json
  {
    "stage": "collector",
    "status": "error",
    "details": "Campo o_que_a_empresa_faz não contém proposta de valor acionável"
  }
  ```
```

**MODIFICAR Seção 7 (linha 76-77):**
```markdown
- **Prompts de Escrita:** Cada prompt DEVE conter:
  1. A "receita" estrutural da seção
  2. Instrução explícita: "Adapte TODO o conteúdo usando a proposta de valor em {o_que_a_empresa_faz}"
  3. Exemplo: "Se a empresa 'ajuda executivos a organizar finanças', o Problema deve ser sobre desorganização financeira, não genérico"

- **Prompts de Revisão:** Critério obrigatório de avaliação:
  1. "O texto está DIRETAMENTE conectado à transformação descrita em {o_que_a_empresa_faz}?"
  2. "Um concorrente poderia usar este texto ou é específico para ESTA empresa?"
```

## 4. TESTES DE VALIDAÇÃO

Para confirmar que a correção funciona, proponha testes que verifiquem:

1. **Teste de Rejeição:**
   - Input: `o_que_a_empresa_faz: "Consultoria"`
   - Esperado: Erro de validação exigindo descrição da transformação

2. **Teste de Especificidade:**
   - Input: `o_que_a_empresa_faz: "Ajudamos mães empreendedoras a triplicar vendas online em 90 dias"`
   - Esperado: StoryBrand com problemas sobre "vendas baixas online" e sucesso sobre "triplicar vendas"

3. **Teste de Contextualização:**
   - Comparar StoryBrand gerado para duas empresas do mesmo setor com propostas diferentes
   - Esperado: Narrativas completamente distintas, cada uma alinhada à sua proposta específica

## 5. SOLICITAÇÃO AO CODEX

Com base nesta análise detalhada, solicitamos que você:

1. **CONFIRME** se esta falha de design compromete a qualidade do sistema
2. **VALIDE** se as correções propostas são suficientes e tecnicamente corretas
3. **PROPONHA** melhorias adicionais se identificar outras lacunas
4. **IMPLEMENTE** as correções no código e no plano, criando:
   - Versão corrigida de `helpers/user_extract_data.py`
   - Versão atualizada de `aprimoramento_plano_storybrand_v2.md`
   - Testes unitários para validar a nova lógica

## 6. CRITÉRIO DE SUCESSO

A correção será considerada bem-sucedida quando:
- O campo `o_que_a_empresa_faz` for tratado como **informação estratégica crítica**
- Validações garantirem captura da **proposta de valor completa**
- Todo o pipeline usar este campo como **contexto principal de adaptação**
- StoryBrands gerados forem **únicos e específicos** para cada empresa

---

**NOTA:** Esta não é uma melhoria opcional. É uma correção crítica para alinhar a implementação técnica com a lógica de negócios fundamental do sistema.