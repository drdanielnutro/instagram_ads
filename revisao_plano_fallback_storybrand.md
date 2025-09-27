# Revisão do Plano de Fallback — Storybrand

## 1. Sumário Executivo
- O plano acerta ao posicionar o `StoryBrandQualityGate` logo após o `landing_page_analyzer` e ao reutilizar `PlanningOrRunSynth`, tirando proveito direto do limiar já exposto em `config.min_storybrand_completeness` e da estrutura atual do pipeline.【F:aprimoramento_plano_storybrand_v2.md†L10-L27】【F:app/agent.py†L260-L278】【F:app/config.py†L34-L58】
- Há inconsistência crítica na lista das 16 seções do fallback: cinco chaves sugeridas com o prefixo `storybrand_` não correspondem às lidas hoje pelo `FallbackStorybrandCompiler`, o que quebraria a compilação do StoryBrand se aplicado literalmente.【F:aprimoramento_plano_storybrand_v2.md†L60-L69】【F:app/agents/fallback_compiler.py†L89-L108】
- O gate, como descrito, encaminha o fluxo para o pipeline de fallback **em vez** de rodar `PlanningOrRunSynth`, deixando de produzir o `feature_briefing` exigido pelos agentes de execução e causando falhas posteriores; é necessário encadear o sintetizador após o fallback.【F:aprimoramento_plano_storybrand_v2.md†L20-L27】【F:app/agent.py†L744-L818】
- O plano também solicita validar a flag frontend `VITE_ENABLE_NEW_FIELDS` antes de permitir fallback forçado, mas o backend não tem visibilidade dessa configuração — hoje apenas as flags de backend são checadas no preflight — o que exige clarificação operacional ou outra fonte de verdade compartilhada.【F:aprimoramento_plano_storybrand_v2.md†L56-L57】【F:app/server.py†L329-L356】

## 2. Itens Corretos e Consistentes
- **Gate após a análise da landing page** — Inserir o `StoryBrandQualityGate` logo depois do `landing_page_analyzer` e chamar `PlanningOrRunSynth` para o caminho feliz mantém o encadeamento atual (análise → planejamento → execução) e aproveita o limiar `config.min_storybrand_completeness` já definido.【F:aprimoramento_plano_storybrand_v2.md†L10-L27】【F:app/agent.py†L260-L278】【F:app/config.py†L34-L58】  
  - Evidências no código: `complete_pipeline` hoje encadeia `landing_page_analyzer` → `PlanningOrRunSynth`, e o limiar está disponível em `DevelopmentConfiguration`.
- **Schema pronto para o contrato pós-fallback** — `StoryBrandAnalysis` já oferece `completeness_score`, `to_summary()` e `to_ad_context()`, permitindo que o fallback injete resultados equivalentes aos do caminho feliz sem alterar consumidores downstream.【F:aprimoramento_plano_storybrand_v2.md†L30-L39】【F:app/schemas/storybrand.py†L90-L181】  
  - Evidências: o callback `process_and_extract_sb7` persiste `storybrand_analysis`, `storybrand_summary` e `storybrand_ad_context` no estado depois da análise da landing page.【F:app/callbacks/landing_page_callbacks.py†L108-L154】
- **Pré-processamento dos inputs obrigatórios** — O `UserInputExtractor` e o `/run_preflight` já enriquecem `o_que_a_empresa_faz`, normalizam `sexo_cliente_alvo`, validam `force_storybrand_fallback` e só liberam a sessão quando os dados atendem aos critérios, exatamente como o plano pressupõe para acionar o fallback com segurança.【F:aprimoramento_plano_storybrand_v2.md†L45-L56】【F:helpers/user_extract_data.py†L423-L599】【F:app/server.py†L302-L358】
- **Compilador existente alinhado às regras 16→7** — O `FallbackStorybrandCompiler` implementado segue as mesmas regras descritas (uso das seções `storybrand_*`, cálculo de `metadata.text_length`, sincronização do score), servindo como base confiável para a etapa final do fallback.【F:aprimoramento_plano_storybrand_v2.md†L30-L39】【F:app/agents/fallback_compiler.py†L80-L158】

## 3. Inconsistências Encontradas
- **Chaves das seções inconsistentes com o compilador**  
  - **Descrição**: A lista de seções sugere nomes como `storybrand_exposition_1`, `storybrand_inciting_incident_1/2` e `storybrand_unmet_needs_summary`, mas o compilador lê `exposition_1`, `inciting_incident_1/2` e `unmet_needs_summary` sem o prefixo, logo os textos ficariam vazios na transformação final.【F:aprimoramento_plano_storybrand_v2.md†L60-L69】【F:app/agents/fallback_compiler.py†L89-L108】  
  - **Impacto**: CRÍTICA — as seções resultariam vazias, gerando `StoryBrandAnalysis` incompleto e invalidando o objetivo do fallback.  
  - **Evidências**: Referência direta no plano e na implementação do compilador.  
  - **Relação ADK**: Afeta o contrato de estado consumido por agentes subsequentes dentro do `SequentialAgent`.  
  - **Correção Sugerida**: Atualizar o plano (e a futura configuração) para usar as mesmas chaves que o compilador espera (`exposition_1`, `inciting_incident_1`, `exposition_2`, `inciting_incident_2`, `unmet_needs_summary`).
