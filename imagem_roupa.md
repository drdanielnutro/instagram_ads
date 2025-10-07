# Plano Estendido — Referências Visuais de Personagem e Produto/Serviço

## 0. Visão Geral & Metas
- **Contexto ampliado**: referências visuais enviadas pelos anunciantes são opcionais, mas quando aprovadas pelo fluxo automático (Google SafeSearch) precisam ser consumidas obrigatoriamente por todos os agentes responsáveis por prompt, geração visual e montagem do pacote final. O plano deve deixar inequívoco como essas condicionais funcionam para evitar interpretações diferentes entre implementadores.
- **Flag de rollout**: a lógica descrita nesta atualização só é aplicada quando `ENABLE_REFERENCE_IMAGES=true` (default `False` para rollout gradual). Com a flag desativada, o pipeline ignora `reference_images`, mantendo o comportamento legado do ADK (três prompts sequenciais obrigatórios, `contexto_landing` em todas as variações e ausência de placeholders novos).
- **Objetivo**: habilitar uploads opcionais de imagens de personagem e produto/serviço, reaproveitando os metadados (SafeSearch + labels) em todo o pipeline de geração de anúncios (copy + visual + imagens finais), garantindo diferenciação clara dos prompts conforme a disponibilidade de cada referência.
- **Abordagem**: introduzir novos schemas e cache compartilhado, estender endpoints/backend e atualizar agentes e prompts, mantendo compatibilidade quando nenhuma referência for enviada e reforçando políticas de uso obrigatório após aprovação.
- **Cenários suportados**:
  - `Cenário A – sem referências`: manter comportamento atual sem placeholders ou instruções adicionais.
  - `Cenário B – apenas personagem`: instruir os prompts a mencionar explicitamente o personagem aprovado, preservando características físicas e permitindo alteração de expressão facial conforme diretrizes do ADK.
  - `Cenário C – apenas produto/serviço`: enfatizar atributos do produto real usando labels/descrições aprovadas, sem menções ao personagem.
  - `Cenário D – personagem e produto`: combinar ambos os resumos garantindo coerência narrativa entre copy e visual.
- **Política de uso obrigatório**: qualquer referência liberada pelo SafeSearch deve ser registrada no cache, aplicada nos prompts (`VISUAL_DRAFT`, `COPY_DRAFT`, `final_assembler`) e refletida no `visual.reference_assets`. Rejeições precisam ser logadas, e o plano documenta como proceder para manter o fluxo sem referências.
- **Compromissos de prompting**: quando `reference_image_character_summary` existir, os prompts devem incluir instruções que preservem aparência (tom de pele, cabelo, formato do rosto), mencionem o personagem pelo nome/descrição fornecida e liberem mudança de expressão facial em função do comando do ADK para cada imagem sequencial.
- **Indicadores de sucesso**: QA (automático e manual) deve comprovar que prompts finais mencionam explicitamente a presença do personagem quando disponível, que mudanças de expressão solicitadas se refletem nos comandos enviados aos modelos e que a ausência de referências não introduz regressões.

### Diagnóstico inicial
Para orientar as próximas fases, foi realizada uma análise estruturada do documento vigente seguindo o procedimento descrito em `plano_atualizacao_imagem_roupa.md`. As lacunas mapeadas foram agrupadas em três categorias principais.

