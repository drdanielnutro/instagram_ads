import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { InputForm } from '@/components/InputForm';
import type {
  ReferenceImageEntry,
  UseReferenceImagesReturn,
} from '@/state/useReferenceImages';

const createEntry = (overrides: Partial<ReferenceImageEntry> = {}): ReferenceImageEntry => ({
  id: null,
  status: 'idle',
  fileName: null,
  signedUrl: null,
  labels: [],
  userDescription: '',
  error: null,
  ...overrides,
});

describe('InputForm submission', () => {
  it('submits homepage form with populated fields', () => {
    const onSubmit = vi.fn();

    render(<InputForm onSubmit={onSubmit} isLoading={false} />);

    fireEvent.change(screen.getByPlaceholderText('https://sua-pagina.com'), {
      target: { value: 'https://example.com' },
    });
    fireEvent.change(
      screen.getByPlaceholderText(
        'Ex.: destacar acompanhamento médico, evitar promessas de emagrecimento rápido.',
      ),
      { target: { value: 'Destacar equipe médica' } },
    );

    fireEvent.click(screen.getByRole('button', { name: /iniciar geração/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toContain('landing_page_url: https://example.com');
    expect(onSubmit.mock.calls[0][0]).toContain('foco: Destacar equipe médica');
  });

  it('prevents submission while uploads are in progress', () => {
    const onSubmit = vi.fn();
    const referenceImages: UseReferenceImagesReturn = {
      character: createEntry(),
      product: createEntry(),
      isUploading: true,
      hasReferences: true,
      uploadReferenceImage: vi.fn(),
      setUserDescription: vi.fn(),
      clearReferenceImage: vi.fn(),
      setError: vi.fn(),
      resetAll: vi.fn(),
      getRequestPayload: vi.fn(() => null),
    };

    render(
      <InputForm onSubmit={onSubmit} isLoading={false} referenceImages={referenceImages} />,
    );

    fireEvent.change(screen.getByPlaceholderText('https://sua-pagina.com'), {
      target: { value: 'https://example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /iniciar geração/i }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/aguarde até que os uploads sejam concluídos/i)).toBeInTheDocument();
  });

  it('envia uploads com informações de usuário e sessão', async () => {
    const uploadReferenceImage = vi.fn().mockResolvedValue(true);
    const setError = vi.fn();

    const referenceImages: UseReferenceImagesReturn = {
      character: createEntry(),
      product: createEntry(),
      isUploading: false,
      hasReferences: false,
      uploadReferenceImage,
      setUserDescription: vi.fn(),
      clearReferenceImage: vi.fn(),
      setError,
      resetAll: vi.fn(),
      getRequestPayload: vi.fn(() => null),
    };

    const { container } = render(
      <InputForm
        onSubmit={() => undefined}
        isLoading={false}
        referenceImages={referenceImages}
        userId="user-123"
        sessionId="sess-789"
      />,
    );

    const inputs = container.querySelectorAll('input[type="file"]');
    const file = new File([new Uint8Array(2048)], 'face.png', { type: 'image/png' });
    fireEvent.change(inputs[0] as HTMLInputElement, { target: { files: [file] } });

    await vi.waitFor(() =>
      expect(uploadReferenceImage).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'character',
          file,
          userId: 'user-123',
          sessionId: 'sess-789',
        }),
      ),
    );
    expect(setError).toHaveBeenCalledWith('character', null);
  });
});
