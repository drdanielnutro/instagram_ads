# 🔍 AUDITORIA: Afirmações do Codex sobre Sistema de Prompts Dinâmicos

**Data:** 2025-10-13
**Objetivo:** Validar tecnicamente as afirmações do Codex sobre como o pipeline usa referências visuais de forma dinâmica

---

## 📊 RESUMO EXECUTIVO

**Status geral:** ✅ **TODAS AS AFIRMAÇÕES VERIFICADAS E CONFIRMADAS**

Das 7 afirmações principais do Codex sobre o sistema de prompts dinâmicos:
- **7/7 (100%)** são tecnicamente precisas
- **0** imprecisões encontradas
- **0** omissões críticas
- Código-fonte confirma implementação completa conforme descrito

---

## 🔬 ANÁLISE DETALHADA POR AFIRMAÇÃO

### 1️⃣ Preflight resolve e injeta metadados

**Afirmação do Codex:**
> "Quando ENABLE_REFERENCE_IMAGES=true, o /run_preflight lê os IDs enviados, recupera metadados do cache (resolve_reference_metadata) e monta initial_state["reference_images"] com GCS URI, labels, descrição do usuário, flags de SafeSearch e resumos já prontos para prompting"

**Verificação no código:**

**Arquivo:** `app/server.py:556-628`

```python
# Linha 569-593
if config.enable_reference_images:
    character_payload = reference_images_payload.get("character") or {}
    product_payload = reference_images_payload.get("product") or {}

    character_metadata = resolve_reference_metadata(character_payload.get("id"))
    product_metadata = resolve_reference_metadata(product_payload.get("id"))

    reference_images_state = {
        "character": merge_user_description(
            character_metadata, character_payload.get("user_description")
        ),
        "product": merge_user_description(
            product_metadata, product_payload.get("user_description")
        ),
    }

    initial_state["reference_images"] = reference_images_state

    summary = build_reference_summary(reference_images_state, raw_payload)
    initial_state["reference_image_summary"] = summary
    initial_state["reference_image_character_summary"] = summary.get("character")
    initial_state["reference_image_product_summary"] = summary.get("product")
    initial_state["reference_image_safe_search_notes"] = summary.get(
        "safe_search_notes"
    )
```

**Status:** ✅ **CONFIRMADO**

**Detalhes adicionais encontrados:**
- Também injeta campos individuais: `reference_image_character_gcs_uri`, `reference_image_character_labels`, `reference_image_character_user_description`
- Mesmos campos para produto (linhas 610-627)
- Log estruturado para auditoria (linhas 630+)

---

### 2️⃣ COPY_DRAFT recebe referências aprovadas

**Afirmação do Codex:**
> "COPY_DRAFT recebe as linhas 'Referências aprovadas disponíveis' com os resumos a serem usados narrativamente"

**Verificação no código:**

**Arquivo:** `app/agent.py:1240-1288`

```python
# Linhas 1283-1290
  Referências aprovadas disponíveis:
  - Personagem: {reference_image_character_summary}
  - Produto/serviço: {reference_image_product_summary}
  Diretrizes condicionais:
  - Se houver personagem aprovado, alinhe a narrativa à descrição real e mantenha tom consistente com as imagens.
  - Se somente o produto existir, destaque atributos reais e **não invente** personagens ou histórias não fornecidas.
  - Quando ambos estiverem presentes, conecte persona e produto de forma coerente nas três variações.
```

**Status:** ✅ **CONFIRMADO**

**Detalhes adicionais encontrados:**
- Instruções condicionais claramente definidas para 3 cenários: só personagem, só produto, ambos
- Placeholders dinâmicos são substituídos em tempo de execução

---

### 3️⃣ VISUAL_DRAFT injeta placeholders e exige preservação

**Afirmação do Codex:**
> "VISUAL_DRAFT injeta {reference_image_character_summary}, {reference_image_product_summary} e as notas de SafeSearch em todos os campos, exigindo preservação do personagem e integração do produto quando existirem, além do bloco de verificação em Markdown"

**Verificação no código:**

