# Guia de Implementação: Wizard UI com Feature Flag

Este manual fornece um roteiro completo para adicionar uma interface wizard ao fluxo de briefing sem tocar no formulário atual. Tudo fica protegido pela variável de ambiente `VITE_ENABLE_WIZARD`, permitindo alternar entre a UI antiga e a nova com um único toggle.

---

## 1. Visão Geral e Metas

- **Garantir compatibilidade total** com a experiência existente: a tela de boas-vindas, toolbar (incluindo botão de download JSON), chat e lógica de sessão permanecem inalterados.
- **Introduzir o wizard como alternativa opt-in**: a UI só aparece quando a flag estiver em `true`.
- **Permitir rollback imediato**: basta desligar a flag e reiniciar o frontend.
- **Isolar o código novo** em arquivos dedicados (`WizardForm`), facilitando a revisão e eventuais refactors futuros.

---

## 2. Configuração da Flag

1. **Adicionar a variável de ambiente**
   - Caminho: `frontend/.env.example` (e em `.env.local` durante o desenvolvimento).
   - Conteúdo sugerido:
     ```env
     # Toggle para habilitar o Wizard UI na tela inicial
     VITE_ENABLE_WIZARD=false
     ```
   - Deixe o valor padrão como `false` para evitar surpresas em máquinas novas.

2. **Documentar a flag**
   - Atualize `frontend/README.md` (ou página equivalente) com uma seção "Feature Flags" explicando:
     - Finalidade da flag
     - Como ativar (`VITE_ENABLE_WIZARD=true`)
     - Necessidade de reiniciar o `npm run dev` após mudanças.

3. **Conversão segura para booleano**
   - Sempre normalize o valor para evitar `undefined` ou capitalização errada:
     ```ts
     const enableWizard = (import.meta.env.VITE_ENABLE_WIZARD ?? 'false')
       .toString()
       .toLowerCase() === 'true';
     ```

---

## 3. Preservando a UI Atual

Nenhum destes arquivos deve ter alterações funcionais (mantemos a implementação atual para garantir rollback instantâneo):

- `frontend/src/components/InputForm.tsx`
- `frontend/src/components/WelcomeScreen.tsx` (apenas introduziremos o `if/else` sem remover o markup antigo)
- `frontend/src/App.tsx`
- `frontend/src/components/ChatMessagesView.tsx`
- `frontend/src/components/ActivityTimeline.tsx`

**IMPORTANTE:**
- Não mover lógica de download ou botões do topo.
- Não alterar estilos globais (`global.css`) a menos que seja para adicionar tokens opcionais.
- Eventuais melhorias na UI atual devem ser tratadas em PR separado.

---

## 4. Estrutura do Wizard (novos arquivos)

Crie os diretórios abaixo (relativos à raiz `frontend/`):

```
src/
├── components/
│   ├── WizardForm/
│   │   ├── WizardForm.tsx
│   │   ├── ProgressHeader.tsx
│   │   ├── StepCard.tsx
│   │   ├── NavigationFooter.tsx
│   │   ├── steps/
│   │   │   ├── LandingPageStep.tsx
│   │   │   ├── ObjectiveStep.tsx
│   │   │   ├── FormatStep.tsx
│   │   │   ├── ProfileStep.tsx
│   │   │   ├── FocusStep.tsx
│   │   │   └── ReviewStep.tsx
│   │   └── index.ts
├── constants/
│   └── wizard.constants.ts
├── types/
│   └── wizard.types.ts
└── utils/
    └── wizard.utils.ts
```

Sugestão de comandos (executados em `frontend/`):
```bash
mkdir -p src/components/WizardForm/steps
mkdir -p src/constants src/types src/utils
```

---

## 5. Implementação Detalhada dos Arquivos

### 5.1 `src/types/wizard.types.ts`

Defina todas as interfaces usadas pelo wizard.

```ts
import type { ComponentType } from 'react';

export interface WizardFormState {
  landing_page_url: string;
  objetivo_final: string;
  formato_anuncio: string;
  perfil_cliente: string;
  foco: string;
}

export interface WizardValidationErrors {
  landing_page_url?: string;
  objetivo_final?: string;
  formato_anuncio?: string;
  perfil_cliente?: string;
  foco?: string;
}

export interface ValidationRule {
  field: keyof WizardFormState;
  validate: (value: string, state: WizardFormState) => string | null;
}

export interface WizardStep {
  id: keyof WizardFormState | 'review';
  title: string;
  subtitle?: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  isOptional?: boolean;
  validationRules?: ValidationRule[];
}
```

### 5.2 `src/constants/wizard.constants.ts`

Responsável por agrupar textos, validações e opções dos selects.

