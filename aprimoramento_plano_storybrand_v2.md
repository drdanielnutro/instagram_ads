### **Plano Final e Definitivo — Branching com Fallback de Alta Fidelidade**
**Caminho do Arquivo:** `aprimoramento_plano_storybrand_v2.md`

#### **1. Objetivos e Princípios**
- **Garantir resiliência:** Ativar um pipeline de reconstrução completa e de alta fidelidade do StoryBrand sempre que a análise automatizada inicial da landing page não atingir o limiar de qualidade pré-definido. O objetivo é eliminar a dependência da qualidade do conteúdo de origem, garantindo um output de excelência em todos os cenários.
- **Preservar eficiência:** Manter o fluxo de execução atual e otimizado (landing page analysis → planning → execution) para todos os casos em que o score de completude (`storybrand_analysis.completeness_score` ou `landing_page_context.storybrand_completeness`) for satisfatório. Isso equilibra o custo computacional e a latência, aplicando o processo mais intensivo apenas quando estritamente necessário.
- **Contratos de Estado Claros:** Definir um "contrato de dados" rigoroso. Ambos os caminhos, o "feliz" e o de "recuperação", devem obrigatoriamente popular o mesmo conjunto de chaves no `session.state`. Isso garante que os agentes subsequentes possam consumir os dados de forma agnóstica, permitindo uma retomada de fluxo transparente e desacoplada.
- **Observabilidade e Melhoria Contínua:** Implementar um sistema de logging e métricas detalhado. As decisões do agente "gate", as iterações e os resultados do pipeline de fallback devem ser registrados para permitir a depuração, a auditoria de qualidade e o ajuste futuro do limiar de ativação.

#### **2. Pontos de Integração no `agent.py`**
- A integração será feita no pipeline principal, `complete_pipeline`, definido no arquivo `app/agent.py`.
- O `StoryBrandQualityGate` **substituirá** a entrada atual do `PlanningOrRunSynth` na lista de `sub_agents`, permanecendo posicionado logo após o `landing_page_analyzer`. O planner existente não ficará mais na lista bruta; em vez disso, será passado para o gate via construtor.
- O `StoryBrandQualityGate` receberá como dependências (argumentos em seu construtor) os dois caminhos que ele orquestrará: o `PlanningOrRunSynth` (para o "caminho feliz") e o novo `fallback_storybrand_pipeline` (para o "caminho de recuperação").
- A lógica interna do `StoryBrandQualityGate` deve ser implementada para ler o valor do limiar diretamente do objeto de configuração, `config.min_storybrand_completeness`, garantindo que qualquer override via variável de ambiente – incluindo o novo `STORYBRAND_MIN_COMPLETENESS` – seja respeitado automaticamente.

