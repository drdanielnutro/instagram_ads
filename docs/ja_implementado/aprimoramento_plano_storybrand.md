## **Plano Expandido e Aprimorado — Branching com Fallback de Alta Fidelidade**
**Caminho do Arquivo:** `/Users/institutorecriare/VSCodeProjects/instagram_ads/plano_storybrand_fallback.md`

#### **1. Objetivos e Princípios**
- **Garantir resiliência:** Ativar um pipeline de reconstrução completa e de alta fidelidade do StoryBrand sempre que a análise automatizada inicial da landing page não atingir o limiar de qualidade pré-definido. O objetivo é eliminar a dependência da qualidade do conteúdo de origem, garantindo um output de excelência em todos os cenários.
- **Preservar eficiência:** Manter o fluxo de execução atual e otimizado (landing page analysis → planning → execution) para todos os casos em que o `storybrand_completeness_score` for satisfatório. Isso equilibra o custo computacional e a latência, aplicando o processo mais intensivo apenas quando estritamente necessário.
- **Contratos de Estado Claros:** Definir um "contrato de dados" rigoroso. Ambos os caminhos, o "feliz" e o de "recuperação", devem obrigatoriamente popular o mesmo conjunto de chaves no `session.state`. Isso garante que os agentes subsequentes possam consumir os dados de forma agnóstica, permitindo uma retomada de fluxo transparente e desacoplada.
- **Observabilidade e Melhoria Contínua:** Implementar um sistema de logging e métricas detalhado. As decisões do agente "gate", as iterações e os resultados do pipeline de fallback devem ser registrados para permitir a depuração, a auditoria de qualidade e o ajuste futuro do limiar de ativação.

#### **2. Pontos de Integração no `agent.py`**
- A integração será feita no pipeline principal, `complete_pipeline`, definido no arquivo `app/agent.py`.
- Um novo agente customizado, `StoryBrandQualityGate`, será inserido na lista de `sub_agents` do `complete_pipeline`, posicionado imediatamente após o agente `landing_page_analyzer`.
- O `StoryBrandQualityGate` receberá como dependências (argumentos em seu construtor) os dois pipelines que ele orquestrará: o `planning_pipeline` (para o "caminho feliz") e o novo `fallback_storybrand_pipeline` (para o "caminho de recuperação").
- A lógica interna do `StoryBrandQualityGate` deve ser implementada para ler o valor do limiar diretamente do objeto de configuração, `config.min_storybrand_completeness`, garantindo que qualquer override via variável de ambiente seja respeitado automaticamente.

#### **3. StoryBrandQualityGate (BaseAgent Customizado)**
- **Arquivo sugerido:** `app/agents/storybrand_gate.py`.
- **Implementação:** A classe `StoryBrandQualityGate` herdará de `google.adk.agents.BaseAgent`.
- **Método `_run_async_impl`:** Este método conterá a lógica central de roteamento.
  - **Leitura e Validação do Estado:** O método acessará o estado via `ctx.session.state`. A primeira ação será ler a chave `state['storybrand_completeness_score']` e verificar a presença de `state['storybrand_analysis']`.
  - **Lógica de Decisão e Logging:** Com base no score, o agente determinará o caminho a seguir (`"happy_path"` ou `"fallback"`). Esta decisão, juntamente com metadados relevantes (score obtido, limiar utilizado, timestamp), será registrada em `state['storybrand_gate_metrics']` para fins de observabilidade. Logs estruturados (`logger.info`) serão emitidos para auditoria em tempo real.
  - **Invocação Condicional:**
    - Se `score >= config.min_storybrand_completeness`, o agente invocará o pipeline `planning_pipeline` passando o `InvocationContext` atual (`async for event in self.planning_pipeline.run_async(ctx): yield event`).
    - Caso contrário, ele invocará o `fallback_storybrand_pipeline`.
  - **Fallback Forçado por Segurança:** Uma verificação de segurança será implementada. Se a chave `storybrand_completeness_score` não existir no estado ou contiver um valor inválido (ex: `None` ou não numérico), o agente acionará o pipeline de fallback por padrão para garantir que o sistema nunca prossiga com dados de qualidade incerta.