**Arquivo:** `app/agent.py:1289-1323`

```python
# Linhas 1300-1303 (exemplo de um dos 3 prompts)
"prompt_estado_atual": "OBRIGATÓRIO: prompt técnico em inglês descrevendo somente a cena 1 (estado atual), com emoção negativa clara, postura coerente e cenário alinhado ao problema, sempre com a mesma persona. Se {reference_image_character_summary} existir, preserve traços físicos (tom de pele, cabelo, formato do rosto) e cite explicitamente que se trata da mesma pessoa. Termine com `Emotion: despair` para rastrear a expressão aplicada.",

# Linhas 1309-1312 (referências explícitas)
  Referências visuais disponíveis:
  - Personagem: {reference_image_character_summary}
  - Produto: {reference_image_product_summary}
  - SafeSearch: {reference_image_safe_search_notes}

# Linhas 1314-1323 (bloco condicional em Markdown)
  ```markdown
  if reference_image_character_summary:
      prompt_visual = (
          "Describe the same {reference_image_character_summary} person, preserve skin tone, hair texture, facial structure;"
          " adapt expression to each stage (Emotion: despair → Emotion: determined → Emotion: joyful)."
      )
  else:
      prompt_visual = original_visual_draft_instruction
  ```
```

**Status:** ✅ **CONFIRMADO**

**Detalhes adicionais encontrados:**
- Instruções específicas para preservar: tom de pele, textura de cabelo, estrutura facial
- Tracking de emoções através de marcadores explícitos: `Emotion: despair`, `Emotion: determined`, `Emotion: joyful`
- Produto mencionado em prompts intermediário e aspiracional (linhas 1302-1303)

---

### 4️⃣ Final assembly preserva metadados seguros

**Afirmação do Codex:**
> "A instrução do final_assembler reforça que, quando houver referências, cada variação deve incluir visual.reference_assets com ID, gcs_uri, labels e descrição (nunca signed_url)"

**Verificação no código:**

**Arquivo:** `app/agent.py:1783-1817`

```python
# Linhas 1785-1788
Referências visuais aprovadas (aplicar somente quando disponíveis):
- Personagem: {reference_image_character_summary} (GCS: {reference_image_character_gcs_uri}, Labels: {reference_image_character_labels}, Descrição: {reference_image_character_user_description})
- Produto: {reference_image_product_summary} (GCS: {reference_image_product_gcs_uri}, Labels: {reference_image_product_labels}, Descrição: {reference_image_product_user_description})
- SafeSearch: {reference_image_safe_search_notes}

# Linhas 1795-1802
  - Quando houver referências aprovadas, inclua `"reference_assets"` com:
    ```json
    {
      "character": {"id": "...", "gcs_uri": "...", "labels": [...], "user_description": "..."},
      "product": {"id": "...", "gcs_uri": "...", "labels": [...], "user_description": "..."}
    }
    ```
    Remova entradas nulas para tipos não fornecidos e **nunca exponha `signed_url`**.
```

**Status:** ✅ **CONFIRMADO**

**Detalhes adicionais encontrados:**
- Instrução explícita para remover signed_url (segurança)
- Orientação para remover entradas nulas quando tipo não fornecido
- Instruções adicionais para manter narrativa coerente entre persona e produto (linhas 1813-1816)

---

### 5️⃣ Callback de persistência sanitiza dados

**Afirmação do Codex:**
> "O callback de persistência sanitiza os dados antes de salvar/subir, removendo URLs sensíveis e registrando TTL de Signed URL"

**Verificação no código:**

**Arquivo:** `app/callbacks/persist_outputs.py:58-109`