- **Fallback sem sintetizar briefing antes da execução**  
  - **Descrição**: O gate, conforme descrito, escolhe entre `PlanningOrRunSynth` *ou* `fallback_storybrand_pipeline`. Se o fallback for executado, `PlanningOrRunSynth` não roda, mas é ele quem produz o `feature_briefing` consumido por `code_generator` e demais agentes de execução.【F:aprimoramento_plano_storybrand_v2.md†L20-L27】【F:app/agent.py†L744-L818】  
  - **Impacto**: CRÍTICA — sem briefing o gerador de tarefas e cópias opera com contexto vazio, quebrando a geração de anúncios.  
  - **Evidências**: `code_generator` referencia explicitamente `{feature_briefing}` em todas as etapas; sem o sintetizador, essa chave não existe no estado.  
  - **Relação ADK**: Quebra o contrato de dados do pipeline principal e pode gerar exceções nos `LlmAgents`.  
  - **Correção Sugerida**: Após executar o fallback, invocar `PlanningOrRunSynth` (mesmo que apenas o sintetizador) antes de continuar para `execution_pipeline`, ou incluir etapa equivalente no pipeline de fallback.
- **Validação de flag frontend fora do alcance do backend**  
  - **Descrição**: O plano afirma que o preflight/gate deve validar `VITE_ENABLE_NEW_FIELDS` antes de permitir acionamentos manuais, mas o backend só conhece `ENABLE_NEW_INPUT_FIELDS` e `ENABLE_STORYBRAND_FALLBACK`; não há mecanismo atual para inspecionar a flag de frontend.【F:aprimoramento_plano_storybrand_v2.md†L56-L57】【F:app/server.py†L329-L356】  
  - **Impacto**: MÉDIA — expectativa de automação que não pode ser cumprida pode gerar suposições incorretas sobre proteção operacional.  
  - **Evidências**: Código do preflight verifica apenas as flags de backend e retorna mensagens orientativas.  
  - **Relação ADK**: Nenhuma direta, mas afeta o contrato de entrada antes de criar a sessão.  
  - **Correção Sugerida**: Ajustar o plano para indicar verificação processual (documentação/observabilidade) ou implementar canal de configuração compartilhada; não presumir validação automática da flag de frontend no backend.

## 4. Pontos de Incerteza
- A etapa que tenta inferir `sexo_cliente_alvo` a partir de `landing_page_context` quando o valor continua indefinido carece de critérios objetivos: o contexto hoje expõe headline, persona e benefícios, mas não necessariamente fornece pronomes/gênero confiáveis para normalização automática. Definir sinais mínimos ou confirmar se prompts adicionais serão necessários.【F:aprimoramento_plano_storybrand_v2.md†L45-L47】【F:app/agent.py†L626-L678】
- Não há detalhe sobre como o `PromptLoader` eager recomendado deve lidar com ambientes onde os arquivos ainda não foram provisionados (ex.: testes). Especificar fallback seguro ou modo lazy ajudaria a evitar falhas em pipelines parciais.【F:aprimoramento_plano_storybrand_v2.md†L86-L92】

## 5. Viabilidade de Implementação (por tema)
- **Integração do Gate no pipeline principal** — Viável. `SequentialAgent` já encadeia `landing_page_analyzer` → `PlanningOrRunSynth`; basta envolver esse agente em um gate que decide qual caminho executar, reaproveitando o limiar existente e preservando o estado compartilhado via `ctx.session.state`.【F:aprimoramento_plano_storybrand_v2.md†L10-L27】【F:app/agent.py†L260-L278】【F:app/agent.py†L1221-L1228】
- **Pipeline de fallback e compilação** — Parcialmente pronto. O compilador implementado cumpre o contrato; faltam criar initializer/coletor/loops com prompts e corrigir a nomenclatura das seções para casar com o compilador. Também é necessário garantir que o sintetizador/planner sejam executados após o fallback.【F:aprimoramento_plano_storybrand_v2.md†L38-L69】【F:app/agents/fallback_compiler.py†L80-L158】
- **Coleta e validação de inputs essenciais** — Altamente viável. O extractor e o preflight já rejeitam entradas genéricas, normalizam sexo e replicam `force_storybrand_fallback`, de modo que o fallback pode confiar na raiz do estado (desde que as flags estejam ativas).【F:aprimoramento_plano_storybrand_v2.md†L45-L56】【F:helpers/user_extract_data.py†L423-L599】【F:app/server.py†L329-L358】
- **Observabilidade proposta (gate/audit trail)** — Existe infraestrutura de logging estruturado no preflight e exemplos de métricas no código atual, tornando plausível expandir para `storybrand_gate_metrics` e `storybrand_audit_trail` seguindo os contratos descritos no plano.【F:aprimoramento_plano_storybrand_v2.md†L20-L27】【F:aprimoramento_plano_storybrand_v2.md†L112-L166】【F:app/server.py†L329-L370】
