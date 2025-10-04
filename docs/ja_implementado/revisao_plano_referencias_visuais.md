# Revisão crítica do "Plano Estendido — Referências Visuais de Personagem e Produto/Serviço"

## 1. Metadados não serializáveis no estado inicial
- **Trecho do plano**: Define `ReferenceImageMetadata` como `BaseModel` e orienta inserir instâncias diretamente em `initial_state["reference_images"]`. 【F:imagem_roupa.md†L21-L46】
- **Incompatibilidade verificada**: O `initial_state` retornado por `/run_preflight` hoje contém apenas tipos primitivos ou dicionários/JSON serializáveis antes de seguir para o ADK. 【F:app/server.py†L335-L398】 A função usa o corpo da requisição (`payload: dict = Body(...)`) e devolve a estrutura sem conversão para objetos Pydantic. Objetos com `datetime` não são serializados implicitamente, quebrando o contrato atual com o frontend/ADK.
- **Correção sugerida**: Ajustar o plano para exigir que `ReferenceImageMetadata` seja convertido para um `dict` com `model_dump(mode="json")` (ou que o schema seja redefinido como `TypedDict`) antes de ser inserido no estado. Também documentar que apenas tipos JSON-compatíveis podem ser colocados em `initial_state`.

## 2. Uso incorreto de `resolve_reference_metadata`
- **Trecho do plano**: Recomenda `resolve_reference_metadata(reference_images.get("character"))`. 【F:imagem_roupa.md†L108-L120】
- **Incompatibilidade verificada**: A própria especificação do payload enviado pela UI fornece objetos `{"id": ..., "user_description": ...}`. 【F:imagem_roupa.md†L75-L85】 Assim, `reference_images.get("character")` retornaria o dicionário completo, enquanto o utilitário proposto aceita apenas `str | None`. 【F:imagem_roupa.md†L47-L53】 O plano também não explica como preservar `user_description` depois da resolução.
- **Correção sugerida**: Atualizar o plano para extrair explicitamente o ID (`reference_images.get("character", {}).get("id")`), combinar o `user_description` com o retorno do cache e armazenar ambos no estado. Documentar o merge antes de popular `initial_state`.

## 3. Referência inexistente a modelo Pydantic em `/run_preflight`
- **Trecho do plano**: “Atualizar o modelo Pydantic usado pelo endpoint (`RunPreflightRequest` ou equivalente)”. 【F:imagem_roupa.md†L108-L120】
- **Incompatibilidade verificada**: O endpoint atual não usa `BaseModel`; recebe diretamente `payload: dict = Body(...)` e processa manualmente os campos. 【F:app/server.py†L307-L410】 Não há classe Pydantic para atualizar, logo a instrução é inexequível como escrita.
- **Correção sugerida**: Esclarecer que será necessário **criar** um schema Pydantic novo (por exemplo, `RunPreflightRequest`) ou, se preferirem manter o dicionário cru, remover a menção a uma atualização inexistente.

## 4. Expectativa impossível no `final_assembler`
- **Trecho do plano**: Determina que o `final_assembler` ajuste o prompt para gerar `visual.reference_assets` com `gcs_uri` e `labels`. 【F:imagem_roupa.md†L54-L64】【F:imagem_roupa.md†L124-L129】
- **Incompatibilidade verificada**: O prompt atual do `final_assembler` não recebe nenhuma informação concreta de referência (URIs, labels) — ele só usa `{landing_page_url}`, `{formato_anuncio}`, `{objetivo_final}`, etc. 【F:app/agent.py†L1008-L1040】 Sem fornecer os dados reais, o LLM não conseguirá preencher campos factuais, podendo inventar valores.
- **Correção sugerida**: O plano deve especificar como os metadados serão injetados no prompt (ex.: campos adicionais em `initial_state` repassados ao agente ou pós-processamento programático que mergeie `reference_images` depois da geração). Sem essa clarificação, a etapa é inviável.

## Risco residual observado
- **Cache em memória**: A proposta de `resolve_reference_metadata` depende de um cache local com TTL. 【F:imagem_roupa.md†L47-L54】 Em implantações com múltiplos workers Uvicorn/Gunicorn, uploads e preflight podem ocorrer em processos distintos, tornando o cache volátil.
- **Recomendação**: Registrar no plano que será preciso usar um backend compartilhado (Redis/Datastore) ou sincronizar o cache para ambientes multiworker, evitando perda de metadados entre requests.

## Atualização
As inconsistências acima foram corrigidas diretamente em `imagem_roupa.md`, incorporando serialização explícita (`model_dump(mode="json")`), extração adequada de IDs e descrições na resolução de metadados, a criação do schema `RunPreflightRequest`, o detalhamento da injeção de dados concretos no `final_assembler` e a mitigação do risco de cache multiworker.