```python
# Função sanitize_reference_images (linhas 58-109)
def sanitize_reference_images(state: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a sanitized copy of reference image metadata for persistence/logging."""

    if not isinstance(state, Mapping):
        return {}

    reference_images = state.get("reference_images")
    if not isinstance(reference_images, Mapping):
        return {}

    sensitive_exact = {"signed_url"}  # Linha 68 - Remove signed_url
    sensitive_suffixes = ("_token", "_tokens")
    sensitive_prefixes = ("raw_",)

    sanitized: dict[str, Any] = {}
    ttl_seconds = int(getattr(config, "image_signed_url_ttl", 0) or 0)  # Linha 73

    for ref_type, raw_entry in reference_images.items():
        # ... sanitização ...

        # Linhas 91-97 - Calcula e registra expiração
        uploaded_at_dt = _parse_uploaded_at(uploaded_at_value)
        if uploaded_at_dt is not None:
            entry["uploaded_at"] = uploaded_at_dt.isoformat()
            if ttl_seconds:
                expires_at = uploaded_at_dt + timedelta(seconds=ttl_seconds)
                entry["signed_url_expires_at"] = expires_at.isoformat()
```

**Chamada em persist_final_delivery (linha 124):**
```python
sanitized_reference_images = sanitize_reference_images(state)
```

**Status:** ✅ **CONFIRMADO**

**Detalhes adicionais encontrados:**
- Remove não apenas `signed_url`, mas também qualquer campo com sufixo `_token`, `_tokens` ou prefixo `raw_`
- Calcula e persiste timestamp de expiração da signed URL
- Registra TTL no metadata (linha 219-221)
- Logs estruturados incluem informações sanitizadas (linhas 240-257)

---

### 6️⃣ ImageAssetsAgent valida payload e injeta metadados

**Afirmação do Codex:**
> "O ImageAssetsAgent valida o payload, grava indicadores character_reference_used/product_reference_used, injeta visual.reference_assets no JSON e passa os metadados para generate_transformation_images"

**Verificação no código:**

**Arquivo:** `app/agent.py:448-713`

```python
# Linhas 450-475 - Carrega e valida metadados de referência
reference_images_state = state.get("reference_images") or {}
character_metadata: ReferenceImageMetadata | None = None
product_metadata: ReferenceImageMetadata | None = None
reference_parse_errors: list[str] = []

if isinstance(reference_images_state, dict) and reference_images_state:
    character_payload = reference_images_state.get("character") or None
    if character_payload:
        try:
            character_metadata = ReferenceImageMetadata.model_validate(
                character_payload
            )
        except ValidationError as exc:
            reference_parse_errors.append(
                f"character reference invalid: {exc.errors()}"
            )
    # ... mesmo para product ...

# Linhas 484-485 - Inicializa indicadores
state["character_reference_used"] = False
state["product_reference_used"] = False

# Linhas 653-674 - Injeta reference_assets no JSON
if character_metadata or product_metadata:
    reference_assets: Dict[str, Any] = {}
    if character_metadata:
        reference_assets["character"] = {
            "id": character_metadata.id,
            "gcs_uri": character_metadata.gcs_uri,
            "labels": character_metadata.labels,
            "user_description": character_metadata.user_description,
        }
    if product_metadata:
        reference_assets["product"] = {
            "id": product_metadata.id,
            "gcs_uri": product_metadata.gcs_uri,
            "labels": product_metadata.labels,
            "user_description": product_metadata.user_description,
        }
    if reference_assets:
        visual["reference_assets"] = reference_assets

# Linhas 676-700 - Passa metadados completos para generate_transformation_images
metadata = {
    "user_id": user_id,
    "session_id": session_identifier,
    "formato": variation.get("formato"),
    "aspect_ratio": visual.get("aspect_ratio"),
    "character_summary": state.get("reference_image_character_summary"),
    "product_summary": state.get("reference_image_product_summary"),
}

task = asyncio.create_task(
    generate_transformation_images(
        prompt_atual=visual["prompt_estado_atual"],
        prompt_intermediario=visual["prompt_estado_intermediario"],
        prompt_aspiracional=visual["prompt_estado_aspiracional"],
        variation_idx=idx,
        metadata=metadata,
        progress_callback=progress_callback,
        reference_character=character_metadata,
        reference_product=product_metadata,
    )
)
```

**Status:** ✅ **CONFIRMADO**

