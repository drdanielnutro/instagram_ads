# Relatório de Auditoria Técnica: `generate_transformation_images`

## 1. Mapa de Fluxo Completo

### A. Visão Geral

O processo de geração de imagens é orquestrado pelo `ImageAssetsAgent` em `app/agent.py`. Este agente é acionado após a montagem do JSON final da campanha (`final_code_delivery`).

O fluxo de execução é o seguinte:

1.  **`ImageAssetsAgent` (`app/agent.py`)**:
    *   Lê o `state` para obter o JSON final (`final_code_delivery`).
    *   Extrai as variações do anúncio.
    *   Para cada variação, extrai os três prompts: `prompt_estado_atual`, `prompt_estado_intermediario`, e `prompt_estado_aspiracional`.
    *   Obtém metadados de imagens de referência (personagem e produto) do `state`.
    *   Chama `generate_transformation_images` para cada variação.

2.  **`generate_transformation_images` (`app/tools/generate_transformation_images.py`)**:
    *   Recebe os três prompts e os metadados das imagens de referência.
    *   Carrega as imagens de referência do Google Cloud Storage (GCS) usando `_load_reference_image`.
    *   **Modifica os prompts** usando templates definidos em `app/config.py`.
    *   Prepara os payloads para três chamadas separadas ao modelo de imagem.
    *   Chama `_call_model` para cada uma das três etapas (atual, intermediário, aspiracional).

3.  **`_call_model` (`app/tools/generate_transformation_images.py`)**:
    *   Formata o payload final com os prompts e as imagens.
    *   Envia a requisição para o modelo Gemini (`gemini-2.5-flash-image`).
    *   Extrai a imagem da resposta.

4.  **`_upload_image` (`app/tools/generate_transformation_images.py`)**:
    *   Faz o upload da imagem gerada para o GCS.
    *   Gera uma URL assinada para a imagem.

5.  **`ImageAssetsAgent` (`app/agent.py`)**:
    *   Recebe as URIs das imagens geradas.
    *   Atualiza o JSON final (`final_code_delivery`) com as URIs das imagens.

### B. Decisões sobre anexos (imagens)
*   **`generate_transformation_images`**: A decisão de anexar imagens é feita com base na existência dos objetos `reference_character` e `reference_product`.
*   **`_load_reference_image`**: Valida se a GCS URI começa com "gs://" antes de tentar carregar a imagem.

### C. Formato e Transporte das Imagens
*   As imagens são carregadas como objetos `Image.Image` e então convertidas para bytes no formato PNG.
*   Elas são enviadas ao modelo como `types.Part.from_bytes` com `mime_type="image/png"`. Não há uso de `Part.from_uri`.
*   As URIs `gs://` são usadas para carregar as imagens, mas não são diretamente enviadas ao modelo.

### G. Cenário e Composição (estado_intermediário)
*   O template para o estado intermediário (`image_intermediate_prompt_template`) contém instruções fixas para manter a consistência visual: "Keep the same person, clothing, environment, framing and lighting. Show determination and focus."

## 2. Tabela de Variáveis e Decisões

| Variável | Função | Propósito |
| --- | --- | --- |
| `state["final_code_delivery"]` | `ImageAssetsAgent` | Fonte do JSON final com os prompts. |
| `state["reference_images"]` | `ImageAssetsAgent` | Contém os metadados das imagens de referência. |
| `reference_character` | `generate_transformation_images` | Metadados da imagem do personagem. |
| `reference_product` | `generate_transformation_images` | Metadados da imagem do produto. |
| `config.image_current_prompt_template` | `generate_transformation_images` | Template para modificar o prompt do estado atual. |
| `config.image_intermediate_prompt_template` | `generate_transformation_images` | Template para modificar o prompt do estado intermediário. |
| `config.image_aspirational_prompt_template` | `generate_transformation_images` | Template para modificar o prompt do estado aspiracional. |
| `config.image_aspirational_prompt_template_with_product` | `generate_transformation_images` | Template alternativo para o estado aspiracional quando há uma imagem de produto. |

## 3. Tabela Verdade (por etapa)

