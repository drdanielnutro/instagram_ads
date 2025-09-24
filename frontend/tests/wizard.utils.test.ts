import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe('formatSubmitPayload', () => {
  it('includes new fields when provided', async () => {
    vi.stubEnv('VITE_ENABLE_NEW_FIELDS', 'true');
    const { formatSubmitPayload } = await import('@/utils/wizard.utils');
    const { WIZARD_INITIAL_STATE } = await import('@/constants/wizard.constants');

    const state = {
      ...WIZARD_INITIAL_STATE,
      landing_page_url: 'https://example.com',
      objetivo_final: 'agendamentos',
      formato_anuncio: 'Reels',
      perfil_cliente: 'profissionais autônomos que buscam praticidade',
      foco: 'Campanha relâmpago',
      nome_empresa: 'Empresa Teste',
      o_que_a_empresa_faz: 'Consultoria especializada em marketing digital',
      sexo_cliente_alvo: 'masculino',
    };

    const payload = formatSubmitPayload(state);

    expect(payload).toContain('nome_empresa: Empresa Teste');
    expect(payload).toContain(
      'o_que_a_empresa_faz: Consultoria especializada em marketing digital',
    );
    expect(payload).toContain('sexo_cliente_alvo: masculino');
  });

  it('applies neutro default when gender is empty', async () => {
    vi.stubEnv('VITE_ENABLE_NEW_FIELDS', 'true');
    const { formatSubmitPayload } = await import('@/utils/wizard.utils');
    const { WIZARD_INITIAL_STATE } = await import('@/constants/wizard.constants');

    const state = {
      ...WIZARD_INITIAL_STATE,
      landing_page_url: 'https://example.com',
      objetivo_final: 'leads',
      formato_anuncio: 'Stories',
      perfil_cliente: 'estudantes universitários que querem aprender marketing',
      nome_empresa: 'Empresa Teste',
      o_que_a_empresa_faz: 'Cursos online de marketing',
      sexo_cliente_alvo: '',
    };

    const payload = formatSubmitPayload(state);

    expect(payload).toContain('sexo_cliente_alvo: neutro');
  });
});