| Seção | Descrição da lacuna | Categoria | Impacto esperado | Prioridade de correção | Seção do código impactada (linhas atuais) |
|-------|----------------------|-----------|------------------|------------------------|-------------------------------------------|
| Visão Geral & Metas | Não havia menção explícita aos quatro cenários de uso (0/1/2 referências) nem orientação sobre obrigatoriedade pós-aprovação. | Opcionalidade | Stakeholders podem presumir comportamento sempre obrigatório ou sempre ausente, gerando implementação inconsistente. | Alta | `app/config.py:52-190` (flags e TTL) |
| Fase 4 – Pipeline de Agents & Prompts | Diretrizes de prompting não diferenciavam personagem vs. produto, tampouco davam instruções sobre preservação de aparência ou mudança de expressão. | Adaptação de expressão/prompt | Risco de o ADK gerar imagens inconsistentes com o personagem enviado ou ignorar o ativo. | Alta | `app/agent.py:420-1218`, `app/tools/generate_transformation_images.py:209-290` |
| Fase 6 – Testes Automatizados & QA | Critérios de QA não exigiam evidências de uso obrigatório após aprovação nem testes específicos para expressões faciais. | Uso obrigatório pós-aprovação | Cobertura de testes insuficiente para detectar regressões no pipeline visual. | Média | `tests/**/*`, `artifacts/qa/reference-images` |

> Metodologia: leitura sequencial de `imagem_roupa.md`, classificação das lacunas em `Opcionalidade`, `Uso obrigatório pós-aprovação` e `Adaptação de expressão/prompt`, seguida de confrontação com os requisitos adicionais fornecidos pelo usuário nesta conversa.

---
## Fase 1 – Schemas e Cache de Referências

### Entregáveis
- **1.1** Criar `app/schemas/reference_assets.py` com:
  - **1.1.1** `ReferenceImageMetadata` (campos: `id`, `type`, `gcs_uri`, `signed_url`, `labels`, `safe_search_flags`, `user_description | None`, `uploaded_at`).
  - **1.1.2** Métodos `model_dump(mode="json")` e `to_state_dict()` para garantir serialização.
- **1.2** Criar `app/utils/reference_cache.py` com funções:
  - **1.2.1** `cache_reference_metadata(metadata: ReferenceImageMetadata) -> None`.
  - **1.2.2** `resolve_reference_metadata(reference_id: str | None) -> ReferenceImageMetadata | None`.
  - **1.2.3** `merge_user_description(metadata: ReferenceImageMetadata | None, description: str | None) -> dict | None`.
  - **1.2.4** `build_reference_summary(reference_images: dict[str, dict | None], payload: dict) -> dict[str, str | None]`.
  - **1.2.5** Implementar cache em memória com TTL configurável (`config.reference_cache_ttl_seconds`) e ganchos para futura troca por Redis/Datastore.
- **1.3** Criar módulo `app/utils/vision.py` com helper assíncrono `analyze_reference_image(..., type: Literal["character", "product"]) -> ReferenceImageMetadata` encapsulando chamadas ao Vertex AI Vision (SafeSearch + labels).
- **1.4** Criar helper `upload_reference_image` em `app/utils/gcs.py` (novo) que utilizará `analyze_reference_image` (criado nesta fase) antes de devolver o ID ao cliente.
- **1.5** Preparar testes unitários base (serão detalhados na Fase 6).

### Dependências existentes
- `BaseModel` (Pydantic) importado no topo de `app/agent.py` (linhas 24-40).
- Utilitário `resolve_state` em `app/utils/session_state.py:10-32` (já utilizado por callbacks).
- Configurações genéricas em `app/config.py` (feature flags e tempo de TTL).

### Integrações planejadas
1. `/run_preflight` (Fase 2) consumirá `resolve_reference_metadata` e `build_reference_summary` (criados nesta fase).
2. Endpoint `/upload/reference-image` (Fase 2) chamará `upload_reference_image` e `analyze_reference_image` (ambos criados nesta fase).
3. `ImageAssetsAgent` (Fase 4) reidratará `ReferenceImageMetadata` a partir dos dicionários retornados pelas funções desta fase.

### Critérios de aceitação
- [ ] Arquivo `app/schemas/reference_assets.py` criado com classes tipadas e métodos helper.
- [ ] Cache em `app/utils/reference_cache.py` suporta `cache`, `resolve`, `merge` e `build_summary` com TTL configurável.
- [ ] Módulo `app/utils/vision.py` exporta `analyze_reference_image` e trata respostas/erros do Vertex AI Vision.
- [ ] Helper `upload_reference_image` em `app/utils/gcs.py` integra-se ao módulo de visão sem expor dados sensíveis.
- [ ] Testes unitários cobrindo cache e visão (Fase 6) executados com sucesso.

