# Inconsistências – Codex Cloud 4

## Tarefa 1 – Backend: `helpers/user_extract_data.py`
**Status: correta.** O extractor ajusta o prompt quando as flags habilitam os novos campos, adiciona few-shots com exemplos e sinônimos, e preenche `data`/`normalized` com `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo`, normalizando o gênero para o domínio controlado e aplicando `neutro` como padrão. O logger do módulo também registra o uso de defaults apenas quando os campos estão habilitados, sem tornar nada obrigatório além das validações já existentes.【F:helpers/user_extract_data.py†L43-L395】

## Tarefa 2 – Backend: `app/server.py` (`/run_preflight`)
**Status: correta.** O endpoint inclui os novos campos no `initial_state` apenas quando a flag de rollout está ativa, aplicando os defaults especificados, preserva as chaves antigas e registra métricas estruturadas tanto em shadow mode quanto quando os campos estão habilitados de fato.【F:app/server.py†L220-L328】

## Tarefa 3 – Frontend: Tipos e estado
**Status: correta.** As interfaces e o estado inicial do wizard foram expandidos para conter `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo`, garantindo que as validações e o fluxo reconheçam as novas chaves.【F:frontend/src/types/wizard.types.ts†L3-L38】【F:frontend/src/constants/wizard.constants.ts†L15-L24】

## Tarefa 4 – Frontend: Constants e Steps
**Status: inconsistente.** O plano define os novos campos como opcionais com defaults aplicados no backend, mas a configuração dos steps torna `nome_empresa` e `o_que_a_empresa_faz` obrigatórios: eles não recebem `isOptional: true` e as validações bloqueiam avanço quando vazios; além disso, a função `canProceed` impede seguir sem preenchê-los. Assim, o usuário é forçado a fornecer valores, contrariando o requisito de campos opcionais documentado no plano e no README.【F:frontend/src/constants/wizard.constants.ts†L92-L141】【F:frontend/src/utils/wizard.utils.ts†L79-L85】【F:refatoracao_campos_entrada.md†L929-L939】【F:README.md†L161-L171】

## Tarefa 5 – Frontend: Componentes de Step
**Status: correta.** Os novos componentes reutilizam os inputs e textarea existentes, aplicam ícones do `lucide-react` já disponíveis e expõem callbacks de alteração/blur consistentes com os demais passos. O formulário principal renderiza os novos steps e o resumo final mostra os campos adicionais com fallback textual apropriado.【F:frontend/src/components/WizardForm/steps/CompanyInfoStep.tsx†L1-L93】【F:frontend/src/components/WizardForm/steps/GenderTargetStep.tsx†L1-L78】【F:frontend/src/components/WizardForm/WizardForm.tsx†L177-L255】【F:frontend/src/components/WizardForm/steps/ReviewStep.tsx†L11-L72】

## Tarefa 6 – Frontend: Payload e validações
**Status: correta.** `formatSubmitPayload` continua a iterar sobre `WIZARD_STEPS`, inclui automaticamente os novos campos quando presentes e impõe o default `sexo_cliente_alvo: neutro` ao encontrar o valor vazio, sem alterar as demais validações.【F:frontend/src/utils/wizard.utils.ts†L107-L125】

## Tarefa 7 – Testes
**Status: correta.** Existem testes unitários cobrindo a extração dos novos campos e o default de gênero no backend, testes de preflight para inclusão/defaults/feature-flag e testes de frontend para o utilitário de payload e renderização dos novos steps.【F:tests/unit/test_user_extract_data.py†L35-L79】【F:tests/unit/test_preflight.py†L40-L163】【F:frontend/tests/wizard.utils.test.ts†L1-L54】【F:frontend/tests/steps.test.tsx†L1-L53】

## Tarefa 8 – Rollout e flags
**Status: correta.** O extractor e o preflight obedecem às variáveis `ENABLE_NEW_INPUT_FIELDS` e `PREFLIGHT_SHADOW_MODE`, enquanto o frontend condiciona os novos steps à flag `VITE_ENABLE_NEW_FIELDS`, permitindo o rollout em fases conforme descrito.【F:helpers/user_extract_data.py†L49-L312】【F:app/server.py†L220-L307】【F:frontend/src/constants/wizard.constants.ts†L41-L279】

## Tarefa 9 – Documentação
**Status: correta.** O README detalha os novos campos como opcionais, com defaults e exemplo de uso, e o plano de fallback StoryBrand aponta que wizard, extractor e preflight já persistem as novas chaves.【F:README.md†L158-L171】【F:revisao_plano_fallback_storybrand.md†L40-L61】

