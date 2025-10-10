import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ReferenceUpload } from '@/components/ReferenceUpload';
import type { ReferenceImageEntry } from '@/state/useReferenceImages';

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

describe('ReferenceUpload component', () => {
  it('blocks files above 5 MB and notifies the user', () => {
    const onUpload = vi.fn();
    const onValidationError = vi.fn();

    const { container } = render(
      <ReferenceUpload
        type="character"
        entry={createEntry()}
        onUpload={onUpload}
        onDescriptionChange={() => undefined}
        onRemove={() => undefined}
        onValidationError={onValidationError}
      />,
    );

    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const largeFile = new File([new Uint8Array(5 * 1024 * 1024 + 1)], 'large.png', { type: 'image/png' });

    fireEvent.change(input, { target: { files: [largeFile] } });

    expect(onValidationError).toHaveBeenCalledWith('Arquivo muito grande. Limite de 5 MB.');
    expect(onUpload).not.toHaveBeenCalled();
    expect(input.value).toBe('');
  });

  it('accepts valid files and shows success feedback after upload', async () => {
    const onUpload = vi.fn().mockResolvedValue(true);
    const onValidationError = vi.fn();

    const { container, rerender } = render(
      <ReferenceUpload
        type="character"
        entry={createEntry()}
        onUpload={onUpload}
        onDescriptionChange={() => undefined}
        onRemove={() => undefined}
        onValidationError={onValidationError}
      />,
    );

    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File([new Uint8Array(1024)], 'face.png', { type: 'image/png' });

    fireEvent.change(input, { target: { files: [file] } });

    await vi.waitFor(() => expect(onUpload).toHaveBeenCalledTimes(1));
    expect(onValidationError).toHaveBeenCalledWith(null);

    rerender(
      <ReferenceUpload
        type="character"
        entry={createEntry({ id: 'ref-1', status: 'uploaded' })}
        onUpload={onUpload}
        onDescriptionChange={() => undefined}
        onRemove={() => undefined}
        onValidationError={onValidationError}
      />,
    );

    expect(screen.getByText('Upload concluído')).toBeInTheDocument();
  });

  it('allows removing an uploaded reference and surfaces SafeSearch errors', () => {
    const onRemove = vi.fn();

    render(
      <ReferenceUpload
        type="product"
        entry={createEntry({
          id: 'prod-77',
          status: 'error',
          error: 'Imagem reprovada pelo SafeSearch.',
          fileName: 'produto.png',
        })}
        onUpload={async () => true}
        onDescriptionChange={() => undefined}
        onRemove={onRemove}
        onValidationError={() => undefined}
      />,
    );

    expect(screen.getByText('Imagem reprovada pelo SafeSearch.')).toBeInTheDocument();

    const removeButton = screen.getByRole('button', { name: /remover/i });
    fireEvent.click(removeButton);

    expect(onRemove).toHaveBeenCalledTimes(1);
  });
});