#### **3. StoryBrandQualityGate (BaseAgent Customizado)**
- **Arquivo sugerido:** `app/agents/storybrand_gate.py`.
- **Implementação:** A classe `StoryBrandQualityGate` herdará de `google.adk.agents.BaseAgent`.
- **Método `_run_async_impl`:** Este método conterá a lógica central de roteamento.
  - **Leitura e Validação do Estado:** O método acessará o estado via `ctx.session.state`. Ler `score = state.get('storybrand_analysis', {}).get('completeness_score')` com fallback em `state.get('landing_page_context', {}).get('storybrand_completeness')`. Verificar também a presença de `state['storybrand_analysis']` quando aplicável.
  - **Lógica de Decisão e Logging:** Com base no score, o agente determinará o caminho a seguir (`"happy_path"` ou `"fallback"`). Esta decisão, juntamente com metadados relevantes (score obtido, limiar utilizado, timestamp), será registrada em `state['storybrand_gate_metrics']` para fins de observabilidade. Logs estruturados (`logger.info`) serão emitidos para auditoria em tempo real.
  - **Sincronização de Flags:** O gate sempre fará parte do `complete_pipeline`; quando **ambas** as flags `config.enable_storybrand_fallback` e `config.enable_new_input_fields` estiverem `True`, ele poderá optar pelo fallback. Antes de consultar o score, ele também verificará `state.get('force_storybrand_fallback')` e `config.storybrand_gate_debug`: quando qualquer uma dessas condições estiver ativa **e** o fallback estiver habilitado pelas flags principais, o gate delegará imediatamente ao pipeline de recuperação, marcando `is_forced_fallback = True` em `storybrand_gate_metrics`. Se `config.enable_storybrand_fallback` ou `config.enable_new_input_fields` estiverem `False`, o agente registrará o bloqueio em `storybrand_gate_metrics` (incluindo o motivo da impossibilidade) e seguirá automaticamente pelo `"happy_path"`, preservando a compatibilidade com fluxos legados. O `/run_preflight` já reforça essa condição ao rejeitar `force_storybrand_fallback` quando as flags estão desativadas.
  - **Invocação Condicional:**
    - Se `state.get('force_storybrand_fallback')` estiver ativo ou `config.storybrand_gate_debug` for `True` e as duas flags principais permitirem o fallback, o agente executará o `fallback_storybrand_pipeline`, registrará o motivo no log estruturado **e**, ao término bem-sucedido, continuará encadeando o `PlanningOrRunSynth` para gerar `feature_briefing` e demais artefatos exigidos pelo pipeline de execução.
    - Se qualquer mecanismo de força/debug estiver ativo **mas** alguma das flags principais estiver `False`, o gate registrará `decision_path = 'happy_path'` com o motivo do bloqueio e continuará com o fluxo padrão.
    - Caso contrário, se `score >= config.min_storybrand_completeness`, o agente invocará o `PlanningOrRunSynth` passando o `InvocationContext` atual (`async for event in self.planning_or_synth.run_async(ctx): yield event`).
    - Se o score estiver abaixo do limiar (e as flags estiverem habilitadas), ele executará primeiro o `fallback_storybrand_pipeline` e, assim que o fallback finalizar, chamará o `PlanningOrRunSynth` com o mesmo contexto. Se `config.enable_storybrand_fallback` ou `config.enable_new_input_fields` estiverem `False`, permanecerá no `"happy_path"` e registrará o bloqueio.
  - **Fallback Forçado por Segurança:** Uma verificação de segurança será implementada. Se o score estiver ausente/inválido **e** as flags permitirem a execução do fallback, o agente acionará o pipeline de recuperação por padrão para garantir que o sistema nunca prossiga com dados de qualidade incerta. Caso as flags bloqueiem o fallback, ele seguirá pelo `"happy_path"` e registrará no `storybrand_gate_metrics` que a recuperação foi impedida por configuração.

#### **3.1 Regras de Mapeamento 16→7 (Compilador)**
- O compilador consolidará as 16 seções narrativas no schema `StoryBrandAnalysis` seguindo estas regras:
  - `character.description` ← `state['storybrand_character']`; `evidence` inclui o próprio texto; `confidence≈0.9` quando presente.
  - `problem.types.external|internal|philosophical` ← `state['storybrand_problem_*']`; `problem.description` = síntese de `exposition_1`, `inciting_incident_1`, `exposition_2`, `inciting_incident_2`, `unmet_needs_summary` (fallback: concatenação dos tipos); `evidence` inclui os tipos; `confidence≈0.9`.
  - `guide.description` prioriza `state['storybrand_value_proposition']` e agrega autoridade de `state['storybrand_guide']`; `authority` ← `storybrand_guide`; `empathy` pode permanecer vazio se não explicitado; `evidence` inclui ambos.
  - `plan.steps` e `plan.description` extraídos de `state['storybrand_plan']` (quebra por linhas/marcadores); `evidence` inclui o texto.
  - `action.primary` e `action.secondary` extraídos das primeiras linhas de `state['storybrand_action']`.
  - `failure.description` e `failure.consequences[0]` ← `state['storybrand_failure']`; `evidence` idem.
  - `success.description` ← `state['storybrand_success']`; `success.transformation` ← `state['storybrand_identity']`; `benefits` das linhas de `success` (fallback: lista unitária).
  - `metadata.text_length` computado a partir da soma dos textos-fonte; `completeness_score = 1.0` (pós‑fallback), e sincronização com `landing_page_context.storybrand_completeness = 1.0`.