#### **4. Fallback StoryBrand Pipeline (SequentialAgent)**
- **Arquivo sugerido:** `app/agents/storybrand_fallback.py`.
- **Estrutura:** Será um `SequentialAgent` robusto, contendo a sequência de sub-agentes que executam a reconstrução completa.
- **Sub-agentes principais:**
  1. `fallback_input_initializer` (BaseAgent): Um agente lógico que garante que as chaves de estado necessárias para o fallback (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) existam no `state`, inicializando-as com valores padrão (ex: strings vazias) se estiverem ausentes.
  2. `fallback_input_collector` (LlmAgent): Sua missão é popular os três inputs essenciais. Ele tentará preenchê-los a partir de `state['landing_page_analysis']`. Se não conseguir, seu prompt deve ser capaz de interagir (se o modo permitir) ou registrar a necessidade de dados explícitos. Ele não deve inferir "persona" ou "tom", pois estes são derivados.
  3. `section_pipeline_runner` (BaseAgent): O orquestrador interno do fallback. Ele carregará a configuração de todas as 16 seções do StoryBrand e executará, em um loop, o bloco de agentes reutilizáveis (preparador de contexto + escritor de seção + loop de revisão) para cada seção, garantindo a construção incremental e coerente.
  4. `fallback_storybrand_compiler` (BaseAgent): Após a conclusão bem-sucedida de todos os loops de revisão, este agente lógico compilará as seções individuais aprovadas (armazenadas em `state['storybrand_*']`) em uma única estrutura de dados, garantindo que o "Contrato de Estado" seja cumprido.
  5. `fallback_quality_reporter` (BaseAgent, opcional): Um agente final que resume os metadados da execução do fallback (número de iterações por seção, feedbacks do revisor, etc.) e os salva em `state['storybrand_recovery_report']` para análise de qualidade.

#### **5. Configuração das Seções**
- **Arquivo sugerido:** `app/agents/storybrand_sections.py`.
- **Estrutura de Dados:** Será criada uma `dataclass` ou `Pydantic Model` chamada `StoryBrandSectionConfig` com os seguintes campos:
  - `key`: O nome da chave no `state` (ex: `"storybrand_character"`).
  - `display_name`: O nome legível (ex: `"Personagem"`).
  - `writer_prompt_path`: O caminho para o arquivo de prompt do agente escritor.
  - `narrative_goal`: Uma descrição do objetivo estratégico da seção (ex: "Definir o herói da história e conectar-se com seus desejos").
- **Lista de Seções:** Uma lista ordenada de instâncias de `StoryBrandSectionConfig` será definida, mapeando todas as **16 seções** do sistema original para garantir a mesma profundidade narrativa: `character`, `exposition_1`, `inciting_incident_1`, `exposition_2`, `inciting_incident_2`, `unmet_needs_summary`, `problem_external`, `problem_internal`, `problem_philosophical`, `guide`, `value_proposition`, `plan`, `action`, `failure`, `success`, `identity`.
- **Lógica do `section_pipeline_runner`:** Este agente irá iterar sobre a lista de configurações. Para cada seção, ele executará a seguinte sequência:
  1. Executar um `context_preparer` (BaseAgent) para popular as chaves genéricas no `state` (`state['chave_secao_atual']`, `state['nome_secao_atual']`, `state['contexto_anterior']`).
  2. Invocar o `section_writer` (LlmAgent), carregando o prompt definido em `writer_prompt_path`.
  3. Invocar o `section_review_loop` (LoopAgent compartilhado) e aguardar sua conclusão bem-sucedida antes de passar para a próxima seção da lista.

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
  - **Prompts de Escrita (16 arquivos, ex: `section_character.txt`, `section_exposition_1.txt`):** Cada prompt conterá a "receita" estrutural para sua respectiva seção, extraída dos modelos `storybrand_*.txt` originais. Por exemplo, `section_problem_internal.txt` instruirá o agente a descrever a frustração causada pelo problema externo.
  - **Prompts de Revisão (`review_masculino.txt`, `review_feminino.txt`):** Estes prompts serão detalhados. Eles conterão a personalidade destilada dos `perfil_cliente_*.txt`, as instruções para atuar como o "empresário consciente" e os critérios de avaliação da dupla consciência (empatia + estratégia).
  - `corrector.txt`: Um prompt genérico e robusto para reescrita guiada por feedback.
  - `compiler.txt`: Instruções para o `fallback_storybrand_compiler` (se for um `LlmAgent`) para transformar as seções aprovadas na estrutura de dados final, garantindo a conformidade com o schema `StoryBrandAnalysis`.

#### **8. Coleta de Inputs Essenciais para o Fallback**
- **Backend (`helpers/user_extract_data.py`):** A classe `UserInputExtractor` e seu prompt serão atualizados para reconhecer e extrair os três novos campos (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) do input do usuário. O schema de saída será expandido para incluí-los.
- **Frontend (`VITE_ENABLE_WIZARD=true`):** A configuração `WIZARD_STEPS` será atualizada para adicionar novos campos de formulário no `WizardForm`, preferencialmente com um componente de seleção (radio/dropdown) para `sexo_cliente_alvo`. A lógica de submissão do formulário será ajustada para enviar esses novos dados ao backend.
- **Opcionalidade:** Os novos campos no frontend serão marcados como opcionais para não criar atrito no "caminho feliz". A validação de sua presença será responsabilidade do `fallback_input_collector` apenas quando o caminho de recuperação for ativado.