---
## Fase 2 – Backend: Upload & Preflight

### Entregáveis
- **2.1** Implementar endpoint `POST /upload/reference-image` em `app/server.py`:
  - **2.1.1** Assinatura com `UploadFile`, `type: Literal["character", "product"]`, `user_id | None`, `session_id | None`.
  - **2.1.2** Validar content-type/tamanho, enviar ao GCS (`upload_reference_image`), analisar via Vision (`analyze_reference_image`), aplicar SafeSearch e `cache_reference_metadata` (Fase 1), devolver `{ "id", "signed_url", "labels" }`.
- **2.2** Criar schema `RunPreflightRequest` (novo módulo `app/schemas/run_preflight.py`) substituindo parse manual atual.
- **2.3** Modificar `run_preflight` em `app/server.py:162-410`:
  - **2.3.1** Reutilizar `RunPreflightRequest`.
  - **2.3.2** Resolver metadados via `resolve_reference_metadata` (criada na Fase 1).
  - **2.3.3** Construir `initial_state["reference_images"]`, `reference_image_summary`, `reference_image_character_summary`, `reference_image_product_summary` e `reference_image_safe_search_notes`.
  - **2.3.4** Garantir retorno enriquecido sem manipulações externas.
  - **2.3.5** Documentar comportamento com `ENABLE_REFERENCE_IMAGES=false` versus true.
- **2.4** Registrar logs estruturados (`logger.log_struct`) para uploads e preflight.

### Dependências existentes
- Função `run_preflight` atual em `app/server.py:162-410` (retorna `initial_state`).
- Logging estruturado (`logger.log_struct`) já usado em preflight (`app/server.py:189-320`).
- Configs `ENABLE_NEW_INPUT_FIELDS` e `ENABLE_STORYBRAND_FALLBACK` (`app/config.py:120-170`).

### Modificações planejadas (resumo/diff)
```diff
# app/server.py
+@app.post("/upload/reference-image")
+async def upload_reference_image(...):
+    metadata = analyze_reference_image(...)
+    cache_reference_metadata(metadata)
+    return {"id": metadata.id, ...}
 
-async def run_preflight(payload: dict = Body(...)) -> dict:
+@app.post("/run_preflight")
+async def run_preflight(request: RunPreflightRequest) -> dict:
     ...
-    initial_state = {...}
+    reference_images = request.reference_images or {}
+    initial_state["reference_images"] = {
+        "character": merge_user_description(
+            resolve_reference_metadata(reference_images.get("character", {}).get("id")),
+            reference_images.get("character", {}).get("user_description"),
+        ),
+        ...
+    }
```

### Critérios de aceitação
- [ ] `/upload/reference-image` retorna 200 com ID válido e bloqueia imagens `LIKELY` em SafeSearch.
- [ ] `/run_preflight` enriquece `initial_state` quando IDs válidos são enviados; mantém comportamento atual quando não há referências.
- [ ] Logs estruturados registram uploads e uso de cache.
- [ ] Teste de integração (Fase 6) cobre upload → cache → preflight.

---
## Fase 3 – Frontend (React + Vite)

### Entregáveis
- **3.1** Criar componente `frontend/src/components/ReferenceUpload.tsx` com props `type="character" | "product"`, validações de extensão e tamanho (máx. 5 MB).
- **3.2** Criar hook/store `useReferenceImages` em `frontend/src/state/referenceImages.ts` para gerenciar IDs e descrições.
- **3.3** Atualizar `frontend/src/App.tsx` (linhas ~420-520):
  - **3.3.1** Submeter uploads imediatamente para `/upload/reference-image` (Fase 2) via `FormData`.
  - **3.3.2** No `handleSubmit`, incluir `reference_images` no payload com `{ id, user_description }` apenas quando houver upload.
