# Plano de Implementação Wizard V2 - Corrigido e Completo

## 1. Definições e Interfaces TypeScript

### 1.1 Tipos Base

```typescript
// types/wizard.types.ts

// Interface para o estado do formulário (evitando conflito com FormData nativo)
export interface WizardFormState {
  landing_page_url: string;
  objetivo_final: string;
  formato_anuncio: string;
  perfil_cliente: string;
  foco: string;
}

// Interface para erros de validação
export interface WizardValidationErrors {
  landing_page_url?: string;
  objetivo_final?: string;
  formato_anuncio?: string;
  perfil_cliente?: string;
  foco?: string;
}

// Interface para definição de steps
export interface WizardStep {
  id: keyof WizardFormState | 'review';
  title: string;
  subtitle?: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  isOptional?: boolean;
  validationRules?: ValidationRule[];
}

// Interface para regras de validação
export interface ValidationRule {
  field: keyof WizardFormState;
  validate: (value: string, formState: WizardFormState) => string | null;
}

// Estados possíveis do wizard
export type WizardStatus = 'idle' | 'validating' | 'submitting' | 'success' | 'error';
```

### 1.2 Constantes e Configurações

```typescript
// constants/wizard.constants.ts
import { LinkIcon, Target, Layout, Users, Sparkles, CheckCircle } from 'lucide-react';
import type { WizardStep } from '../types/wizard.types';

// Definição completa de todos os steps
export const WIZARD_STEPS: WizardStep[] = [
  {
    id: 'landing_page_url',
    title: 'Landing Page',
    subtitle: 'Passo 1 de 5',
    description: 'Informe a URL principal que resume a oferta. Usaremos a página para validar copy, tom e CTA.',
    icon: LinkIcon,
    isOptional: false,
    validationRules: [
      {
        field: 'landing_page_url',
        validate: (value: string) => {
          if (!value.trim()) return 'URL é obrigatória';
          try {
            new URL(value);
            return null;
          } catch {
            return 'URL inválida. Use formato: https://exemplo.com';
          }
        }
      }
    ]
  },
  {
    id: 'objetivo_final',
    title: 'Objetivo',
    subtitle: 'Passo 2 de 5',
    description: 'Escolha a ação esperada do público para ajustar copy, CTA e fluxo do anúncio.',
    icon: Target,
    isOptional: false,
    validationRules: [
      {
        field: 'objetivo_final',
        validate: (value: string) => {
          if (!value.trim()) return 'Objetivo é obrigatório';
          const validOptions = ['agendamentos', 'leads', 'vendas', 'contato'];
          if (!validOptions.includes(value)) return 'Selecione um objetivo válido';
          return null;
        }
      }
    ]
  },
  {
    id: 'formato_anuncio',
    title: 'Formato do Anúncio',
    subtitle: 'Passo 3 de 5',
    description: 'Feed, Stories ou Reels determinam limites de texto, aspect ratio e estilo visual.',
    icon: Layout,
    isOptional: false,
    validationRules: [
      {
        field: 'formato_anuncio',
        validate: (value: string) => {
          if (!value.trim()) return 'Formato é obrigatório';
          const validFormats = ['Feed', 'Stories', 'Reels']; // Mantendo separados conforme backend
          if (!validFormats.includes(value)) return 'Selecione um formato válido';
          return null;
        }
      }
    ]
  },
  {
    id: 'perfil_cliente',
    title: 'Perfil do Cliente',
    subtitle: 'Passo 4 de 5',
    description: 'Resuma persona, dores, desejos e estilo de comunicação desejado para manter coerência.',
    icon: Users,
    isOptional: false,
    validationRules: [
      {
        field: 'perfil_cliente',
        validate: (value: string) => {
          if (!value.trim()) return 'Perfil do cliente é obrigatório';
          if (value.length < 20) return 'Descreva com pelo menos 20 caracteres';
          if (value.length > 500) return 'Máximo de 500 caracteres';
          return null;
        }
      }
    ]
  },
  {
    id: 'foco',
    title: 'Foco da Campanha',
    subtitle: 'Passo 5 de 5 (Opcional)',
    description: 'Liste diferenciais, mensagens obrigatórias ou restrições (compliance, claims proibidos, etc.).',
    icon: Sparkles,
    isOptional: true, // Campo opcional - pode ser pulado
    validationRules: [] // Sem validação obrigatória
  },
  {
    id: 'review',
    title: 'Revisão Final',
    subtitle: 'Confirme os dados',
    description: 'Revise todas as informações antes de gerar os anúncios.',
    icon: CheckCircle,
    isOptional: false,
    validationRules: [] // Validação ocorre nos campos individuais
  }
];

// Valores padrão para o formulário
export const WIZARD_INITIAL_STATE: WizardFormState = {
  landing_page_url: '',
  objetivo_final: '',
  formato_anuncio: '',
  perfil_cliente: '',
  foco: ''
};

// Opções para campos de seleção
export const OBJETIVO_OPTIONS = [
  { value: 'agendamentos', label: 'Agendamentos', description: 'Marcar consultas ou reuniões' },
  { value: 'leads', label: 'Geração de Leads', description: 'Capturar contatos qualificados' },
  { value: 'vendas', label: 'Vendas Diretas', description: 'Converter em vendas imediatas' },
  { value: 'contato', label: 'Contato', description: 'Receber mensagens e interações' }
];

export const FORMATO_OPTIONS = [
  { value: 'Feed', label: 'Feed', ratio: '1:1 ou 4:5', description: 'Posts no feed principal' },
  { value: 'Stories', label: 'Stories', ratio: '9:16', description: 'Conteúdo vertical temporário' },
  { value: 'Reels', label: 'Reels', ratio: '9:16', description: 'Vídeos curtos e envolventes' }
];
```

