# Plano de Correção – Final Delivery Validation

## 1. Diagnóstico e Alinhamento
- Confirmar nas execuções recentes (`logs/backend*.log`) as duas causas principais:  
  - `visual.reference_assets` rejeitado por `extra="forbid"` no schema atual.  
  - `copy.cta_texto`/`cta_instagram` fora de `CTA_INSTAGRAM_CHOICES`, gerando falha no validador determinístico.
- Mapear o fluxo do payload: snippets aprovados (`code_generator` + reviewers) → `final_assembler_llm` → `FinalAssemblyNormalizer` → `FinalDeliveryValidatorAgent` → (`ImageAssetsAgent`, persistência).  
- Reforçar com stakeholders que:  
  - Referências precisam chegar ao JSON final sem `signed_url`.  
  - CTAs devem permanecer dentro do conjunto homologado até que a plataforma autorize novos valores.  
  - A solução deve eliminar regressões na montagem sem relaxar as restrições do canal.

## 2. Saída Estruturada para o `final_assembler_llm`

### 2.1 Esquema Pydantic consolidado
- Definir `AdVariationsPayload` em `app/schemas/final_delivery.py` (ou módulo dedicado) com `variations: conlist(StrictAdItem, min_length=3, max_length=3)`, explicitando no docstring a estrutura final.  
- Estrutura esperada de cada `StrictAdItem`:  
  - `landing_page_url: constr(min_length=1)`  
  - `formato: Literal["Feed","Reels","Stories"]` (derivado de `FORMAT_SPECS`)  
  - `copy: StrictAdCopy` (`headline`, `corpo`, `cta_texto` com `Literal` de CTAs permitidos)  
  - `visual: StrictAdVisual` (`descricao_imagem`, prompts com `constr(min_length=1)`, `aspect_ratio` como `Literal` dependente do formato, `reference_assets: Optional[ReferenceAssetsPublic]`)  
  - `cta_instagram: Literal[...]`  
  - `fluxo`, `referencia_padroes`: `constr(min_length=1)`  
  - `contexto_landing: Union[str, dict[str, Any]]` (normalizado posteriormente)  
- Declarar `ReferenceAssetsPublic` em `app/schemas/reference_assets.py` com `character`/`product` opcionais contendo `id`, `gcs_uri`, `labels`, `user_description`; garantir reuso por fallback e pipeline principal.  
- Aplicar `Field(..., min_length=1)`/`constr` nos campos livres para impedir strings vazias e documentar a justificativa no módulo.

### 2.2 Refatorar o `final_assembler_llm`
- Atualizar o `LlmAgent` em `app/agent.py` adicionando `output_schema=AdVariationsPayload` e definir `output_key` (ex.: `"final_ad_variations"` ou manter `"final_code_delivery"`).  
- Revisar o prompt (`final_assembler_instruction`) para citar explicitamente o schema e reforçar:  
  - “Retorne somente JSON válido, sem markdown.”  
  - “Preencha exatamente três variações que se encaixem em AdVariationsPayload.”  
  - “Não altere valores aprovados de CTA, formato, aspect ratio.”  
- Registrar que, ao usar `output_schema`, o agente não poderá utilizar `tools`/transfer — aceitável no caso por ser um agente de montagem terminal.

### 2.3 Consumidores downstream
- `FinalAssemblyNormalizer`: adaptar para usar o objeto Pydantic já validado; decidir se a saída oficial continuará armazenada como objeto (`state["final_ad_variations"]`) ou como string JSON (`state["final_code_delivery"]`). Se serializar, documentar a conversão explícita (incluindo normalização de `contexto_landing` → string) e garantir idempotência.  
- `FinalDeliveryValidatorAgent`: simplificar para checar a presença/instância de `AdVariationsPayload` no estado; preservar métricas/audit trail atuais, mesmo que a validação reduza-se a um sanity check. Se for mantido `final_code_delivery` em string, garantir conversão inversa para compatibilidade.  
- `persist_outputs.py`/callbacks: ajustar para lidar com o novo formato (objeto vs string) mantendo compatibilidade com artefatos persistidos e com a lógica de referência visual; atualizar docstrings/comentários para indicar o formato esperado.

## 3. Regras de Domínio e Campos Obrigatórios
- Consolidar todos os campos de domínio fixo no schema (inclusive para o fluxo fallback, garantindo reutilização do mesmo modelo):  
  - `formato`: chaves de `FORMAT_SPECS`.  
  - `visual.aspect_ratio`: valores permitidos em `FORMAT_SPECS[formato]`.  
  - `copy.cta_texto` / `cta_instagram`: `CTA_INSTAGRAM_CHOICES` (ver expansão na seção 5).  
  - Qualquer outro campo controlado (ex.: fluxo padrão) decidir se será `Literal`.