- **3.4** Atualizar `frontend/src/components/InputForm.tsx` para usar o novo componente e capturar descrições.
- **3.5** Adicionar mensagens de feedback (sucesso/erro) relacionadas ao upload de referências.

### Dependências existentes
- Função `handleSubmit` em `frontend/src/App.tsx:423-498`.
- Campo `foco` já presente em `frontend/src/components/InputForm.tsx:250-270`.

### Integrações planejadas
- Payload submetido continuará compatível com `/run` atual, apenas adicionando `reference_images` (consumido na Fase 2).
- Hooks serão usados na Fase 6 (testes de frontend).

### Critérios de aceitação
- [ ] Uploads exibem progresso, validam extensões e retornos do backend.
- [ ] `handleSubmit` envia `reference_images` somente quando disponíveis.
- [ ] Plano de testes de frontend (RTL/Cypress) cobre cenários com e sem uploads.
- [ ] UX mantém comportamento original quando recursos não são usados.

---
## Fase 4 – Integração no Pipeline de Agents & Prompts

### Objetivo revisado
Detalhar, na própria descrição do pipeline, como os agentes devem consumir dados de referências visuais e como os prompts se adaptam a cada cenário, mantendo compatibilidade com as instruções determinísticas já estabelecidas para `code_generator`, `code_reviewer` e `code_refiner`.

#### 4.1 Placeholders e estrutura de dados
- **4.1.1** Atualizar prompts em `app/agent.py` para incluir placeholders condicionais derivados da Fase 2:
  - **4.1.1.1** `VISUAL_DRAFT` (`app/agent.py:1108-1120`): `{reference_image_character_summary}`, `{reference_image_product_summary}`, `{reference_image_safe_search_notes}`.
  - **4.1.1.2** `COPY_DRAFT` (`app/agent.py:1092-1100`): `{reference_image_product_summary}` e `{reference_image_character_summary}` quando relevantes para consistência narrativa.
  - **4.1.1.3** `final_assembler` (`app/agent.py:1576-1614`): injetar `reference_images.<type>.gcs_uri`, `.labels`, `.user_description` e preencher `visual.reference_assets` com metadados aprovados.
- **4.1.2** Atualizar `ImageAssetsAgent` (`app/agent.py:420-792`) para reidratar `ReferenceImageMetadata` via `model_validate`, armazenar flags `character_reference_used` e `product_reference_used` e garantir que o summary exponha quando uma referência foi descartada por reprovação do SafeSearch.
- **4.1.3** Atualizar `generate_transformation_images` (`app/tools/generate_transformation_images.py:209-290`) aceitando novos parâmetros opcionais para personagem/produto e centralizando carregamento de ativos no helper `_load_reference_image`.
- **4.1.4** Atualizar templates em `app/config.py` para introduzir `image_current_prompt_template` e `image_aspirational_prompt_template_with_product`, ativando-os apenas quando as referências correspondentes estiverem aprovadas.

#### 4.2 Diretrizes de prompting para personagem
- **4.2.1** Instruir que sempre que `reference_images.character.status == "approved"`:
  - **4.2.1.1** Os prompts nomeiem ou descrevam o personagem com base no resumo aprovado.
  - **4.2.1.2** As características físicas (tom de pele, cabelo, traços faciais, vestimenta principal) sejam preservadas explicitamente em cada uma das três imagens sequenciais (`prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional`).
  - **4.2.1.3** Seja adicionada instrução para permitir mudança de expressão facial conforme pedido pelo ADK: "render the same character now showing <emoção solicitada>".
  - **4.2.1.4** Logs do summary registrem qual emoção final foi aplicada em cada etapa.
- **4.2.2** Registrar no documento final uma lista de verificação em bloco de código Markdown (logo após esta subseção) com frases-modelo e condicionais, por exemplo:
  ```markdown
  if reference_image_character_summary:
      prompt_visual = (
          "Describe the same {reference_image_character_summary} person,"
          " preserve: skin tone, hair texture, facial structure;"
          " adapt expression to {requested_emotion}."
      )
  else:
      prompt_visual = original_visual_draft_instruction
  ```

