# Checklist UI Polish

## 1. Tokens Globais
- Fonte global Inter, títulos Space Grotesk, variáveis de cor e sombras definidas.
- Fundo base `#0e1219`, cartões translúcidos, primário `#7f5bff` funcionando em `make dev`.

## 2. Componentes Utilitários
- `SectionCard`, `StatusBadge`, `StatPill` criados em `frontend/src/components/ui` (standalone, sem uso direto).

## 3. WelcomeScreen + Formulário
- `WelcomeScreen` com hero central, badge, card "Briefing" usando SectionCard.
- Formulário com grid, ícones em campos/textos auxiliares; Select de `objetivo_final`/`formato_anuncio` ajustados.
- Verificar inputs funcionais após recarregar `make dev`.

## 4. ChatMessagesView (pendente)
- Substituir painel por `bg-surface`, aplicar `StatusBadge` para estágios.
- Bubbles harmonizadas; rodapé com `StatPill` para tokens/tempo.

## 5. QA Responsivo / Acessibilidade (pendente)
- Testar 360/768/1024/1440 px.
- Foco visível, contraste ok, teclado navegável.