## 2. Funções Utilitárias Completas

### 2.1 Validação e Navegação

```typescript
// utils/wizard.utils.ts

import { WizardFormState, WizardValidationErrors, WizardStep } from '../types/wizard.types';
import { WIZARD_STEPS } from '../constants/wizard.constants';

/**
 * Retorna os índices dos steps já completados com sucesso
 */
export function getCompletedSteps(
  formState: WizardFormState,
  currentStep: number
): number[] {
  const completed: number[] = [];

  for (let i = 0; i < currentStep; i++) {
    const step = WIZARD_STEPS[i];
    if (step.id === 'review') continue;

    const fieldValue = formState[step.id as keyof WizardFormState];
    const isValid = validateStepField(step, fieldValue, formState);

    if (isValid === null) {
      completed.push(i);
    }
  }

  return completed;
}

/**
 * Valida um campo específico do step
 */
export function validateStepField(
  step: WizardStep,
  value: string,
  formState: WizardFormState
): string | null {
  if (!step.validationRules || step.validationRules.length === 0) {
    return null;
  }

  for (const rule of step.validationRules) {
    const error = rule.validate(value, formState);
    if (error) return error;
  }

  return null;
}

/**
 * Verifica se o usuário pode avançar para o próximo step
 */
export function canProceed(
  currentStep: number,
  formState: WizardFormState,
  errors: WizardValidationErrors
): boolean {
  const step = WIZARD_STEPS[currentStep];

  // Step de revisão sempre pode prosseguir se chegou até aqui
  if (step.id === 'review') {
    return !hasAnyErrors(errors);
  }

  // Steps opcionais sempre podem prosseguir
  if (step.isOptional) {
    return true;
  }

  // Valida o campo atual
  const fieldName = step.id as keyof WizardFormState;
  const fieldValue = formState[fieldName];
  const fieldError = errors[fieldName];

  return fieldValue.trim() !== '' && !fieldError;
}

/**
 * Verifica se um step é opcional
 */
export function isOptionalStep(stepIndex: number): boolean {
  const step = WIZARD_STEPS[stepIndex];
  return step?.isOptional || false;
}

/**
 * Verifica se há algum erro no formulário
 */
export function hasAnyErrors(errors: WizardValidationErrors): boolean {
  return Object.values(errors).some(error => error !== undefined && error !== null);
}

/**
 * Valida todo o formulário
 */
export function validateForm(formState: WizardFormState): WizardValidationErrors {
  const errors: WizardValidationErrors = {};

  for (const step of WIZARD_STEPS) {
    if (step.id === 'review') continue;
    if (step.isOptional) continue;

    const fieldName = step.id as keyof WizardFormState;
    const fieldValue = formState[fieldName];
    const error = validateStepField(step, fieldValue, formState);

    if (error) {
      errors[fieldName] = error;
    }
  }

  return errors;
}

/**
 * Formata o payload final para envio
 */
export function formatSubmitPayload(formState: WizardFormState): string {
  const lines: string[] = [];

  if (formState.landing_page_url.trim()) {
    lines.push(`landing_page_url: ${formState.landing_page_url.trim()}`);
  }
  if (formState.objetivo_final.trim()) {
    lines.push(`objetivo_final: ${formState.objetivo_final.trim()}`);
  }
  if (formState.perfil_cliente.trim()) {
    lines.push(`perfil_cliente: ${formState.perfil_cliente.trim()}`);
  }
  if (formState.formato_anuncio.trim()) {
    lines.push(`formato_anuncio: ${formState.formato_anuncio.trim()}`);
  }
  if (formState.foco.trim()) {
    lines.push(`foco: ${formState.foco.trim()}`);
  }

  return lines.join('\n');
}
```