#### **4. Fallback StoryBrand Pipeline (SequentialAgent)**
- **Arquivo sugerido:** `app/agents/storybrand_fallback.py`.
- **Estrutura:** Será um `SequentialAgent` robusto, contendo a sequência de sub-agentes que executam a reconstrução completa.
- **Sub-agentes principais:**
  1. `fallback_input_initializer` (BaseAgent): Um agente lógico que garante que as chaves de estado necessárias para o fallback (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) existam no `state`, inicializando-as com valores padrão (ex: strings vazias) se estiverem ausentes.
  2. `fallback_input_collector` (LlmAgent): Sua missão é confirmar os três inputs essenciais já enriquecidos pelo preflight. Ele deve confiar, por padrão, nos valores presentes na **raiz** do estado (`state['nome_empresa']`, `state['o_que_a_empresa_faz']`, `state['sexo_cliente_alvo']`), assumindo que `o_que_a_empresa_faz` chegou como frase transformacional produzida pelo LangExtract. Somente se algum campo estiver ausente ou sinalizado como inválido o coletor recorrerá a `state['landing_page_context']` (ou sinais adicionais do estado) como fonte suplementar para recomputar o valor e registrar o ocorrido em `state['storybrand_audit_trail']`. Ele não deve inferir "persona" ou "tom" arbitrariamente; essas nuances derivam da seleção do `sexo_cliente_alvo` e da aplicação dos modelos de sucesso.
     - Caso, mesmo após a etapa anterior, `sexo_cliente_alvo` permaneça `"neutro"`, vazio ou `None`, o agente realizará uma **última tentativa de inferência contextual** com base em `state['landing_page_context']` (ex.: pronomes usados na headline, personas mencionadas nos benefícios). Se a inferência falhar, ele registrará um evento com `status: 'error'` e `details: 'Pré-requisito crítico sexo_cliente_alvo não pôde ser determinado.'` em `state['storybrand_audit_trail']` e abortará o pipeline imediatamente, emitindo um `Event` com `EventActions(escalate=True)` (ou lançando uma exceção) para interromper o `SequentialAgent` conforme o padrão do ADK.
  3. `section_pipeline_runner` (BaseAgent): O orquestrador interno do fallback. Ele carregará a configuração de todas as 16 seções do StoryBrand e executará, em um loop, o bloco de agentes reutilizáveis (preparador de contexto + escritor de seção + loop de revisão) para cada seção, garantindo a construção incremental e coerente.
  4. `fallback_storybrand_compiler` (BaseAgent): Após a conclusão bem-sucedida de todos os loops de revisão, este agente lógico compilará as 16 seções individuais aprovadas em uma única e rica estrutura de dados, garantindo que o "Contrato de Estado" com os 8 campos principais seja cumprido. Implementação de referência: `app/agents/fallback_compiler.py` (segue as regras da seção 3.1).
  5. `fallback_quality_reporter` (BaseAgent, opcional): Um agente final que resume os metadados da execução do fallback (número de iterações por seção, feedbacks do revisor, etc.) e os salva em `state['storybrand_recovery_report']` para análise de qualidade.

- **Encadeamento pós-fallback:** Ao final desse `SequentialAgent`, o `StoryBrandQualityGate` retomará o fluxo chamando o `PlanningOrRunSynth` (ao menos o `context_synthesizer`) para garantir que `feature_briefing` e demais artefatos sigam disponíveis para o `execution_pipeline`.

- **Motor principal:** O preflight (`helpers/user_extract_data.py`) passa a ser responsável por transformar descrições genéricas em frases completas de proposta de valor utilizando LangExtract. O resultado enriquecido deve ser persistido diretamente em `state['o_que_a_empresa_faz']`, permitindo que o fallback (e o caminho feliz) reutilizem o mesmo statement transformacional.
- **Critérios mínimos:** A frase resultante precisa ter pelo menos 30 caracteres, conter verbo de ação e comunicar claramente quem é ajudado, qual resultado é prometido e por meio de qual abordagem. A validação no preflight deve rejeitar apenas quando esses critérios não puderem ser atingidos pelo modelo.
- **Integração com `sexo_cliente_alvo`:** Quando o gênero estiver disponível, o LangExtract deve personalizar a narrativa (ex.: "Ajudamos homens...", "Ajudamos mães...") garantindo consistência com os prompts sensíveis a gênero usados no fallback.
- **Falhas e auditoria:** Se o enriquecimento falhar, o helper devolve erro estruturado e o `/run_preflight` responde 422, impedindo a criação da sessão ADK. Nenhuma execução de fallback deve iniciar sem que o preflight tenha retornado `success=True`.
- **Flag de força opcional:** O preflight pode, opcionalmente, definir `state['force_storybrand_fallback'] = True` (por configuração ou ação explícita do usuário) quando for desejável pular o caminho feliz mesmo com score desconhecido, **desde que** `config.enable_new_input_fields` e `config.enable_storybrand_fallback` estejam `True`. O gate usa essa flag para tomar a decisão conforme descrito na Seção 3. Como o backend não possui visibilidade direta sobre `VITE_ENABLE_NEW_FIELDS`, o plano deve orientar uma checagem operacional/documental desse flag frontend antes de permitir acionamentos manuais.
- **Referências cruzadas:** Documentar quaisquer ajustes adicionais no `plano_langextract_enriquecimento.md` e manter ambos os planos sincronizados para evitar divergências de implementação.

