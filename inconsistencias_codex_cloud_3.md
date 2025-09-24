# Inconsistências – Revisão da Refatoração de Campos de Entrada

## Tarefa 1 – Backend (`helpers/user_extract_data.py`)
- **Resultado:** Inconsistente.
- **Conformidades:** O prompt do extractor enumera os novos campos e os few-shots acrescentam exemplos com sinônimos de gênero, além de mapear o valor normalizado para `sexo_cliente_alvo` com default neutro no dicionário `normalized`. 【F:helpers/user_extract_data.py†L49-L112】【F:helpers/user_extract_data.py†L266-L335】
- **Divergências:** O plano exige que a inclusão dos novos campos no prompt e no `_convert` seja condicionada às flags `ENABLE_NEW_INPUT_FIELDS`/`PREFLIGHT_SHADOW_MODE`, mantendo retrocompatibilidade em shadow mode. 【F:refatoracao_campos_entrada.md†L763-L775】【F:refatoracao_campos_entrada.md†L861-L939】 Entretanto, o código atual sempre adiciona os campos e não consulta nenhuma flag de rollout, violando a estratégia descrita.

## Tarefa 2 – Backend (`app/server.py`)
- **Resultado:** Inconsistente.
- **Conformidades:** O `initial_state` passa a conter `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo`, com defaults aplicados e log estruturado emitindo métricas básicas sobre os novos campos. 【F:app/server.py†L220-L289】
- **Divergências:** O plano determina que o servidor leia as flags `ENABLE_NEW_INPUT_FIELDS` e `PREFLIGHT_SHADOW_MODE` para só incluir os novos campos quando habilitados, além de registrar um evento `preflight_new_fields_shadow` durante o shadow mode e usar as chaves `o_que_faz`/`sexo_alvo` no mapa de defaults. 【F:refatoracao_campos_entrada.md†L954-L989】【F:refatoracao_campos_entrada.md†L1193-L1205】 O código atual ignora as flags, inclui as novas chaves incondicionalmente e registra `defaults_used` com outras chaves, desviando do plano.

## Tarefa 3 – Frontend (Tipos e estado)
- **Resultado:** Conforme.
- **Justificativa:** As interfaces `WizardFormState` e `WizardValidationErrors` foram estendidas com os três campos adicionais, e `WIZARD_INITIAL_STATE` define defaults vazios conforme especificado. 【F:frontend/src/types/wizard.types.ts†L1-L29】【F:frontend/src/constants/wizard.constants.ts†L15-L24】 O plano lista exatamente essas adições. 【F:refatoracao_campos_entrada.md†L433-L465】

## Tarefa 4 – Frontend (Constants e Steps)
- **Resultado:** Inconsistente.
- **Conformidades:** Foram criados `SEXO_CLIENTE_OPTIONS` e passos específicos para `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo`, com regras de validação alinhadas aos limites do plano. 【F:frontend/src/constants/wizard.constants.ts†L41-L237】
- **Divergências:** O plano exige encapsular os novos passos atrás da flag `VITE_ENABLE_NEW_FIELDS` (`ENABLE_NEW_FIELDS` no código) e combinar `EXTRA_STEPS` com `BASE_STEPS` apenas quando a flag estiver ativa. 【F:refatoracao_campos_entrada.md†L463-L571】 A implementação atual publica os passos diretamente, sem qualquer condicional. Além disso, os textos de opção (`label` e `description` do valor neutro) divergem do copy indicado no plano, que pedia “Neutro/Misto” e “Público diversificado”. 【F:refatoracao_campos_entrada.md†L463-L474】

## Tarefa 5 – Frontend (Componentes de Step e integração)
- **Resultado:** Inconsistente.
- **Conformidades:** Foram criados componentes dedicados (`CompanyInfoStep`, `GenderTargetStep`) reutilizando os inputs da base e adicionados os novos cases ao `WizardForm`, além do `ReviewStep` listar automaticamente todos os passos. 【F:frontend/src/components/WizardForm/steps/CompanyInfoStep.tsx†L1-L60】【F:frontend/src/components/WizardForm/steps/GenderTargetStep.tsx†L1-L47】【F:frontend/src/components/WizardForm/WizardForm.tsx†L172-L255】【F:frontend/src/components/WizardForm/steps/ReviewStep.tsx†L12-L57】
- **Divergências:** O plano especifica props com `field`, `touched` e `onBlur` para os componentes de step e determina que o `WizardForm` passe essas props ao renderizar cada caso. 【F:refatoracao_campos_entrada.md†L579-L716】 A versão atual usa um `variant` simplificado e não expõe `onBlur`/`touched`, obrigando o formulário a marcar campos como tocados em `onChange`, o que não segue o fluxo planejado.

## Tarefa 6 – Frontend (Payload e validações)
- **Resultado:** Conforme.
- **Justificativa:** `formatSubmitPayload` continua iterando `WIZARD_STEPS`, inclui automaticamente os novos campos e força o default `neutro` quando `sexo_cliente_alvo` está vazio, exatamente como descrito no plano. 【F:frontend/src/utils/wizard.utils.ts†L107-L125】【F:refatoracao_campos_entrada.md†L724-L745】 As validações pré-existentes permanecem inalteradas no utilitário.

## Tarefa 7 – Testes
- **Resultado:** Conforme.
- **Justificativa:** Existem testes unitários cobrindo o extractor e o preflight com os novos campos, além de testes frontend para `formatSubmitPayload` e renderização dos passos recém-criados, atendendo à matriz solicitada. 【F:tests/unit/test_user_extract_data.py†L35-L75】【F:tests/unit/test_preflight.py†L54-L123】【F:frontend/tests/wizard.utils.test.ts†L6-L44】【F:frontend/tests/steps.test.tsx†L10-L38】

## Tarefa 8 – Rollout e flags
- **Resultado:** Inconsistente.
- **Divergências:** O plano determina rollout em fases utilizando as flags `ENABLE_NEW_INPUT_FIELDS`, `PREFLIGHT_SHADOW_MODE` e `VITE_ENABLE_NEW_FIELDS` para gradualmente expor os campos no backend e frontend. 【F:refatoracao_campos_entrada.md†L1174-L1230】 O código revisado ignora essas flags: o extractor, o servidor e o frontend publicam imediatamente os campos sem qualquer proteção, o que contraria a estratégia de migração.

## Tarefa 9 – Documentação
- **Resultado:** Conforme.
- **Justificativa:** O `README` documenta os novos campos no fluxo de uso e na descrição das entradas opcionais, e o plano de fallback foi atualizado para reconhecer os campos no estado, como requisitado. 【F:README.md†L20-L40】【F:README.md†L120-L179】【F:revisao_plano_fallback_storybrand.md†L47-L55】
