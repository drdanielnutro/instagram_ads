# Inconsistências — Codex 8

1. **Flag `enable_storybrand_fallback` duplicada no plano — corrigida**
   - **Descrição**: Inconsistência sanada. A Seção 14 agora orienta a reutilização da flag já existente `enable_storybrand_fallback` e enfatiza apenas o reforço documental e o condicionamento do gate a essa configuração.
   - **Impacto (resolvido)**: O risco de duplicidade foi eliminado; o plano permanece alinhado ao atributo atual da `DevelopmentConfiguration`.
   - **Evidências**: Texto atualizado do plano e definição prévia na configuração e checklist.【F:aprimoramento_plano_storybrand_v2.md†L143-L146】【F:app/config.py†L34-L100】【F:checklist.md†L49-L52】
   - **Relação com ADK**: Mantida a dependência controlada do gate pela flag sem introduzir novos estados divergentes.

2. **Contrato contraditório para o `PromptLoader` — corrigido**
   - **Descrição**: Inconsistência sanada. A Seção 16.4 define explicitamente o carregamento eager com cache em memória e a validação completa do diretório durante a inicialização, removendo o conflito com a exigência de erro imediato.
   - **Impacto (resolvido)**: A implementação fica inequívoca, padronizando o comportamento do utilitário e reduzindo riscos de falhas em runtime.
   - **Evidências**: Texto atualizado da Seção 16.4.【F:aprimoramento_plano_storybrand_v2.md†L212-L220】
   - **Relação com ADK**: O pipeline passa a depender de um contrato determinístico de prompts, alinhado às expectativas dos agentes consumidores.
