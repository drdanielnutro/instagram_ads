import React from 'react';
import { describe, expect, it } from 'vitest';
import { renderToString } from 'react-dom/server';

import { CompanyInfoStep } from '@/components/WizardForm/steps/CompanyInfoStep';
import { GenderTargetStep } from '@/components/WizardForm/steps/GenderTargetStep';

const noop = () => undefined;

describe('Wizard steps', () => {
  it('renders company name step', () => {
    expect(() =>
      renderToString(
        <CompanyInfoStep
          field="nome_empresa"
          value="Empresa"
          error={undefined}
          touched={false}
          onChange={noop}
          onBlur={noop}
        />,
      ),
    ).not.toThrow();
  });

  it('renders company description step', () => {
    expect(() =>
      renderToString(
        <CompanyInfoStep
          field="o_que_a_empresa_faz"
          value="Consultoria especializada"
          error={undefined}
          touched={false}
          onChange={noop}
          onBlur={noop}
        />,
      ),
    ).not.toThrow();
  });

  it('renders gender target step', () => {
    expect(() =>
      renderToString(
        <GenderTargetStep
          value="masculino"
          error={undefined}
          touched={false}
          onChange={noop}
          onBlur={noop}
        />,
      ),
    ).not.toThrow();
  });
});