| Etapa | Imagem de Upload Personagem | Imagem de Upload Produto | Imagem Gerada Anterior | Prompt cita Imagem? | Onde é decidido |
| --- | --- | --- | --- | --- | --- |
| **`estado_atual`** | Anexada se `reference_character` existir | Anexada se `reference_product` existir | N/A | Sim, se a imagem de personagem existir | `generate_transformation_images` |
| **`estado_intermediario`** | Anexada se `reference_character` existir | Anexada se `reference_product` existir | `image_atual` é anexada | Não diretamente, mas a imagem é fornecida como contexto | `generate_transformation_images` |
| **`estado_aspiracional`** | Anexada se `reference_character` existir | Anexada se `reference_product` existir | `image_intermediario` é anexada | Sim, se a imagem de produto existir | `generate_transformation_images` |

## 4. Trechos de Código

### A. Como o Prompt é Montado

**`app/tools/generate_transformation_images.py`**:

```python
# Etapa 1 – estado atual
prompt_estado_atual = prompt_atual
if reference_character is not None and character_image is not None:
    prompt_estado_atual = config.image_current_prompt_template.format(
        prompt_atual=prompt_atual,
        character_labels=character_labels,
        character_summary=character_summary or character_labels,
    )
elif reference_product is not None and product_summary:
    prompt_estado_atual = (
        f"{prompt_atual} Highlight the approved product reference: {product_summary}."
    )

# Etapa 2 – intermediário (usa imagem base)
transform_prompt_inter = config.image_intermediate_prompt_template.format(
    prompt_intermediario=prompt_intermediario
)

# Etapa 3 – aspiracional (usa imagem intermediária)
if reference_product is not None and product_image is not None:
    transform_prompt_asp = (
        config.image_aspirational_prompt_template_with_product.format(
            prompt_aspiracional=prompt_aspiracional,
            product_labels=product_labels,
            product_summary=product_summary or product_labels,
        )
    )
else:
    transform_prompt_asp = config.image_aspirational_prompt_template.format(
        prompt_aspiracional=prompt_aspiracional
    )
```

### B. Como as Imagens são Anexadas

**`app/tools/generate_transformation_images.py`**:

```python
# Etapa 1
stage_one_inputs: list[Any] = []
if character_image is not None:
    stage_one_inputs.append(character_image)
if product_image is not None:
    stage_one_inputs.append(product_image)
stage_one_inputs.append(prompt_estado_atual)
image_atual = await _call_model(stage_one_inputs)

# Etapa 2
stage_two_inputs: list[Any] = [image_atual]
if character_image is not None:
    stage_two_inputs.append(character_image)
if product_image is not None:
    stage_two_inputs.append(product_image)
stage_two_inputs.append(transform_prompt_inter)
image_intermediario = await _call_model(stage_two_inputs)

# Etapa 3
stage_three_inputs: list[Any] = [image_intermediario]
if product_image is not None:
    stage_three_inputs.append(product_image)
if character_image is not None:
    stage_three_inputs.append(character_image)
stage_three_inputs.append(transform_prompt_asp)
image_aspiracional = await _call_model(stage_three_inputs)
```

## 5. Checklist de Auditoria

*   **Os prompts são usados “como vieram”?**
    *   **Não.** Eles são modificados por templates. (`app/tools/generate_transformation_images.py`)

*   **Alguma função os altera?**
    *   **Sim.** `generate_transformation_images` os altera. (`app/tools/generate_transformation_images.py`)

*   **Há lógica condicional para anexos?**
    *   **Sim.** A lógica para anexar imagens de referência e imagens geradas anteriormente existe em `generate_transformation_images`. (`app/tools/generate_transformation_images.py`)

*   **Há envio de LABELS?**
    *   **Não.** O código lê os labels de `ReferenceImageMetadata`, mas não os envia para o modelo de imagem. Eles são usados para preencher os templates de prompt.

*   **Há reuso entre etapas?**
    *   **Sim.** A imagem do `estado_atual` é usada no `estado_intermediario`, e a imagem do `estado_intermediario` é usada no `estado_aspiracional`. (`app/tools/generate_transformation_images.py`)