**Detalhes adicionais encontrados:**
- Validação usando Pydantic (ReferenceImageMetadata.model_validate)
- Erros de parsing são coletados e reportados sem bloquear pipeline
- Log estruturado completo (linhas 582-597)
- Progress tracking via queue assíncrona (linhas 648-651)

---

### 7️⃣ Geração de imagens usa texto E imagens de referência

**Afirmação do Codex:**
> "A função de geração carrega as imagens aprovadas (prefere Signed URL, cai para GCS), ajusta os prompts com templates que incluem os resumos, envia as imagens de referência como contexto do Gemini e reaproveita o resultado entre as três etapas"

**Verificação no código:**

**Arquivo:** `app/tools/generate_transformation_images.py`

#### 7.1 Carregamento de imagens (linhas 68-104)

```python
def _load_reference_image(metadata: ReferenceImageMetadata) -> Image.Image:
    """Load a reference image either from a signed URL or directly from GCS."""

    if not metadata.gcs_uri:
        raise ValueError("Reference metadata must include a GCS URI")

    # Prefer signed URL when available to avoid requiring elevated permissions.
    if metadata.signed_url:
        try:
            response = requests.get(metadata.signed_url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Failed to download reference image {metadata.id} via signed URL"
            ) from exc
        with BytesIO(response.content) as buffer:
            image = Image.open(buffer)
            return image.convert("RGB")

    # Fallback to direct GCS access.
    # ... código GCS ...
```

#### 7.2 Templates dinâmicos (linhas 328-339)

```python
# Linha 331-335 - Template aplicado dinamicamente
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
```

**Templates em `app/config.py:90-105`:**

```python
image_current_prompt_template: str = (
    "Use the approved character reference to anchor identity (summary: {character_summary};"
    " labels: {character_labels}). {prompt_atual}"
)
image_intermediate_prompt_template: str = (
    "Transform this scene to show the immediate positive action: {prompt_intermediario}. "
    "Keep the same person, clothing, environment, framing and lighting. Show determination and focus."
)
image_aspirational_prompt_template: str = (
    "Show the same person after some time has passed achieving the successful outcome: {prompt_aspiracional}. "
    "Preserve identity and core features while allowing improvements in environment, wardrobe and expression."
)
image_aspirational_prompt_template_with_product: str = (
    "Integrate the approved product reference ({product_summary}; labels: {product_labels}) into the success scene. "
    "{prompt_aspiracional}"
)
```

#### 7.3 Envio ao Gemini com contexto visual (linhas 341-356)

```python
# Linhas 341-346 - Etapa 1 inclui imagens de referência
stage_one_inputs: list[Any] = []
if character_image is not None:
    stage_one_inputs.append(character_image)
if product_image is not None:
    stage_one_inputs.append(product_image)
stage_one_inputs.append(prompt_estado_atual)

image_atual = await _call_model(stage_one_inputs)

# Linhas 363-368 - Etapa 2 usa imagem gerada + referências
stage_two_inputs: list[Any] = [image_atual]
if character_image is not None:
    stage_two_inputs.append(character_image)
if product_image is not None:
    stage_two_inputs.append(product_image)
stage_two_inputs.append(transform_prompt_inter)

# Linhas 395-400 - Etapa 3 usa imagem intermediária + referências
stage_three_inputs: list[Any] = [image_intermediario]
if product_image is not None:
    stage_three_inputs.append(product_image)
if character_image is not None:
    stage_three_inputs.append(character_image)
stage_three_inputs.append(transform_prompt_asp)
```

**Status:** ✅ **CONFIRMADO**

**Detalhes adicionais encontrados:**
- Ordem estratégica: etapa 1 usa referências, etapa 2 reutiliza imagem gerada + referências, etapa 3 reutiliza intermediária + referências
- Tentativa com signed URL primeiro, fallback para GCS direto
- Templates configuráveis via variáveis de ambiente
- Metadados retornados incluem indicadores de uso (linhas 425-443)

---

## 🎯 CONCLUSÃO TÉCNICA

### Precisão das Afirmações

O Codex apresentou uma **descrição tecnicamente precisa e completa** do sistema de prompts dinâmicos. Todas as 7 afirmações principais foram verificadas e confirmadas no código-fonte.