#### **5. Configuração das Seções**
- **Arquivo sugerido:** `app/agents/storybrand_sections.py`.
- **Estrutura de Dados:** Será criada uma `dataclass` ou `Pydantic Model` chamada `StoryBrandSectionConfig` com os seguintes campos:
  - `key`: O nome da chave no `state` (ex: `"storybrand_character"`).
  - `display_name`: O nome legível (ex: `"Personagem"`).
  - `writer_prompt_path`: O caminho para o arquivo de prompt do agente escritor.
  - `review_prompt_paths`: Um dicionário mapeando o gênero aos caminhos dos prompts de revisão (ex: `{'masculino': '...', 'feminino': '...'}`).
  - `corrector_prompt_path`: O caminho para o arquivo de prompt do agente corretor.
  - `narrative_goal`: Uma descrição do objetivo estratégico da seção (ex: "Definir o herói da história e conectar-se com seus desejos").
- **Uso obrigatório do contexto enriquecido:** Cada configuração deve receber `o_que_a_empresa_faz` (enriquecido) via `extra_context`, garantindo que escritores, revisores e corretores tenham acesso ao mesmo statement transformacional durante todo o loop.
- **Lista de Seções:** Uma lista ordenada de instâncias de `StoryBrandSectionConfig` será definida, mapeando todas as **16 seções** do sistema original para garantir a mesma profundidade narrativa: `storybrand_character`, `exposition_1`, `inciting_incident_1`, `exposition_2`, `inciting_incident_2`, `unmet_needs_summary`, `storybrand_problem_external`, `storybrand_problem_internal`, `storybrand_problem_philosophical`, `storybrand_guide`, `storybrand_value_proposition`, `storybrand_plan`, `storybrand_action`, `storybrand_failure`, `storybrand_success`, `storybrand_identity`. **Atenção:** as seções de exposição/inciting/unmet não possuem o prefixo `storybrand_` e devem seguir exatamente os nomes consumidos por `FallbackStorybrandCompiler`.
- **Lógica do `section_pipeline_runner`:** Este agente irá iterar sobre a lista de configurações. Para cada seção, ele executará a seguinte sequência:
  1. Executar um `context_preparer` (BaseAgent) para popular as chaves genéricas no `state` (`state['chave_secao_atual']`, `state['nome_secao_atual']`, `state['contexto_anterior']`).
  2. Injetar no contexto da seção o valor de `state['o_que_a_empresa_faz']` (e demais campos enriquecidos) antes de acionar qualquer LlmAgent.
  3. Invocar o `section_writer` (LlmAgent), carregando o prompt definido em `writer_prompt_path`.
  4. Invocar o `section_review_loop` (LoopAgent compartilhado) e aguardar sua conclusão bem-sucedida antes de passar para a próxima seção da lista.

#### **6. Loop de Revisão Compartilhado**
- **Componentes do Loop (`section_review_loop`):**
  - `section_reviewer` (LlmAgent): Este agente atuará como o **"empresário consciente"**. Seu prompt será carregado dinamicamente (masculino ou feminino) e instruído a aplicar uma **dupla consciência**: avaliar a ressonância emocional do texto (empatia pelo cliente) e sua eficácia estratégica (aderência ao framework StoryBrand). A opção de um revisor "neutro" será descartada para manter a força dos arquétipos. A saída será um JSON estruturado: `{ "grade": "pass|fail", "comment": "..." }`.
  - `approval_checker` (BaseAgent): Um agente lógico que inspeciona o `grade` no resultado do revisor. Se for `"pass"`, ele dispara `actions.escalate=True` para encerrar o loop.
  - `section_corrector` (LlmAgent): Ativado apenas em caso de `"fail"`, este agente recebe o texto original e o `comment` do revisor, e sua única tarefa é aplicar as correções sugeridas, sobrescrevendo a chave de estado da seção atual.
- **Parâmetros e Configuração:**
  - O número máximo de iterações será controlado por `config.fallback_storybrand_max_iterations` (com um default seguro de 3), permitindo override via variável de ambiente `FALLBACK_STORYBRAND_MAX_ITERATIONS`.
  - Cada iteração do loop (revisão, checagem, correção) será registrada com logs detalhados, incluindo o nome da seção, o status da revisão (`pass`/`fail`) e o comentário completo do revisor para facilitar a depuração.