## 3. Componentes Completos - TODOS os Steps

### 3.1 ProfileStep (Campo 4 - Faltante no V1)

```tsx
// components/WizardForm/steps/ProfileStep.tsx

import React from 'react';
import { Users, AlertCircle } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/utils';

interface ProfileStepProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function ProfileStep({ value, onChange, error }: ProfileStepProps) {
  const charCount = value.length;
  const maxChars = 500;

  return (
    <div className="space-y-6">
      {/* Helper card */}
      <div className="bg-primary/10 rounded-xl p-4 border border-primary/20">
        <p className="text-sm text-foreground/80 flex items-start gap-2">
          <Users className="w-4 h-4 mt-0.5 flex-shrink-0" />
          Descreva seu público-alvo: idade, gênero, interesses, dores e desejos.
          Quanto mais específico, melhor o resultado.
        </p>
      </div>

      {/* Textarea field */}
      <div className="space-y-2">
        <label htmlFor="perfil-cliente" className="text-sm font-medium text-foreground">
          Perfil do Cliente Ideal
        </label>
        <Textarea
          id="perfil-cliente"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Ex.: Mulheres 35-55, buscam emagrecimento com suporte médico, tom acolhedor..."
          className={cn(
            "min-h-[120px] resize-none",
            "bg-background border-2",
            "focus:border-primary focus:ring-2 focus:ring-primary/20",
            "transition-all duration-200",
            error && "border-destructive focus:border-destructive"
          )}
          maxLength={maxChars}
        />

        {/* Character count */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            {error && (
              <p className="text-sm text-destructive flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                {error}
              </p>
            )}
          </div>
          <span className={cn(
            "text-xs",
            charCount > maxChars * 0.9 ? "text-warning" : "text-muted-foreground"
          )}>
            {charCount}/{maxChars}
          </span>
        </div>
      </div>

      {/* Examples chips */}
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">Elementos sugeridos:</p>
        <div className="flex flex-wrap gap-2">
          {[
            'Faixa etária',
            'Localização',
            'Renda',
            'Dores/problemas',
            'Objetivos',
            'Tom de voz'
          ].map(element => (
            <span
              key={element}
              className="px-3 py-1 text-xs bg-card-elevated rounded-full border border-border/50"
            >
              {element}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
```

### 3.2 FocusStep (Campo 5 - Faltante no V1)

```tsx
// components/WizardForm/steps/FocusStep.tsx

import React from 'react';
import { Sparkles, Info } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/utils';

interface FocusStepProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function FocusStep({ value, onChange, error }: FocusStepProps) {
  return (
    <div className="space-y-6">
      {/* Optional badge */}
      <div className="bg-blue-500/10 rounded-xl p-4 border border-blue-500/20">
        <p className="text-sm text-foreground/80 flex items-start gap-2">
          <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>
            <strong>Campo opcional:</strong> Use para diferenciais, promoções ou
            restrições específicas (compliance, claims proibidos, etc.)
          </span>
        </p>
      </div>

      {/* Textarea field */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label htmlFor="foco" className="text-sm font-medium text-foreground">
            Foco da Campanha
          </label>
          <span className="text-xs text-muted-foreground bg-card px-2 py-1 rounded">
            Opcional
          </span>
        </div>

        <Textarea
          id="foco"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Ex.: destacar acompanhamento médico, evitar promessas de emagrecimento rápido..."
          className={cn(
            "min-h-[100px] resize-none",
            "bg-background border-2",
            "focus:border-primary focus:ring-2 focus:ring-primary/20",
            "transition-all duration-200",
            error && "border-destructive focus:border-destructive"
          )}
        />

        {error && (
          <p className="text-sm text-destructive flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {error}
          </p>
        )}
      </div>

      {/* Skip hint */}
      <div className="text-center">
        <p className="text-xs text-muted-foreground">
          Você pode pular este campo e deixar o assistente decidir o melhor approach
        </p>
      </div>
    </div>
  );
}
```

