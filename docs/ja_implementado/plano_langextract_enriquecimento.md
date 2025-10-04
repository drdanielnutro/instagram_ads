# Plano de Implementação: LangExtract como Motor de Enriquecimento

## 1. Visão da Mudança

### Situação Atual (Problema)
- LangExtract usado apenas como parser literal
- Descrições genéricas são rejeitadas
- Usuário precisa escrever frases completas
- Campo `o_que_a_empresa_faz` tratado isoladamente

### Situação Desejada (Solução)
- LangExtract como enriquecedor contextual
- Descrições genéricas são transformadas
- Sistema ajuda o usuário a criar propostas de valor
- Campos se complementam para gerar contexto rico

## 2. Mudanças no Código

### 2.1 Prompt Base (`helpers/user_extract_data.py:58-80`)

**ANTES:**
```python
base_prompt += (
    ". Use exact user wording for values when present. Do not invent. "
    "If a field is not present, leave empty."
)
```

**DEPOIS:**
```python
base_prompt += (
    ". Para campos simples (nome, URL, formato), use o texto original. "
    "Para o_que_a_empresa_faz: se o texto for genérico ou incompleto, "
    "ENRIQUEÇA criando uma frase de transformação completa usando TODOS "
    "os campos disponíveis (perfil_cliente, sexo_cliente_alvo, objetivo_final). "
    "Formato ideal: 'Ajudamos [QUEM] a [CONSEGUIR O QUÊ] através de [COMO]'."
)
```

### 2.2 Exemplos Few-Shot Transformacionais

**ADICIONAR em `_examples()` após linha 144:**

```python
# Exemplo 5 - Enriquecimento de descrição genérica masculina
txt5 = (
    "empresa: Clínica Vitalidade\n"
    "descrição: tratamento médico para emagrecer\n"
    "perfil: homens executivos 40-50 anos\n"
    "sexo: masculino\n"
    "objetivo: agendamentos\n"
)
examples.append(
    lx.data.ExampleData(
        text=txt5,
        extractions=[
            lx.data.Extraction(
                extraction_class="nome_empresa",
                extraction_text="Clínica Vitalidade",
            ),
            lx.data.Extraction(
                extraction_class="o_que_a_empresa_faz",
                extraction_text="tratamento médico para emagrecer",
                attributes={
                    "enriched": "Ajudamos executivos acima dos 40 a recuperar energia e forma física através de tratamento médico personalizado para emagrecimento sustentável"
                }
            ),
            lx.data.Extraction(
                extraction_class="perfil_cliente",
                extraction_text="homens executivos 40-50 anos",
            ),
            lx.data.Extraction(
                extraction_class="sexo_cliente_alvo",
                extraction_text="masculino",
                attributes={"normalized": "masculino"},
            ),
        ],
    )
)

# Exemplo 6 - Enriquecimento com contexto feminino
txt6 = (
    "nome: Espaço Bem-Estar\n"
    "serviço: consultoria nutricional\n"
    "público: mulheres mães 30-40\n"
    "sexo alvo: feminino\n"
    "meta: leads\n"
)
examples.append(
    lx.data.ExampleData(
        text=txt6,
        extractions=[
            lx.data.Extraction(
                extraction_class="nome_empresa",
                extraction_text="Espaço Bem-Estar",
            ),
            lx.data.Extraction(
                extraction_class="o_que_a_empresa_faz",
                extraction_text="consultoria nutricional",
                attributes={
                    "enriched": "Ajudamos mães ocupadas a conquistar uma alimentação equilibrada para toda a família através de consultoria nutricional prática e personalizada"
                }
            ),
            lx.data.Extraction(
                extraction_class="perfil_cliente",
                extraction_text="mulheres mães 30-40",
            ),
            lx.data.Extraction(
                extraction_class="sexo_cliente_alvo",
                extraction_text="feminino",
                attributes={"normalized": "feminino"},
            ),
        ],
    )
)
```

### 2.3 Ajuste na Conversão (`_convert` linha 319)

**ADICIONAR após linha 351:**

```python
# Para o_que_a_empresa_faz, priorizar versão enriquecida
if cls == "o_que_a_empresa_faz":
    enriched = attrs.get("enriched")
    if enriched and len(enriched) >= 30:
        # Usar versão enriquecida se disponível e válida
        data[cls] = enriched.strip()
    else:
        # Fallback para texto original
        data[cls] = txt.strip()
```

### 2.4 Validação Adaptativa (`_is_transformational_description`)

**MODIFICAR linha 475-520:**