#### **7. Prompts Necessários**
- **Diretório sugerido:** `prompts/storybrand_fallback/`.
- **Conteúdo e Filosofia dos Prompts:**
  - `collector.txt`: Instruções para o `fallback_input_collector` focar na extração dos 3 inputs essenciais, com exemplos.
  - **Prompts de Escrita (16 arquivos, ex: `section_character.txt`, `section_exposition_1.txt`):** Além da "receita" estrutural da seção (derivada dos modelos `storybrand_*.txt`), cada prompt deve instruir explicitamente o LLM a usar `{o_que_a_empresa_faz}` como fio condutor da narrativa, adaptando problemas, soluções e promessas ao statement transformacional enriquecido.
  - **Prompts de Revisão (`review_masculino.txt`, `review_feminino.txt`):** Devem manter a personalidade do "empresário consciente" e, adicionalmente, incluir critérios objetivos perguntando se a saída é claramente específica ao `{o_que_a_empresa_faz}` enriquecido e se um concorrente genérico poderia reutilizar o texto. Respostas que não refletirem a transformação devem ser rejeitadas com feedback acionável.
  - `corrector.txt`: Um prompt genérico e robusto para reescrita guiada por feedback.
  - `compiler.txt`: Instruções para o `fallback_storybrand_compiler` (se for um `BaseAgent`, esta lógica estará em código) para consolidar as 16 seções nos 8 campos principais do schema `StoryBrandAnalysis`, criando descrições ricas e coerentes.
- **Disponibilidade dos Arquivos:** A criação desses prompts é parte integrante da implementação do fallback. O `PromptLoader` descrito na Seção 16.4 deve validar a existência de cada arquivo antes de disponibilizar a função de carregamento, retornando erro claro quando algum prompt estiver ausente. Enquanto os arquivos não forem entregues ao repositório, o loader deve executar em modo "lazy" (carregamento sob demanda) ou ser habilitado apenas em conjunto com os prompts para evitar falhas no import.

#### **8. Coleta de Inputs Essenciais para o Fallback**
- **Backend (`helpers/user_extract_data.py`):** O preflight passa a combinar extração + enriquecimento. LangExtract, alimentado por prompts e few-shots específicos, transforma descrições genéricas em frases transformacionais e devolve `o_que_a_empresa_faz` já alinhado ao formato "Ajudamos [quem] a [resultado] através de [como]". O helper registra o status do enriquecimento (sucesso/falha) e fornece mensagens pedagógicas quando o modelo não consegue cumprir o contrato.
- **Frontend (flags `VITE_ENABLE_WIZARD` e `VITE_ENABLE_NEW_FIELDS`):** `VITE_ENABLE_WIZARD` continua habilitando a experiência baseada em wizard, enquanto `VITE_ENABLE_NEW_FIELDS` controla o fluxo com os novos campos obrigatórios. A interface deve refletir as mensagens de validação atualizadas, guiando o usuário a fornecer insumos suficientes para que o LangExtract gere a frase transformacional. A validação dessa flag permanece um passo de checklist do time de operações/front-end, não uma verificação automática do backend.
- **Pré-condição para o fallback:** O pipeline pressupõe que `nome_empresa`, `o_que_a_empresa_faz` (enriquecido) e `sexo_cliente_alvo` foram produzidos com sucesso pelo preflight e armazenados na raiz do estado. Este comportamento já está implementado em `helpers/user_extract_data.py` e exposto pelo endpoint `/run_preflight`; o plano registra-o aqui como referência e não requer reimplementação. O helper só retorna 200 quando esses campos atendem aos critérios; `fallback_input_collector` apenas confirma/normaliza e registra métricas. Quando necessário, o preflight pode adicionar `state['force_storybrand_fallback'] = True` para sinalizar que o caminho feliz deve ser pulado, sempre após validar que `config.enable_new_input_fields` e `config.enable_storybrand_fallback` estão ativos e registrar, em checklist, que o flag frontend `VITE_ENABLE_NEW_FIELDS` já foi habilitado pelo time responsável.

