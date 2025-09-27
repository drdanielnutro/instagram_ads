# Revisão das Instruções de Correção do Plano StoryBrand

## Resumo
As instruções propostas estão alinhadas com o diagnóstico prévio: evitam duplicar overrides já presentes, reforçam que o pré-flight descrito no plano é documentação do comportamento atual e tratam a lacuna do diretório de prompts exigindo uma decisão explícita. Nenhuma orientação cria conflito com o código vigente.

## Evidências
- O override `STORYBRAND_MIN_COMPLETENESS` já é lido em `app/config.py`, portanto o plano deve apenas referenciar essa leitura existente.【F:app/config.py†L34-L114】
- O plano `aprimoramento_plano_storybrand_v2.md` ainda solicita a criação de um "novo override", reforçando a necessidade de ajustar essa seção.【F:aprimoramento_plano_storybrand_v2.md†L108-L117】
- A seção de pré-flight do plano descreve comportamentos já implementados, devendo ser mantida como documentação em vez de tarefa.【F:aprimoramento_plano_storybrand_v2.md†L54-L57】
- O plano depende de prompts em `prompts/storybrand_fallback/`, inexistentes no repositório atual, exigindo decisão sobre versionamento ou fallback no carregamento.【F:aprimoramento_plano_storybrand_v2.md†L41-L52】
