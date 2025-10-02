# Plano de Suporte a Upload de Imagem de Referência na Fase Aspiracional

## 1. Objetivo e Cenário Atual
- **Objetivo**: permitir que anunciantes enviem opcionalmente uma imagem (ex.: peça de roupa real) e que o estágio aspiracional utilize essa referência além do prompt textual e da imagem intermediária.
- **Fluxo atual**:
  - UI solicita apenas texto; nenhum upload é aceito.
  - O preflight (`app/server.py:301-393`) popula o estado inicial sem campos de imagem.
  - `ImageAssetsAgent` (`app/agent.py:310-577`) chama `generate_transformation_images` (`app/tools/generate_transformation_images.py:209-293`) que gera três imagens sequenciais usando somente prompts.
  - O modelo aspiracional recebe `image_intermediario` como contexto + `prompt_aspiracional` (configurado em `app/config.py:57-102`).

## 2. Requisitos Funcionais
1. **Upload opcional** na UI com validação de formato (PNG/JPEG) e tamanho máximo (ex.: 5 MB).
2. **Persistência temporária** do arquivo em GCS sob pasta segregada por usuário/sessão.
3. **Propagação de metadados** até o pipeline (`state['reference_image']` com URI assinado ou `gs://…`).
4. **Geração aspiracional condicionada**: quando o campo existir, a chamada do modelo deve incluir a imagem de referência e ajustar o prompt.
5. **Fallback**: se upload falhar ou o arquivo for inválido, a geração deve seguir com o comportamento atual (somente prompts).
6. **Segurança e limpeza**: garantir que uploads sejam autenticados, sem sobrescrever arquivos alheios; opcionalmente remover artefatos órfãos via job.

## 3. Alterações por Camada

### 3.1 Frontend (React + Vite)
Arquivos principais: `frontend/src/App.tsx`, componentes em `frontend/src/components/**`.
- Adicionar campo de upload (componente `<input type="file">` ou Dropzone) limitado a uma imagem.
- Mostrar preview e permitir remoção antes de enviar.
- Ao enviar, chamar novo endpoint `/upload/reference-image` (ver seção 3.2) e armazenar o identificador retornado.
- Incluir o identificador ao disparar `/run_preflight` e `/run` (`payload.initial_state.reference_image_uri`).
- Atualizar validações e mensagens de erro para lidar com upload opcional.

### 3.2 Backend FastAPI (`app/server.py`)
- Criar rota `POST /upload/reference-image` que receba `UploadFile` (FastAPI) e utilize `app/utils/gcs.py` para enviar ao bucket configurado.
  - Validar `content_type` (`image/png`, `image/jpeg`), tamanho máximo, e checar quota básica.
  - Salvar no bucket apontado por `DELIVERIES_BUCKET` ou novo `REFERENCE_IMAGES_BUCKET`; retorno deve conter `gcs_uri` + `signed_url` curta (para preview) + um `reference_image_id`.
- Atualizar `run_preflight` para aceitar `reference_image_uri` e propagar para `initial_state` quando presente.
- Ajustar log estruturado para rastrear uploads (`event: reference_image_upload`).

### 3.3 Estado e Pipeline dos Agentes (`app/agent.py`)
- Garantir que o estado carregado em `FeatureOrchestrator` contenha `reference_image_uri` (ou nomenclatura semelhante).
- No `ImageAssetsAgent._run_async_impl` (`app/agent.py:316-577`):
  - Recuperar `state.get("reference_image_uri")`.
  - Ao chamar `generate_transformation_images`, passar novo argumento opcional (`reference_image_uri`).
  - Registrar em `summary` quais variações usaram imagem de referência.