### 3.3 Componente Principal - WizardForm Completo

```tsx
// components/WizardForm/WizardForm.tsx

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/utils';

// Import types and constants
import type { WizardFormState, WizardValidationErrors } from '@/types/wizard.types';
import { WIZARD_STEPS, WIZARD_INITIAL_STATE } from '@/constants/wizard.constants';

// Import utilities
import {
  getCompletedSteps,
  canProceed,
  validateForm,
  formatSubmitPayload,
  validateStepField
} from '@/utils/wizard.utils';

// Import components
import { ProgressHeader } from './ProgressHeader';
import { StepCard } from './StepCard';
import { NavigationFooter } from './NavigationFooter';
import { BackgroundEffects } from './BackgroundEffects';

// Import step components
import { LandingPageStep } from './steps/LandingPageStep';
import { ObjectiveStep } from './steps/ObjectiveStep';
import { FormatStep } from './steps/FormatStep';
import { ProfileStep } from './steps/ProfileStep';
import { FocusStep } from './steps/FocusStep';
import { ReviewStep } from './steps/ReviewStep';

interface WizardFormProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
  onCancel: () => void;
}

export function WizardForm({ onSubmit, isLoading, onCancel }: WizardFormProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formState, setFormState] = useState<WizardFormState>(WIZARD_INITIAL_STATE);
  const [errors, setErrors] = useState<WizardValidationErrors>({});
  const [touched, setTouched] = useState<Set<keyof WizardFormState>>(new Set());

  // Handle field changes
  const handleFieldChange = useCallback((field: keyof WizardFormState, value: string) => {
    setFormState(prev => ({ ...prev, [field]: value }));

    // Mark field as touched
    setTouched(prev => new Set([...prev, field]));

    // Validate field in real-time if touched
    const step = WIZARD_STEPS[currentStep];
    if (step.id === field) {
      const error = validateStepField(step, value, formState);
      setErrors(prev => ({ ...prev, [field]: error || undefined }));
    }
  }, [currentStep, formState]);

  // Navigate to next step
  const handleNext = useCallback(() => {
    const step = WIZARD_STEPS[currentStep];

    // Skip validation for optional steps if empty
    if (step.isOptional && step.id !== 'review') {
      const fieldName = step.id as keyof WizardFormState;
      if (!formState[fieldName].trim()) {
        setCurrentStep(prev => Math.min(prev + 1, WIZARD_STEPS.length - 1));
        return;
      }
    }

    // Validate current step before proceeding
    if (step.id !== 'review') {
      const fieldName = step.id as keyof WizardFormState;
      const error = validateStepField(step, formState[fieldName], formState);

      if (error) {
        setErrors(prev => ({ ...prev, [fieldName]: error }));
        setTouched(prev => new Set([...prev, fieldName]));
        return;
      }
    }

    setCurrentStep(prev => Math.min(prev + 1, WIZARD_STEPS.length - 1));
  }, [currentStep, formState]);

  // Navigate to previous step
  const handleBack = useCallback(() => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  }, []);

  // Submit form
  const handleSubmit = useCallback(() => {
    const validationErrors = validateForm(formState);

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      // Go to first step with error
      const firstErrorStep = WIZARD_STEPS.findIndex(
        step => step.id in validationErrors
      );
      if (firstErrorStep !== -1) {
        setCurrentStep(firstErrorStep);
      }
      return;
    }

    const payload = formatSubmitPayload(formState);
    onSubmit(payload);
  }, [formState, onSubmit]);

  // Edit field from review step
  const handleEdit = useCallback((field: keyof WizardFormState) => {
    const stepIndex = WIZARD_STEPS.findIndex(step => step.id === field);
    if (stepIndex !== -1) {
      setCurrentStep(stepIndex);
    }
  }, []);

  // Render current step content
  const renderStepContent = () => {
    const step = WIZARD_STEPS[currentStep];

    switch (step.id) {
      case 'landing_page_url':
        return (
          <LandingPageStep
            value={formState.landing_page_url}
            onChange={(value) => handleFieldChange('landing_page_url', value)}
            error={touched.has('landing_page_url') ? errors.landing_page_url : undefined}
          />
        );

      case 'objetivo_final':
        return (
          <ObjectiveStep
            value={formState.objetivo_final}
            onChange={(value) => handleFieldChange('objetivo_final', value)}
            error={touched.has('objetivo_final') ? errors.objetivo_final : undefined}
          />
        );

      case 'formato_anuncio':
        return (
          <FormatStep
            value={formState.formato_anuncio}
            onChange={(value) => handleFieldChange('formato_anuncio', value)}
            error={touched.has('formato_anuncio') ? errors.formato_anuncio : undefined}
          />
        );

      case 'perfil_cliente':
        return (
          <ProfileStep
            value={formState.perfil_cliente}
            onChange={(value) => handleFieldChange('perfil_cliente', value)}
            error={touched.has('perfil_cliente') ? errors.perfil_cliente : undefined}
          />
        );

      case 'foco':
        return (
          <FocusStep
            value={formState.foco}
            onChange={(value) => handleFieldChange('foco', value)}
            error={touched.has('foco') ? errors.foco : undefined}
          />
        );

      case 'review':
        return (
          <ReviewStep
            formState={formState}
            onEdit={handleEdit}
          />
        );

      default:
        return null;
    }
  };

  // Check if animations should be reduced
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Background effects with motion preference check */}
      {!prefersReducedMotion && <BackgroundEffects />}

      {/* Main container */}
      <div className="flex-1 flex flex-col max-w-2xl mx-auto w-full px-4 py-8">

        {/* Progress header */}
        <ProgressHeader
          steps={WIZARD_STEPS}
          currentStep={currentStep}
          completedSteps={getCompletedSteps(formState, currentStep)}
        />

        {/* Step card with animations */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={prefersReducedMotion ? false : { opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={prefersReducedMotion ? false : { opacity: 0, x: -50 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="flex-1 flex items-center justify-center py-8"
          >
            <StepCard step={WIZARD_STEPS[currentStep]}>
              {renderStepContent()}
            </StepCard>
          </motion.div>
        </AnimatePresence>

        {/* Navigation footer */}
        <NavigationFooter
          currentStep={currentStep}
          totalSteps={WIZARD_STEPS.length}
          onNext={handleNext}
          onBack={handleBack}
          onSubmit={handleSubmit}
          onCancel={onCancel}
          canProceed={canProceed(currentStep, formState, errors)}
          isLoading={isLoading}
          isOptional={WIZARD_STEPS[currentStep]?.isOptional}
        />
      </div>
    </div>
  );
}
```