### Pontos Fortes da Implementação

1. **Arquitetura em Camadas:** Separação clara entre resolução de metadados (preflight) → injeção em prompts (agent.py) → geração visual (tools)
2. **Segurança:** Sanitização consistente de URLs sensíveis antes de persistência
3. **Flexibilidade:** Suporta cenários parciais (só personagem, só produto, ambos, nenhum)
4. **Rastreabilidade:** Logs estruturados em todas as camadas
5. **Robustez:** Fallbacks quando signed URLs falham, validação de schemas Pydantic

### Fluxo Completo Verificado

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. PREFLIGHT (server.py:556-628)                                │
│    • Resolve reference IDs via cache                             │
│    • Gera summaries para prompting                               │
│    • Injeta em initial_state[reference_images]                   │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. COPY_DRAFT (agent.py:1283-1290)                              │
│    • Substitui {reference_image_character_summary}               │
│    • Substitui {reference_image_product_summary}                 │
│    • Aplica diretrizes condicionais                              │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. VISUAL_DRAFT (agent.py:1300-1323)                            │
│    • Injeta referências em todos os 3 prompts visuais            │
│    • Exige preservação de traços físicos                         │
│    • Inclui SafeSearch notes                                     │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. FINAL_ASSEMBLY (agent.py:1785-1817)                          │
│    • Monta variations[] com reference_assets                     │
│    • Remove signed_url (segurança)                               │
│    • Preserva id, gcs_uri, labels, user_description              │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. IMAGE_ASSETS_AGENT (agent.py:653-700)                        │
│    • Valida metadados via Pydantic                               │
│    • Injeta reference_assets no JSON                             │
│    • Passa metadados + imagens para geração                      │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. GENERATE_TRANSFORMATION_IMAGES (tools/..:328-410)            │
│    • Carrega imagens (signed URL → fallback GCS)                 │
│    • Aplica templates dinâmicos                                  │
│    • Envia imagens + texto ao Gemini                             │
│    • Reutiliza outputs entre etapas (1→2→3)                      │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. PERSIST_OUTPUTS (callbacks/persist_outputs.py:58-109, 124)   │
│    • Sanitiza reference_images                                   │
│    • Remove signed_url e tokens                                  │
│    • Calcula/registra expiração (TTL)                            │
│    • Salva localmente + GCS                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Recomendação

**✅ As afirmações do Codex podem ser consideradas confiáveis como documentação técnica do sistema.**

O sistema está completamente implementado conforme descrito, com:
- ✅ Prompts dinâmicos baseados em contexto de referências
- ✅ Injeção condicional em múltiplas camadas
- ✅ Segurança (sanitização de URLs sensíveis)
- ✅ Flexibilidade (suporta cenários parciais)
- ✅ Rastreabilidade (logs em todas as fases)

---

## 📎 REFERÊNCIAS DE CÓDIGO

| Afirmação | Arquivo | Linhas | Status |
|-----------|---------|--------|--------|
| Preflight resolve metadados | `app/server.py` | 556-628 | ✅ |
| COPY_DRAFT recebe referências | `app/agent.py` | 1283-1290 | ✅ |
| VISUAL_DRAFT injeta placeholders | `app/agent.py` | 1300-1323 | ✅ |
| Final assembly preserva metadados | `app/agent.py` | 1785-1817 | ✅ |
| Callback sanitiza dados | `app/callbacks/persist_outputs.py` | 58-109, 124 | ✅ |
| ImageAssetsAgent valida/injeta | `app/agent.py` | 448-475, 653-700 | ✅ |
| generate_transformation_images usa refs | `app/tools/generate_transformation_images.py` | 68-104, 328-410 | ✅ |
| Templates dinâmicos | `app/config.py` | 90-105 | ✅ |

---

**Auditado por:** Claude (Sonnet 4.5)
**Método:** Leitura direta do código-fonte + verificação linha por linha
**Confiabilidade:** Alta (código-fonte é fonte primária de verdade)
