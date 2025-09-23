import { describe, expect, it } from 'vitest';

import { formatSubmitPayload } from '@/utils/wizard.utils';
import { WIZARD_INITIAL_STATE } from '@/constants/wizard.constants';

describe('formatSubmitPayload', () => {
  it('includes new fields when provided', () => {
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

  it('applies neutro default when gender is empty', () => {
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