## 4. Integração com App.tsx

### 4.1 Modificação do WelcomeScreen

```tsx
// components/WelcomeScreen.tsx

import { WizardForm } from '@/components/WizardForm/WizardForm';

interface WelcomeScreenProps {
  handleSubmit: (query: string) => void;
  isLoading: boolean;
  onCancel: () => void;
}

export function WelcomeScreen({
  handleSubmit,
  isLoading,
  onCancel,
}: WelcomeScreenProps) {
  return (
    <WizardForm
      onSubmit={handleSubmit}
      isLoading={isLoading}
      onCancel={onCancel}
    />
  );
}
```

### 4.2 Modificação do App.tsx

```tsx
// App.tsx (modificação parcial)

// Em vez de InputForm, agora usa WizardForm através de WelcomeScreen
// O handleSubmit recebe a string formatada do wizard
const handleSubmit = async (query: string) => {
  // query já vem formatada como:
  // landing_page_url: https://exemplo.com
  // objetivo_final: agendamentos
  // formato_anuncio: Feed
  // perfil_cliente: ...
  // foco: ...

  // Processa normalmente
  await processQuery(query);
};
```

## 5. Ajustes de Tema (Incrementais, não globais)

### 5.1 CSS Variables Adicionais (não sobrescreve existentes)

