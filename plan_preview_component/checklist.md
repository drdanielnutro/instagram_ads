# Checklist – Componente de Preview de Anúncios

## 1. Ativação do Preview
- [x] Adicionar `VITE_ENABLE_ADS_PREVIEW=false` em `frontend/.env.example`
- [x] Documentar a flag em `frontend/README.md`
- [x] Implementar helper `isPreviewEnabled` em `frontend/src/utils/featureFlags.ts`
- [x] Exibir botão `Preview` em `App.tsx` quando `deliveryMeta?.ok` estiver verdadeiro
- [x] Implementar handler `openPreview` que inicia o fluxo do modal
- [x] Realizar GET em `/api/delivery/final/download?user_id=<...>&session_id=<...>`
- [x] Tratar respostas inline (JSON direto) e assinadas (`{ signed_url }`), normalizando para um único objeto
- [x] Invocar parsing do JSON final e acionar abertura do modal

## 2. Estrutura Simplificada (MVP)
- [x] Criar arquivo `frontend/src/components/AdsPreview.tsx` concentrando o MVP
- [x] Postergar extração de subcomponentes até a necessidade de refatoração

## 3. Componente Principal
- [x] Declarar `AdsPreviewProps` com `userId`, `sessionId`, `isOpen`, `onClose`
- [x] Definir estados internos (`variations`, `currentVariation`, `currentImageIndex`, `isFetchingPreview`, `imageErrors`)
- [x] Garantir importação de `Button`, `Badge`, `Card`, `CardContent`, `CardHeader`, `CardTitle`, `ScrollArea`, `Tabs`, `TabsList`, `TabsTrigger`

## 4. Layout do Modal
- [x] Configurar `Dialog.Root`/`Dialog.Content` com tokens (`bg-card`, `border-border`, `shadow` etc.)
- [x] Criar cabeçalho com título e botão de fechar (`variant="ghost"`)
- [x] Renderizar lista dinâmica de variações via `Tabs` quando houver mais de uma
- [x] Dispor conteúdo principal em layout responsivo (`ScrollArea` para dispositivo e textos)
- [x] Incluir rodapé com botão “Recarregar dados” (`variant="outline"`)

## 5. Renderização por Formato
- [x] Implementar `renderFeedDevice` usando moldura 4:5/1:1 com `ImageCarousel`
- [x] Implementar `renderVerticalDevice` com moldura arredondada e faixas de “safe zone”
- [x] Adicionar cards auxiliares para CTA/explicações conforme formato
- [x] Registrar observação sobre fallback textual enquanto não houver URLs de imagem

## 6. Componente Carrossel
- [x] Criar `ImageCarousel` recebendo lista opcional de imagens e aspecto
- [x] Exibir placeholder temático quando não houver URLs disponíveis
- [x] Ajustar botões/dots com tokens do tema
- [x] Destacar etapa atual (Estado Atual / Intermediário / Aspiracional)

## 7. Área de Textos
- [x] Estruturar cards para copy (headline, corpo, CTA com `Badge`)
- [x] Exibir metadados (formato, CTA IG, fluxo, link da landing)
- [x] Apresentar descrição visual e prompts usando `PromptBlock`
- [x] Criar blocos colapsáveis (detalhes) para referências e StoryBrand

## 8. Fetch e Atualização de Dados
- [x] Resetar estados ao abrir modal (`variations`, índices, erros)
- [x] Tentar endpoint principal, depois URL assinada se existir
- [x] Parsear resposta (string/JSON) e garantir que `variations` seja sempre array
- [x] Encerrar com controle de loading e tratamento de erros (toast/log)

## 9. Tratamento de Erros de Imagem
- [x] Mapear falhas por combinação variação+imagem
- [x] Exibir placeholder com mensagem/ação “Tentar novamente”
- [x] Reutilizar `fetchPreviewData()` para recarregar imagens

## 10. Responsividade
- [x] Suportar modal fullscreen em mobile com layout vertical
- [x] Centralizar conteúdo e limitar altura (`md:h-[90vh]`) em desktop
- [x] Garantir navegação confortável em diferentes breakpoints

## 11. Integração em `App.tsx`
- [x] Adicionar estado `showPreview`
- [x] Adicionar botão “Preview” ao lado de “Baixar JSON” na toolbar somente quando `isPreviewEnabled()`
- [x] Reutilizar `handleDownloadFinal` existente para downloads
- [x] Renderizar `AdsPreview` conectado aos estados/props corretos

## 12. Tipos TypeScript
- [x] Criar `frontend/src/types/ad-preview.ts` com `VisualInfo` e `AdVariation`
- [x] Atualizar consumidores para usar os novos tipos

## 13. Helpers
- [x] Implementar `getAspectRatioClass`, `isVerticalFormat`, `getVariationImages`
- [x] Exportar `isPreviewEnabled` via `featureFlags.ts`
- [x] Documentar comportamento futuro para URLs de imagem
- [x] Disponibilizar `PromptBlock` para reutilização nos cards de texto

## 14. Estilos e Temas
- [x] Garantir uso de tokens do tema escuro (`bg-card`, `border-border`, etc.)
- [x] Aplicar sombras e bordas arredondadas alinhadas ao wizard
- [x] Utilizar variações com opacidade para profundidade

## 15. Considerações Finais
- [x] Validar aderência ao MVP e extensibilidade pós-MVP
- [x] Revisar consistência com guidelines do projeto e dados do JSON final
