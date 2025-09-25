# Inconsistências Identificadas — README.md

## 1. Itens Corretos e Consistentes
- Visão geral como sistema multiagente ADK que monta três variações de anúncios e exige validação final coincide com o pipeline atual (incluindo montagem em lote, checagem de esquema e persistência em `artifacts/ads_final`).
  - Evidências no código: `app/agent.py` (agente `final_assembler` instruindo três variações e validador final) e callback de persistência salvando no diretório previsto.【F:README.md†L5-L7】【F:README.md†L220-L238】【F:app/agent.py†L986-L1039】【F:app/callbacks/persist_outputs.py†L114-L193】
- O fluxo descrito para o frontend (gera `sessionId`/`userId` fixo `u_999`, chama `/run_preflight`, lida com 422 e depois consome `/delivery/*`) reflete exatamente o componente principal da SPA.【F:README.md†L35-L76】【F:frontend/src/App.tsx†L73-L199】
- A etapa de análise StoryBrand via `web_fetch_tool`, com truncagem controlada por `STORYBRAND_TRUNCATE_LIMIT_CHARS` e logging de duração, está implementada conforme documentado.【F:README.md†L175-L188】【F:app/callbacks/landing_page_callbacks.py†L41-L149】
- O endpoint `/run_preflight` realmente injeta plano fixo, especificações por formato e sinalizador `planning_mode="fixed"` antes de devolver o estado inicial, alinhando-se ao README.【F:README.md†L373-L386】【F:app/server.py†L200-L316】

## 2. Inconsistências Encontradas
- Campos "opcionais" `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` viram obrigatórios quando `ENABLE_NEW_INPUT_FIELDS=true`, contradizendo a seção de campos opcionais e a nota de refatoração.
  - Impacto: Usuários seguirão a documentação achando que os campos são opcionais e receberão 422 do preflight quando a flag for ativada.
  - Evidências no código: validações que rejeitam valores vazios para esses campos quando a flag está ativa.【F:README.md†L167-L171】【F:README.md†L103-L106】【F:helpers/user_extract_data.py†L300-L420】
  - **Correção Sugerida**: Atualizar o README para deixar claro que, com `ENABLE_NEW_INPUT_FIELDS=true`, os campos passam a ser obrigatórios (e explicar o fallback `shadow`), ou ajustar o código para mantê-los realmente opcionais.
- O README afirma que os loops de revisão chegam a 7/8/10 iterações, mas a configuração atual limita Plan Review a 1, Code Review a 3 e Final Validation a 3.
  - Impacto: Equipe pode planejar tempos de execução e tuning de loops com expectativas equivocadas.
  - Evidências no código: limites em `config` e na definição dos loops, divergindo dos números citados.【F:README.md†L208-L211】【F:README.md†L129-L130】【F:app/config.py†L28-L33】【F:app/agent.py†L1133-L1199】
  - **Correção Sugerida**: Sincronizar os valores documentados com os configurados ou explicar que os limites foram reduzidos.
- A documentação cita upload opcional para `gs://…/ads/final/...`, porém o código envia para `deliveries/<user>/<session>/...`.
  - Impacto: Operações e suporte podem procurar artefatos no prefixo errado no GCS.
  - Evidências no código: caminho de upload construído com prefixo `deliveries` na callback de persistência.【F:README.md†L108-L115】【F:app/callbacks/persist_outputs.py†L167-L193】
  - **Correção Sugerida**: Ajustar o README para o prefixo `deliveries/…` (ou alterar o código se o contrato for realmente `ads/final/`).
- O README orienta a **não** definir `GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json`, mas o `make dev` exporta exatamente essa variável por padrão.
  - Impacto: Execuções locais seguirão o Makefile e podem quebrar a autenticação por apontar para um arquivo inexistente, contrariando a recomendação oficial.
  - Evidências no código: instrução no README versus export automático no Makefile.【F:README.md†L93-L99】【F:Makefile†L26-L32】
  - **Correção Sugerida**: Harmonizar o Makefile com a recomendação (usar ADC sem setar a variável por default) ou atualizar o README para refletir o comportamento real.
- A seção de estrutura lista apenas `landing_page_callbacks.py` dentro de `app/callbacks`, ignorando `persist_outputs.py` presente no repositório.
  - Impacto: Desenvolvedores podem não descobrir o callback responsável por salvar entregas finais.
  - Evidências no código: listagem real da pasta inclui arquivo adicional.【F:README.md†L268-L279】【190d86†L1-L1】
  - **Correção Sugerida**: Atualizar a árvore de arquivos para incluir `persist_outputs.py` (e demais itens relevantes).
- O README ainda referencia `app/agent.py` com ~881 linhas, mas o arquivo cresceu para 1281 linhas.
  - Impacto: Dica obsoleta sobre tamanho do arquivo pode atrapalhar navegação ou revisões.
  - Evidências no código: contagem atual do arquivo usando `wc -l`.【F:README.md†L268-L272】【5082cb†L1-L2】

## 3. Pontos de Incerteza
- O README menciona travamento específico ao usar o campo `foco` (diagnóstico em `langextract_sb7.py` linha ~309). Não há logs automatizados ou testes reproduzindo esse cenário no repositório; não foi possível confirmar se o bug persiste ou se já foi mitigado.【F:README.md†L9-L16】
- O status “✅ Funcional” com mitigação de latência (2025-09-15) não possui evidências automatizadas de saúde geral (ex.: testes de ponta a ponta). Apenas verificações manuais mostraram alinhamento parcial; manter monitoramento adicional pode ser necessário.【F:README.md†L5-L7】