```ts
import {
  LinkIcon,
  Target,
  Layout,
  Users,
  Sparkles,
  CheckCircle,
} from 'lucide-react';

import type { WizardFormState, WizardStep } from '@/types/wizard.types';

export const WIZARD_INITIAL_STATE: WizardFormState = {
  landing_page_url: '',
  objetivo_final: '',
  formato_anuncio: '',
  perfil_cliente: '',
  foco: '',
};

export const WIZARD_STEPS: WizardStep[] = [
  // defina cada step com validação inline
];

export const OBJETIVO_OPTIONS = [
  { value: 'agendamentos', label: 'Agendamentos', description: 'Marcar consultas ou reuniões' },
  { value: 'leads', label: 'Geração de Leads', description: 'Capturar contatos qualificados' },
  { value: 'vendas', label: 'Vendas Diretas', description: 'Converter em vendas imediatas' },
  { value: 'contato', label: 'Contato', description: 'Receber mensagens e interações' },
];

export const FORMATO_OPTIONS = [
  { value: 'Feed', label: 'Feed', ratio: '1:1 ou 4:5', description: 'Posts no feed principal' },
  { value: 'Stories', label: 'Stories', ratio: '9:16', description: 'Conteúdo vertical temporário' },
  { value: 'Reels', label: 'Reels', ratio: '9:16', description: 'Vídeos curtos e envolventes' },
];
```

**Dica de validações** (preencher no array `WIZARD_STEPS`):
- `landing_page_url`: campo obrigatório + validação de URL com `new URL(value)`.
- `objetivo_final`: obrigatório; garanta que o valor esteja em `OBJETIVO_OPTIONS`.
- `formato_anuncio`: obrigatório; valores `Feed | Stories | Reels`.
- `perfil_cliente`: obrigatório; mínimo 20 caracteres, máximo 500.
- `foco`: opcional; sem regras obrigatórias.
- `review`: step sem validação (apenas exibe resumo).

### 5.3 `src/utils/wizard.utils.ts`

Inclua todas as funções puras usadas pelo formulário.

```ts
import type {
  WizardFormState,
  WizardValidationErrors,
  WizardStep,
} from '@/types/wizard.types';

import { WIZARD_STEPS } from '@/constants/wizard.constants';

export function validateStepField(
  step: WizardStep,
  value: string,
  formState: WizardFormState,
): string | null {
  // percorre step.validationRules, retorna o primeiro erro
}

export function getCompletedSteps(
  formState: WizardFormState,
  currentStep: number,
): number[] {
  // retorna índices dos steps anteriores sem erro
}

export function canProceed(
  currentStep: number,
  formState: WizardFormState,
  errors: WizardValidationErrors,
): boolean {
  // impede avanço se campo obrigatório vazio ou com erro
}

export function validateForm(formState: WizardFormState): WizardValidationErrors {
  // usado no submit final
}

export function formatSubmitPayload(formState: WizardFormState): string {
  // monta string "campo: valor" para cada campo preenchido
}
```

### 5.4 `src/components/WizardForm/index.ts`

Arquivo simples de re-export:
```ts
export { WizardForm } from './WizardForm';
```

### 5.5 `src/components/WizardForm/WizardForm.tsx`

Estrutura o fluxo completo.

```tsx
import { useCallback, useMemo, useState } from 'react';

import type {
  WizardFormState,
  WizardValidationErrors,
} from '@/types/wizard.types';
import {
  WIZARD_INITIAL_STATE,
  WIZARD_STEPS,
} from '@/constants/wizard.constants';
import {
  canProceed,
  formatSubmitPayload,
  getCompletedSteps,
  validateForm,
  validateStepField,
} from '@/utils/wizard.utils';

import { ProgressHeader } from './ProgressHeader';
import { StepCard } from './StepCard';
import { NavigationFooter } from './NavigationFooter';
import { LandingPageStep } from './steps/LandingPageStep';
// importe os demais steps...

interface WizardFormProps {
  onSubmit: (payload: string) => void;
  isLoading: boolean;
  onCancel: () => void;
}

export function WizardForm({ onSubmit, isLoading, onCancel }: WizardFormProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formState, setFormState] = useState<WizardFormState>(WIZARD_INITIAL_STATE);
  const [errors, setErrors] = useState<WizardValidationErrors>({});
  const [touched, setTouched] = useState<Set<keyof WizardFormState>>(new Set());

  const handleFieldChange = useCallback(
    (field: keyof WizardFormState, value: string) => {
      setFormState(prev => ({ ...prev, [field]: value }));
      setTouched(prev => new Set([...prev, field]));
      const step = WIZARD_STEPS[currentStep];
      if (step.id === field) {
        const error = validateStepField(step, value, formState);
        setErrors(prev => ({ ...prev, [field]: error || undefined }));
      }
    },
    [currentStep, formState],
  );

  // implementar handleNext, handleBack, handleSubmit, renderStepContent...
  // use StepCard + ProgressHeader para compor a tela

  return (
    <div className="min-h-screen flex flex-col bg-background px-4 py-8">
      <div className="mx-auto w-full max-w-2xl flex-1 flex flex-col gap-6">
        <ProgressHeader
          steps={WIZARD_STEPS}
          currentStep={currentStep}
          completedSteps={getCompletedSteps(formState, currentStep)}
        />

        <StepCard step={WIZARD_STEPS[currentStep]}>
          {/* renderStepContent() */}
        </StepCard>

        <NavigationFooter
          currentStep={currentStep}
          totalSteps={WIZARD_STEPS.length}
          onNext={handleNext}
          onBack={handleBack}
          onSubmit={handleSubmit}
          onCancel={onCancel}
          canProceed={canProceed(currentStep, formState, errors)}
          isLoading={isLoading}
          isOptional={Boolean(WIZARD_STEPS[currentStep]?.isOptional)}
        />
      </div>
    </div>
  );
}
```

