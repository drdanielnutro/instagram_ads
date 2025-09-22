# Checklist de Implementação – Correção do Preview de Anúncios

> Convenção de status: substitua manualmente o marcador de cada item conforme avança.
> - `[ ]` = pending (padrão)
> - `[>]` = in progress
> - `[x]` = done

## 1. Análise do Problema
- [ ] Confirmar que o JSON no GCS possui campos `image_estado_atual_url`, `image_estado_intermediario_url`, `image_estado_aspiracional_url`
- [ ] Verificar que o campo `images[]` não existe no JSON atual
- [ ] Confirmar que a função `getVariationImages` busca apenas em `visual.images`
- [ ] Documentar que o problema é incompatibilidade de estrutura de dados

## 2. Preparação para Correção
- [ ] Abrir o arquivo `frontend/src/components/AdsPreview.tsx`
- [ ] Localizar a função `getVariationImages` (linhas 336-342)
- [ ] Criar backup do código atual antes das alterações
- [ ] Verificar que o parâmetro `inline: "1"` está presente no fetchPreviewData (linha 403)

## 3. Implementação da Modificação
### 3.1. Aplicar a Correção
- [ ] Adicionar verificação de `variation.visual` no início da função
- [ ] Manter a verificação do campo `images[]` para compatibilidade futura
- [ ] Adicionar fallback para buscar campos individuais de URL
- [ ] Implementar a ordem correta: estado_atual → estado_intermediario → estado_aspiracional
- [ ] Adicionar cast `as any` para acessar campos extras sem quebrar tipos

### 3.2. Código a Implementar
- [ ] Substituir o código atual da função `getVariationImages`
- [ ] Verificar indentação e formatação
- [ ] Confirmar que a função retorna `string[]` em todos os casos
- [ ] Validar que retorna array vazio se não encontrar dados

## 4. Validação da Implementação
### 4.1. Verificar Estrutura do Código
- [ ] Confirmar que a função é retrocompatível
- [ ] Verificar que primeiro tenta `visual.images`
- [ ] Confirmar que depois busca campos individuais como fallback
- [ ] Validar que mantém a ordem lógica das imagens

### 4.2. Verificar Tipos TypeScript
- [ ] Confirmar que não há erros de compilação TypeScript
- [ ] Verificar que o uso de `as any` está localizado
- [ ] Confirmar que a assinatura da função não mudou
- [ ] Validar que o tipo de retorno continua sendo `string[]`

## 5. Testes Funcionais
### 5.1. Reiniciar e Testar
- [ ] Executar `make dev` para reiniciar o frontend
- [ ] Aguardar compilação sem erros
- [ ] Abrir o navegador em http://localhost:5173/app/
- [ ] Fazer uma requisição completa para gerar anúncios

### 5.2. Testar Preview
- [ ] Clicar no botão "Preview" quando disponível
- [ ] Verificar que o modal abre sem erros
- [ ] Confirmar que as 3 imagens aparecem no carrossel
- [ ] Testar navegação entre as imagens (Estado Atual, Intermediário, Aspiracional)

### 5.3. Validar Funcionalidades
- [ ] Verificar que os botões de navegação lateral funcionam
- [ ] Confirmar que os dots indicadores aparecem e funcionam
- [ ] Verificar que os labels das etapas estão corretos
- [ ] Testar navegação entre diferentes variações (se houver múltiplas)

## 6. Verificação de Console
- [ ] Abrir DevTools (F12)
- [ ] Verificar aba Console para erros JavaScript
- [ ] Confirmar ausência de erros relacionados a `images`
- [ ] Verificar que não há warnings de tipos TypeScript

## 7. Testes de Regressão
- [ ] Verificar que textos (headline, corpo, CTA) continuam aparecendo
- [ ] Confirmar que metadados são exibidos corretamente
- [ ] Testar que blocos colapsáveis funcionam (Referências, StoryBrand)
- [ ] Verificar que o botão "Recarregar dados" funciona

## 8. Documentação
- [ ] Adicionar comentário na função explicando o fallback
- [ ] Documentar que o campo `visual.images` será usado no futuro
- [ ] Registrar a data da correção no código se necessário
- [ ] Atualizar documentação técnica se existir

## 9. Commit e Versionamento
- [ ] Executar `git add frontend/src/components/AdsPreview.tsx`
- [ ] Criar commit com mensagem descritiva da correção
- [ ] Fazer push para o branch atual
- [ ] Verificar CI/CD se aplicável

## 10. Validação Final
- [ ] Testar em diferentes navegadores se possível
- [ ] Confirmar que o preview funciona consistentemente
- [ ] Verificar que não há degradação de performance
- [ ] Marcar a tarefa como concluída na documentação do projeto

---

**Observações:**
- CORS já foi resolvido pelo Codex Cloud com o parâmetro `inline=true`
- Esta correção foca apenas no mapeamento de campos
- A solução é retrocompatível e preparada para mudanças futuras