#### 4.3 Diretrizes quando apenas produto estiver presente
- **4.3.1** Se apenas `reference_images.product` estiver aprovado:
  - **4.3.1.1** Remover qualquer menção a personagem dos prompts, reforçando atributos do produto (labels, materiais, uso principal).
  - **4.3.1.2** Adaptar `COPY_DRAFT` para destacar diferenciais do produto real, mantendo coerência com as imagens.
  - **4.3.1.3** Documentar fallback textual que reitera que a narrativa deve focar no produto sem inventar personagens ausentes.

#### 4.4 Cenários combinados e compatibilidade com instruções fixas
- **4.4.1** Quando ambos os ativos existirem, combinar resumos mantendo coerência (`personagem interage com produto`) e distribuir responsabilidades entre copy e visual.
- **4.4.2** Reafirmar que os agentes continuam produzindo exatamente três prompts sequenciais; os novos placeholders complementam, mas não substituem, `prompt_estado_atual`, `prompt_estado_intermediario` e `prompt_estado_aspiracional`.
- **4.4.3** Inserir nota explícita de que as instruções endurecidas dos agentes (`instrucoes_fixas_agentes.md`) permanecem válidas; quaisquer mudanças devem ser incrementais e não podem afrouxar os critérios de falha estabelecidos.
- **4.4.4** Atualizar referências de linha no documento para refletir o código atual: `code_reviewer` (`app/agent.py:1142-1203`), `code_refiner` (`app/agent.py:1205-1221`) e `final_assembler_instruction` (`app/agent.py:1576-1597`).

#### 4.5 Quadro comparativo de prompts por cenário

| Cenário | Personagem | Produto | Prompt `VISUAL_DRAFT` | Prompt `COPY_DRAFT` |
|---------|------------|---------|----------------------|--------------------|
| 0 referências | ❌ | ❌ | Reutilizar instruções atuais (3 cenas genéricas) sem placeholders extras. | Narrativa padrão baseada em `landing_page_context` e StoryBrand. |
| Apenas personagem | ✅ | ❌ | "Describe the same {reference_image_character_summary} person preserving physical traits; adjust expression according to {requested_emotion}." | Referenciar persona aprovada e sua jornada; evitar criação de produtos inexistentes. |
| Apenas produto | ❌ | ✅ | "Highlight the real product from {reference_image_product_summary}" as the main focus, sem citar personagens. | Destacar benefícios/atributos do produto real, mantendo o tom definido pelo ADK. |
| Personagem e produto | ✅ | ✅ | Combinar persona aprovada com produto, garantindo interação coerente e preservação física + emoção solicitada. | Storytelling completo unindo persona e produto, reforçando consistência copy/visual. |

#### 4.6 Exemplo guiado (antes/depois) – adaptação de expressão
```
Antes (sem referência):
- prompt_estado_atual: Render a customer trying the outfit in-store.

Depois (com personagem aprovado pedindo expressão triste):
- prompt_estado_atual: Render the same character from {reference_image_character_summary}, preserving facial features and hairstyle, now showing a sad expression while trying the outfit in-store.
```

### Entregáveis
- Seção reescrita com subtítulos 4.1–4.6, placeholders condicionais e quadro comparativo cobrindo os quatro cenários.
- Anexo de exemplo antes/depois incorporado, ilustrando mudança de expressão mantendo aparência.
- Referência explícita à compatibilidade com as instruções fixas dos agentes e aos três prompts sequenciais.

### Dependências existentes
- `ImageAssetsAgent` atual (`app/agent.py:420-792`).
- Função `generate_transformation_images` (`app/tools/generate_transformation_images.py:209-290`).
- Config `image_signed_url_ttl` declarada em `app/config.py:88` e sobrescrita via env em `app/config.py:170`.
- Instruções vigentes em `instrucoes_fixas_agentes.md` para `code_generator`, `code_reviewer` e `code_refiner`.

