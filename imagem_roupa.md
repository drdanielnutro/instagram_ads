# Plano Estendido — Referências Visuais de Personagem e Produto/Serviço

## 1. Visão Geral
- Evoluir o fluxo de geração de imagens para aceitar **dois uploads opcionais** (personagem e produto/serviço) e integrá-los nos estágios adequados do pipeline (`app/tools/generate_transformation_images.py`).
- Garantir segurança, consistência narrativa e alinhamento entre os prompts gerados em `app/agent.py` e as imagens finais.
- Utilizar **Vertex AI Vision** (SafeSearch + Label/Object Detection) para classificar as imagens logo após o upload, armazenando metadados no estado do agente e em GCS.

## 2. Motivação
- Permitir que anunciantes “vistam” um personagem real com o produto fornecido (ex.: vestir uma modelo com a peça da coleção).
- Reduzir discrepância entre o que o prompt descreve e o que a imagem sintetiza, aumentando confiabilidade para segmentos de moda, beleza, serviços premium etc.

## 3. Escopo Funcional
1. Upload de **Personagem** (imagem base usada no estágio “estado atual”).
2. Upload de **Produto/Serviço** (incorporado no estágio “estado aspiracional”).
3. Integração opcional: se nenhum upload for fornecido, o pipeline permanece idêntico ao atual.
4. Análise automática das imagens (conteúdo impróprio + rótulos principais).
5. Exposição de metadados (labels, descrições) para os agentes de copy/visual.
6. Registro das referências usadas no JSON final e nos logs estruturados.

## 4. Modelo de Dados & Estado
- Novo módulo sugerido: `app/schemas/reference_assets.py` contendo:
  ```python
  class ReferenceImageMetadata(BaseModel):
      id: str
      type: Literal["character", "product"]
      gcs_uri: str
      signed_url: str
      labels: list[str]
      safe_search_flags: dict[str, str]
      user_description: str | None = None
      uploaded_at: datetime
  ```
- Estado compartilhado montado em `run_preflight` antes da criação da sessão ADK:
  ```python
  initial_state["reference_images"] = {
      "character": ReferenceImageMetadata | None,
      "product": ReferenceImageMetadata | None,
  }
  initial_state["reference_image_summary"] = {
      "character": "Modelo feminina, cabelos cacheados...",
      "product": "Bolsa de couro caramelo com alça metálica...",
  }
  initial_state["reference_image_character_summary"] = initial_state["reference_image_summary"].get("character")
  initial_state["reference_image_product_summary"] = initial_state["reference_image_summary"].get("product")
  ```
  (apenas quando as referências existirem). Esses campos precisam estar presentes no dicionário retornado por `/run_preflight` para que o ADK os replique em `state` após `createSession`.
- Resolver IDs recebidos por `run_preflight` usando utilitário dedicado `app/utils/reference_cache.py`:
  ```python
  from app.utils.reference_cache import resolve_reference_metadata
  ```
  `resolve_reference_metadata(reference_id: str | None) -> ReferenceImageMetadata | None` deve consultar um cache em memória com TTL configurável, retornar `None` para IDs ausentes e registrar logs estruturados para diagnósticos.
- No mesmo módulo, implementar `build_reference_summary(reference_images: dict[str, ReferenceImageMetadata | None], payload: dict) -> dict[str, str | None]` agregando labels e descrições (`user_description`) e produzindo frases curtas usadas pelos prompts.
- Expor também `cache_reference_metadata(metadata: ReferenceImageMetadata) -> None` para ser chamado logo após cada upload, garantindo que `resolve_reference_metadata` encontre os valores durante o `run_preflight` seguinte.
- JSON final (produzido pelo `final_assembler` em `app/agent.py:1023-1049`):
  ```json
  "visual": {
    ...,
    "reference_assets": {
      "character": {"gcs_uri": "gs://...", "labels": [...]},
      "product": {"gcs_uri": "gs://...", "labels": [...]}
    }
  }
  ```
  (apenas quando as referências existirem).

## 5. UI (React + Vite)
- Arquivos relevantes: `frontend/src/App.tsx`, `frontend/src/components/*`.
- Criar componente dedicado `frontend/src/components/ReferenceUpload.tsx` com propriedades `type="character" | "product"`.
- Validações no cliente: extensões (`.png`, `.jpg`, `.jpeg`), limite de 5 MB, dimensões mínimas.
- Fluxo recomendado para upload:
  1. Permitir que o usuário selecione o arquivo e envie `POST /upload/reference-image` imediatamente com `FormData` (`file`, `type`, `userId?`, `sessionId?`).
  2. Tratar `userId` e `sessionId` como opcionais; quando ausentes, o backend gera `reference_id` e associa aos metadados do upload.
  3. Armazenar a resposta (`referenceId`, `signedUrl`, `labels`) em um store (ex.: hook `useReferenceImages`) para reaproveitar no submit principal.
