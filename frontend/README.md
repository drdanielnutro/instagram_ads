# Frontend

## Feature Flags

### Wizard UI (`VITE_ENABLE_WIZARD`)

A flag que controla a nova experiência de onboarding baseada em wizard na tela de boas-vindas.

- **Finalidade:** habilitar o formulário guiado que substitui o formulário clássico somente quando desejado.
- **Como ativar:** copie `frontend/.env.example` para `.env.local` (se ainda não existir) e defina `VITE_ENABLE_WIZARD=true`.
- **Como desativar:** mantenha `VITE_ENABLE_WIZARD=false` para preservar a experiência atual.
- **Reinicialização necessária:** após alterar o valor da flag, interrompa o servidor de desenvolvimento (`npm run dev`) e inicie-o novamente para que o Vite recarregue as variáveis de ambiente.

> ℹ️ A flag permanece `false` por padrão para evitar que a nova UI seja exibida inesperadamente em ambientes que ainda não foram atualizados.
