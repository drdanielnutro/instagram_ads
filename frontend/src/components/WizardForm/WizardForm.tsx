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
import { ObjectiveStep } from './steps/ObjectiveStep';
import { FormatStep } from './steps/FormatStep';
import { ProfileStep } from './steps/ProfileStep';
import { FocusStep } from './steps/FocusStep';
import { ReviewStep } from './steps/ReviewStep';
import { CompanyInfoStep } from './steps/CompanyInfoStep';
import { GenderTargetStep } from './steps/GenderTargetStep';

// Botões simples sem dependências extras
function MobileToggle({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      aria-label="Abrir/fechar lista de passos"
      onClick={onToggle}
      className="lg:hidden mb-3 inline-flex items-center gap-2 rounded-md border border-border/60 bg-card/70 px-3 py-2 text-sm"
    >
      {open ? 'Fechar passos' : 'Ver passos'}
    </button>
  );
}

type WizardField = keyof WizardFormState;

interface WizardFormProps {
  onSubmit: (payload: string) => void;
  isLoading: boolean;
  onCancel: () => void;
}

export function WizardForm({ onSubmit, isLoading, onCancel }: WizardFormProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formState, setFormState] =
    useState<WizardFormState>(WIZARD_INITIAL_STATE);
  const [errors, setErrors] = useState<WizardValidationErrors>({});
  const [touched, setTouched] = useState<Set<WizardField>>(new Set());
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const currentWizardStep = WIZARD_STEPS[currentStep];

  const completedSteps = useMemo(
    () => getCompletedSteps(formState, currentStep),
    [formState, currentStep],
  );

  const markFieldTouched = useCallback((field: WizardField) => {
    setTouched(prevTouched => {
      if (prevTouched.has(field)) {
        return prevTouched;
      }
      const updated = new Set(prevTouched);
      updated.add(field);
      return updated;
    });
  }, []);

  const updateFieldError = useCallback(
    (field: WizardField, value: string, nextState: WizardFormState) => {
      const step = WIZARD_STEPS.find(item => item.id === field);
      if (!step) {
        return;
      }

      const validationError = validateStepField(step, value, nextState);
      setErrors(prevErrors => {
        if (validationError) {
          return { ...prevErrors, [field]: validationError };
        }

        if (!(field in prevErrors)) {
          return prevErrors;
        }

        const { [field]: _, ...rest } = prevErrors;
        return rest;
      });
    },
    [],
  );

  const handleFieldChange = useCallback(
    (field: WizardField, value: string) => {
      setFormState(prevState => {
        const nextState = { ...prevState, [field]: value };
        markFieldTouched(field);
        updateFieldError(field, value, nextState);
        return nextState;
      });
    },
    [markFieldTouched, updateFieldError],
  );

  const goToStep = useCallback((stepIndex: number) => {
    setCurrentStep(() => {
      if (stepIndex < 0) {
        return 0;
      }
      if (stepIndex >= WIZARD_STEPS.length) {
        return WIZARD_STEPS.length - 1;
      }
      return stepIndex;
    });
  }, []);

  const handleNext = useCallback(() => {
    const step = WIZARD_STEPS[currentStep];
    if (!step || step.id === 'review') {
      return;
    }

    const field = step.id;
    const value = formState[field];
    markFieldTouched(field);
    updateFieldError(field, value, formState);

    const validationError = validateStepField(step, value, formState);
    if (validationError) {
      setErrors(prev => ({ ...prev, [field]: validationError }));
      return;
    }

    goToStep(currentStep + 1);
  }, [currentStep, formState, goToStep, markFieldTouched, updateFieldError]);

  const handleBack = useCallback(() => {
    goToStep(currentStep - 1);
  }, [currentStep, goToStep]);

  const handleSubmit = useCallback(() => {
    const validationErrors = validateForm(formState);
    setErrors(validationErrors);

    const errorFields = Object.keys(validationErrors) as WizardField[];
    if (errorFields.length > 0) {
      setTouched(prevTouched => {
        const updated = new Set(prevTouched);
        errorFields.forEach(field => updated.add(field));
        return updated;
      });

      const firstErrorStep = WIZARD_STEPS.findIndex(
        step => step.id !== 'review' && validationErrors[step.id as WizardField],
      );

      if (firstErrorStep >= 0) {
        goToStep(firstErrorStep);
      }
      return;
    }

    const payload = formatSubmitPayload(formState);
    onSubmit(payload);
  }, [formState, goToStep, onSubmit]);

  const handleEditStep = useCallback(
    (field: WizardField) => {
      const stepIndex = WIZARD_STEPS.findIndex(step => step.id === field);
      if (stepIndex >= 0) {
        goToStep(stepIndex);
      }
    },
    [goToStep],
  );

  const renderStepContent = useCallback(() => {
    if (!currentWizardStep) {
      return null;
    }

    switch (currentWizardStep.id) {
      case 'landing_page_url':
        return (
          <LandingPageStep
            value={formState.landing_page_url}
            onChange={value => handleFieldChange('landing_page_url', value)}
            error={touched.has('landing_page_url') ? errors.landing_page_url : undefined}
          />
        );
      case 'objetivo_final':
        return (
          <ObjectiveStep
            value={formState.objetivo_final}
            onChange={value => handleFieldChange('objetivo_final', value)}
            error={touched.has('objetivo_final') ? errors.objetivo_final : undefined}
          />
        );
      case 'nome_empresa':
        return (
          <CompanyInfoStep
            field="nome_empresa"
            value={formState.nome_empresa}
            error={errors.nome_empresa}
            touched={touched.has('nome_empresa')}
            onChange={value => handleFieldChange('nome_empresa', value)}
            onBlur={() => markFieldTouched('nome_empresa')}
          />
        );
      case 'o_que_a_empresa_faz':
        return (
          <CompanyInfoStep
            field="o_que_a_empresa_faz"
            value={formState.o_que_a_empresa_faz}
            error={errors.o_que_a_empresa_faz}
            touched={touched.has('o_que_a_empresa_faz')}
            onChange={value => handleFieldChange('o_que_a_empresa_faz', value)}
            onBlur={() => markFieldTouched('o_que_a_empresa_faz')}
          />
        );
      case 'formato_anuncio':
        return (
          <FormatStep
            value={formState.formato_anuncio}
            onChange={value => handleFieldChange('formato_anuncio', value)}
            error={touched.has('formato_anuncio') ? errors.formato_anuncio : undefined}
          />
        );
      case 'perfil_cliente':
        return (
          <ProfileStep
            value={formState.perfil_cliente}
            onChange={value => handleFieldChange('perfil_cliente', value)}
            error={touched.has('perfil_cliente') ? errors.perfil_cliente : undefined}
          />
        );
      case 'foco':
        return (
          <FocusStep
            value={formState.foco}
            onChange={value => handleFieldChange('foco', value)}
            error={touched.has('foco') ? errors.foco : undefined}
          />
        );
      case 'sexo_cliente_alvo':
        return (
          <GenderTargetStep
            value={formState.sexo_cliente_alvo}
            error={errors.sexo_cliente_alvo}
            touched={touched.has('sexo_cliente_alvo')}
            onChange={value => handleFieldChange('sexo_cliente_alvo', value)}
            onBlur={() => markFieldTouched('sexo_cliente_alvo')}
          />
        );
      case 'review':
        return <ReviewStep formState={formState} onEdit={handleEditStep} />;
      default:
        return null;
    }
  }, [currentWizardStep, errors, formState, handleEditStep, handleFieldChange, markFieldTouched, touched]);

  return (
    <div className="w-full h-screen flex flex-col bg-background overflow-hidden">
      {/* Layout responsivo: coluna única no mobile; sidebar + conteúdo no desktop */}
      <div className="w-full h-full flex lg:flex-row">
        {/* Sidebar / Header de progresso */}
        <aside className="hidden lg:block w-80 flex-shrink-0 border-r border-border/60 p-6">
          <ProgressHeader
            steps={WIZARD_STEPS}
            currentStep={currentStep}
            completedSteps={completedSteps}
            orientation="vertical"
            onStepClick={(idx) => {
              setCurrentStep(idx);
            }}
          />
        </aside>

        {/* Coluna da direita: conteúdo principal */}
        <div className="flex-1 flex flex-col min-h-0 min-w-0 p-6">
          {/* Toggle e header no mobile */}
          <MobileToggle
            open={isMobileSidebarOpen}
            onToggle={() => setIsMobileSidebarOpen((v) => !v)}
          />
          {isMobileSidebarOpen && (
            <div className="lg:hidden mb-4 rounded-xl border border-border/60 bg-card/70 p-4">
              <ProgressHeader
                steps={WIZARD_STEPS}
                currentStep={currentStep}
                completedSteps={completedSteps}
                orientation="vertical"
                onStepClick={(idx) => {
                  setCurrentStep(idx);
                  setIsMobileSidebarOpen(false);
                }}
              />
            </div>
          )}

          <div className="flex-1 min-h-0 min-w-0 overflow-y-auto flex items-center">
            <StepCard step={currentWizardStep}>{renderStepContent()}</StepCard>
          </div>

          <NavigationFooter
            currentStep={currentStep}
            totalSteps={WIZARD_STEPS.length}
            onNext={handleNext}
            onBack={handleBack}
            onSubmit={handleSubmit}
            onCancel={onCancel}
            canProceed={canProceed(currentStep, formState, errors)}
            isLoading={isLoading}
            isOptional={Boolean(currentWizardStep?.isOptional)}
          />
        </div>
      </div>
    </div>
  );
}
