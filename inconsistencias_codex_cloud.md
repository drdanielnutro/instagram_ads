# Auditoria do Plano "Wizard UI com Feature Flag"

A tabela a seguir documenta o estado de cada item do `checklist.md`, confrontando o código vigente com as expectativas descritas em `WIZARD_FEATURE_FLAG_PLAN.md`.

## 1. Configuração da Flag
- **1.1 `.env.example`** – *Status: Conformidade.* A variável `VITE_ENABLE_WIZARD` está presente com valor padrão `false`, conforme instrução de manter a flag desligada por padrão.【F:WIZARD_FEATURE_FLAG_PLAN.md†L18-L25】【F:frontend/.env.example†L1-L8】
- **1.2 Documentação no README** – *Status: Conformidade.* O `frontend/README.md` contém seção própria explicando finalidade, ativação, desativação e necessidade de reiniciar o `npm run dev`, atendendo ao plano.【F:WIZARD_FEATURE_FLAG_PLAN.md†L27-L31】【F:frontend/README.md†L5-L14】 
- **1.3 Normalização booleana** – *Status: Conformidade.* A leitura da flag na `WelcomeScreen` normaliza o valor exatamente como no trecho recomendado, evitando variações de capitalização ou valores indefinidos.【F:WIZARD_FEATURE_FLAG_PLAN.md†L33-L39】【F:frontend/src/components/WelcomeScreen.tsx†L20-L28】

## 2. Preservação da UI Atual
- **2.1 `InputForm.tsx`** – *Status: Conformidade.* O formulário clássico permanece com os mesmos campos e formato de payload (`campo: valor`), sem condicionais relativas à flag, garantindo compatibilidade do modo antigo.【F:WIZARD_FEATURE_FLAG_PLAN.md†L43-L57】【F:frontend/src/components/InputForm.tsx†L61-L96】
- **2.2 `WelcomeScreen.tsx` (modo clássico)** – *Status: Conformidade.* Quando a flag está desativada, o componente renderiza o markup pré-existente (SectionCard + InputForm + botão de cancelamento) intacto, apenas guardado atrás do `if/else` recomendado.【F:WIZARD_FEATURE_FLAG_PLAN.md†L448-L466】【F:frontend/src/components/WelcomeScreen.tsx†L32-L80】 
- **2.3 Demais arquivos legados** – *Status: Conformidade.* `App.tsx`, `ChatMessagesView.tsx` e `ActivityTimeline.tsx` continuam consumindo os componentes originais sem lógica adicional ligada ao wizard, preservando o comportamento histórico.【F:WIZARD_FEATURE_FLAG_PLAN.md†L43-L57】【F:frontend/src/App.tsx†L1-L67】【F:frontend/src/components/ChatMessagesView.tsx†L1-L14】【F:frontend/src/components/ActivityTimeline.tsx†L1-L40】

## 3. Estrutura de Pastas e Arquivos Novos
Todos os arquivos e diretórios listados no plano foram criados nos caminhos indicados, atendendo integralmente ao item 3.【F:WIZARD_FEATURE_FLAG_PLAN.md†L60-L92】【F:frontend/src/components/WizardForm/WizardForm.tsx†L1-L27】【F:frontend/src/components/WizardForm/index.ts†L1-L1】【F:frontend/src/types/wizard.types.ts†L1-L32】【F:frontend/src/constants/wizard.constants.ts†L1-L161】【F:frontend/src/utils/wizard.utils.ts†L1-L121】

## 4. Tipos, Constantes e Utilitários
- **4.1 `wizard.types.ts`** – *Status: Conformidade.* As interfaces `WizardFormState`, `WizardValidationErrors`, `ValidationRule` e `WizardStep` foram implementadas exatamente como descrito.【F:WIZARD_FEATURE_FLAG_PLAN.md†L96-L135】【F:frontend/src/types/wizard.types.ts†L1-L32】
- **4.2 `wizard.constants.ts`** – *Status: Conformidade.* O arquivo define `WIZARD_INITIAL_STATE`, `WIZARD_STEPS` com validações inline, além das coleções `OBJETIVO_OPTIONS` e `FORMATO_OPTIONS`, seguindo as orientações de validação.【F:WIZARD_FEATURE_FLAG_PLAN.md†L137-L199】【F:frontend/src/constants/wizard.constants.ts†L1-L161】
- **4.3 `wizard.utils.ts`** – *Status: **Inconsistência**.* As funções de validação (`validateStepField`, `getCompletedSteps`, `canProceed`, `validateForm`) respeitam o plano; entretanto `formatSubmitPayload` monta o payload com os títulos legíveis dos passos (ex.: “Qual é a página de destino?”) em vez do formato `campo: valor` exigido para manter compatibilidade com o backend – o plano requer explicitamente “monta string `"campo: valor"`” e o formulário clássico continua enviando as chaves em snake case (`landing_page_url`, etc.).【F:WIZARD_FEATURE_FLAG_PLAN.md†L223-L229】【F:frontend/src/utils/wizard.utils.ts†L107-L121】【F:frontend/src/components/InputForm.tsx†L67-L90】 Essa divergência pode gerar payloads inesperados quando o wizard está ativo.

