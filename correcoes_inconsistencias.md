# Plano de Correção: Centralizar a Leitura da Feature Flag

**Objetivo:** Modificar o componente `WelcomeScreen.tsx` para que ele utilize a função utilitária `isWizardEnabled`, eliminando a duplicação de código e tornando a implementação mais robusta e fácil de manter.

**Arquivo a ser modificado:**
*   `frontend/src/components/WelcomeScreen.tsx`

---

**Passo 1: Importar a função utilitária**

No topo do arquivo, adicione a importação da função `isWizardEnabled` que já existe no projeto.

```tsx
// frontend/src/components/WelcomeScreen.tsx

import { ArrowRight, Sparkles } from "lucide-react";

// ... outras importações
import { InputForm } from "@/components/InputForm";
import { WizardForm } from "@/components/WizardForm";
import { isWizardEnabled } from '@/utils/featureFlags'; // <<< ADICIONAR ESTA LINHA
```

---

**Passo 2: Substituir a lógica inline pela chamada da função**

Localize a linha onde a variável `wizardEnabled` é declarada e substitua a implementação manual pela chamada à função que acabamos de importar.

*   **Código ATUAL a ser removido:**
    ```tsx
    export function WelcomeScreen({ ... }) {
      const wizardEnabled = (import.meta.env.VITE_ENABLE_WIZARD ?? "false")
        .toString()
        .toLowerCase() === "true";

      // ... resto do componente
    }
    ```

*   **Novo código a ser inserido no lugar:**
    ```tsx
    export function WelcomeScreen({ ... }) {
      const wizardEnabled = isWizardEnabled();

      // ... resto do componente
    }
    ```

---

**Justificativa e Impacto:**

*   **Impacto:** Mínimo. A função `isWizardEnabled()` é funcionalmente idêntica (e até mais robusta) à lógica que está sendo removida. Não haverá nenhuma mudança no comportamento da aplicação.
*   **Benefício:** A lógica de leitura da feature flag passa a existir em um único lugar (`frontend/src/utils/featureFlags.ts`). Qualquer futura manutenção ou correção será feita apenas nesse arquivo, garantindo consistência em todo o projeto.

Este plano resolve a inconsistência da Tarefa 1 de forma limpa e segura.

---

# Plano Detalhado de Correção (Codex)

  - 1. Entendimento do Problema
      - Relembrar o formato aceito pela pipeline: verificar como o backend interpreta landing_page_url: ... etc. (consultar frontend/src/components/InputForm.tsx:69-95 e, se
  necessário, rastrear até app/server.py para confirmar que as chaves em snake_case são obrigatórias).
      - Revisar o contrato visual do wizard definido no checklist e o layout atual do ProgressHeader (frontend/src/components/WizardForm/ProgressHeader.tsx:1-64), garantindo que a
  presença do ícone é requisito funcional, não apenas cosmético.
  - 2. Correção do Payload (formatSubmitPayload)
      - Abrir frontend/src/utils/wizard.utils.ts.
      - Ajustar a função para:
          - Iterar apenas sobre steps com step.id !== 'review'.
          - Montar cada linha via template literal `${step.id}: ${formState[step.id].trim()}` preservando a ordem das etapas.
          - Ignorar campos vazios pós-trim, tal como o formulário clássico.
      - Avaliar se precisamos de helper para conversão (ex.: criar const fieldKey = step.id as keyof WizardFormState para type safety).
      - Conferir se não existe step sem ID mapeado (review não deve entrar).
      - Caso a string final fique vazia, comportamento deve ser idêntico ao formulário clássico (não enviar nada).
      - (Opcional, mas recomendado) Adicionar teste unitário simples em frontend/src/utils/__tests__/wizard.utils.test.ts exercitando formatSubmitPayload com estado parcialmente
  preenchido e verificando o formato produzido.
      - Garantir que outras funções (validateForm, canProceed) não dependem de step.title.
  - 3. Inclusão de Ícones no ProgressHeader
      - Atualizar o JSX de frontend/src/components/WizardForm/ProgressHeader.tsx:
          - Dentro do map, inserir <step.icon /> junto ao número. Ex.: um span ou div flex alinhando ícone e número.
          - Definir classes globais: className="h-4 w-4" ou similar, para manter ícone proporcional.
          - Ajustar estados (isActive, isCompleted) para aplicar classes de cor tanto ao ícone quanto ao número; pode ser necessário envolver ambos em um div que compartilha as
  mesmas classes (border, bg-primary/10, etc.).
          - Testar fallback: caso algum step futuro não defina icon, decidir comportamento (hoje todos definem, então basta assumir).
      - Verificar responsividade com flex-wrap habilitado (já existente), garantindo que inclusão do ícone não quebra o layout em telas menores. Se necessário, usar gap-2 e items-
  center.
      - Manter completedSteps highlight sem regressões: ícone deve mudar de cor junto com o badge numerado.
  - 4. Verificações Manuais / Testes
      - Executar npm run lint (ou make lint) para garantir que alterações respeitam regras de estilo/TS.
      - Executar npm run build para verificar que bundler aceita as mudanças.
      - Smoke test manual (opcional, mas recomendável):
          - Iniciar npm run dev.
          - Com VITE_ENABLE_WIZARD=true, preencher wizard até o final; copiar o payload gerado e confirmar formato campo: valor.
          - Com a flag desligada, garantir que o formulário clássico segue inalterado.
          - Visualizar ProgressHeader em viewport desktop e reduzir para ~375px para observar wrap.
      - Caso tenha sido criado teste unitário, rodar npm test ou uv run pytest (conforme stack) para confirmar execução.
  - 5. Documentação e Comunicação
      - Atualizar inconsistencias_codex_cli.md (ou arquivo de rastreamento equivalente) marcando as correções efetuadas e incluindo observações de verificação.
      - Se testes manuais foram realizados, registrar data e resultados no mesmo documento.
      - (Opcional) Considerar abrir ticket/nota para futura refatoração da utilidade isWizardEnabled ou padronização de tokens (caso seja desejo do time), deixando claro que não é
  problema atual.
  - 6. Follow-up
      - Sugerir revisão por outro dev/QA após PR.
      - Checar se novas inconsistências surgiram durante o ajuste (ex.: se o payload formato campo: valor precisa incluir labels legíveis em algum lugar visual – avaliar UX com o
  time, se necessário).
      - Planejar publicação de patch release caso a inconsistência tenha impacto imediato em produção.
