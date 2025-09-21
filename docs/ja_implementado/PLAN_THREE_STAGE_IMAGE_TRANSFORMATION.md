# Plano de Implementação — Três Estados Visuais Sequenciais (Atual, Intermediário, Aspiracional)

## 1. Objetivo
Estender o pipeline ADK para gerar e entregar, para cada variação do anúncio, uma narrativa visual em três atos:
1. **Estado Atual** — momento de dor/fracasso.
2. **Estado Intermediário** — mesma persona/cenário, exibindo a decisão ou ação imediata de mudança.
3. **Estado Aspiracional** — resultado obtido em médio prazo, permitindo mudanças visuais mais amplas.

O JSON final deve conter três prompts técnicos em inglês, além de seis URIs de imagens (3 GCS + 3 Signed URLs) por variação, garantindo consistência da persona e clareza temporal.

## 2. Estado Atual
- O pipeline já produz `prompt_estado_atual` e `prompt_estado_aspiracional` (plano `PLAN_ASPIRATIONAL_PROMPTS.md`).
- O plano de integração atual (`PLAN_IMAGE_ASSETS_INTEGRATION.md`) gera duas imagens usando a técnica base + edição.
- Não há campo intermediário, logo a narrativa pula de “dor” direto para “resultado final”.
- Frontend e persistência esperam quatro URIs por variação (duas imagens); precisamos evoluir para seis URIs sem quebrar compatibilidade.

## 3. Proposta de Arquitetura
1. **Novo campo textual** `prompt_estado_intermediario` em todas as camadas (modelos, persistência, planos LLM, validações).
2. **Atualização dos planos VISUAL_DRAFT / QA** para instruir a geração de três prompts correlacionados e coerentes com o arco narrativo.
3. **Ferramenta de geração de imagens** passa a produzir três arquivos por variação:
   - Chamada 1 (texto → imagem) para o estado atual.
   - Chamada 2 (imagem + texto) usando a imagem anterior como base para retratar a decisão imediata (mesmo ambiente/vestuário).
   - Chamada 3 (imagem + texto) usando a segunda imagem como base, permitindo mudanças de cenário/roupa para ilustrar resultados de médio prazo.
4. **Persistência**: cada variação terá campos `image_estado_atual_*`, `image_estado_intermediario_*`, `image_estado_aspiracional_*`.
5. **Frontend**: atualizar consumidores para lidar com 3 cenas; fornecer flag opcional indicando se o usuário deseja as três imagens ou apenas duas (para fallback futuro).
6. **Observabilidade**: ampliar eventos SSE para relatar progresso “Imagem 1/3… 2/3… 3/3…”.

## 4. Detalhamento das Alterações Necessárias

### 4.1 Configuração
- `app/config.py`:
  - Manter `IMAGE_GENERATION_TIMEOUT` e `IMAGE_GENERATION_MAX_RETRIES`.
  - Adicionar `IMAGE_TRANSFORMATION_STEPS = 3` (para centralizar o número de cenas) e `IMAGE_INTERMEDIATE_PROMPT_TEMPLATE`.
- `.env`/documentação: sem novos secrets, apenas adicionar as chaves opcionais acima.

### 4.2 Modelos & Tipagem
- `app/agent.py` e/ou `app/utils/typing.py`:
  - Atualizar `AdVisual` (ou modelo equivalente) com o novo campo:
    ```python
    class AdVisual(BaseModel):
        descricao_imagem: str
        prompt_estado_atual: str
        prompt_estado_intermediario: str
        prompt_estado_aspiracional: str
        aspect_ratio: Literal["9:16", "1:1", "4:5", "16:9"]
    ```
  - Propagar alterações para `SessionState`, estruturas auxiliares e callbacks que manipulam `visual`.
- Ajustar schema dos estados intermediários (quaisquer dicionários `visual` existentes nos agentes ou planos fixos).

### 4.3 Planos Fixos e Templates LLM
- `app/plan_models/fixed_plans.py` (ou arquivo equivalente):
  - Atualizar a descrição dos planos VISUAL_DRAFT, exigindo explicitamente os três momentos.
  - Incluir orientações específicas para o prompt intermediário: “mesmo cenário/vestuário, mostrar ação imediata de mudança (ex.: jogando sorvete no lixo)”.
- `app/agent.py` (bloco VISUAL_DRAFT do `code_generator`):
  - Exigir JSON com três prompts (`prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional`).
  - Fornecer exemplos de narrativa em três etapas.
- `code_reviewer` e `final_validator`:
  - Validar que os três prompts são coerentes, descrevem a mesma persona e respeitam políticas do Meta (sem alegações irreais).
  - Checar que a descrição (`descricao_imagem`) menciona os três atos.
- QA/Compliance:
  - Atualizar regras para permitir a narrativa em três passos enquanto evita promessas médicas/impossíveis.

### 4.4 Ferramenta de Transformação de Imagens (`app/tools/generate_transformation_images.py`)
- Função principal deve aceitar três prompts:
  ```python
  async def generate_transformation_images(
      prompt_atual: str,
      prompt_intermediario: str,
      prompt_aspiracional: str,
      variation_idx: int,
      metadata: Dict[str, Any]
  ) -> Dict[str, Any]:
  ```
