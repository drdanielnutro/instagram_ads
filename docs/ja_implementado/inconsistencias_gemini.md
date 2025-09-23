# Análise de Inconsistências - Wizard UI Feature Flag

Este documento registra as inconsistências encontradas ao revisar as tarefas de implementação do Wizard UI, conforme o `CHECKLIST.md`.

## Tarefa 1: Configuração da Flag

- **Status:** Implementada, mas com inconsistência.
- **Verificação:**
  - `[CORRETO]` A flag `VITE_ENABLE_WIZARD=false` foi adicionada ao arquivo `frontend/.env.example`.
  - `[CORRETO]` A documentação da flag foi adicionada ao `frontend/README.md`.
  - `[INCONSISTENTE]` A leitura da flag foi implementada de duas formas diferentes.
- **Justificativa:**
  O arquivo `frontend/src/components/WelcomeScreen.tsx` implementa a lógica de normalização da flag localmente, exatamente como sugerido no plano:
  ```tsx
  const wizardEnabled = (import.meta.env.VITE_ENABLE_WIZARD ?? "false")
    .toString()
    .toLowerCase() === "true";
  ```
  No entanto, foi criado um arquivo utilitário em `frontend/src/utils/featureFlags.ts` que contém uma função mais robusta e centralizada para o mesmo fim (`isWizardEnabled`), mas ela não é utilizada pelo `WelcomeScreen.tsx`. Isso gera duplicação de código e abre margem para futuras divergências, onde uma implementação pode ser atualizada e a outra não. A implementação correta seria `WelcomeScreen.tsx` importar e usar a função de `featureFlags.ts`.

