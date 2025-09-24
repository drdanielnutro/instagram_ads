# Frontend

## Feature Flags

### Wizard UI (`VITE_ENABLE_WIZARD`)

A flag que controla a nova experiência de onboarding baseada em wizard na tela de boas-vindas.

- **Finalidade:** habilitar o formulário guiado que substitui o formulário clássico somente quando desejado.
- **Como ativar:** copie `frontend/.env.example` para `.env.local` (se ainda não existir) e defina `VITE_ENABLE_WIZARD=true`.
- **Como desativar:** mantenha `VITE_ENABLE_WIZARD=false` para preservar a experiência atual.
- **Reinicialização necessária:** após alterar o valor da flag, interrompa o servidor de desenvolvimento (`npm run dev`) e inicie-o novamente para que o Vite recarregue as variáveis de ambiente.

> ℹ️ A flag permanece `false` por padrão para evitar que a nova UI seja exibida inesperadamente em ambientes que ainda não foram atualizados.

### Novos Campos do Wizard (`VITE_ENABLE_NEW_FIELDS`)

- **Finalidade:** exibir/ocultar novos passos/campos (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`).
- **Como ativar:** defina `VITE_ENABLE_NEW_FIELDS=true` em `frontend/.env.local`.
- **Como desativar:** `VITE_ENABLE_NEW_FIELDS=false` (padrão sugerido no rollout).
- **Observação:** é independente da flag do backend. Se o backend não estiver com `ENABLE_NEW_INPUT_FIELDS=true`, os campos podem aparecer na UI, mas não serão incluídos no initial_state (a menos que você mantenha apenas no payload para preflight). Reinicie `npm run dev` após alterações.

## Sistema de Flags – Guia de Fases

### Backend (.env)
- ENABLE_NEW_INPUT_FIELDS=false (off por padrão)
- PREFLIGHT_SHADOW_MODE=true (on por padrão) — extrai/loga novos campos sem incluí-los no initial_state.

### Frontend (frontend/.env.local)
- VITE_ENABLE_WIZARD=true (habilita wizard)
- VITE_ENABLE_NEW_FIELDS=false (oculta novos steps inicialmente)

### Rollout sugerido
1. Backend: `ENABLE_NEW_INPUT_FIELDS=false`, `PREFLIGHT_SHADOW_MODE=true` (sem impacto de contrato).
2. Frontend: `VITE_ENABLE_NEW_FIELDS=true` para subset de usuários; coletar feedback e erros.
3. Backend: `ENABLE_NEW_INPUT_FIELDS=true` para incluir novos campos no initial_state.
4. Opcional: Desligar `PREFLIGHT_SHADOW_MODE` após estabilização.

### Preview de Anúncios (`VITE_ENABLE_ADS_PREVIEW`)

Controla o modal de preview das variações finais geradas pelo pipeline.

- **Finalidade:** permitir a avaliação visual e textual do JSON final diretamente na interface, sem necessidade de download.
- **Como ativar:** copie `frontend/.env.example` para `.env.local` (se ainda não existir) e defina `VITE_ENABLE_ADS_PREVIEW=true`.
- **Como desativar:** mantenha `VITE_ENABLE_ADS_PREVIEW=false` para ocultar o modal e manter apenas o download do JSON.
- **Reinicialização necessária:** após alterar a flag, reinicie `npm run dev` para que o Vite recarregue as variáveis de ambiente.

> ℹ️ A flag nasce desativada para facilitar rollback imediato caso o preview apresente inconsistências.

## Validação do Preview de Anúncios

- MVP revisado manualmente com os dados de saída atuais do endpoint `/api/delivery/final/download`, confirmando aderência ao plano de UX definido em `PLAN_PREVIEW_COMPONENT.md`.
- Layout, tokens de tema e responsividade alinhados às diretrizes existentes do projeto (mesmos padrões do wizard), garantindo comportamento consistente em mobile e desktop.
- O modal pode ser desligado rapidamente via `VITE_ENABLE_ADS_PREVIEW=false`, servindo como mecanismo de rollback enquanto o rollout gradual (staging → produção) é conduzido.
