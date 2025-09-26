# Inconsistências — Codex 6

1. **Uso de `config.ENABLE_NEW_INPUT_FIELDS` inexistente**
   - Descrição: O plano exige que o gate só libere o fallback quando `config.ENABLE_NEW_INPUT_FIELDS` for `True`, mas o objeto de configuração não expõe essa propriedade — a flag é lida diretamente via `os.getenv` no backend.
   - Impacto: Provoca exceção ou impede o rollout controlado, pois o gate não refletirá o estado real das flags.
   - Evidências: Plano (Seções 3 e 16.3) e ausência do atributo/uso direto das variáveis de ambiente no código.【F:aprimoramento_plano_storybrand_v2.md†L22-L26】【F:aprimoramento_plano_storybrand_v2.md†L201-L203】【F:app/config.py†L34-L71】【F:app/server.py†L220-L312】
   - Relação com ADK: O gate executa antes dos demais agentes; um erro aqui interrompe a sessão.

2. **Dependência de `state['preflight_meta']` sem fonte de dados**
   - Descrição: O plano prevê que o preflight marque `state['preflight_meta']['o_que_a_empresa_faz']` com o status do enriquecimento, mas o helper atual não produz essa estrutura e o endpoint bloqueia requisições inválidas antes de montar o `initial_state`.
   - Impacto: O `fallback_input_collector` ficaria aguardando metadados inexistentes, podendo abortar erroneamente ou exigir mudanças não especificadas no backend.
   - Evidências: Plano (Seção 4.1) e implementação atual do preflight/helper que não gera `preflight_meta` nem envia essa informação ao estado.【F:aprimoramento_plano_storybrand_v2.md†L50-L55】【F:helpers/user_extract_data.py†L412-L567】【F:app/server.py†L150-L312】
   - Relação com ADK: Sem o meta esperado, o coletor não consegue cumprir a lógica de validação proposta para o fallback.

3. **Caminho de arquivo absoluto desatualizado no plano**
   - Descrição: O documento ainda referencia `/Users/institutorecriare/.../plano_storybrand_fallback.md`, divergindo do arquivo versionado `aprimoramento_plano_storybrand_v2.md` na raiz do repositório.
   - Impacto: Pode confundir responsáveis durante incidentes, levando à consulta de um arquivo inexistente.
   - Evidências: Cabeçalho do plano com o caminho antigo.【F:aprimoramento_plano_storybrand_v2.md†L1-L2】
   - Relação com ADK: Documentação incorreta dificulta acionar o fallback manualmente de acordo com o plano certo.