- Utilizar o campo existente `foco` no formulário para capturar a descrição textual do produto/elemento visual obrigatório quando não houver imagem.
- Atualizar `handleSubmit` (`frontend/src/App.tsx`) para enviar payload contendo o texto original e as referências:
  ```json
  {
    "text": "...",
    "reference_images": {
      "character": {"id": "ref-123", "user_description": "Modelo plus size"},
      "product": {"id": "ref-456", "user_description": "Bolsa caramelo P"}
    }
  }
  ```
  Certifique-se de montar esse objeto a partir do store/hook de referências, enviando apenas os uploads efetivamente realizados.

## 6. Backend — Endpoints FastAPI (`app/server.py`)
### 6.1 Upload
- Adicionar rota perto das demais definições (após `run_preflight` para manter agrupamento):
  ```python
  @app.post("/upload/reference-image")
  async def upload_reference_image(
      file: UploadFile = File(...),
      type: Literal["character", "product"] = Form(...),
      user_id: str | None = Form(default=None),
      session_id: str | None = Form(default=None),
  ) -> dict:
      ...
  ```
- Passos internos:
  1. Validar `content_type` e tamanho (`file.spool_max_size`).
  2. Subir para GCS via helper `app/utils/gcs.py` (nova função `upload_reference_image`).
  3. Chamar Vision AI (`app/utils/vision.py`, nova função `analyze_reference_image`) para SafeSearch + Label/Object detection.
  4. Bloquear upload se `adult | violence | racy >= LIKELY`.
  5. Persistir metadados em cache (dicionário em memória com TTL ou Datastore opcional) e retornar `{"id": ..., "signed_url": ..., "labels": [...]}`.
  6. Adicionar `google-cloud-vision>=3.4.0` (ou a biblioteca Vertex AI equivalente) a `requirements.txt`/`uv.lock` e documentar que `make install` deve ser reexecutado.

### 6.2 Preflight (`run_preflight`) — `app/server.py:300-393`
- Atualizar o modelo Pydantic usado pelo endpoint (`RunPreflightRequest` ou equivalente) para aceitar `reference_images` opcional além de `text`/flags existentes.
- Resolver IDs para metadados completos antes de montar `initial_state`:
  ```python
  reference_images = payload.get("reference_images", {})
  initial_state["reference_images"] = {
      "character": resolve_reference_metadata(reference_images.get("character")),
      "product": resolve_reference_metadata(reference_images.get("product")),
  }
  initial_state["reference_image_summary"] = build_reference_summary(initial_state["reference_images"], payload)
  initial_state["reference_image_character_summary"] = initial_state["reference_image_summary"].get("character")
  initial_state["reference_image_product_summary"] = initial_state["reference_image_summary"].get("product")
  ```
- `build_reference_summary` deve combinar labels + descrições do usuário, retornando strings curtas para cada tipo. Caso não haja metadados, devolver `None` e manter o campo ausente no initial state.
- Antes de finalizar o endpoint, executar `initial_state.update(...)` para incluir essas chaves no payload retornado por `/run_preflight`.

## 7. Agentes (`app/agent.py`)
### 7.1 Prompts de geração
- **VISUAL_DRAFT (c. linha 880)**: adicionar placeholders planos `{reference_image_character_summary}` e `{reference_image_product_summary}` e instruir o agente a alinhar narrativa com as referências disponíveis.
- **COPY_DRAFT (c. linha 830)**: caso haja labels de produto, sugerir que headline/corpo mencionem a peça real usando as mesmas chaves planas.
- **final_assembler (linhas 1023-1049)**: reforçar no prompt que variações devem incorporar `visual.reference_assets` quando existirem e que `descricao_imagem` precisa citar o produto real, consumindo os campos planos adicionados ao `initial_state`.

### 7.2 `ImageAssetsAgent._run_async_impl` (`app/agent.py:316-577`)
- Recuperar `reference_images = state.get("reference_images") or {}` garantindo dicionário vazio quando não houver uploads.
- Montar argumentos para `generate_transformation_images` apenas quando os metadados existirem:
  ```python
  reference_character = reference_images.get("character")
  reference_product = reference_images.get("product")
  assets = await generate_transformation_images(
      ..., reference_character=reference_character, reference_product=reference_product
  )
  ```
- Registrar em `summary` se as referências foram usadas ou se houve fallback.

### 7.3 Logs/Auditoria
- Inserir eventos adicionais usando `logger.info` (ex.: `"reference_image_attached"`) e armazenar no estado (`state['image_generation_audit']`).

