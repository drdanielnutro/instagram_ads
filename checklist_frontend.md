# Checklist – Refatoração de Campos de Entrada (Frontend + Backend preflight)

Objetivo: adicionar campos opcionais `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo` ao fluxo (frontend + extractor + preflight), mantendo retrocompatibilidade e sem conectar o fallback.

## 1) Backend – helpers/user_extract_data.py
- [ ] Atualizar prompt do `UserInputExtractor` para incluir novos campos.
- [ ] Adicionar few-shots com os novos campos e sinônimos de gênero (mulheres→feminino, homem→masculino, todos/misto→neutro).
- [ ] Incluir novos campos no `data` do `_convert`:
  - `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`.
- [ ] Incluir normalização em `normalized`:
  - `sexo_cliente_alvo_norm` (masculino|feminino|neutro) com mapa de sinônimos.
- [ ] Default: definir `sexo_cliente_alvo_norm = 'neutro'` quando ausente.
- [ ] Logging: garantir `logger = logging.getLogger(__name__)` no módulo e usar dentro do `_convert` (não depender do logger local de `extract`).
- [ ] Manter validações mínimas existentes (não tornar os novos campos obrigatórios).
- [ ] Export: `extract_user_input` inalterado (somente enriquecer o retorno).

## 2) Backend – app/server.py (/run_preflight)
- [ ] Incluir novos campos no `initial_state` (opcionais):
  - `nome_empresa`: `data.get('nome_empresa') or 'Empresa'`
  - `o_que_a_empresa_faz`: `data.get('o_que_a_empresa_faz') or ''`
  - `sexo_cliente_alvo`: `norm.get('sexo_cliente_alvo_norm') or 'neutro'`
- [ ] Adicionar log estruturado com métricas dos novos campos (presentes/defaults usados), sem tornar obrigatórios.
- [ ] Garantir que a resposta continua retrocompatível (chaves antigas preservadas).

## 3) Frontend – Tipos e estado
- [ ] Atualizar `frontend/src/types/wizard.types.ts` (interface `WizardFormState`) para incluir:
  - `nome_empresa: string`
  - `o_que_a_empresa_faz: string`
  - `sexo_cliente_alvo: string`
- [ ] Atualizar `WizardValidationErrors` para incluir as novas chaves.
- [ ] Atualizar `WIZARD_INITIAL_STATE` em `frontend/src/constants/wizard.constants.ts` com defaults vazios (sexo default aplicado no payload).

## 4) Frontend – Constants e Steps
- [ ] Adicionar `SEXO_CLIENTE_OPTIONS` com valores controlados: masculino|feminino|neutro.
- [ ] Incluir novos steps em `WIZARD_STEPS` (ajustar numeração):
  - Step "nome_empresa" com validação (2–100 chars).
  - Step "o_que_a_empresa_faz" com validação (10–200 chars).
  - Step "sexo_cliente_alvo" (opcional) com validação de domínio.
- [ ] Ícones: verificar disponibilidade no `lucide-react`.
  - Preferir `Building2` (caso `Building` não exista) e `Briefcase`.
  - Importar somente ícones realmente usados.

## 5) Frontend – Componentes de Step
- [ ] Criar `CompanyInfoStep.tsx` (reutilizar Input padrão já usado nos outros steps; evitar dependências novas como `cn` caso não exista util).
- [ ] Criar `GenderTargetStep.tsx` (reutilizar o padrão dos selects/botões já usados; se usar RadioGroup de shadcn, confirmar que os componentes existem no projeto).
- [ ] Atualizar `WizardForm.tsx` (switch `renderStepContent`) adicionando cases para os novos steps.
- [ ] Atualizar `ReviewStep.tsx` para exibir os novos campos no resumo final.

## 6) Frontend – Payload e validações
- [ ] Atualizar `formatSubmitPayload` em `frontend/src/utils/wizard.utils.ts` para:
  - Incluir os novos steps automaticamente (a função já itera `WIZARD_STEPS`).
  - Forçar default `sexo_cliente_alvo: neutro` quando vazio.
- [ ] Garantir que as validações existentes (URL, objetivo, formato, perfil) permanecem iguais; novos campos não bloqueiam submissão se vazios (exceto as regras nos seus próprios steps).

## 7) Testes
- [ ] Backend: criar `tests/test_user_extract_data.py` cobrindo extração de novos campos e normalização de gênero.
- [ ] Backend: criar `tests/test_preflight.py` validando presença dos novos campos no `initial_state` (com e sem defaults).
- [ ] Frontend: criar `tests/wizard.utils.test.ts` para verificar `formatSubmitPayload` (inclui campos; default de `sexo_cliente_alvo`).
- [ ] Frontend: testes de renderização/validação dos novos steps (mínimo smoke test).

## 8) Rollout e flags
- [ ] Rollout em duas fases: (1) backend primeiro; (2) frontend depois.
- [ ] Opcional: adicionar flag `VITE_ENABLE_NEW_FIELDS` para esconder os novos steps até finalizar o rollout.

## 9) Documentação
- [ ] Atualizar README com os novos campos e exemplo de payload.
- [ ] Referenciar no plano de fallback que os campos agora existem no `state` (sem conectar fallback).

---

Notas de implementação:
- Evitar introduzir novas dependências de UI; reutilizar o padrão já presente nos steps existentes.
- Se `lucide-react` não expor `Building`, usar `Building2`.
- Garantir que o logger usado no extractor é obtido via `logging.getLogger(__name__)` no escopo do módulo.


