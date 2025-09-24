import type { ComponentType } from 'react';

export interface WizardFormState {
  landing_page_url: string;
  objetivo_final: string;
  formato_anuncio: string;
  perfil_cliente: string;
  foco: string;
  nome_empresa: string;
  o_que_a_empresa_faz: string;
  sexo_cliente_alvo: string;
}

export interface WizardValidationErrors {
  landing_page_url?: string;
  objetivo_final?: string;
  formato_anuncio?: string;
  perfil_cliente?: string;
  foco?: string;
  nome_empresa?: string;
  o_que_a_empresa_faz?: string;
  sexo_cliente_alvo?: string;
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