### 3.4 Ferramenta de Geração (`app/tools/generate_transformation_images.py`)
- Alterar assinatura para receber `reference_image_uri: str | None`.
- Se o campo existir:
  1. Baixar o arquivo do GCS (utilizando `storage.Client().bucket(..).blob(..).download_as_bytes()`).
  2. Abrir com `PIL.Image.open(BytesIO(...)).convert("RGB")` (mesma lógica usada para imagens geradas).
  3. Na etapa aspiracional, chamar `_call_model([image_intermediario, user_reference_image, transform_prompt_asp])` ao invés de apenas `[image_intermediario, transform_prompt_asp]`.
- Incluir try/except para falhas de download; se ocorrer erro, logar `logger.warning` e continuar com fluxo padrão.
- Atualizar retorno `meta` indicando `reference_image_used: bool`.

### 3.5 Ajustes de Prompt (`app/config.py` e estado)
- Definir `config.image_aspirational_prompt_template_with_reference` com texto que explicite o uso da imagem enviada (ex.: “Use the clothing from the provided reference image …”).
- Em `ImageAssetsAgent`, decidir qual template usar com base na presença de `reference_image_uri`.
- Opcional: armazenar o nome/tipo da peça para personalizar prompts (se UI coletar esse metadado).

### 3.6 Persistência e Auditoria
- Incluir a URI da imagem de referência nas saídas persistidas (`app/callbacks/persist_outputs.py`) para acompanhamento.
- Atualizar logs estruturados e audit trail com eventos `reference_image_attached` (similar ao que é feito no fallback).

## 4. Segurança e Compliance
- **Autenticação**: reutilizar mecanismo já usado para as demais chamadas; o endpoint de upload deve respeitar CORS e exigir token/API key existente.
- **Limpeza**: definir política para remover imagens não referenciadas em 24–48 h (job externo ou cron Cloud Functions).
- **DoS Storage**: limitar tamanho e implementar contagem de uploads por sessão.
- **Conteúdo inseguro**: opcionalmente integrar serviço de SafeSearch / Vision API para bloquear imagens inadequadas.

## 5. Testes
- **Unit Tests**:
  - Novo módulo `tests/unit/tools/test_generate_transformation_images.py` com mocks da `storage.Client` garantindo que, quando `reference_image_uri` existe, `_call_model` recebe três partes.
  - Testes para fallback em caso de download falho.
- **Integration Tests**:
  - Simulação do fluxo com `TestClient` do FastAPI: upload → preflight → execução parcial para validar que `reference_image_uri` chega ao estado do agente.
  - Teste e2e manual (CLI/Streamlit) verificando se a imagem aspiracional reflete a peça enviada.
- **Frontend**:
  - Atualizar testes de componentes (React Testing Library ou Cypress se disponível) cobrindo upload e remoção da imagem.

## 6. Passo a Passo de Implementação
1. Implementar endpoint de upload e utilitário de GCS (se necessário, criar helper em `app/utils/gcs.py`).
2. Ajustar preflight e orquestração para aceitar o novo campo.
3. Atualizar UI com campo de upload, preview e integração com o endpoint.
4. Evoluir `ImageAssetsAgent` e `generate_transformation_images` com suporte ao parâmetro opcional.
5. Revisar templates de prompt e logging.
6. Criar testes unitários/integrados.
7. Documentar no README (seção de geração de imagens) e no manual interno.

## 7. Riscos e Mitigações
- **Erro ao baixar imagem**: tratar via fallback silencioso para não travar a geração.
- **Referência imprópria**: integrar checagens (Vision API) ou alertas manuais.
- **Tempo extra de geração**: uso de imagem adicional pode aumentar latência; monitorar e, se necessário, ajustar `config.image_generation_timeout` (`app/config.py:57-104`).
- **Armazenamento**: growth de arquivos não limpos → planejar limpeza periódica.

## 8. Próximos Passos
- Validar com stakeholders se o upload deve ficar restrito a determinados formatos de anúncio (ex.: Feed moda).
- Estimar esforço de UI/Backend/Agentes e agendar iterações.
- Após MVP, avaliar extensão para múltiplas referências (ex.: aspiração + moodboard) se houver demanda.
