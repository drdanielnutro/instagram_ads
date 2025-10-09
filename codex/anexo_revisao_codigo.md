# Anexo – Revisão de Código Implementado (Plano Validação Determinística)

Estas instruções complementam `AGENTS.md` e são obrigatórias sempre que o Codex validar entregas concluídas do plano de Validação Determinística (`imagem_roupa.md`). Devem ser aplicadas após sincronizar o repositório com o trabalho executado pelo Codex Cloud ou qualquer outra fonte.

## 1. Objetivo

Garantir que cada fase concluída no checklist `imagem_roupa_checklist.md` foi implementada exatamente conforme o plano, observando:

- Cobertura integral das subtarefas da fase.
- Aderência ao design previsto e às diretrizes de `AGENTS.md`.
- Ausência de regressões ou alterações colaterais indevidas.
- Evidências concretas em código, testes e documentação.

## 2. Escopo

A auditoria deve ocorrer **fase a fase**. Para cada rodada:

1. Identifique no `imagem_roupa_checklist.md` a fase/subtarefas marcadas como concluídas.
2. Extraia do `imagem_roupa.md` o conteúdo correspondente à fase concluída.
3. Audite o código-fonte real para validar a implementação contra o plano.
4. Avalie testes, documentação, configurações e efeitos colaterais.
5. Produza um relatório detalhado com achados e recomendações.

## 3. Preparação Obrigatória

Antes de iniciar a revisão:

- Leia `AGENTS.md` para contextualizar dependências, flags, testes e responsabilidades vigentes.
- Abra `imagem_roupa_checklist.md` e identifique a última fase concluída.
- Releia a seção correspondente em `imagem_roupa.md` (entregáveis, dependências, critérios, riscos).
- Sincronize o repositório (`git pull`) para trabalhar no commit mais recente após a entrega analisada.
- Configure o ambiente de leitura (IDE, diff viewer, `rg`, etc.) para navegar pelos arquivos referenciados.

## 4. Procedimento de Revisão

1. **Mapeamento Fase → Código**
   - Liste arquivos, classes, funções, constantes e configurações mencionados no plano para a fase.
   - Registre caminhos e linhas-alvo observando o diff ou a base atual.

2. **Verificação de Implementação**
   - Confirme que cada subtarefa do plano/checklist está presente no código.
   - Valide assinaturas, tipos, campos, nomes, valores default e comportamentos descritos.
   - Audite integrações (imports, chamadas, callbacks, atualizações de estado, logs).

3. **Análise de Testes**
   - Verifique a existência de testes especificados (arquivos, funções, asserts).
   - Avalie cobertura lógica: happy-path, falhas, fallback, toggles de flag.
   - Confirme conformidade com `pytest`, `mypy`, `ruff` e demais ferramentas.

4. **Documentação e Observabilidade**
   - Confira README, playbooks, comentários críticos e logs estruturados quando previstos.
   - Valide mensagens, campos e métricas expostos em SSE, audit trails, status reporters e dashboards.

5. **Detecção de Riscos e Side-effects**
   - Avalie regressões potenciais no fluxo legado e compatibilidade com flag desativada.
   - Inspecione mudanças fora do escopo da fase; determine se são justificadas.
   - Identifique lacunas de testes, tipagem ou validações de entrada.

## 5. Critérios de Sucesso

A fase revisada só é considerada aprovada se todos os itens abaixo forem verdadeiros:

- Todas as subtarefas foram implementadas conforme plano e checklist.
- Estruturas, contratos e integrações refletem exatamente o design especificado.
- Testes (unitários/integrados) foram adicionados/atualizados e passam localmente quando executados.
- Documentação e logs foram ajustados quando exigido.
- Nenhum arquivo fora do escopo sofreu alteração relevante sem justificativa explícita.
- Feature flags e caminhos de fallback preservam comportamento legado quando desativados.
- Não há violações de estilo, lint, tipagem ou segurança descritas em `AGENTS.md`.

## 6. Critérios de Erro / Achados

Classifique achados conforme severidade:

- **P0 (Bloqueante)** – funcionalidade ausente, contratos quebrados, regressão crítica, testes prometidos inexistentes. Requer retrabalho imediato.
- **P1 (Alto)** – implementação parcial, lógica incorreta, testes insuficientes, documentação ausente. Deve ser corrigido antes de avançar.
- **P2 (Médio)** – desvios menores de design, falta de logs não críticos, ajustes recomendados. Pode ser tratado em follow-up próximo.
- **P3 (Baixo)** – nitpicks, formatação, oportunidades de melhoria sem impacto funcional.

## 7. Boas Práticas

- Utilize diff unificado e navegação por símbolos para contextualizar mudanças.
- Se algo parecer ausente, verifique variações (métodos renomeados, arquivos movidos).
- Rode testes localmente quando necessário para confirmar comportamento.
- Documente evidências com `arquivo:linha` (ex.: `app/agent.py:512`).
- Evite suposições; questione casos não especificados no plano antes de reprovar.
- Registre incertezas separadamente, sem classificá-las como blockers até obter confirmação.

## 8. Relatório Final

Ao concluir a revisão da fase:

1. Forneça resumo executivo (achados por severidade e impacto).
2. Liste cada finding com severidade, descrição, referência ao checklist/plano, evidência (`arquivo:linha`) e ação recomendada.
3. Indique se a fase está aprovada ou se requer correções antes de prosseguir.
4. Destaque riscos residuais, pendências ou dúvidas em aberto.
5. Informe commit analisado e data/hora (America/Sao_Paulo).

---

Seguir este anexo garante revisões consistentes, auditáveis e alinhadas às melhores práticas de code review para o plano de Validação Determinística.