### Critérios de aceitação
- [ ] Subtópicos 4.1–4.6 documentam preservação de aparência e mudança de expressão facial para personagem aprovado.
- [ ] Tabela comparativa cobre os quatro cenários possíveis sem contradizer instruções existentes.
- [ ] `ImageAssetsAgent`, `generate_transformation_images` e templates possuem orientação textual clara para uso obrigatório após aprovação.
- [ ] Nota explícita assegura que os três prompts sequenciais e critérios de falha dos agentes permanecem válidos.

---
## Fase 5 – Observabilidade, Persistência e Sanitização

### Entregáveis
- **5.1** Refatorar `persist_final_delivery(callback_context)` (`app/callbacks/persist_outputs.py:35-141`):
  - **5.1.1** Criar helper `sanitize_reference_images(state: dict[str, Any]) -> dict[str, Any]` removendo `signed_url`, tokens e payloads crus da Vision.
  - **5.1.2** Persistir metadados sanitizados em `meta["reference_images"]` e nos logs.
  - **5.1.3** Manter assinatura atual (usa `resolve_state(callback_context)`).
- **5.2** Adicionar logs estruturados (`logger.log_struct`) nos pontos-chave:
  - **5.2.1** Upload (Fase 2), preflight (Fase 2), pipeline de agentes (Fase 4) e persistência (esta fase).
- **5.3** Avaliar TTL curto para `signed_url` via `config.image_signed_url_ttl` e documentar política.

### Dependências existentes
- `resolve_state` (`app/utils/session_state.py:10-32`).
- `clear_failure_meta` (`app/utils/delivery_status.py:110-124`).
- Logging com `logger.log_struct` já usado nos endpoints principais.

### Critérios de aceitação
- [ ] `persist_final_delivery` salva metadados sem campos sensíveis e mantém compatibilidade com callbacks existentes (`ImageAssetsAgent` e `final_assembler`).
- [ ] Logs estruturados exibem referências usadas e decisões do SafeSearch.
- [ ] Documentação de TTL e limpeza de signed URLs atualizada (Fase 7).

### 5.6 Mapa de implementação para a próxima etapa
- Preparar, ao final desta fase de documentação, um apêndice que será utilizado quando o desenvolvimento iniciar, contendo:
  - Sequência recomendada de implementação (Schemas/Cache → Backend → Frontend → Pipeline → Observabilidade/Testes → Docs/Rollout).
  - Linhas atuais de cada arquivo que servirão como ponto de referência para os diffs (ex.: `app/agent.py:1108-1120` para VISUAL_DRAFT, `app/agent.py:1576-1614` para final_assembler, `app/server.py:162-410` para run_preflight).
  - Checkpoints de testes após cada fase (unitários após Fase 1/2, integração após Fase 2, frontend após Fase 3, regressão completa e flag desativada após Fase 6).

---
## Fase 6 – Testes Automatizados & QA

### Entregáveis
- **Unit Tests**:
  - **6.1.1** `tests/unit/utils/test_reference_cache.py` (cache, TTL, merge com descrições).
  - **6.1.2** `tests/unit/utils/test_vision.py` (mocks do SafeSearch aprovando/reprovando e registrando notas utilizadas nos prompts).
  - **6.1.3** `tests/unit/tools/test_generate_transformation_images.py` (parâmetros com referências vs. fallback, verificando comandos de expressão facial por imagem sequencial).
  - **6.1.4** `tests/unit/agents/test_image_assets_agent.py` (reidratação de metadados, flags de summary e registro de emoções solicitadas).
  - **6.1.5** `tests/unit/callbacks/test_persist_outputs.py` (sanitização de `reference_images` e garantia de remoção de `signed_url`).
- **Integração**:
  - **6.2.1** `tests/integration/api/test_reference_upload.py`: upload → análise → cache → `/run_preflight` recuperando metadados no `initial_state`, cobrindo respostas aprovadas e reprovadas do SafeSearch.
  - **6.2.2** `tests/integration/agents/test_reference_pipeline.py`: pipeline parcial com referências, verificando JSON final, `reference_assets` e presença dos comandos de expressão gerados em cada prompt sequencial.