## 8. Ferramenta de Geração (`app/tools/generate_transformation_images.py`)
### 8.1 Assinatura
- Alterar função (linhas 209-293) para aceitar:
  ```python
  async def generate_transformation_images(...,
      reference_character: ReferenceImageMetadata | None = None,
      reference_product: ReferenceImageMetadata | None = None,
  )
  ```
- Criar helper `_load_reference_image(metadata: ReferenceImageMetadata) -> Image.Image` que faça download de `metadata.gcs_uri` via `storage.Client` (com cache simples em dicionário local).

### 8.2 Etapas
- **Etapa 1 (estado atual)**:
  - Se `reference_character`, usar `_call_model([character_image, prompt_atual_com_labels])`.
  - `prompt_atual_com_labels` deriva de `config.image_current_prompt_template` + labels/descrição.
- **Etapa 2 (intermediária)**: manter fluxo atual.
- **Etapa 3 (aspiracional)**:
  - Montar `prompt_aspiracional_enriquecido` com labels do produto e contexto (“incorpore a bolsa marrom da imagem de referência”).
  - Se `reference_product`, chamar `_call_model([image_intermediario, product_image, prompt_aspiracional_enriquecido])`.
- Em caso de falha no download ou no modelo, registrar `logger.warning` e prosseguir sem a referência (garantia de fallback).
- Retorno `meta` deve incluir flags `"character_reference_used"` e `"product_reference_used"`.

## 9. Configuração & Templates (`app/config.py`)
- Adicionar novas strings:
  ```python
  image_current_prompt_template = (
      "Use the provided character reference ({character_labels}). {prompt_atual}"
  )
  image_aspirational_prompt_template_with_product = (
      "Integrate the product from the reference image ({product_labels}). {prompt_aspiracional}"
  )
  ```
- Em `ImageAssetsAgent`, selecionar o template conforme existência das referências.

## 10. Observabilidade & Persistência
- Atualizar `app/callbacks/persist_outputs.py:45-56` para receber `state` no `persist_final_delivery`, extrair `state.get("reference_images")`, remover campos sensíveis (`signed_url`, tokens) e salvar o restante em `meta["reference_images"]`. Ajustar os testes correspondentes para validar o novo contrato.
- Garantir que `logger.log_struct` (em `app/server.py` e `app/agent.py`) capture uploads, decisões de SafeSearch e uso efetivo na geração.
- Configurar TTL curto nas `signed_url`; armazenar apenas `gcs_uri` no JSON final e documentar como essa política se relaciona com `config.image_signed_url_ttl`.

## 11. Estratégia de Testes
- **Unitários**:
  - `tests/unit/utils/test_vision.py`: mocks da Vision API (SafeSearch + labels).
  - `tests/unit/tools/test_generate_transformation_images.py`: verificar chamadas a `_call_model` com referências.
  - `tests/unit/agent/test_image_assets_agent.py`: garantir passagem dos metadados corretos.
- **Integração**:
  - `tests/integration/api/test_reference_upload.py`: upload → análise → resposta.
  - `tests/integration/agents/test_reference_pipeline.py`: pipeline parcial com fixtures de referência.
- **Frontend**:
  - Atualizar testes de componentes/upload (React Testing Library) e cenários em Cypress se existente.
- **QA manual**:
  - Cenários com apenas personagem, apenas produto, ambos, e nenhum.

## 12. Riscos e Mitigações
| Risco | Mitigação |
|-------|-----------|
| Vision AI indisponível | fallback que rejeita upload com mensagem amigável; monitorar via logging |
| Latência adicional | medir tempos; ajustar `config.image_generation_timeout` se necessário |
| Inconsistência narrativa | reforçar prompts (copy + visual) com labels e descrições; incluir QA manual inicialmente |
| Crescimento de arquivos em GCS | planejar job de limpeza (Cloud Scheduler + função que remove uploads sem uso em X dias) |

## 13. Roadmap Sugerido
1. **Infra**: endpoint de upload + Vision integration + schema `ReferenceImageMetadata`.
2. **UI**: componentes de upload e integração com novo endpoint.
3. **Estado & Prompts**: ajustes em `run_preflight`, prompts VISUAL/COPY, `final_assembler`.
4. **Ferramenta de imagem**: suporte aos novos parâmetros e fallback.
5. **Validação/Logs**: persistência e auditoria.
6. **Testes**: unitários, integração e QA manual.
7. **Documentação**: atualizar `README.md` (seção imagem) e materiais internos.

---

**Conclusão**: esta versão do plano mapeia arquivos e trechos específicos, define estruturas de estado, detalha integrações (Vision AI + GCS) e estabelece passos de implementação/testes. Com a adoção das referências visuais, o pipeline passa a combinar criatividade controlada com fidelidade ao produto real, entregando valor direto para verticais que precisam de consistência visual.
