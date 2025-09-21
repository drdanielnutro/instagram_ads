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
- [ ] Revisar e confirmar que `frontend/src/components/WelcomeScreen.tsx` mantém o markup atual para o modo clássico
- [ ] Revisar e confirmar que `frontend/src/App.tsx`, `ChatMessagesView.tsx` e `ActivityTimeline.tsx` não foram modificados além da integração da flag

## 3. Estrutura de Pastas e Arquivos Novos
- [ ] Criar diretório `frontend/src/components/WizardForm/steps`
- [ ] Criar arquivo `frontend/src/types/wizard.types.ts`
- [ ] Criar arquivo `frontend/src/constants/wizard.constants.ts`
- [ ] Criar arquivo `frontend/src/utils/wizard.utils.ts`
- [ ] Criar arquivo `frontend/src/components/WizardForm/index.ts`
- [ ] Criar arquivo `frontend/src/components/WizardForm/WizardForm.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/ProgressHeader.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/StepCard.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/NavigationFooter.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/steps/LandingPageStep.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/steps/ObjectiveStep.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/steps/FormatStep.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/steps/ProfileStep.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/steps/FocusStep.tsx`
- [ ] Criar arquivo `frontend/src/components/WizardForm/steps/ReviewStep.tsx`

## 4. Implementação dos Tipos, Constantes e Utilitários
- [ ] Preencher `wizard.types.ts` com as interfaces `WizardFormState`, `WizardValidationErrors`, `ValidationRule` e `WizardStep`
- [ ] Preencher `wizard.constants.ts` com `WIZARD_INITIAL_STATE`, `WIZARD_STEPS`, `OBJETIVO_OPTIONS` e `FORMATO_OPTIONS`
- [ ] Implementar `wizard.utils.ts` com as funções `validateStepField`, `getCompletedSteps`, `canProceed`, `validateForm` e `formatSubmitPayload`

## 5. Implementação dos Componentes do Wizard
- [ ] Implementar lógica principal em `WizardForm.tsx` (state, navegação, submit, renderização condicional dos steps)
- [ ] Implementar `ProgressHeader.tsx` exibindo stepper e progresso
- [ ] Implementar `StepCard.tsx` como container padrão dos conteúdos dos steps
- [ ] Implementar `NavigationFooter.tsx` com botões Voltar/Próximo/Gerar e botão Cancelar quando `isLoading`
- [ ] Implementar `LandingPageStep.tsx` com input, dicas e tratamento de erros
- [ ] Implementar `ObjectiveStep.tsx` com cards selecionáveis baseados em `OBJETIVO_OPTIONS`
- [ ] Implementar `FormatStep.tsx` com cards selecionáveis baseados em `FORMATO_OPTIONS`
- [ ] Implementar `ProfileStep.tsx` com textarea, contador de caracteres e validação visual
- [ ] Implementar `FocusStep.tsx` com textarea opcional e indicação de campo
- [ ] Implementar `ReviewStep.tsx` listando dados finais e botões “Editar”

## 6. Integração Condicional na WelcomeScreen
- [ ] Importar `WizardForm` e `InputForm` em `frontend/src/components/WelcomeScreen.tsx`
- [ ] Ler e normalizar `VITE_ENABLE_WIZARD` no topo do arquivo
- [ ] Renderizar `WizardForm` quando a flag estiver ativa e manter o markup atual quando desativada

## 7. Verificações de Estilo e Tokens
- [ ] Garantir uso exclusivo de classes já suportadas (ex.: `bg-card`, `border-border`, `text-muted-foreground`)
- [ ] Adicionar novos tokens em `global.css` apenas se necessário, sem sobrescrever existentes

## 8. Testes e QA
- [ ] Testar fluxo completo com flag desativada (`VITE_ENABLE_WIZARD=false`)
- [ ] Testar fluxo completo com flag ativada (`VITE_ENABLE_WIZARD=true`), incluindo validações, cancelamento e envio
- [ ] Testar responsividade (mobile e desktop) e navegação por teclado no wizard
- [ ] Executar `npm run build` com flag desativada
- [ ] Executar `npm run build` com flag ativada

## 9. Rollout e Documentação
- [ ] Planejar rollout (staging → produção → canary → GA) conforme seção 9 do plano
- [ ] Atualizar documentação de suporte/comunicação interna após validação
- [ ] Registrar instruções de rollback (desligar flag e reiniciar frontend)
