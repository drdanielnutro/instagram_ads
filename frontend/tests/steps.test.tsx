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
        <CompanyInfoStep variant="name" value="Empresa" onChange={noop} error={undefined} />,
      ),
    ).not.toThrow();
  });

  it('renders company description step', () => {
    expect(() =>
      renderToString(
        <CompanyInfoStep
          variant="description"
          value="Consultoria especializada"
          onChange={noop}
          error={undefined}
        />,
      ),
    ).not.toThrow();
  });

  it('renders gender target step', () => {
    expect(() =>
      renderToString(
        <GenderTargetStep value="masculino" onChange={noop} error={undefined} />,
      ),
    ).not.toThrow();
  });
});