**Observações:**
- Use as classes já disponíveis (`bg-background`, `border-border`, `text-foreground` etc.).
- Nenhuma animação é necessária; mantenha o layout estático.

### 5.6 `ProgressHeader.tsx`

Objetivo: exibir os passos, estado atual e progresso.

Dicas:
- Representar a barra com `div` usando `bg-border` para base e `bg-primary` para a parte preenchida.
- Cada step deve mostrar o ícone (`<step.icon />`), número e título.
- Props esperadas: `steps`, `currentStep`, `completedSteps`.
- Use utilitário `cn` (`@/utils`) para combinar classes condicionalmente.

### 5.7 `StepCard.tsx`

Container genérico para o conteúdo.

```tsx
import type { WizardStep } from '@/types/wizard.types';
import { cn } from '@/utils';

interface StepCardProps {
  step: WizardStep;
  children: React.ReactNode;
}

export function StepCard({ step, children }: StepCardProps) {
  return (
    <section
      className={cn(
        'bg-card border border-border/60 rounded-2xl shadow-lg',
        'p-8 flex flex-col gap-6',
      )}
    >
      <header className="flex items-start gap-4">
        <div className="rounded-xl bg-primary/20 text-primary p-3">
          <step.icon className="h-6 w-6" />
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-foreground">{step.title}</h2>
          {step.subtitle && (
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              {step.subtitle}
            </span>
          )}
          <p className="text-sm text-muted-foreground">{step.description}</p>
        </div>
      </header>
      <div>{children}</div>
    </section>
  );
}
```

### 5.8 `NavigationFooter.tsx`

Responsável pelos botões de navegação.

- Use o componente `Button` existente (`@/components/ui/button`).
- Estrutura sugerida: botão "Voltar" à esquerda, indicador "Passo X de Y" no centro, botão "Próximo" ou "Gerar anúncios" à direita.
- Exibir "Cancelar geração" (variante `ghost`, classe `text-destructive`) quando `isLoading` estiver `true`.
- Props: `currentStep`, `totalSteps`, `onNext`, `onBack`, `onSubmit`, `onCancel`, `canProceed`, `isLoading`, `isOptional`.

### 5.9 Componentes de Step (`steps/*.tsx`)

Todos utilizam componentes já existentes (`Input`, `Textarea`, `Select`, `Button`, `Badge` etc.).

- **LandingPageStep**
  - Input (`@/components/ui/input`), label e helper text.
  - Chips com exemplos (botões `type="button"`).
  - Exibir mensagem de erro (`AlertCircle`) quando `error` existir.

- **ObjectiveStep**
  - Mapear `OBJETIVO_OPTIONS` em cards cliqueáveis (pode usar `<button>` com classes utilitárias).
  - Indicar item selecionado com borda `border-primary`.

- **FormatStep**
  - Semelhante ao Objective, porém usando `FORMATO_OPTIONS`.
  - Mostrar ratio/descrição.

- **ProfileStep**
  - Textarea com contador de caracteres. Utilize `text-amber-500` quando o contador estiver > 90% do limite.

- **FocusStep**
  - Textarea opcional + medalha "Opcional".
  - `AlertCircle` importado de `lucide-react` para indicar erros.

- **ReviewStep**
  - Recebe `formState` e `onEdit`.
  - Renderizar cada campo com label, valor e botão "Editar" que chama `onEdit('campo')`.
  - Indicar campos vazios como "Não preenchido".

### 5.10 Regras de Validação (no `WizardForm.tsx`)

- `handleNext`
  - Executa `validateStepField` antes de avançar.
  - Se `step.isOptional` e o valor estiver vazio, permite pular.

- `handleSubmit`
  - Chama `validateForm`; se houver erro, move para o primeiro step com problema.
  - Quando não houver erros, gera payload usando `formatSubmitPayload(formState)` e chama `onSubmit`.

