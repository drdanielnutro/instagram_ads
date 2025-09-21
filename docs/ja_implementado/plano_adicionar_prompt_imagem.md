# Plano Expandido: Adicionar Campo `prompt_imagem` ao Sistema

## Visão Geral
Adicionar o campo `prompt_imagem` ao modelo de dados para armazenar prompts técnicos de geração de imagem com IA (Midjourney, DALL-E, Stable Diffusion), mantendo separação clara entre descrição editorial (`descricao_imagem`) e prompt técnico (`prompt_imagem`).

## Estratégia: Opção B (TASK-009 separada)
Criar nova tarefa dedicada para geração do prompt técnico, garantindo separação de responsabilidades e melhor manutenibilidade.

## Arquivos a Modificar

### 1. `/Users/institutorecriare/VSCodeProjects/instagram_ads/app/agent.py`

#### Modificação 1.1: Modelo Pydantic (linha 58-61)
```python
class AdVisual(BaseModel):
    descricao_imagem: str
    prompt_imagem: str  # NOVO: Prompt técnico para geração de imagem com IA
    aspect_ratio: Literal["9:16", "1:1", "4:5", "16:9"]
```

#### Modificação 1.2: Prompt do code_generator (linha 569-576)
```python
- VISUAL_DRAFT:
  {
    "visual": {
      "descricao_imagem": "Descrição detalhada da imagem estática...",
      "prompt_imagem": "Prompt técnico para IA: estilo, composição, iluminação, mood...",
      "aspect_ratio": "definido conforme especificação do formato"
    },
    "formato": "{formato_anuncio}"
  }
```

#### Modificação 1.3: Prompt do final_assembler (linha 704)
```python
- "visual": { "descricao_imagem", "prompt_imagem", "aspect_ratio" } (sem duracao - apenas imagens)
```

#### Modificação 1.4: Prompt do final_validator (linha 732-733)
```python
   visual{descricao_imagem,prompt_imagem,aspect_ratio}, cta_instagram, fluxo, referencia_padroes, contexto_landing
```

### 2. `/Users/institutorecriare/VSCodeProjects/instagram_ads/app/plan_models/fixed_plans.py`

#### Modificação 2.1: Adicionar TASK-009 para Reels (após linha 93)
```python
{
    "id": "TASK-009",
    "category": "VISUAL_DRAFT",
    "title": "Prompt técnico para geração de imagem (Reels)",
    "description": (
        "Gerar prompt_imagem: prompt técnico detalhado para ferramentas de IA (Midjourney/DALL-E). "
        "Incluir: estilo artístico, composição, iluminação, paleta de cores, mood, câmera/lente, "
        "qualidade (8K, photorealistic, etc). Formato: inglês, separado por vírgulas. "
        "Exemplo: 'professional photography, warm lighting, rule of thirds, bokeh background, "
        "vibrant colors, modern aesthetic, 8K resolution, shot on Canon R5'."
    ),
    "file_path": f"{base_dir}/TASK-009.json",
    "action": "CREATE",
    "dependencies": ["TASK-005"],
}
```

#### Modificação 2.2: Atualizar TASK-008 dependencies para Reels (linha 116)
```python
"dependencies": ["TASK-002", "TASK-004", "TASK-006", "TASK-007", "TASK-009"],
```

#### Modificação 2.3: Adicionar TASK-009 para Stories (após linha 193)
```python
{
    "id": "TASK-009",
    "category": "VISUAL_DRAFT",
    "title": "Prompt técnico para geração de imagem (Stories)",
    "description": (
        "Gerar prompt_imagem: prompt técnico para IA com foco em Stories. "
        "Considerar: composição vertical, elementos bold, cores vibrantes, "
        "simplicidade visual, alto contraste. Formato: inglês técnico. "
        "Exemplo: 'vertical composition, bold typography, high contrast, minimalist design, "
        "bright colors, mobile-first aesthetic, clean background'."
    ),
    "file_path": f"{base_dir}/TASK-009.json",
    "action": "CREATE",
    "dependencies": ["TASK-005"],
}
```

#### Modificação 2.4: Atualizar TASK-008 dependencies para Stories (linha 216)
```python
"dependencies": ["TASK-002", "TASK-004", "TASK-006", "TASK-007", "TASK-009"],
```

