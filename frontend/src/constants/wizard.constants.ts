import {
  CheckCircle,
  Layout,
  LinkIcon,
  Sparkles,
  Target,
  Users,
} from 'lucide-react';

import type { WizardFormState, WizardStep } from '@/types/wizard.types';

export const WIZARD_INITIAL_STATE: WizardFormState = {
  landing_page_url: '',
  objetivo_final: '',
  formato_anuncio: '',
  perfil_cliente: '',
  foco: '',
};

export const OBJETIVO_OPTIONS = [
  { value: 'agendamentos', label: 'Agendamentos', description: 'Marcar consultas ou reuniões' },
  { value: 'leads', label: 'Geração de Leads', description: 'Capturar contatos qualificados' },
  { value: 'vendas', label: 'Vendas Diretas', description: 'Converter em vendas imediatas' },
  { value: 'contato', label: 'Contato', description: 'Receber mensagens e interações' },
] as const;

export const FORMATO_OPTIONS = [
  { value: 'Feed', label: 'Feed', ratio: '1:1 ou 4:5', description: 'Posts no feed principal' },
  { value: 'Stories', label: 'Stories', ratio: '9:16', description: 'Conteúdo vertical temporário' },
  { value: 'Reels', label: 'Reels', ratio: '9:16', description: 'Vídeos curtos e envolventes' },
] as const;

const objetivoValues = new Set<string>(OBJETIVO_OPTIONS.map(option => option.value));
const formatoValues = new Set<string>(FORMATO_OPTIONS.map(option => option.value));

export const WIZARD_STEPS: WizardStep[] = [
  {
    id: 'landing_page_url',
    title: 'Qual é a página de destino?',
    subtitle: 'Passo 1',
    description: 'Informe a URL principal onde as pessoas devem chegar após clicarem no anúncio.',
    icon: LinkIcon,
    validationRules: [
      {
        field: 'landing_page_url',
        validate: value => {
          const trimmedValue = value.trim();
          if (!trimmedValue) {
            return 'Informe a URL da página de destino.';
          }

          try {
            const parsedUrl = new URL(trimmedValue);
            if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
              return 'Utilize URLs iniciadas com http:// ou https://';
            }
          } catch (error) {
            return 'Digite uma URL válida, incluindo http(s)://';
          }

          return null;
        },
      },
    ],
  },
  {
    id: 'objetivo_final',
    title: 'Qual é o objetivo principal?',
    subtitle: 'Passo 2',
    description: 'Escolha o resultado desejado para medir o sucesso da campanha.',
    icon: Target,
    validationRules: [
      {
        field: 'objetivo_final',
        validate: value => {
          if (!value.trim()) {
            return 'Selecione um objetivo para a campanha.';
          }

          if (!objetivoValues.has(value)) {
            return 'Escolha um objetivo disponível na lista.';
          }

          return null;
        },
      },
    ],
  },
  {
    id: 'formato_anuncio',
    title: 'Qual formato será utilizado?',
    subtitle: 'Passo 3',
    description: 'Selecione o formato que melhor se adapta ao criativo e ao canal escolhido.',
    icon: Layout,
    validationRules: [
      {
        field: 'formato_anuncio',
        validate: value => {
          if (!value.trim()) {
            return 'Selecione um formato de anúncio.';
          }

          if (!formatoValues.has(value)) {
            return 'Escolha um formato válido.';
          }

          return null;
        },
      },
    ],
  },
  {
    id: 'perfil_cliente',
    title: 'Descreva o público ideal',
    subtitle: 'Passo 4',
    description: 'Resuma quem é o cliente ideal, dores, desejos e comportamentos.',
    icon: Users,
    validationRules: [
      {
        field: 'perfil_cliente',
        validate: value => {
          const trimmed = value.trim();
          if (!trimmed) {
            return 'Descreva brevemente o público do anúncio.';
          }

          if (trimmed.length < 20) {
            return 'Use pelo menos 20 caracteres para detalhar o público.';
          }

          if (trimmed.length > 500) {
            return 'Resuma o perfil em no máximo 500 caracteres.';
          }

          return null;
        },
      },
    ],
  },
  {
    id: 'foco',
    title: 'Algum foco específico?',
    subtitle: 'Passo 5',
    description: 'Compartilhe diferenciais, promoções ou mensagens obrigatórias (opcional).',
    icon: Sparkles,
    isOptional: true,
    validationRules: [
      {
        field: 'foco',
        validate: () => null,
      },
    ],
  },
  {
    id: 'review',
    title: 'Revise antes de gerar',
    subtitle: 'Passo 6',
    description: 'Confira os dados informados e edite qualquer etapa antes de gerar os anúncios.',
    icon: CheckCircle,
  },
];
