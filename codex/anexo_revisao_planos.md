# Anexo – Revisão de Planos `.md`

Estas instruções complementam `AGENTS.md` e **devem ser seguidas sempre que o usuário solicitar que o Codex "revise um plano .md"** ou qualquer variação equivalente ("revisar plano", "validar plano markdown", etc.).

## Contexto
- Trabalhe em PT-BR e use America/Sao_Paulo quando precisar citar horários.
- Trate o código-fonte como fonte da verdade. Nunca presuma que o plano está correto.
- Utilize as instruções detalhadas do agente `plan-code-validator` (`.claude/agents/plan-code-validator.md`) como referência técnica obrigatória.

## Procedimento Obrigatório
1. **Localizar e ler o plano** indicado pelo usuário. Resuma rapidamente o objetivo e anote caminhos de arquivos relevantes.
2. **Extrair todas as alegações** do plano sobre elementos existentes (classes, funções, rotas, variáveis, configs, dependências, etc.).
3. **Classificar cada alegação** conforme o sistema do `plan-code-validator`:
   - `DEPENDÊNCIA`: deve existir hoje e será usada.
   - `MODIFICAÇÃO`: elemento existente que será alterado.
   - `ENTREGA`: item novo a ser criado (não validar no código; apenas registrar).
4. **Validar no código** todas as alegações `DEPENDÊNCIA` e `MODIFICAÇÃO`:
   - Localize os arquivos correspondentes no repositório.
   - Verifique assinaturas, tipos, contratos, rotas, constantes, configs e integrações mencionadas.
   - Registre sempre o caminho e a linha (`arquivo.py:42`) usados como evidência.
5. **Avaliar severidade** de cada discrepância usando a escala P0–P3 do `plan-code-validator`.
6. **Montar relatório estruturado** com:
   - Resumo executivo (quantidade de achados por severidade e impacto).
   - Lista de inconsistências, cada uma com: severidade, alegação original, evidência no código, ação recomendada.
   - Tabela mapa Plano ↔ Código (quando aplicável).
   - Itens de incerteza ou verificações pendentes.
7. **Responder ao usuário** somente após revisar todo o plano. Informe claramente se o plano está alinhado ou detalhe as inconsistências encontradas.

## Boas Práticas
- Priorize achados críticos (P0/P1) antes dos demais.
- Se algo parecer dinâmico/metaprogramado, marque como incerteza em vez de assumir ausência.
- Não rode testes ou comandos destrutivos sem autorização explícita.
- Não modifique arquivos do repositório durante a revisão.

## Resultado Esperado
Uma resposta final que permita ao usuário corrigir o plano antes da implementação, evitando retrabalho. O relatório deve ser autoexplicativo, com links de código e ações concretas para cada divergência.