#### Modificação 2.5: Adicionar TASK-009 para Feed (após linha 290)
```python
{
    "id": "TASK-009",
    "category": "VISUAL_DRAFT",
    "title": "Prompt técnico para geração de imagem (Feed)",
    "description": (
        "Gerar prompt_imagem: prompt técnico para IA otimizado para Feed. "
        "Incluir: composição equilibrada, espaço negativo, profissionalismo, "
        "clareza visual, paleta harmônica. Formato: inglês técnico. "
        "Exemplo: 'professional composition, balanced layout, negative space, "
        "corporate aesthetic, soft lighting, premium quality, detailed textures'."
    ),
    "file_path": f"{base_dir}/TASK-009.json",
    "action": "CREATE",
    "dependencies": ["TASK-005"],
}
```

#### Modificação 2.6: Atualizar TASK-008 dependencies para Feed (linha 312)
```python
"dependencies": ["TASK-002", "TASK-004", "TASK-006", "TASK-007", "TASK-009"],
```

### 3. `/Users/institutorecriare/VSCodeProjects/instagram_ads/tests/test_refactored.py`

#### Modificação 3.1: Adicionar validação do novo campo (linha 62-63)
```python
print(f"  - Tem descricao_imagem: {'✓' if ad.get('visual', {}).get('descricao_imagem') else '✗'}")
print(f"  - Tem prompt_imagem: {'✓' if ad.get('visual', {}).get('prompt_imagem') else '✗'}")
print(f"  - Sem duração: {'✓' if 'duracao' not in ad.get('visual', {}) else '✗'}")
```

### 4. `/Users/institutorecriare/VSCodeProjects/instagram_ads/app/format_specifications.py` (Opcional)

#### Adicionar especificações para prompt_imagem em cada formato:
```python
"visual": {
    "aspect_ratio": "9:16",
    "prompt_specs": {
        "style": "dynamic, high-energy, modern",
        "technical": "vertical composition, mobile-optimized"
    },
    "notas": [...]
}
```

## Validações de Consistência

1. **Separação Clara**:
   - `descricao_imagem`: Texto descritivo para humanos ("Homem sorrindo em escritório moderno")
   - `prompt_imagem`: Prompt técnico para IA ("corporate photography, male executive, genuine smile, modern office, glass walls, natural lighting, shallow DOF, 85mm lens")

2. **Dependências Corretas**: TASK-009 sempre depende de TASK-005 (precisa da descrição antes do prompt)

3. **Formato-Específico**: Cada formato tem instruções diferentes para o prompt técnico

4. **Validação Completa**: Final validator verifica presença de ambos os campos

## Benefícios da Abordagem

1. **Modularidade**: Cada tarefa tem responsabilidade única
2. **Reprocessamento**: Se prompt falhar, não precisa refazer descrição
3. **Evolução**: Fácil adicionar parâmetros futuros (modelo preferido, negative prompts, seeds)
4. **Rastreabilidade**: Clara separação entre falhas de descrição vs prompt
5. **Qualidade**: Prompts especializados para cada formato

## Ordem de Execução

1. Atualizar modelo Pydantic em `agent.py`
2. Adicionar TASK-009 nos 3 planos fixos
3. Atualizar dependencies da TASK-008
4. Ajustar prompts dos agentes
5. Atualizar validações
6. Adicionar testes

## Riscos Mitigados

- Sem hardcoding do número de tarefas
- Pipeline suporta tarefas adicionais dinamicamente
- Separação clara evita sobrecarga cognitiva dos agentes
- Validações garantem presença do novo campo

## Exemplos de Output Esperado

### Antes (atual):
```json
{
  "visual": {
    "descricao_imagem": "Profissional de saúde sorrindo em consultório moderno",
    "aspect_ratio": "9:16"
  }
}
```

### Depois (com prompt_imagem):
```json
{
  "visual": {
    "descricao_imagem": "Profissional de saúde sorrindo em consultório moderno",
    "prompt_imagem": "medical professional, genuine smile, modern clinic interior, clean aesthetic, soft natural lighting, shallow depth of field, 85mm lens, warm color palette, professional photography, high resolution, rule of thirds composition",
    "aspect_ratio": "9:16"
  }
}
```

## Notas de Implementação

1. O campo `prompt_imagem` deve sempre estar em inglês para compatibilidade com ferramentas de IA
2. Manter consistência entre `descricao_imagem` (português) e `prompt_imagem` (inglês técnico)
3. TASK-009 pode evoluir para incluir parâmetros específicos de cada ferramenta de IA
4. Considerar adicionar TASK-010 futuramente para QA específico do prompt técnico