- **Frontend**:
  - **6.3.1** RTL tests para `ReferenceUpload` e `handleSubmit` com/sem uploads, cobrindo feedback ao usuário quando SafeSearch reprovar arquivos.
  - **6.3.2** Cenários Cypress (se suite existir) para formulário completo com evidência de envio condicional.
- **QA manual**:
  - **6.4.1** Roteiro com quatro cenários (nenhuma referência, apenas personagem, apenas produto, ambos) validando UX e resultados, incluindo captura de screenshots/logs dos prompts com mudança de expressão.
  - **6.4.2** Execução com `ENABLE_REFERENCE_IMAGES=false` garantindo 3/3 variações entregues, prompts completos e `contexto_landing` presente.
  - **6.4.3** Criação da pasta `artifacts/qa/reference-images` com exemplos antes/depois de prompts e imagens geradas, registrando emoção solicitada e resultado observado.

### Critérios de aceitação
- [ ] **6.5.1** `make test` cobre novas suites sem regressões e verifica comandos de expressão facial nos prompts.
- [ ] **6.5.2** Testes de integração validam ciclo completo (incluindo sanitização e branchs SafeSearch aprovado/reprovado).
- [ ] **6.5.3** Roteiro manual documenta prints/logs de cada cenário, evidenciando mudança de expressão quando personagem estiver disponível.
- [ ] **6.5.4** Execuções com `ENABLE_REFERENCE_IMAGES=false` comprovam ausência de regressões (3/3 variações entregues, prompts completos, `contexto_landing` presente).
- [ ] **6.5.5** Pasta `artifacts/qa/reference-images` contém exemplos antes/depois aprovados pelo QA.

---
## Fase 7 – Documentação & Rollout

### Entregáveis
- **7.1** Atualizar `README.md` (seção de geração de imagens) com fluxo de uploads, limitações (5 MB, formatos) e política de TTL.
- **7.2** Criar/atualizar playbooks internos (`docs/`) descrevendo auditoria (`state['image_generation_audit']`) e monitoramento.
- **7.3** Adicionar notas de migração (changelog) destacando schema `reference_images` no JSON final e novos endpoints.
- **7.4** Planejar estratégia de rollout (flag `ENABLE_REFERENCE_IMAGES` opcional em `app/config.py`) para ativar gradualmente.

### Critérios de aceitação
- [ ] **7.5.1** Documentação revisada pelo time.
- [ ] **7.5.2** Plano de rollback inclui desativar flag e limpar cache/GCS de uploads não usados.

---
## Dependências Externas e Configuração
- **8.1** `google-cloud-vision>=3.4.0` — adicionar a `requirements.txt` (linha nova) e `uv.lock`.
- **8.2** `google-cloud-storage` já presente (`requirements.txt:15`) – reutilizado.
- **8.3** Configurações novas em `app/config.py`:
  - **8.3.1** `reference_cache_ttl_seconds` (int, default 3600).
  - **8.3.2** `enable_reference_images` (bool, default `False` para rollout).

## Riscos & Mitigações
| Risco | Mitigação |
|-------|-----------|
| Indisponibilidade do Vision AI | Capturar exceções em `analyze_reference_image`, retornar erro amigável ao usuário e registrar log estruturado; fallback permite continuar sem referências. |
| Latência adicional de upload/análise | Medir tempos (logs de duração), ajustar `config.image_generation_timeout` e permitir operação sem referências. |
| Inconsistência narrativa entre copy/visual | Prompts (Fase 4) reforçam uso das labels; QA manual cobre cenários com e sem referências. |
| Crescimento de arquivos no GCS | Incluir job de limpeza (planejado em docs de rollout) para remover uploads não utilizados após TTL; documentação explicita política. |
| Cache em memória entre múltiplos workers | Abstrair utilitário permitindo futura troca por Redis/Datastore; documentar limitação e recomendar afinidade de sessão até adoção do backend compartilhado. |

