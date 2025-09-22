# Checklist de Implementação – Refatoração Container Responsivo do Wizard

> Convenção de status: substitua manualmente o marcador de cada item conforme avança.
> - `[ ]` = pending (padrão)
> - `[>]` = in progress
> - `[x]` = done

## 1. Análise e Preparação
- [ ] Revisar o arquivo `frontend/src/components/WizardForm/WizardForm.tsx`
- [ ] Confirmar a estrutura atual do JSX (linha 224-246)
- [ ] Validar que o problema de overflow existe atualmente
- [ ] Criar backup do arquivo atual antes das alterações
- [ ] Testar o comportamento atual com conteúdo longo para documentar o problema

## 2. Implementação da Correção
### 2.1. Localização do Código
- [ ] Localizar o método `return` do componente `WizardForm`
- [ ] Identificar a estrutura do container principal (linha ~225)
- [ ] Identificar a posição do `<StepCard>` (linha ~232)

### 2.2. Aplicação da Refatoração
- [ ] Adicionar o wrapper `<div>` ao redor do `<StepCard>`
- [ ] Aplicar a classe `flex-1` ao novo wrapper
- [ ] Aplicar a classe `min-h-0` ao novo wrapper
- [ ] Aplicar a classe `overflow-y-auto` ao novo wrapper
- [ ] Garantir que o `<StepCard>` está completamente dentro do novo wrapper
- [ ] Verificar indentação e formatação do código

## 3. Validação da Estrutura
### 3.1. Verificação do Código
- [ ] Confirmar que `<ProgressHeader>` permanece como primeiro filho direto
- [ ] Confirmar que o novo wrapper div está como segundo filho direto
- [ ] Confirmar que `<NavigationFooter>` permanece como terceiro filho direto
- [ ] Validar que a estrutura segue o padrão:
  ```tsx
  <div className="mx-auto w-full max-w-4xl lg:max-w-5xl flex-1 flex flex-col gap-6">
    <ProgressHeader ... />
    <div className="flex-1 min-h-0 overflow-y-auto">
      <StepCard ...>
        {renderStepContent()}
      </StepCard>
    </div>
    <NavigationFooter ... />
  </div>
  ```

### 3.2. Verificação das Classes CSS
- [ ] Confirmar que `flex-1` está aplicado corretamente ao wrapper
- [ ] Confirmar que `min-h-0` está presente (crucial para funcionamento)
- [ ] Confirmar que `overflow-y-auto` está configurado
- [ ] Verificar que não há conflitos com classes existentes

## 4. Testes Funcionais
### 4.1. Testes de Layout
- [ ] Testar em viewport desktop (1920x1080)
- [ ] Testar em viewport tablet (768x1024)
- [ ] Testar em viewport mobile (375x667)
- [ ] Verificar que `NavigationFooter` permanece sempre visível
- [ ] Verificar que `ProgressHeader` permanece sempre visível

### 4.2. Testes de Overflow
- [ ] Adicionar conteúdo longo em um step e verificar scroll
- [ ] Testar com mensagens de erro visíveis
- [ ] Verificar que apenas a área central possui scroll
- [ ] Confirmar que a barra de scroll aparece apenas quando necessário
- [ ] Testar navegação entre steps com diferentes alturas de conteúdo

### 4.3. Testes de Interação
- [ ] Verificar que botões do `NavigationFooter` permanecem acessíveis
- [ ] Testar navegação com teclado (Tab, Shift+Tab)
- [ ] Verificar que o scroll reseta ao mudar de step
- [ ] Testar comportamento com zoom do navegador (75%, 100%, 125%)

## 5. Validação Cross-Browser
- [ ] Testar no Chrome/Chromium
- [ ] Testar no Firefox
- [ ] Testar no Safari (se disponível)
- [ ] Testar no Edge
- [ ] Verificar comportamento do scroll em cada navegador

## 6. Performance e Acessibilidade
- [ ] Verificar que não há repaint/reflow desnecessário
- [ ] Confirmar que o scroll é suave e responsivo
- [ ] Testar com leitor de tela (se aplicável)
- [ ] Verificar que foco do teclado não fica preso no scroll

## 7. Build e Deploy
- [ ] Executar `npm run build` no frontend
- [ ] Verificar que não há erros de compilação
- [ ] Testar a build em modo produção
- [ ] Executar testes automatizados (se existirem)

## 8. Documentação
- [ ] Atualizar comentários no código se necessário
- [ ] Documentar a mudança no commit message
- [ ] Registrar a correção em changelog/release notes se aplicável
- [ ] Atualizar documentação técnica se existir

## 9. Rollback Plan
- [ ] Documentar como reverter a mudança se necessário
- [ ] Manter backup do arquivo original
- [ ] Preparar comando git revert se usando versionamento

## 10. Sign-off Final
- [ ] Code review por outro desenvolvedor (se aplicável)
- [ ] QA aprova a correção
- [ ] Deploy em ambiente de staging
- [ ] Validação final em produção