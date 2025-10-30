## Ajustes de Overlay no Preview (Versão Refinada)

### 1. Revisar Dados de Entrada
- Referências: `frontend/src/components/AdsPreview.tsx`, `frontend/src/types/ad-preview.ts`, `json_completo_que_deu_certo.json`.
- Confirmar campos normalizados por `sanitizeVariation`:
  - `copy.headline`, `copy.cta_texto`, `cta_instagram`, `landing_page_url`.
  - `visual.images` (ou fallback `image_estado_atual_url`, `image_estado_intermediario_url`, `image_estado_aspiracional_url`).
  - `visual.prompt_estado_atual`, `visual.prompt_estado_intermediario`, `visual.prompt_estado_aspiracional`.
  - Verificar existência de `nome_empresa`; caso ausente, planejar fallback.

### 2. Helper de Identidade da Marca
- Adicionar utilitário `resolveBrandLabel(variation: AdVariation)` em `AdsPreview.tsx`:
  1. Retornar `variation.nome_empresa` se presente (adicionar campo opcional em `AdVariation` e `sanitizeVariation` para mapear `raw.nome_empresa`).
  2. Caso contrário, parsear `landing_page_url`:
     - Se domínio **não** for `instagram.com`, `facebook.com`, `linktr.ee` → usar `hostname` sem `www.`.
     - Para domínios sociais, extrair slug/username após a última `/`, limpar traços e sublinhados, capitalizar inicial.
  3. Se parsing falhar ou retornar string vazia → ocultar selo.
- Memoizar resultado por variação (`useMemo`) para evitar recomputações.

### 3. Headline no Estado Atual
- Ajustar overlay do índice 0 em `ImageCarousel`:
  - Container `absolute inset-x-0 top-0 z-[5] bg-gradient-to-b from-black/75 via-black/40 to-transparent`.
  - Padding `pt-12 pl-6 pr-8 pb-10`, largura máxima `max-w-[70%]`.
  - Tipografia: `text-xl sm:text-2xl font-bold leading-tight tracking-tight text-white`, `drop-shadow`.
  - Permitir múltiplas linhas (ex.: `line-clamp-3` com `sm:line-clamp-none`).
  - Ajustar badge de etapa para não ser sobreposto (manter `z-10`).

### 4. Selo da Empresa na Etapa Intermediária
- Renderizar apenas quando `resolveBrandLabel` retornar conteúdo.
- Estilo: `absolute left-5 top-16 z-10 rounded-full border border-border/50 bg-background/85 px-4 py-1.5 text-sm font-semibold text-foreground/90 shadow-md backdrop-blur`.
- Garantir que badge principal (“Intermediário”) permaneça visível.

### 5. CTA no Aspiracional
- Contêiner `absolute bottom-5 right-5 sm:bottom-6 sm:right-6` com `max-w-[220px]` e `px-4`.
- Em telas estreitas (`max-sm`), centralizar (`left-1/2 translate-x-[-50%] right-auto`), mantendo margem inferior.
- Botão `<Button size="sm" className="w-full justify-center shadow-xl">`, texto `copy.cta_texto || cta_instagram`.
- Adicionar `aria-label` e `title` com o texto resolvido.

### 6. Tipos e Sanitização
- Atualizar `frontend/src/types/ad-preview.ts` para incluir `nome_empresa?: string`.
- Em `sanitizeVariation`, mapear `raw.nome_empresa` (quando existir) usando `coerceString`.
- Garantir que helpers tratem strings vazias/undefined sem warnings (try/catch no parse de URL).

### 7. Compatibilidade e Estados Especiais
- Renderizar overlays somente quando `hasImages && imageSrc`.
- Manter fallback textual/erro/loader inalterados.
- Ajustar `z-index` dos botões de navegação se necessário (CTA deve ter `z-30`).
- Garantir que overlays não apareçam durante `isLoading` ou `hasError`.

### 8. Testes Manuais
- Variação com domínio próprio → headline/label/CTA renderizados conforme esperado.
- URL Instagram/Facebook/Linktree → selo exibe handle amigável.
- Cenário sem imagens (somente prompts) → overlay não aparece.
- Responsividade: testar ~360px, >=768px, >=1024px.
- Verificar acessibilidade: foco no CTA, `aria-label` presentes, overlays não obstruem navegação.