---
## Checklist Final do Plano
- [ ] **9.1** Entregáveis usam verbos declarativos (Criar/Implementar/Modificar/Estender).
- [ ] **9.2** Dependências existentes possuem caminho e, quando relevante, intervalo de linhas.
- [ ] **9.3** Itens referenciados em fases posteriores indicam “(criado na Fase X)”.
- [ ] **9.4** Diffs ou resumos de modificações em arquivos existentes estão presentes.
- [ ] **9.5** Critérios de aceitação definidos para cada fase.
- [ ] **9.6** Dependências externas e flags documentadas.
- [ ] **9.7** Fluxo de testes cobre unitário, integração, frontend e QA manual.
- [ ] **9.8** Plano pode ser validado pelo `plan-code-validator` sem falsos P0.

---
## Resumo das Atualizações de Prompt
- **Opcionalidade**: documentação agora enumera explicitamente os quatro cenários possíveis (nenhum, apenas personagem, apenas produto, ambos) e descreve o comportamento esperado em cada fase, assegurando que uploads continuem opcionais.
- **Uso obrigatório pós-aprovação**: reforços textuais determinam que referências aprovadas pelo SafeSearch devem aparecer nos prompts (`VISUAL_DRAFT`, `COPY_DRAFT`, `final_assembler`), nos metadados (`visual.reference_assets`) e nos logs estruturados.
- **Adaptação de expressão**: diretrizes específicas instruem como preservar aparência e variar expressão facial nas três imagens sequenciais, com exemplos antes/depois e verificações automatizadas/QA.
- **Compatibilidade com agentes**: reiterada a manutenção das instruções determinísticas de `code_generator`, `code_reviewer` e `code_refiner`, destacando que os novos placeholders complementam — mas não substituem — os três prompts obrigatórios.
- **Rastreabilidade**: todas as lacunas mapeadas na tabela de diagnóstico inicial foram cobertas ao longo das fases 2–4; eventuais pendências futuras devem ser registradas explicitamente nesta seção.

---
## Resumo Executivo da Implementação
1. **Fase 1 (Fundação)**: schemas e cache para metadados de referência.
2. **Fase 2 (Backend)**: endpoint de upload + `/run_preflight` enriquecido.
3. **Fase 3 (Frontend)**: componentes de upload e payload estendido.
4. **Fase 4 (Pipeline)**: prompts, agentes e ferramenta de imagens incorporando referências.
5. **Fase 5 (Observabilidade)**: sanitização de persistência e logs.
6. **Fase 6 (Qualidade)**: testes automatizados e QA manual asseguram fluxo ponta a ponta.
7. **Fase 7 (Docs/Rollout)**: documentação e estratégia de ativação gradual.

Sequenciar dessa forma evita dependências circulares (schemas e cache devem existir antes de endpoints, que precisam estar prontos antes dos agentes, etc.) e garante rastreabilidade completa para validação automática e implementação por múltiplos times ou agentes.

---
## Checklist de Aprovação da Atualização
- [ ] **10.1** Confirmar presença e preenchimento da tabela "Lacunas de Detalhamento" logo após a Visão Geral.
- [ ] **10.2** Verificar que a seção 0 descreve os quatro cenários e a política de uso obrigatório pós-aprovação.
- [ ] **10.3** Revisar a Fase 4 para garantir que as diretrizes de expressão facial e preservação de aparência estão documentadas com exemplos.
- [ ] **10.4** Validar que os critérios de testes/QA (Fase 6) exigem evidências de mudança de expressão e cobrem reprovação do SafeSearch.
- [ ] **10.5** Checar que a seção "Resumo das Atualizações de Prompt" sintetiza os reforços e reitera compatibilidade com os agentes fixos.
- [ ] **10.6** Registrar aprovação das lideranças responsáveis antes de executar ajustes no código.
