import type {
  WizardFormState,
  WizardValidationErrors,
  WizardStep,
} from '@/types/wizard.types';

import { WIZARD_STEPS } from '@/constants/wizard.constants';

function getStepByIndex(index: number): WizardStep | undefined {
  return WIZARD_STEPS[index];
}

export function validateStepField(
  step: WizardStep,
  value: string,
  formState: WizardFormState,
): string | null {
  if (!step.validationRules || step.validationRules.length === 0) {
    return null;
  }

  for (const rule of step.validationRules) {
    const fieldValue =
      rule.field === step.id ? value : formState[rule.field] ?? '';
    const error = rule.validate(fieldValue, formState);
    if (error) {
      return error;
    }
  }

  return null;
}

export function getCompletedSteps(
  formState: WizardFormState,
  currentStep: number,
): number[] {
  const completed: number[] = [];

  WIZARD_STEPS.forEach((step, index) => {
    if (index >= currentStep) {
      return;
    }

    if (step.id === 'review') {
      completed.push(index);
      return;
    }

    const value = formState[step.id];
    const error = validateStepField(step, value, formState);
    if (!error) {
      completed.push(index);
    }
  });

  return completed;
}

export function canProceed(
  currentStep: number,
  formState: WizardFormState,
  errors: WizardValidationErrors,
): boolean {
  const step = getStepByIndex(currentStep);
  if (!step) {
    return false;
  }

  if (step.id === 'review') {
    return Object.values(errors).every(error => !error);
  }

  const fieldValue = formState[step.id];
  if (errors[step.id]) {
    return false;
  }

  if (!step.isOptional && !fieldValue.trim()) {
    return false;
  }

  const validationError = validateStepField(step, fieldValue, formState);
  return !validationError;
}

export function validateForm(
  formState: WizardFormState,
): WizardValidationErrors {
  const validationErrors: WizardValidationErrors = {};

  WIZARD_STEPS.forEach(step => {
    if (step.id === 'review') {
      return;
    }

    const value = formState[step.id];
    const error = validateStepField(step, value, formState);
    if (error) {
      validationErrors[step.id] = error;
    }
  });

  return validationErrors;
}

export function formatSubmitPayload(formState: WizardFormState): string {
  const lines = WIZARD_STEPS.flatMap(step => {
    if (step.id === 'review') {
      return [];
    }

    const fieldId = step.id as keyof WizardFormState;
    const value = formState[fieldId].trim();
    if (!value) {
      if (fieldId === 'sexo_cliente_alvo') {
        return [`${fieldId}: neutro`];
      }
      return [];
    }

    return [`${fieldId}: ${value}`];
  });

  return lines.join('\n');
}