#### **9. Contrato de Estado Pós-Fallback**
- O `fallback_storybrand_compiler` tem a missão crítica de garantir que, ao final de sua execução, o `session.state` seja indistinguível do estado gerado pelo "caminho feliz". Ele deve:
  - Popular `state['storybrand_analysis']` com um objeto compatível com o schema Pydantic `StoryBrandAnalysis` definido em `app/schemas/storybrand.py`. **Nenhuma alteração no schema original é necessária.**
  - Popular `state['storybrand_summary']` e `state['storybrand_ad_context']` usando os métodos `.to_summary()` e `.to_ad_context()` do objeto Pydantic `StoryBrandAnalysis` instanciado.
  - Atualizar `storybrand_analysis['completeness_score'] = 1.0` e sincronizar `landing_page_context['storybrand_completeness'] = 1.0` para prevenir loops de recuperação acidentais.
  - Opcionalmente, salvar os metadados da recuperação em `state['storybrand_recovery_report']`.

#### **10. Ajustes em `app/config.py`**
- Os seguintes parâmetros de configuração serão adicionados/ajustados na classe `DevelopmentConfiguration`:
  - `fallback_storybrand_max_iterations: int = 3`.
  - `fallback_storybrand_model: str | None = None` (para permitir o uso de um modelo mais potente, como o `gemini-2.5-pro`, especificamente para o fallback, com override via `FALLBACK_STORYBRAND_MODEL`).
  - `storybrand_gate_debug: bool` já existe; o plano deve apenas garantir documentação e testes.
  - `min_storybrand_completeness`: manter o consumo do valor já exposto em `config.min_storybrand_completeness`, que continua sendo alimentado automaticamente pela variável de ambiente `STORYBRAND_MIN_COMPLETENESS` implementada em `app/config.py`. Não há nova lógica a ser criada; o plano apenas reforça esse comportamento para o gate.

#### **11. Logs, Métricas e Observabilidade**
- **Gate:** A decisão do `StoryBrandQualityGate` (`score`, `threshold`, `path`) será logada e salva em `state['storybrand_gate_metrics']`, obedecendo ao contrato da Seção 16.1. Quando `state['force_storybrand_fallback']` ou `config.storybrand_gate_debug` forem utilizados, o log deve evidenciar o motivo (`force_flag_active`, `debug_flag_active`). As instruções de "Como fazer" do plano e dos artefatos complementares devem ser revisadas para citar explicitamente `config.enable_storybrand_fallback`/`config.enable_new_input_fields` (em vez de variantes em maiúsculas) ao apresentar exemplos de código.
- **Preflight:** Registrar no log estruturado o resultado do enriquecimento (valor final, status e mensagens de erro quando aplicável) para facilitar auditoria e depuração antes mesmo do gate.
- **Fallback:** O início e o fim da execução de cada seção, o número de iterações de revisão e os feedbacks completos do revisor serão logados.
- **Trilha de Auditoria:** Uma chave `state['storybrand_audit_trail']` será mantida como uma lista ordenada de eventos (Seção 16.2), registrando cada etapa principal do fallback para facilitar a depuração e a análise de performance.

#### **12. Testes e Validação**
- **Testes Unitários:**
  - Testar o `StoryBrandQualityGate` com scores acima, abaixo e iguais ao limiar, mockando os pipelines que ele invoca.
  - Cobrir o cenário "force fallback" garantindo que, com score alto mas `state['force_storybrand_fallback'] = True`, o gate roteie para o pipeline de recuperação e registre `is_forced_fallback` corretamente.
  - Adicionar teste unitário dedicado que falhe caso o gate ou os utilitários associem-se a atributos inexistentes (`config.ENABLE_*`). O teste deve reforçar o uso das propriedades `config.enable_storybrand_fallback` e `config.enable_new_input_fields` nas decisões de roteamento.
  - Atualizar os testes E2E/integração do preflight para cobrir a propagação de `initial_state['force_storybrand_fallback']` e o bloqueio quando as flags obrigatórias não estiverem habilitadas.
  - Testar a `StoryBrandSectionConfig` e a lógica de carregamento das 16 seções.
  - Testar as funções de compilação do `fallback_storybrand_compiler`.
  - Cobrir `UserInputExtractor` garantindo que entradas genéricas sejam enriquecidas corretamente, que mensagens pedagógicas apareçam em casos extremos e que o atributo `enriched` seja priorizado.