```css
/* global.css - Adicionar sem quebrar o existente */

/* Wizard-specific tokens */
:root {
  /* Preserve existing variables */
  /* ... existing variables remain unchanged ... */

  /* Add new wizard-specific variables */
  --wizard-bg: var(--background);
  --wizard-card: var(--card);
  --wizard-card-hover: #2a2f3d;
  --wizard-border-active: rgba(124, 92, 255, 0.4);
  --wizard-progress-bg: rgba(255, 255, 255, 0.1);
  --wizard-progress-fill: var(--primary);
  --wizard-step-complete: #10b981;
  --wizard-step-active: var(--primary);
  --wizard-step-pending: var(--muted);
}

/* Accessibility: Reduced motion */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Wizard-specific utilities */
@layer utilities {
  .wizard-container {
    @apply min-h-screen flex flex-col;
  }

  .wizard-card {
    @apply bg-wizard-card rounded-2xl border-2 border-border/50;
    @apply shadow-xl;
  }

  .wizard-card-hover {
    @apply hover:bg-wizard-card-hover hover:border-wizard-border-active;
    @apply transition-all duration-200;
  }
}
```

## 6. Animações com Acessibilidade

### 6.1 BackgroundEffects com prefers-reduced-motion

```tsx
// components/WizardForm/BackgroundEffects.tsx

export function BackgroundEffects() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReducedMotion) {
    // Versão estática para acessibilidade
    return (
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
      </div>
    );
  }

  // Versão animada normal
  return (
    <>
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-primary/10 rounded-full blur-3xl animate-pulse animation-delay-2000" />
      </div>
      <div className="fixed inset-0 bg-grid-pattern opacity-[0.02] pointer-events-none" />
    </>
  );
}
```

## 7. Package.json Dependencies

```json
{
  "dependencies": {
    // Existing dependencies...
    "framer-motion": "^10.16.4", // Para animações
    "lucide-react": "^0.263.1"   // Já deve estar instalado
  }
}
```

## 8. Estrutura de Arquivos Final

```
src/
├── components/
│   ├── WizardForm/
│   │   ├── WizardForm.tsx
│   │   ├── ProgressHeader.tsx
│   │   ├── StepCard.tsx
│   │   ├── NavigationFooter.tsx
│   │   ├── BackgroundEffects.tsx
│   │   ├── steps/
│   │   │   ├── LandingPageStep.tsx
│   │   │   ├── ObjectiveStep.tsx
│   │   │   ├── FormatStep.tsx
│   │   │   ├── ProfileStep.tsx  ✅ (novo)
│   │   │   ├── FocusStep.tsx     ✅ (novo)
│   │   │   └── ReviewStep.tsx
│   │   └── index.ts
│   └── WelcomeScreen.tsx (modificado)
├── types/
│   └── wizard.types.ts           ✅ (novo)
├── constants/
│   └── wizard.constants.ts       ✅ (novo)
├── utils/
│   └── wizard.utils.ts          ✅ (novo)
└── App.tsx (sem mudanças no handleSubmit)
```

## 9. Checklist de Implementação

- [ ] Instalar framer-motion
- [ ] Criar estrutura de pastas
- [ ] Implementar types/wizard.types.ts
- [ ] Implementar constants/wizard.constants.ts
- [ ] Implementar utils/wizard.utils.ts
- [ ] Criar todos os 6 step components
- [ ] Implementar WizardForm principal
- [ ] Adicionar CSS variables do wizard
- [ ] Integrar com WelcomeScreen
- [ ] Testar acessibilidade (keyboard nav, screen reader, reduced motion)
- [ ] Testar responsividade (mobile, tablet, desktop)

## 10. Validação Final

Este plano V2 resolve TODOS os problemas apontados:

✅ **FormData renomeado** para WizardFormState
✅ **Todas as funções utilitárias** definidas e implementadas
✅ **Tipagem completa** com interfaces TypeScript
✅ **ProfileStep e FocusStep** implementados
✅ **Formatos separados** (Feed, Stories, Reels)
✅ **Tema incremental** sem quebrar o app
✅ **Acessibilidade completa** com prefers-reduced-motion
✅ **Integração clara** com código existente

O plano está pronto para implementação real.