# Plano Expandido de Correção – Preview de Anúncios

> Objetivo: sanar todas as inconsistências identificadas nos relatórios (`inconsistencias_codex_cli_2.md`, `inconsistencias_codex_cloud_2.md`, `inconsistencias_gemini_2.md`), mantendo o escopo restrito ao componente de preview e integrações relacionadas. Itens ligados exclusivamente a testes automatizados ou validações externas ficam fora deste ciclo.

## 1. Governança do Botão "Preview" (`frontend/src/App.tsx`)
- **Condição de exibição**: alterar o bloco que renderiza o botão para só construí-lo quando `previewEnabled` **e** `deliveryMeta?.ok` forem verdadeiros. Eliminar a renderização do botão em estado desabilitado quando os dados ainda não estão prontos.
- **Defesa dupla**: manter a lógica `disabled={!canOpenPreview}` para evitar regressões durante o carregamento.
- **Verificação**: confirmar que, ao revogar `deliveryMeta?.ok`, o botão desaparece e o modal é fechado automaticamente (comportamento já existente deve permanecer).

## 2. Ajustes de Layout dos Dispositivos (`frontend/src/components/AdsPreview.tsx`)
### 2.1 Feed (renderFeedDevice)
- **Estrutura**: reorganizar para seguir o plano original (carrossel + card de copy/CTA). A sequência deve ser:
  1. "Dispositivo (Feed)" – etiqueta de seção.
  2. Moldura do carrossel com `ImageCarousel` utilizando `aspectRatioClass`.
  3. `Card` contendo:
     - `CardContent` com `headline` (texto principal), `copy.corpo` (texto corrido) e botão CTA (`variation.copy.cta_texto`), replicando a simulação de feed descrita no plano.
  4. Mensagem auxiliar “fallback textual” dentro do mesmo card ou em bloco imediatamente subsequente, conforme wireframe.
- **Remoção de duplicidade**: retirar o card de descrição visual hoje presente no feed; a descrição passa para a área de textos (seção 4).

### 2.2 Vertical (renderVerticalDevice)
- **Safe zones**: substituir as caixas com borda atuais por overlays semitransparentes (`bg-background/35`, `bg-background/40`) aplicados via elementos posicionados, com altura proporcional à especificação do plano.
- **Card auxiliar**: recolocar o card informativo "💡 Em formatos verticais..." abaixo do dispositivo, conforme descrito.
- **Descrição visual**: remover o card duplicado da seção vertical (a descrição será tratada na área de textos).

## 3. Área de Textos e Metadados (`frontend/src/components/AdsPreview.tsx`)
- **Card de Copy**: manter o card atual, ajustando apenas para receber a descrição visual quando necessário (ver seção 4).
- **Card de Metadados**: reestruturar para conter, neste exato formato, os campos:
  - `Formato` (valor direto);
  - `CTA Instagram` (`variation.cta_instagram`);
  - `Fluxo`;
  - `Landing` com link clicável (`<a href target="_blank" rel="noreferrer">`).
  - Qualquer conteúdo adicional (ex. referências) deve sair deste card.
- **Referências e StoryBrand**: substituir os cards estáticos por dois blocos colapsáveis usando `<details>`/`<summary>` com estilização condizente. Conteúdo interno conserva o texto atual (`referencia_padroes`, `contexto_landing`).

## 4. Organização de Prompts e Descrição Visual
- **Descrição visual**: movê-la para o card "Prompts visuais" (ou card dedicado) conforme o plano, garantindo que o usuário encontre prompts e descrição no mesmo agrupamento textual.
- **Fallback textual**: assegurar que, ao faltar prompts, o card informe claramente que os dados não estão disponíveis, mantendo o texto de fallback existente.

## 5. Reimplementação do Carrossel (`frontend/src/components/AdsPreview.tsx`)
- **Controles laterais**: adicionar botões posicionados à esquerda e à direita do carrossel, com comportamento de desativação nas extremidades.
- **Indicadores (dots)**: inserir a fileira de dots centralizada na base da imagem (apenas quando houver imagens).
- **Badge de estágio**: aplicar a etiqueta fixa no canto superior esquerdo da imagem utilizando o array `['Estado Atual', 'Intermediário', 'Aspiracional']`. Essa etiqueta deve aparecer sempre, independentemente da existência de imagens.
- **Acessibilidade**: garantir atributos `aria-label` nos botões e foco navegável por teclado.
- **Navegação por prompts**: manter a melhoria atual (botões por etapa) como reforço opcional, desde que não conflite visualmente.

## 6. Tipagem Estrita e Normalização
- **Tipos (`frontend/src/types/ad-preview.ts`)**:
  - Tornar obrigatórios os campos previstos em `PLAN_PREVIEW_COMPONENT.md` (evitando `?`), exceto se houver justificativa documentada.
  - Restringir `aspect_ratio` ao union literal (`"4:5" | "9:16" | "1:1"`).
- **Normalização (`normalizeVariations` e consumidores)**:
  - Adaptar o parse para validar objetos antes de usá-los. Se houver payload incompleto, aplicar defaults seguros ou descartar a entrada com log no console.
  - Garantir que ajustes no tipo não causem crashes caso o backend envie dados extras (usar asserts/guards ao setar estado).

## 7. `PromptBlock` Reutilizável
- **Extração/Export**:
  - Opção A: exportar `PromptBlock` diretamente do arquivo atual (`export { PromptBlock }`), movendo-o para o final do arquivo para evitar declarações antes da exportação por default.
  - Opção B: criar arquivo dedicado (`frontend/src/components/PromptBlock.tsx`) e importar no preview. Escolher a alternativa que minimize riscos de regressão.
- **Estilo**: manter classes (`border`, `bg-background/40`, `text-xs uppercase`) para consistência.

## 8. Comentário sobre `visual.images`
- **Documentação inline**: adicionar comentário claro em `getVariationImages` ou imediatamente acima da função informando como `visual.images` será preenchido futuramente, conforme instrução do plano (sem alterar lógica atual).

## 9. Documentação da Validação Final
- **Registro**: incluir nota/conclusão (ex.: seção curta no `frontend/README.md` ou novo arquivo em `docs/`) informando que o MVP foi validado e alinhado às guidelines e ao JSON final, conforme itens 15.1 e 15.2.
- **Escopo**: limitar-se a documentação; não criar novas etapas de teste automatizado neste plano.

## 10. Conferência Pós-Correção
- **Checklist interna**: após as alterações acima, revisar `inconsistencias_codex_cli_2.md`, `inconsistencias_codex_cloud_2.md` e `inconsistencias_gemini_2.md` para assegurar que cada ponto foi sanado.
- **Verificação visual**: executar `npm --prefix frontend run dev` com a flag ativa e desativada para confirmar que:
  - o botão "Preview" aparece/desaparece corretamente;
  - os layouts (feed/vertical) correspondem ao plano;
  - o carrossel exibe controles novos e mantém comportamentos de fallback;
  - os blocos colapsáveis funcionam sem warnings.

> Resultado esperado: após aplicar este plano, as inconsistências listadas devem se reduzir aos itens explicitamente fora do escopo (ex.: testes automatizados omitidos). Nenhuma nova divergência deve ser introduzida.