- **Testes de Integração:**
  - Simular uma execução completa do `fallback_storybrand_pipeline`, mockando as respostas dos `LlmAgents` para verificar se o fluxo de estado, os loops e o contrato de estado final funcionam como esperado.
  - Garantir que o "caminho feliz" permanece funcional e não é afetado pelas novas mudanças.
  - Verificar que o fallback é abortado corretamente quando `sexo_cliente_alvo` não pode ser determinado como `masculino` ou `feminino`, garantindo o registro do evento de erro em `state['storybrand_audit_trail']`.
  - Exercitar o caminho "force fallback" (score alto + flag ativa) para validar logs, métricas e consistência do estado final.
  - Executar cenário comparativo produzindo StoryBrands distintos para empresas de mesmo segmento porém com propostas de valor diferentes, validando que o enriquecimento impulsiona narrativas únicas.
- **Testes Manuais (QA):**
  - Executar o sistema, forçando um score baixo (ex.: `storybrand_analysis.completeness_score`), e observar os logs e o resultado final para validar a qualidade e o comportamento do fallback.
  - Testar casos de borda, como a ausência dos inputs essenciais (`sexo_cliente_alvo`, etc.).

#### **13. Documentação**
- O arquivo `AGENTS.md` será atualizado para incluir a documentação do `StoryBrandQualityGate`, do `fallback_storybrand_pipeline` e de todos os seus sub-agentes.
- Um novo documento, `docs/storybrand_fallback.md`, será criado para detalhar a arquitetura, o fluxo de controle e a lógica de prompts do caminho de recuperação.
- O processo seguirá o checklist oficial (`checklist.md` na raiz), em conformidade com o fluxo “Checklist Primeiro, Código Depois”.
- Os novos campos de entrada (`nome_empresa`, etc.) serão documentados no `README.md` principal e em exemplos de uso da API.
- A seção "Como fazer" (tanto neste plano quanto nos playbooks derivados) deve ser auditada para corrigir referências obsoletas a `config.ENABLE_*` e destacar as variáveis de ambiente `ENABLE_STORYBRAND_FALLBACK`/`ENABLE_NEW_INPUT_FIELDS` e `VITE_ENABLE_NEW_FIELDS` que habilitam o fluxo completo.

#### **14. Feature Flag (Opcional, mas Recomendado)**
- Reutilizar a flag de configuração **já existente** `enable_storybrand_fallback: bool = False` em `app/config.py`, mantendo o override atual via variável de ambiente `ENABLE_STORYBRAND_FALLBACK`.
- Revisar a documentação do rollout para reforçar o uso dessa flag e garantir que ambientes legados estejam cientes do comportamento padrão (`False`).
- Mesmo com a flag desligada, o `StoryBrandQualityGate` permanece no pipeline em modo observador: ele registra o bloqueio, mantém o caminho feliz e evita duplicação de lógica. Dessa forma, reativar o fallback em produção exige apenas ligar a flag, sem nova publicação.

#### **15. Etapas Futuras (Opcional)**
- Implementar um sistema para monitorar as métricas do `StoryBrandQualityGate` ao longo do tempo, permitindo a recalibração periódica do `min_storybrand_completeness` com base em dados reais.
- Avaliar a possibilidade de implementar um cache para os StoryBrands reconstruídos. Se a mesma landing page falhar repetidamente, o sistema poderia reutilizar um resultado de fallback já gerado e aprovado.
- Desenvolver uma interface de auditoria simples que leia o `state['storybrand_audit_trail']` para facilitar a análise de execuções de fallback com falha.

#### **16. Especificações de Contratos e Convenções**

Esta seção consolida os contratos de dados e as convenções operacionais que garantem uma implementação determinística do fallback.

**16.1 Contrato de Dados – `storybrand_gate_metrics`**
- A chave `state['storybrand_gate_metrics']` armazenará um único objeto JSON por execução do gate (sem histórico acumulado) e os logs estruturados devem refletir o mesmo formato.
- Formato:
  ```json
  {
    "score_obtained": "float | null",
    "score_threshold": "float",
    "decision_path": "Literal['happy_path', 'fallback']",
    "timestamp_utc": "str (ISO 8601 format)",
    "is_forced_fallback": "bool",
    "debug_flag_active": "bool"
  }
  ```