- `renderStepContent`
  - Switch pelo `step.id`, retornando componente correspondente com props `value`, `onChange`, `error` (usar `touched.has(field)` para decidir se exibe erro).

---

## 6. Integração Condicional na `WelcomeScreen`

1. **Importações**
   ```tsx
   import { WizardForm } from '@/components/WizardForm';
   import { InputForm } from '@/components/InputForm';
   ```

2. **Leitura da flag** (logo no topo do arquivo):
   ```tsx
   const enableWizard = (import.meta.env.VITE_ENABLE_WIZARD ?? 'false')
     .toString()
     .toLowerCase() === 'true';
   ```

3. **Renderização condicional**
   ```tsx
   export function WelcomeScreen(props: WelcomeScreenProps) {
     if (enableWizard) {
       return (
         <WizardForm
           onSubmit={props.handleSubmit}
           isLoading={props.isLoading}
           onCancel={props.onCancel}
         />
       );
     }

     return (
       // Reutilize exatamente a marcação atual (SectionCard + InputForm)
       <ExistingWelcomeMarkup {...props} />
     );
   }
   ```

   - `ExistingWelcomeMarkup` é apenas um placeholder; mantenha o JSX como está hoje.
   - Não remova `StatusBadge`, `SectionCard`, `InputForm`, botões ou textos existentes.

4. **Chat**
   - Nenhuma mudança: a área de chat (`ChatMessagesView`) continua exibindo `InputForm` para envios posteriores.

---

## 7. Estilos e Tokens

- Use as classes Tailwind já fornecidas (`bg-card`, `border-border`, `text-muted-foreground`, `rounded-2xl`, etc.).
- Caso precise de cor adicional, inclua `var(--primary)` e similares diretamente no `style` ou adicione variáveis novas em `global.css` (sem sobrescrever as existentes).
- Evite criar classes customizadas via `@layer` sem atualizar o tema; manter a consistência com o design atual é prioridade.

---

## 8. Testes e QA

1. **Fluxo com flag desligada**
   - `VITE_ENABLE_WIZARD=false`
   - Rodar `npm run dev`
   - Garantir que o formulário antigo aparece e a geração funciona (inclusive botão "Baixar JSON").

2. **Fluxo com flag ligada**
   - `VITE_ENABLE_WIZARD=true`
   - Rodar `npm run dev`
   - Percorrer cada passo do wizard:
     - Verificar validação de URL.
     - Selecionar objetivo/formato.
     - Testar limites de caracteres em perfil.
     - Pular foco (deve prosseguir mesmo vazio).
     - Confirmar review e envio (payload idêntico, geração bem-sucedida).
   - Testar cancelamento enquanto `isLoading`.
   - Testar responsividade: viewport 375px (mobile) e >1280px (desktop).
   - Testar navegação por teclado (Tab/Shift+Tab) e foco visível nos elementos interativos.

3. **Build**
   - Rodar `npm run build` com a flag `false` e `true` para garantir que nada depende de runtime.

4. **Checklist de UI**
   - Toolbar continua no topo.
   - Switch de preflight continua funcionando.
   - Contagem de mensagens e timeline permanecem operacionais.

---

## 9. Estratégia de Rollout

1. **Staging**: habilitar a flag em `VITE_ENABLE_WIZARD=true`, validar com o time.
2. **Produção**: deploy inicial com flag `false` (ambiente seguro).
3. **Canary**: habilitar flag apenas para contas internas (via `.env` específico ou build separado).
4. **Medição**: monitorar abandono, tempo até envio e erros de validação.
5. **GA (lançamento total)**: quando métricas forem satisfatórias, mudar o default para `true` e comunicar suporte/UX.

---

## 10. Checklist Final

- [ ] Flag adicionada e documentada (`frontend/.env.example`, README).
- [ ] Estrutura de pastas criada conforme seção 4.
- [ ] Arquivos de tipos (`wizard.types.ts`), constantes e utils implementados.
- [ ] Componentes `WizardForm`, `ProgressHeader`, `StepCard`, `NavigationFooter` e steps finalizados.
- [ ] `WelcomeScreen.tsx` alterna entre UI antiga e nova usando `enableWizard`.
- [ ] Fluxo antigo validado com flag OFF (incluindo download de JSON).
- [ ] Fluxo wizard validado com flag ON (desktop + mobile + teclado).
- [ ] `npm run build` passando em ambos os cenários.
- [ ] Documentação atualizada descrevendo como ligar/desligar a flag.
- [ ] Plano de rollback testado (desligar flag e reiniciar).

---

Com estes passos, qualquer pessoa (ou agente IA) consegue implementar a UI wizard de forma segura, isolada e plenamente reversível.
