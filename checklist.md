# Checklist de Implementação – Wizard UI com Feature Flag

> Convenção de status: substitua manualmente o marcador de cada item conforme avança.
> - `[ ]` = pending (padrão)
> - `[>]` = in progress
> - `[x]` = done

## 1. Configuração da Flag
- [x] Adicionar `VITE_ENABLE_WIZARD=false` em `frontend/.env.example` (e replicar em `.env.local` quando necessário)
- [x] Documentar a flag em `frontend/README.md` explicando finalidade, uso e necessidade de reiniciar `npm run dev`
- [x] Garantir leitura segura da flag (normalização para booleano) nos arquivos que dependem dela

## 2. Preservação da UI Atual
- [x] Revisar e confirmar que `frontend/src/components/InputForm.tsx` permanece inalterado
- [x] Revisar e confirmar que `frontend/src/components/WelcomeScreen.tsx` mantém o markup atual para o modo clássico
- [x] Revisar e confirmar que `frontend/src/App.tsx`, `ChatMessagesView.tsx` e `ActivityTimeline.tsx` não foram modificados além da integração da flag

## 3. Estrutura de Pastas e Arquivos Novos
- [x] Criar diretório `frontend/src/components/WizardForm/steps`
- [x] Criar arquivo `frontend/src/types/wizard.types.ts`
- [x] Criar arquivo `frontend/src/constants/wizard.constants.ts`
- [x] Criar arquivo `frontend/src/utils/wizard.utils.ts`
- [x] Criar arquivo `frontend/src/components/WizardForm/index.ts`
- [x] Criar arquivo `frontend/src/components/WizardForm/WizardForm.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/ProgressHeader.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/StepCard.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/NavigationFooter.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/steps/LandingPageStep.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/steps/ObjectiveStep.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/steps/FormatStep.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/steps/ProfileStep.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/steps/FocusStep.tsx`
- [x] Criar arquivo `frontend/src/components/WizardForm/steps/ReviewStep.tsx`

## 4. Implementação dos Tipos, Constantes e Utilitários
- [x] Preencher `wizard.types.ts` com as interfaces `WizardFormState`, `WizardValidationErrors`, `ValidationRule` e `WizardStep`
- [x] Preencher `wizard.constants.ts` com `WIZARD_INITIAL_STATE`, `WIZARD_STEPS`, `OBJETIVO_OPTIONS` e `FORMATO_OPTIONS`
- [x] Implementar `wizard.utils.ts` com as funções `validateStepField`, `getCompletedSteps`, `canProceed`, `validateForm` e `formatSubmitPayload`

## 5. Implementação dos Componentes do Wizard
- [x] Implementar lógica principal em `WizardForm.tsx` (state, navegação, submit, renderização condicional dos steps)
- [x] Implementar `ProgressHeader.tsx` exibindo stepper e progresso
- [x] Implementar `StepCard.tsx` como container padrão dos conteúdos dos steps
- [x] Implementar `NavigationFooter.tsx` com botões Voltar/Próximo/Gerar e botão Cancelar quando `isLoading`
- [x] Implementar `LandingPageStep.tsx` com input, dicas e tratamento de erros
- [x] Implementar `ObjectiveStep.tsx` com cards selecionáveis baseados em `OBJETIVO_OPTIONS`
- [x] Implementar `FormatStep.tsx` com cards selecionáveis baseados em `FORMATO_OPTIONS`
- [x] Implementar `ProfileStep.tsx` com textarea, contador de caracteres e validação visual
- [x] Implementar `FocusStep.tsx` com textarea opcional e indicação de campo
- [x] Implementar `ReviewStep.tsx` listando dados finais e botões “Editar”

## 6. Integração Condicional na WelcomeScreen
- [x] Importar `WizardForm` e `InputForm` em `frontend/src/components/WelcomeScreen.tsx`
- [x] Ler e normalizar `VITE_ENABLE_WIZARD` no topo do arquivo
- [x] Renderizar `WizardForm` quando a flag estiver ativa e manter o markup atual quando desativada

## 7. Verificações de Estilo e Tokens
- [x] Garantir uso exclusivo de classes já suportadas (ex.: `bg-card`, `border-border`, `text-muted-foreground`)
- [x] Adicionar novos tokens em `global.css` apenas se necessário, sem sobrescrever existentes

## 8. Testes e QA
- [>] Testar fluxo completo com flag desativada (`VITE_ENABLE_WIZARD=false`)
- [x] Testar fluxo completo com flag ativada (`VITE_ENABLE_WIZARD=true`), incluindo validações, cancelamento e envio
- [ ] Testar responsividade (mobile e desktop) e navegação por teclado no wizard
- [ ] Executar `npm run build` com flag desativada
- [ ] Executar `npm run build` com flag ativada

## 9. Rollout e Documentação
- [ ] Planejar rollout (staging → produção → canary → GA) conforme seção 9 do plano
- [ ] Atualizar documentação de suporte/comunicação interna após validação
- [ ] Registrar instruções de rollback (desligar flag e reiniciar frontend)