- Significado dos campos:
  - `score_obtained`: valor lido do estado; `null` quando inexistente/ inválido.
  - `score_threshold`: valor de `config.min_storybrand_completeness` utilizado na avaliação.
  - `decision_path`: caminho escolhido (`happy_path` ou `fallback`).
  - `timestamp_utc`: timestamp no formato ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`).
  - `is_forced_fallback`: `true` quando o fallback for acionado sem considerar o score — seja por ausência/invalidade do score, seja por `state['force_storybrand_fallback']`/`config.storybrand_gate_debug`. Se o fallback for bloqueado por configuração, mantenha `false` e registre `decision_path = 'happy_path'`.
  - `debug_flag_active`: `true` quando `config.storybrand_gate_debug` estiver habilitado, sinalizando uma execução forçada.

**16.2 Contrato de Dados – `storybrand_audit_trail`**
- A chave `state['storybrand_audit_trail']` conterá uma lista de eventos em ordem cronológica. O `section_pipeline_runner` adicionará entradas antes e depois de cada subagente, sem limites de crescimento dentro de uma execução.
- Cada evento seguirá o formato:
  ```json
  {
    "stage": "Literal['collector', 'preparer', 'writer', 'reviewer', 'checker', 'corrector', 'compiler']",
    "section_key": "str | null",
    "iteration": "int | null",
    "status": "Literal['started', 'completed', 'pass', 'fail', 'corrected', 'error']",
    "details": "str | dict",
    "timestamp_utc": "str (ISO 8601 format)",
    "duration_ms": "int | null"
  }
  ```
- Orientações adicionais:
  - `section_key` recebe a chave da seção atual (ex.: `storybrand_character`) ou `null` para estágios globais.
  - `iteration` representa a iteração do loop de revisão; use `null` fora do contexto do loop.
  - `details` armazena feedbacks completos do revisor ou mensagens de erro estruturadas.
  - `duration_ms` registra o tempo de execução do estágio; pode ser `null` para eventos de início (`status='started'`).

**16.3 Vocabulário e Lógica – `sexo_cliente_alvo`**
- Valor final obrigatório: `masculino` ou `feminino`. Valores como `"neutro"` ou variações livres só podem existir durante a etapa de coleta; o estado final entregue aos consumidores deve estar normalizado.
- Fontes primárias e suplementares:
  - O `run_preflight` e o `UserInputExtractor` populam `state['sexo_cliente_alvo']` diretamente na raiz do estado. O `fallback_input_collector` valida e normaliza esse valor como primeira etapa.
  - `state['landing_page_context']` é utilizado apenas como fonte suplementar quando o campo estiver ausente, vazio ou igual a `"neutro"`, fornecendo sinais narrativos (pronomes, personas, depoimentos) para uma inferência guiada.
- Normalização:
  - `homem`, `homens`, `masc`, `mulher`, `mulheres`, `fem` e variações semelhantes devem ser convertidas consistentemente para `masculino` ou `feminino`.
  - Os prompts do coletor precisam instruir o modelo a trabalhar sempre com a forma canônica (`masculino`/`feminino`) ao atualizar o estado.
- Salvaguarda final:
  - Caso, após a normalização e a tentativa suplementar de inferência, o valor permaneça `"neutro"`, `None` ou indeterminado, o `fallback_input_collector` registrará `{"stage": "collector", "status": "error", "details": "Pré-requisito crítico sexo_cliente_alvo não pôde ser determinado."}` em `state['storybrand_audit_trail']` e abortará a execução.
  - Esse cenário deve resultar em `decision_path = "happy_path"` quando `config.enable_new_input_fields` estiver `False`, pois o gate não permitirá a entrada no fallback sem os campos obrigatórios habilitados.
- Efeito prático:
  - O valor final controla a seleção de prompts sensíveis a gênero (`review_masculino.txt` ou `review_feminino.txt`) e garante a consistência narrativa das seções revisadas. Os demais agentes utilizam o contexto completo do negócio, independente do gênero escolhido.

**16.4 Convenção de Carregamento de Prompts**
- Um utilitário dedicado (`PromptLoader` em `app/utils/prompt_loader.py`) ficará responsável por carregar, cachear e renderizar prompts; agentes não lerão arquivos diretamente.
- Convenções:
  - Diretório base: `prompts/storybrand_fallback/`.
  - Nomenclatura: `[tipo]_[chave].txt` (ex.: `writer_character.txt`, `reviewer_masculino.txt`, `corrector.txt`).
  - Encoding obrigatório: UTF-8.
- Comportamento do loader:
  - Carregamento **eager** com cache em memória. Durante a inicialização, o utilitário varre o diretório configurado, carrega todos os arquivos e armazena os conteúdos em um dicionário interno. Caso algum arquivo obrigatório não seja encontrado, um `FileNotFoundError` é disparado imediatamente, evitando execuções com prompts incompletos.
  - Renderização via placeholders `{variavel}`; agentes fornecem o contexto (dict) e recebem a string final. Erros de interpolação devem gerar exceção com mensagem descritiva.
