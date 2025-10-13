import type { ComponentType } from 'react';

export type WizardStepId =
  | 'landing_page_url'
  | 'objetivo_final'
  | 'formato_anuncio'
  | 'perfil_cliente'
  | 'foco'
  | 'nome_empresa'
  | 'o_que_a_empresa_faz'
  | 'sexo_cliente_alvo'
  | 'reference_image_character'
  | 'reference_image_product'
  | 'review';

export type WizardStepKind = 'text' | 'upload';

export interface WizardFormState {
  landing_page_url: string;
  objetivo_final: string;
  formato_anuncio: string;
  perfil_cliente: string;
  foco: string;
  nome_empresa: string;
  o_que_a_empresa_faz: string;
  sexo_cliente_alvo: string;
  reference_image_character: string;
  reference_image_product: string;
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
  reference_image_character?: string;
  reference_image_product?: string;
}

export interface ValidationRule {
  field: keyof WizardFormState;
  validate: (value: string, state: WizardFormState) => string | null;
}

export interface WizardStep {
  id: WizardStepId;
  title: string;
  subtitle?: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  isOptional?: boolean;
  kind?: WizardStepKind;
  validationRules?: ValidationRule[];
}