```python
@staticmethod
def _is_transformational_description(descricao: str) -> bool:
    """Valida se a descrição comunica transformação acionável."""

    if not descricao:
        return False

    clean = descricao.strip()
    if len(clean) < 30:
        return False

    desc_lower = clean.lower()

    # Se já tem estrutura "Ajudamos X a Y", aceita
    if desc_lower.startswith("ajudamos") and " a " in desc_lower:
        return True

    # Verificar verbos de transformação
    action_verbs = [
        "ajud", "transform", "capacit", "auxili",
        "gui", "facilit", "oferec", "fornec",
        "entreg", "possibilit", "criar", "desenvolv"
    ]
    has_action = any(verb in desc_lower for verb in action_verbs)

    # Verificar conectores de resultado
    result_connectors = [" para ", " através ", " com ", " até "]
    has_result = any(conn in desc_lower for conn in result_connectors)

    # Se foi enriquecido pelo LangExtract, confiar mais
    if has_action and (has_result or len(clean) > 50):
        return True

    # Rejeitar apenas termos muito genéricos isolados
    generic_single_terms = {
        "consulta", "consultoria", "serviços", "empresa", "negócio"
    }
    if desc_lower in generic_single_terms and len(clean.split()) <= 2:
        return False

    return has_action
```

## 3. Testes de Validação

### 3.1 Teste de Enriquecimento Masculino
```python
def test_enrichment_male_context():
    input_text = """
    empresa: MedFit
    descrição: tratamento para emagrecer
    público: homens sedentários
    sexo: masculino
    """

    result = extract_user_input(input_text)

    # Deve enriquecer para algo como:
    # "Ajudamos homens sedentários a conquistar uma vida mais saudável
    #  através de tratamento médico especializado em emagrecimento"

    assert result['success'] is True
    assert len(result['data']['o_que_a_empresa_faz']) >= 50
    assert 'ajudamos' in result['data']['o_que_a_empresa_faz'].lower()
```

### 3.2 Teste de Enriquecimento Feminino
```python
def test_enrichment_female_context():
    input_text = """
    empresa: Bella Forma
    serviço: academia
    perfil: mulheres pós-parto
    sexo: feminino
    """

    result = extract_user_input(input_text)

    # Deve enriquecer para algo como:
    # "Ajudamos mulheres no pós-parto a recuperar a forma física
    #  e autoestima através de treinos especializados"

    assert result['success'] is True
    assert 'mulheres' in result['data']['o_que_a_empresa_faz'].lower()
```

## 4. Benefícios Esperados

1. **Para o Usuário:**
   - Pode inserir descrições simples
   - Sistema ajuda a criar propostas de valor
   - Menos frustrações com rejeições

2. **Para o Sistema:**
   - StoryBrand sempre terá contexto rico
   - Maior taxa de sucesso do pipeline
   - Narrativas mais específicas e relevantes

3. **Para o Negócio:**
   - Melhor qualidade dos anúncios gerados
   - Maior satisfação do usuário
   - Diferencial competitivo

## 5. Riscos e Mitigações

### Risco: Over-creativity
- **Problema:** LangExtract inventa demais
- **Mitigação:** Few-shots conservadores, validação ainda rejeita absurdos

### Risco: Inconsistência
- **Problema:** Enriquecimentos diferentes para mesma entrada
- **Mitigação:** Exemplos consistentes, cache de resultados

### Risco: Performance
- **Problema:** Mais processamento do LLM
- **Mitigação:** Cache agressivo, otimizar prompts

## 6. Métricas de Sucesso

- Taxa de aceitação de descrições genéricas > 80%
- Comprimento médio de `o_que_a_empresa_faz` > 60 caracteres
- Score de completude StoryBrand > 0.8
- Satisfação do usuário com sugestões > 4/5

## 7. Implementação Faseada

### Fase 1: Ajuste de Prompts (1 dia)
- Modificar prompt base
- Adicionar 3-4 exemplos de enriquecimento

### Fase 2: Validação Adaptativa (1 dia)
- Ajustar `_is_transformational_description`
- Criar testes unitários

### Fase 3: Integração e Testes (2 dias)
- Testar com entradas reais
- Ajustar few-shots baseado em resultados

### Fase 4: Deploy e Monitoramento (1 dia)
- Deploy com feature flag
- Monitorar métricas de qualidade

## 8. Conclusão

Esta mudança transforma o `user_extract_data.py` de um **validador restritivo** em um **assistente inteligente** que ajuda o usuário a articular sua proposta de valor.

É a diferença entre:
- ❌ "Sua descrição é muito genérica, tente novamente"
- ✅ "Entendi sua empresa! Que tal essa descrição: [proposta enriquecida]?"

**Isso é usar LangExtract em seu potencial máximo!**