# Plano – Campos Obrigatórios para StoryBrand Fallback

## 1. Contexto e Objetivo
- Garantir que os campos `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` sejam coletados obrigatoriamente no fluxo do wizard sempre que a flag `VITE_ENABLE_NEW_FIELDS` estiver ativa.
- Eliminar cenários em que o pipeline de fallback falha por falta desses insumos, alinhando a UI com o contrato rígido definido no `aprimoramento_plano_storybrand_v2.md`.
- Preservar retrocompatibilidade quando a flag estiver desativada e manter o fluxo feliz funcional, apenas adicionando validações front-end.

## 2. Escopo
- **Frontend (React/Vite):** atualizações em estado, passos do wizard, validações, mensagens de erro e UX copy.
- **Backend (`helpers/user_extract_data.py`):** alinhar o extractor LangExtract às novas regras obrigatórias, garantindo falha imediata quando qualquer campo estiver ausente ou inválido.
- **Testes:** unitários/integração do frontend e backend cobrindo as regras obrigatórias.
- **Documentação:** atualizar artefatos que descrevem o wizard, o extractor e os checklists afetados.

## 3. Feature Flags e Comportamento
- `VITE_ENABLE_NEW_FIELDS = false`: o wizard se comporta como hoje (sem passos extras).
- `VITE_ENABLE_NEW_FIELDS = true`: 
  - Os passos dos três campos são incluídos e marcados como obrigatórios.
  - O usuário não avança nem conclui o wizard enquanto não preencher cada campo dentro das regras de validação.

## 4. Regras de Validação
- `nome_empresa`: string 2–100 caracteres; remover espaços extras antes de validar.
- `o_que_a_empresa_faz`: string 10–200 caracteres; permitir acentuação, rejeitar somente espaços.
- `sexo_cliente_alvo`: seleção obrigatória entre `masculino` e `feminino`.
- Mensagens de erro devem explicar que as informações alimentam o modo de qualidade avançada (fallback) e garantir clareza no motivo da obrigatoriedade.

## 5. Itens de Implementação
1. **Tipos e Estado Inicial**
   - Atualizar `WizardFormState` e `WizardValidationErrors` (se necessário) para refletir o tratamento obrigatório.
   - Revisar `WIZARD_INITIAL_STATE` e garantir que o reset do formulário respeite campos vazios, mas indique erro ao prosseguir.
2. **Configuração de Steps**
   - Ajustar `WIZARD_STEPS` para incluir validações síncronas que retornem erro quando as regras da seção 4 falharem.
   - Revisar ordem e ícones conforme necessidade.
3. **Componentes de Step**
   - Atualizar `CompanyInfoStep.tsx` (ou equivalente) para mostrar contadores de caracteres e mensagens de erro inline.
   - Atualizar o step de sexo alvo para forçar seleção e exibir tooltip/copy contextual.
4. **WizardForm / Hooks**
   - Garantir que `handleNextStep` e `handleSubmit` bloqueiem a navegação quando houver erro de validação.
   - Confirmar que o payload enviado contém os campos já normalizados.
5. **Copy e Feedback Visual**
   - Ajustar textos nos steps e review para explicar a utilização dos dados no fallback.
   - Verificar acessibilidade (aria-live em mensagens de erro, foco ao invalid field).
6. **Testes Frontend**
   - Atualizar/Adicionar testes que verifiquem: validação de comprimento, obrigatoriedade do sexo alvo, bloqueio de submissão e presença dos campos no payload final.
7. **Documentação e Checklist**
   - Atualizar `checklist_frontend.md` com os novos itens obrigatórios.
   - Revisar README/docs relevantes com exemplos do wizard.
8. **Backend – `helpers/user_extract_data.py`**
   - **Prompt de extração (`UserInputExtractor.__init__`):** atualizar `base_prompt` para listar apenas `masculino`/`feminino` como valores válidos; remover referências a `neutro` e ajustar a frase “map synonyms to masculino|feminino”.
   - **Few-shots (`UserInputExtractor._examples`):** revisar exemplos para garantir que todos produzem `sexo_cliente_alvo` normalizado em `masculino` ou `feminino`; substituir o exemplo que hoje retorna `neutro` por uma variação feminina/masculina.
   - **Conversão (`UserInputExtractor._convert`):**
     - Remover o bloco que injeta defaults (`optional_with_defaults`) para os três campos.
     - Após mapear os dados, validar explicitamente: se `nome_empresa`, `o_que_a_empresa_faz` ou `sexo_cliente_alvo_norm` estiverem vazios/ausentes, anexar erros (`errors.append({...})`) e retornar `success=False`.
     - Ajustar a lógica de fallback para não mais definir `sexo_cliente_alvo_norm = "neutro"` quando faltar valor; em vez disso, manter `None` e registrar erro.
   - **Normalização (`UserInputExtractor._normalize_sexo`):**
     - Atualizar o conjunto de aliases para retornar apenas `"masculino"` ou `"feminino"`.
     - Para entradas não reconhecidas, retornar `""`/`None` para sinalizar invalidade, permitindo que `_convert` gere o erro obrigatório.
   - **Erros retornados:** garantir que `errors` contenha mensagens claras (ex.: `"field": "sexo_cliente_alvo", "message": "Campo obrigatório. Escolha masculino ou feminino."`).
   - **Telemetria:** ajustar logs (`logger.info`) removendo mensagens sobre aplicação de defaults e, se desejado, logar as falhas de obrigatoriedade para observabilidade.
   - **Função pública (`extract_user_input`)**: sem alterações, mas os novos erros devem chegar ao `/run_preflight` para que o endpoint retorne 422.

## 6. Estratégia de Testes
- **Unitários (Frontend):** utilitários de validação, hooks do wizard, formatação do payload.
- **Unitários (Backend):** criar/atualizar testes de `helpers/user_extract_data.py` assegurando que `success=False` e `errors` apropriados sejam retornados quando qualquer campo faltar ou conter valor inválido.
- **Component Tests (frontend – vitest + testing-library):** interação passo a passo, mensagens de erro, submissão bloqueada.
- **Integração `/run_preflight`:** mockar entrada sem os campos obrigatórios e validar que a API responde 422 com as mensagens alinhadas.
- **Smoke Manual:** percorrer o wizard com flag ativa e inativa, garantindo experiência consistente.

## 7. Observabilidade e Regressão
- Garantir logs de console inexistentes após validação (usar testes para prevenir regressões).
- Verificar que a alteração não altera outras métricas do frontend (ex.: event tracking) – atualizar analytics se rastrearem os passos.

## 8. Dependências e Riscos
- Requer coordenação com o backend para validar os mesmos requisitos (evitar mensagens inconsistentes).
- UX: tornar campos obrigatórios pode aumentar atrito; considerar copy clara e possivelmente links para ajuda.
- Testes existentes podem precisar de ajustes (snapshots, mocks com estado incompleto).

## 9. Linha do Tempo Sugerida
1. Alinhar copy com stakeholders de produto/UX.
2. Implementar validações + atualizações de componentes.
3. Atualizar testes e documentação.
4. Executar QA manual e revisar com time responsável pelo fallback.
5. Merge após aprovação.

## 10. Critérios de Aceite
- Com `VITE_ENABLE_NEW_FIELDS=true`, é impossível concluir o wizard sem preencher os 3 campos válidos.
- O payload enviado ao backend sempre contém os 3 campos normalizados.
- Testes automatizados cobrindo validações obrigatórias passam.
- Documentação e checklist alinhados à nova política.