- Para campos livres (headline, corpo, prompts, fluxo, referencia_padroes, contexto), usar tipos com `min_length` e validadores Pydantic garantindo não-nulidade.
- Atualizar documentação técnica (ex.: `docs/ja_implementado/CORRECAO_VALIDACAO_DETERMINISTICA.md`) explicando a nova validação na origem.
- Garantir que o fallback StoryBrand (`FallbackStorybrandCompiler`, `PersistStorybrandSectionsAgent`) reaproveite os mesmos modelos ao propagar dados para o estado.

### 3.1 Checklist de arquivos/prompt/documentação
- `app/schemas/final_delivery.py`, `app/schemas/reference_assets.py` (novos modelos/enums).  
- `app/agent.py` (`final_assembler_llm`, prompt e importações).  
- `app/validators/final_delivery_validator.py`, `app/agent.py` (`FinalAssemblyNormalizer`).  
- Prompts (`prompts/.../final_assembler_instruction`, `code_generator` quando citar CTAs).  
- Documentação: `docs/ja_implementado/CORRECAO_VALIDACAO_DETERMINISTICA.md`, `docs/plano_validacao_json_v2.md`, README/diagramas.  
- Dashboards/alertas que consumem `deterministic_final_validation`.

## 4. Testes e Rollout
- Sequência recomendada:  
  1. Testes unitários de schema (`AdVariationsPayload`, `ReferenceAssetsPublic`).  
  2. Teste unitário/integrado do assembler com `output_schema` (simular CTA inválido → garantir bloqueio).  
  3. Atualizar testes existentes que esperavam JSON string (`final_code_delivery`).  
  4. Testes de integração (`tests/integration/pipeline/test_deterministic_flow.py`, `tests/unit/validators/test_final_delivery_validator.py`).  
  5. Execução manual (sessão real) com CTA inválido e referências para validar logs/metadados.  
- Executar `uv run pytest` após cada etapa crítica, garantindo cobertura.  
- Planejar rollout: manter `ENABLE_DETERMINISTIC_FINAL_VALIDATION=true` durante a transição; monitorar logs após migração.  
- Documentar passos de QA (ex.: reprocessar sessão com CTA inválido e referências) e checklist de flags impactadas.  
- Comunicar no changelog e recomendar validação em staging antes de produção.

## 5. Expansão de CTAs (ação subsequente)
- Levantar/validar com produto o catálogo completo de CTAs aceitos pela plataforma (listagem em andamento).  
- Atualizar `CTA_INSTAGRAM_CHOICES` e `CTA_BY_OBJECTIVE` conforme a lista homologada, refletindo no schema Pydantic (`Literal`/`Enum`).  
- Revisar prompts (`code_generator`, `final_assembler_llm`) para mencionar o conjunto expandido assim que estiver aprovado.  
- Garantir que frontend/API que expõem CTAs estejam alinhados antes de liberar a nova enumeração; programar rollout coordenado com UX/wizard.  
- Base de referência inicial (extraída de `cta_permitidos_instagram_ads.md`, sujeita à validação):  
  - Reconhecimento/awareness: `Saber mais`, `Ver mais`, `Ouvir agora`, `Visitar perfil do Instagram`.  
  - Tráfego/vendas de baixo comprometimento: `Visitar website`, `Ver menu`.  
  - Leads/agendamentos: `Registar`, `Subscrever`, `Transferir`, `Pedir orçamento`, `Candidatar-se`, `Contactar-nos`, `Pedir horário`, `Obter acesso`, `Obter oferta`.  
  - Interação/contato: `Enviar mensagem`, `Enviar mensagem do WhatsApp`, `Ligar agora`, `Call now`, `Guardar`.  
  - Vendas/conversão: `Comprar agora`, `Encomendar agora`, `Reservar agora`, `Iniciar encomenda`, `Comprar bilhetes`, `Subscrever`, `Doar agora`.  
  - Promoção de app/jogos: `Instalar agora`, `Usar app`, `Jogar`.
- Registrar a validação oficial da lista de CTAs (responsável, data, fonte) antes de atualizar código e prompts; manter artefato vinculado (issue/confluence).

## 6. Considerações Adicionais
- Avaliar se ainda faz sentido manter um validador determinístico pesado após a adoção do schema estruturado; decidir se o agente vira apenas um sanity check ou se mantém lógica extra (ex.: coerência com objetivo). Garantir que telemetry (`delivery_audit_trail`, `deterministic_final_validation`) continue populada para dashboards.  
- Caso o assembler precise gerar conteúdo faltante em cenários de fallback, considerar separar montagem determinística de correções via agente secundário.  
- Preparar plano de rollback (reverter `output_schema` e ajustes no normalizer) até conclusão da migração.  
- Atualizar diagramas/documentação do pipeline para refletir a nova arquitetura com geração controlada.