- Fluxo das chamadas:
  1. `response_atual = await asyncio.to_thread(client.models.generate_content, model=..., contents=[prompt_atual])`
  2. Converter `response_atual` em `Image` (PIL) e armazenar.
  3. `response_intermediario = await asyncio.to_thread(client.models.generate_content, model=..., contents=[transform_prompt_intermediario, image_atual])`
  4. Converter em imagem, manter referência para terceira chamada.
  5. `response_aspiracional = await asyncio.to_thread(client.models.generate_content, model=..., contents=[transform_prompt_aspiracional, image_intermediaria])`
- Uploads no GCS:
  - `estado_atual_{idx}.png`
  - `estado_intermediario_{idx}.png`
  - `estado_aspiracional_{idx}.png`
- Assinatura de URLs (Signed URLs 24h) para cada arquivo.
- Estrutura de retorno:
  ```json
  {
    "estado_atual": {"gcs_uri": "...", "signed_url": "..."},
    "estado_intermediario": {"gcs_uri": "...", "signed_url": "..."},
    "estado_aspiracional": {"gcs_uri": "...", "signed_url": "..."}
  }
  ```
- Templates das mensagens:
  - `transform_prompt_intermediario`: enfatizar “same outfit, same location, immediate positive action…”.
  - `transform_prompt_aspiracional`: permitir mudanças amplas de cenário/roupa, mas exigir manutenção da persona (mesmo rosto/identidade).
- Tratamento de erros: manter retries com Tenacity, registrando falhas por etapa; se a terceira etapa falhar após todos os retries, retornar erro parcial (`image_generation_error`) apontando a etapa afetada.

### 4.5 Ajustes no Agente de Imagens
- `ImageAssetsAgent`:
  - Atualizar iteração sobre variações para chamar a função com três prompts.
  - Expandir eventos SSE: “Gerando imagens 1/3… 2/3… 3/3…”.
  - Incluir no estado final os campos:
    - `image_estado_atual_gcs`, `image_estado_atual_url`
    - `image_estado_intermediario_gcs`, `image_estado_intermediario_url`
    - `image_estado_aspiracional_gcs`, `image_estado_aspiracional_url`
  - Registrar metadados extras em `state["image_assets"]` (ex.: tempos por etapa).
  - Em caso de erro parcial, persistir JSON com flag `image_generation_status` indicando quais cenas foram geradas.

### 4.6 Persistência e Callbacks
- `persist_final_delivery` deve aceitar regravação com os novos campos (sem mudanças significativas se já serializa o dict completo).
- Se houver armazenamento local (`artifacts/`), criar subpasta `images/intermediario` ou manter padrão atual com nomes distintos; documentar estrutura para evitar colisões.

### 4.7 Frontend & APIs
- `app/routers/delivery.py`: garantir que os campos novos sejam expostos nas respostas.
- Frontend (`frontend/`):
  - Atualizar componentes que renderizam imagens para lidar com três cenas.
  - Adicionar (ou preparar) toggle “Exibir transformação intermediária” caso desejem ocultar por padrão.
  - Atualizar tipos TypeScript/GraphQL (se existirem) para incluir os novos campos.

### 4.8 Observabilidade
- Logging estruturado por etapa (`estado_atual`, `intermediario`, `aspiracional`).
- Métricas simples: tempo total, tempo por etapa, número de retries.
- Adicionar alertas em caso de falha recorrente em qualquer etapa (ex.: mais de X erros/h).

## 5. Testes
- **Unitários**:
  - Mockar a tool para garantir que o agente escreve todos os campos no estado final.
  - Validar que erros parciais geram entradas `image_generation_error` adequadas.
- **Integração**:
  - Simular um pipeline completo com geração mockada (fixtures) garantindo que três prompts são consumidos e as seis URLs aparecem no JSON persistido.
- **Contract/Schema**:
  - Atualizar testes que verificam o schema do JSON final (`tests/test_refactored.py`, outros).
- **Frontend**:
  - Ajustar testes de snapshot/componentes para refletir três imagens.

## 6. Documentação
- Atualizar `README.md` (seção de saída do JSON) para explicar os três passos.
- Atualizar `PLAN_IMAGE_ASSETS_INTEGRATION.md` para referenciar este plano como extensão.
- Incluir exemplos completos de JSON com os novos campos.
- Adicionar nota ao `nano_banana_doc.md` (se necessário) explicando o uso encadeado de duas edições.

## 7. Riscos e Mitigações
- **Latência e custo**: agora são 9 chamadas (3 variações × 3 etapas). Mitigar mantendo paralelização por variação e reuso de clientes.
- **Inconsistência visual**: direcionar prompts intermediários e aspiracionais com instruções claras sobre mesma persona; usar sempre a imagem anterior como base.
- **Falhas parciais**: garantir idempotência e permitir reexecução apenas da etapa que falhou (guardar estado por etapa?
  - Opcional: armazenar as imagens geradas com timestamp para evitar sobrescrita).
- **Complexidade do prompt**: fornecer exemplos detalhados nas instruções LLM para evitar interpretações incorretas das cenas.
- **Frontend não atualizado**: coordenar release para garantir que o consumo de 6 URIs não quebre a UI.

## 8. Próximos Passos
1. Validar o plano com stakeholders (produto + design).
2. Implementar alterações de modelo/tipagem e atualizar planos fixos/LLM.
3. Ajustar a ferramenta de imagens e o `ImageAssetsAgent` para tratar três etapas.
4. Atualizar persistência, APIs e frontend.
5. Escrever/atualizar testes (unit, integração, frontend).
6. Atualizar documentação e executar validação end-to-end.
7. Medir latência/custo e ajustar configurações se necessário.