## 5. Implementação dos Componentes do Wizard
- **5.1 `WizardForm.tsx`** – *Status: Conformidade.* O componente controla estado, navegação, validações e envio conforme especificado, além de expor `onCancel` e alternar os passos pelo `renderStepContent` com uso de `touched` e `errors`.【F:WIZARD_FEATURE_FLAG_PLAN.md†L239-L430】【F:frontend/src/components/WizardForm/WizardForm.tsx†L1-L244】
- **5.2 `ProgressHeader.tsx`** – *Status: **Inconsistência**.* Embora exiba barra de progresso, passo atual e etapas concluídas, o cabeçalho não renderiza o ícone de cada step, contrariando a diretriz “Cada step deve mostrar o ícone (`<step.icon />`)”.【F:WIZARD_FEATURE_FLAG_PLAN.md†L330-L338】【F:frontend/src/components/WizardForm/ProgressHeader.tsx†L41-L75】
- **5.3 `StepCard.tsx`** – *Status: Conformidade.* O container segue exatamente o layout sugerido, incluindo ícone, título, subtítulo e descrição do passo.【F:WIZARD_FEATURE_FLAG_PLAN.md†L340-L378】【F:frontend/src/components/WizardForm/StepCard.tsx†L1-L33】
- **5.4 `NavigationFooter.tsx`** – *Status: Conformidade.* O footer oferece botões Voltar/Próximo (ou Gerar), indicador de passo e botão “Cancelar geração” visível apenas durante carregamento, alinhado ao plano.【F:WIZARD_FEATURE_FLAG_PLAN.md†L381-L388】【F:frontend/src/components/WizardForm/NavigationFooter.tsx†L1-L80】
- **5.5 Passos individuais** – *Status: Conformidade.*
  - `LandingPageStep` fornece input, dicas, exemplos e mensagem de erro.【F:WIZARD_FEATURE_FLAG_PLAN.md†L390-L398】【F:frontend/src/components/WizardForm/steps/LandingPageStep.tsx†L1-L68】
  - `ObjectiveStep` e `FormatStep` geram cards clicáveis com as opções configuradas, destacando a seleção.【F:WIZARD_FEATURE_FLAG_PLAN.md†L399-L405】【F:frontend/src/components/WizardForm/steps/ObjectiveStep.tsx†L12-L52】【F:frontend/src/components/WizardForm/steps/FormatStep.tsx†L12-L53】
  - `ProfileStep` apresenta textarea com contador e alerta visual próximo ao limite de 500 caracteres.【F:WIZARD_FEATURE_FLAG_PLAN.md†L407-L408】【F:frontend/src/components/WizardForm/steps/ProfileStep.tsx†L11-L47】
  - `FocusStep` indica tratar-se de campo opcional e mantém suporte a mensagens de erro via `AlertCircle`.【F:WIZARD_FEATURE_FLAG_PLAN.md†L410-L412】【F:frontend/src/components/WizardForm/steps/FocusStep.tsx†L1-L43】
  - `ReviewStep` lista cada campo, marca vazios como “Não preenchido” e expõe botão “Editar” por passo.【F:WIZARD_FEATURE_FLAG_PLAN.md†L414-L417】【F:frontend/src/components/WizardForm/steps/ReviewStep.tsx†L11-L66】

## 6. Integração Condicional na WelcomeScreen
- **6.1 Importações e leitura da flag** – *Status: Conformidade.* O componente importa `WizardForm` e `InputForm`, lê `VITE_ENABLE_WIZARD` com a normalização indicada e guarda o valor em `wizardEnabled` no topo do arquivo.【F:WIZARD_FEATURE_FLAG_PLAN.md†L436-L447】【F:frontend/src/components/WelcomeScreen.tsx†L1-L28】
- **6.2 Renderização condicional** – *Status: Conformidade.* O retorno alterna integralmente entre o wizard e o markup antigo sem remover badges, SectionCard, botões ou textos originais, respeitando o fallback imediato previsto.【F:WIZARD_FEATURE_FLAG_PLAN.md†L449-L471】【F:frontend/src/components/WelcomeScreen.tsx†L24-L80】

## 7. Estilos e Tokens
- *Status: Conformidade.* Os novos componentes utilizam classes já existentes (`bg-card`, `border-border`, `text-muted-foreground`, `bg-primary/…`) e não introduzem tokens adicionais em `global.css`, cumprindo o item 7.【F:WIZARD_FEATURE_FLAG_PLAN.md†L477-L481】【F:frontend/src/components/WizardForm/NavigationFooter.tsx†L30-L76】【F:frontend/src/components/WizardForm/steps/LandingPageStep.tsx†L20-L66】

## 8. Testes e QA
- *Status: Não verificado.* Não há evidências no repositório de que os fluxos foram testados com a flag desligada/ligada, nem de execuções de `npm run build` nas duas configurações ou validações de responsividade e acessibilidade indicadas. Recomenda-se registrar esses testes antes do rollout.【F:WIZARD_FEATURE_FLAG_PLAN.md†L485-L512】

## 9. Rollout e Documentação
- *Status: Não verificado.* Não foram encontrados registros de planejamento de rollout, atualização de documentação interna ou instruções de rollback além da própria existência da flag. Esses tópicos seguem pendentes conforme o plano.【F:WIZARD_FEATURE_FLAG_PLAN.md†L515-L520】
