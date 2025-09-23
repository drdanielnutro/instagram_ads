import {
  Briefcase,
  Building2,
  CheckCircle,
  Layout,
  LinkIcon,
  Sparkles,
  Target,
  Users,
  Venus,
} from 'lucide-react';

import type { WizardFormState, WizardStep } from '@/types/wizard.types';

export const WIZARD_INITIAL_STATE: WizardFormState = {
  landing_page_url: '',
  objetivo_final: '',
  formato_anuncio: '',
  perfil_cliente: '',
  foco: '',
  nome_empresa: '',
  o_que_a_empresa_faz: '',
  sexo_cliente_alvo: '',
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
const sexoClienteValues = new Set<string>(['masculino', 'feminino', 'neutro']);

export const SEXO_CLIENTE_OPTIONS = [
  {
    value: 'masculino',
    label: 'Masculino',
    description: 'Comunicação direcionada para homens',
  },
  {
    value: 'feminino',
    label: 'Feminino',
    description: 'Tom e referências voltados para mulheres',
  },
  {
    value: 'neutro',
    label: 'Neutro',
    description: 'Mensagem inclusiva para todos os públicos',
  },
] as const;

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
    id: 'nome_empresa',
    title: 'Qual é o nome da empresa?',
    subtitle: 'Passo 2',
    description: 'Informe como a marca deve ser citada nos criativos e mensagens.',
    icon: Building2,
    validationRules: [
      {
        field: 'nome_empresa',
        validate: value => {
          const trimmed = value.trim();
          if (!trimmed) {
            return 'Informe o nome da empresa ou marca.';
          }
          if (trimmed.length < 2) {
            return 'Use ao menos 2 caracteres para o nome da empresa.';
          }
          if (trimmed.length > 100) {
            return 'O nome da empresa deve ter no máximo 100 caracteres.';
          }
          return null;
        },
      },
    ],
  },
  {
    id: 'o_que_a_empresa_faz',
    title: 'O que a empresa oferece?',
    subtitle: 'Passo 3',
    description: 'Descreva a proposta de valor ou principais serviços de forma objetiva.',
    icon: Briefcase,
    validationRules: [
      {
        field: 'o_que_a_empresa_faz',
        validate: value => {
          const trimmed = value.trim();
          if (!trimmed) {
            return 'Explique brevemente o que a empresa faz.';
          }
          if (trimmed.length < 10) {
            return 'Use pelo menos 10 caracteres para descrever a empresa.';
          }
          if (trimmed.length > 200) {
            return 'Resuma a descrição em até 200 caracteres.';
          }
          return null;
        },
      },
    ],
  },
  {
    id: 'objetivo_final',
    title: 'Qual é o objetivo principal?',
    subtitle: 'Passo 4',
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
    subtitle: 'Passo 5',
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
    subtitle: 'Passo 6',
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
    id: 'sexo_cliente_alvo',
    title: 'Existe um gênero predominante?',
    subtitle: 'Passo 7',
    description: 'Selecione caso haja comunicação direcionada a um gênero específico (opcional).',
    icon: Venus,
    isOptional: true,
    validationRules: [
      {
        field: 'sexo_cliente_alvo',
        validate: value => {
          const trimmed = value.trim();
          if (!trimmed) {
            return null;
          }
          if (!sexoClienteValues.has(trimmed)) {
            return 'Escolha entre masculino, feminino ou neutro.';
          }
          return null;
        },
      },
    ],
  },
  {
    id: 'foco',
    title: 'Algum foco específico?',
    subtitle: 'Passo 8',
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
    subtitle: 'Passo 9',
    description: 'Confira os dados informados e edite qualquer etapa antes de gerar os anúncios.',
    icon: CheckCircle,
  },
];