#### **9. Contrato de Estado Pós-Fallback**
- O `fallback_storybrand_compiler` tem a missão crítica de garantir que, ao final de sua execução, o `session.state` seja indistinguível do estado gerado pelo "caminho feliz". Ele deve:
  - Popular `state['storybrand_analysis']` com um objeto compatível com o schema Pydantic `StoryBrandAnalysis`.
  - Popular `state['storybrand_summary']` e `state['storybrand_ad_context']` usando os métodos `.to_summary()` e `.to_ad_context()` do objeto Pydantic, ou prompts dedicados.
  - Definir `state['storybrand_completeness']` com um valor alto (ex: 1.0) para prevenir loops de recuperação acidentais.
  - Opcionalmente, salvar os metadados da recuperação em `state['storybrand_recovery_report']`.

#### **10. Ajustes em `app/config.py`**
- Os seguintes parâmetros de configuração serão adicionados à classe `DevelopmentConfiguration`:
  - `fallback_storybrand_max_iterations: int = 3`.
  - `fallback_storybrand_model: str | None = None` (para permitir o uso de um modelo mais potente, como o `gemini-2.5-pro`, especificamente para o fallback, com override via `FALLBACK_STORYBRAND_MODEL`).
  - `storybrand_gate_debug: bool = False` (para forçar o fallback durante testes, com override via `STORYBRAND_GATE_DEBUG`).

#### **11. Logs, Métricas e Observabilidade**
- **Gate:** A decisão do `StoryBrandQualityGate` (`score`, `threshold`, `path`) será logada e salva em `state['storybrand_gate_metrics']`.
- **Fallback:** O início e o fim da execução de cada seção, o número de iterações de revisão e os feedbacks completos do revisor serão logados.
- **Trilha de Auditoria:** Uma chave `state['storybrand_audit_trail']` será mantida como uma lista ordenada de eventos, registrando cada etapa principal do fallback para facilitar a depuração e a análise de performance.

#### **12. Testes e Validação**
- **Testes Unitários:**
  - Testar o `StoryBrandQualityGate` com scores acima, abaixo e iguais ao limiar, mockando os pipelines que ele invoca.
  - Testar a `StoryBrandSectionConfig` e a lógica de carregamento das 16 seções.
  - Testar as funções de compilação do `fallback_storybrand_compiler`.
- **Testes de Integração:**
  - Simular uma execução completa do `fallback_storybrand_pipeline`, mockando as respostas dos `LlmAgents` para verificar se o fluxo de estado, os loops e o contrato de estado final funcionam como esperado.
  - Garantir que o "caminho feliz" permanece funcional e não é afetado pelas novas mudanças.
- **Testes Manuais (QA):**
  - Executar o sistema, forçando um `storybrand_completeness_score` baixo (via debug ou configuração), e observar os logs e o resultado final para validar a qualidade e o comportamento do fallback.
  - Testar casos de borda, como a ausência dos inputs essenciais (`sexo_cliente_alvo`, etc.).

#### **13. Documentação**
- O arquivo `AGENTS.md` será atualizado para incluir a documentação do `StoryBrandQualityGate`, do `fallback_storybrand_pipeline` e de todos os seus sub-agentes.
- Um novo documento, `docs/storybrand_fallback.md`, será criado para detalhar a arquitetura, o fluxo de controle e a lógica de prompts do caminho de recuperação.
- Os novos campos de entrada (`nome_empresa`, etc.) serão documentados no `README.md` principal e em exemplos de uso da API.

#### **14. Feature Flag (Opcional, mas Recomendado)**
- Uma nova flag de configuração, `ENABLE_STORYBRAND_FALLBACK: bool = True`, será adicionada em `app/config.py`.
- A inserção do `StoryBrandQualityGate` no `complete_pipeline` em `agent.py` será condicionada a esta flag. Isso permite desativar rapidamente todo o mecanismo de fallback em caso de problemas em produção, sem a necessidade de um novo deploy.

#### **15. Etapas Futuras (Opcional)**
- Implementar um sistema para monitorar as métricas do `StoryBrandQualityGate` ao longo do tempo, permitindo a recalibração periódica do `min_storybrand_completeness` com base em dados reais.
- Avaliar a possibilidade de implementar um cache para os StoryBrands reconstruídos. Se a mesma landing page falhar repetidamente, o sistema poderia reutilizar um resultado de fallback já gerado e aprovado.
- Desenvolver uma interface de auditoria simples que leia o `state['storybrand_audit_trail']` para facilitar a análise de execuções de fallback com falha.