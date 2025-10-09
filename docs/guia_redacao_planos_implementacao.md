# Guia de Redação de Planos de Implementação e Refatoração

## Princípio Fundamental

**Um plano de implementação deve distinguir claramente entre:**
1. **Entregas** - O que será criado/modificado pelo plano
2. **Dependências** - O que já existe no código e será utilizado

A confusão entre esses dois tipos de elementos gera **falsos bloqueadores** durante validação automatizada.

---

## Padrões de Linguagem

### ✅ Linguagem Declarativa (USAR)

Deixa claro que o elemento é uma **entrega do plano**:

```markdown
✅ "Criar arquivo `app/schemas/reference_assets.py` com schema `ReferenceImageInput`"
✅ "Implementar função `upload_reference_image()` em `app/utils/helpers.py`"
✅ "Adicionar endpoint POST `/upload/reference-image` em `app/server.py`"
✅ "Desenvolver componente `ReferenceUpload.tsx` que permitirá upload de imagens"
✅ "Estender schema `RunPreflightRequest` para incluir campo `reference_image_url`"
```

**Verbos recomendados para entregas**:
- Criar, Implementar, Desenvolver, Adicionar, Estender, Construir
- Modificar, Atualizar, Refatorar (quando alterando código existente)

---

### ❌ Linguagem Imperativa (EVITAR)

Sugere que o elemento **já existe** como dependência:

```markdown
❌ "O endpoint validará usando `ReferenceImageInput`"
   → Parece que ReferenceImageInput já existe

❌ "O sistema utilizará `reference_cache.get_image()`"
   → Implica que a função já está disponível

❌ "Integrar com `app/utils/vision.py`"
   → Sugere que vision.py é pré-requisito existente

❌ "`upload_reference_image` fará upload para GCS"
   → Não deixa claro se a função existe ou será criada
```

---

## Templates Recomendados

### Template 1: Criar Novo Arquivo

```markdown
**Tarefa**: Criar `<caminho/arquivo>`

**Descrição**: Implementar módulo `<nome>` que fornecerá funcionalidades de `<propósito>`.

**Estrutura**:
- Classe/função `X`: responsável por `<responsabilidade>`
- Classe/função `Y`: responsável por `<responsabilidade>`

**Dependências externas**:
- Importará `<módulo_existente>` de `<caminho_existente>` (já presente no código)
- Utilizará biblioteca `<lib>` (já listada em requirements.txt)

**Integrações planejadas**:
- Será importado por `<arquivo_futuro>` (também entrega deste plano)
- Será chamado pelo endpoint `<endpoint>` (a ser criado na Fase X)
```

---

### Template 2: Modificar Arquivo Existente

```markdown
**Tarefa**: Estender `<caminho/arquivo>` existente

**Descrição**: Adicionar funcionalidade `<nova_feature>` ao módulo existente `<nome>`.

**Alterações planejadas**:
1. Adicionar novo método `X()` à classe `<ClasseExistente>`
2. Importar nova dependência `<lib>` (adicionar a requirements.txt)
3. Modificar método existente `Y()` para integrar com nova lógica

**Código base (já existe)**:
- Classe `<ClasseExistente>` em linha X (será estendida)
- Método `<metodo_atual>()` em linha Y (será modificado)

**Novo código (será criado)**:
- Método `<metodo_novo>()`
- Validação `<funcao_validacao>()`
```

---

### Template 3: Criar Endpoint API

```markdown
**Tarefa**: Implementar endpoint `POST <rota>`

**Descrição**: Criar novo endpoint em `app/server.py` para `<propósito>`.

**Request Schema**: Criar `<SchemaName>` em `app/schemas/<arquivo>.py` com campos:
- `campo1: tipo` - descrição
- `campo2: tipo` - descrição

**Response Schema**: Criar `<ResponseSchemaName>` com campos:
- `status: str`
- `data: dict`

**Lógica do endpoint**:
1. Validar request usando schema criado acima
2. Chamar função `<funcao_helper>()` (a ser criada em `app/utils/<arquivo>.py`)
3. Retornar response com schema criado acima

**Dependências**:
- Utilizará decorator `@app.post()` do FastAPI (já disponível)
- Importará `<classe_existente>` de `<arquivo_existente>` (já presente)
```

---

### Template 4: Criar Componente Frontend

```markdown
**Tarefa**: Desenvolver componente React `<ComponentName>.tsx`

**Descrição**: Criar componente em `frontend/src/components/` para `<propósito>`.

**Props Interface**: Criar interface `<ComponentName>Props` com:
- `prop1: tipo` - descrição
- `prop2: tipo` - descrição

**Estado Interno**: Gerenciar estado usando hooks:
- `useState` para `<estado>`
- `useEffect` para `<efeito>`

**Integrações**:
- Será importado pelo componente `<ComponentePai>` existente em `<caminho>`
- Chamará API endpoint `<rota>` (a ser criado na Fase X deste plano)
- Utilizará componente UI `<ComponenteUI>` da biblioteca shadcn/ui (já disponível)

**Novo código (será criado)**:
- Componente `<ComponentName>`
- Interface `<ComponentName>Props`
- Função helper `handle<Acao>()`

**Código existente (será integrado)**:
- Componente pai `<ComponentePai>` em linha X (será modificado para importar este componente)
```

---

## Estrutura de Seções do Plano

### 1. Resumo Executivo
```markdown
## Resumo Executivo

**Objetivo**: Implementar sistema de `<funcionalidade>` para `<propósito>`.

**Escopo**: Este plano cobre a criação de:
- X novos arquivos (backend, frontend, schemas)
- Y modificações em arquivos existentes
- Z integrações com código atual

**Entregas principais**:
1. `<entrega1>` - descrição breve
2. `<entrega2>` - descrição breve

**Dependências do código atual**:
- `<arquivo_existente>` - será utilizado para X
- `<biblioteca_existente>` - já presente em requirements.txt
```

---

### 2. Faseamento e Ordem de Implementação

```markdown
## Faseamento

### Fase 1: Fundação (Schemas e Utils)
**Objetivo**: Criar estruturas de dados e utilitários base.

**Entregas**:
1. Criar `app/schemas/reference_assets.py`
   - Schema `ReferenceImageInput` com validação de URL/tipo
   - Schema `ReferenceImageMetadata` para persistência

2. Criar `app/utils/reference_cache.py`
   - Função `cache_reference_image(url: str) -> str`
   - Função `get_cached_image(cache_key: str) -> bytes`

**Dependências** (já existentes no código):
- `pydantic.BaseModel` para schemas
- `google.cloud.storage` para cache em GCS

**Razão da ordem**: Schemas devem existir antes de serem usados pelos endpoints.

---

### Fase 2: API Backend
**Objetivo**: Implementar endpoints e integrações com pipeline.

**Entregas**:
1. Adicionar endpoint `POST /upload/reference-image` em `app/server.py`
   - Usará schema `ReferenceImageInput` criado na Fase 1
   - Chamará função `cache_reference_image()` criada na Fase 1

2. Estender `run_preflight()` em `app/server.py`
   - Adicionar campo `reference_image_url` ao schema `RunPreflightRequest`
   - Integrar com cache criado na Fase 1

**Dependências** (já existentes no código):
- Função `run_preflight()` existente em `app/server.py:93`
- Class `FastAPI` instanciada como `app`

**Razão da ordem**: Endpoints dependem de schemas/utils da Fase 1.
```

---

### 3. Detalhamento de Entregas

Para cada arquivo a ser criado/modificado:

```markdown
## Detalhamento: `app/schemas/reference_assets.py`

### Status
**Arquivo**: Novo (será criado)

### Propósito
Definir schemas Pydantic para validação de uploads de imagens de referência.

### Estrutura do Código

#### Schema 1: `ReferenceImageInput`
```python
class ReferenceImageInput(BaseModel):
    """Schema para upload de imagem de referência (SERÁ CRIADO)."""
    image_url: HttpUrl
    image_type: Literal["product", "style", "model"]
    metadata: Optional[dict] = None
```

**Uso planejado**:
- Será importado pelo endpoint `/upload/reference-image` (Fase 2, entrega 1)
- Será usado para validar request body

#### Schema 2: `ReferenceImageMetadata`
```python
class ReferenceImageMetadata(BaseModel):
    """Metadados de imagem cacheada (SERÁ CRIADO)."""
    cache_key: str
    original_url: HttpUrl
    cached_at: datetime
    image_type: str
```

**Uso planejado**:
- Será retornado pela função `cache_reference_image()` (Fase 1, entrega 2)
- Será persistido no state do agente

### Dependências Externas
- `pydantic.BaseModel` (já disponível - listado em requirements.txt)
- `pydantic.HttpUrl` (já disponível)
- `typing.Literal, Optional` (stdlib Python)

### Integrações
**Este módulo será importado por**:
1. `app/server.py` - endpoint `/upload/reference-image` (entrega futura deste plano)
2. `app/utils/reference_cache.py` - função `cache_reference_image()` (entrega futura deste plano)

**Este módulo importará**:
- Apenas bibliotecas já presentes (pydantic, typing, datetime)
```

---

## Checklist de Qualidade

Antes de finalizar um plano, verificar:

### ✅ Clareza de Entregas
- [ ] Cada arquivo novo usa verbos "Criar", "Implementar", "Desenvolver"
- [ ] Cada modificação usa verbos "Estender", "Modificar", "Atualizar"
- [ ] Está claro o que existe vs. o que será criado

### ✅ Rastreabilidade de Dependências
- [ ] Dependências existentes têm caminho completo do arquivo
- [ ] Dependências existentes citam número de linha (quando relevante)
- [ ] Dependências de bibliotecas citam requirements.txt

### ✅ Ordem de Implementação
- [ ] Schemas/modelos vêm antes de endpoints
- [ ] Utils/helpers vêm antes de quem os usa
- [ ] Backend vem antes de frontend
- [ ] Cada fase explica POR QUE essa ordem

### ✅ Integrações Explícitas
- [ ] Para cada arquivo criado, listar "quem importará este arquivo"
- [ ] Para cada arquivo modificado, listar "o que será alterado"
- [ ] Integrações com código futuro (do mesmo plano) estão marcadas como "entrega da Fase X"

### ✅ Validação Automatizada
- [ ] Plano pode ser validado por `plan-code-validator` sem falsos P0
- [ ] Elementos ausentes são claramente entregas, não dependências
- [ ] Elementos existentes têm caminhos verificáveis

---

## Exemplos de Seções Completas

### Exemplo 1: Criação de Schema

```markdown
## Fase 1.1: Criar `app/schemas/reference_assets.py`

### Objetivo
Implementar schemas Pydantic para validação de dados de imagens de referência.

### Entregas (o que será criado)

1. **Schema `ReferenceImageInput`**
   - Campos: `image_url` (HttpUrl), `image_type` (Literal), `metadata` (Optional[dict])
   - Validação: URL válida, tipo permitido (product/style/model)

2. **Schema `ReferenceImageMetadata`**
   - Campos: `cache_key`, `original_url`, `cached_at`, `image_type`
   - Propósito: representar metadados de imagens cacheadas

### Dependências (o que já existe e será usado)

**Bibliotecas**:
- `pydantic` >= 2.0 (já em requirements.txt linha 12)
- `typing.Literal, Optional` (Python stdlib)

**Não possui dependências de código interno** (arquivo base, sem imports de app/*)

### Integrações Futuras (quem usará este código)

**Será importado por**:
1. `app/server.py` - endpoint `/upload/reference-image`
   - Fase 2.1 deste plano
   - Usará `ReferenceImageInput` para validar request body

2. `app/utils/reference_cache.py` - função `cache_reference_image()`
   - Fase 1.2 deste plano
   - Retornará instância de `ReferenceImageMetadata`

### Código Base

```python
# app/schemas/reference_assets.py (ARQUIVO NOVO - SERÁ CRIADO)

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, HttpUrl


class ReferenceImageInput(BaseModel):
    """
    Schema para validação de upload de imagem de referência.

    Será usado por:
    - Endpoint POST /upload/reference-image (Fase 2.1)
    """
    image_url: HttpUrl
    image_type: Literal["product", "style", "model"]
    metadata: Optional[dict] = None


class ReferenceImageMetadata(BaseModel):
    """
    Metadados de imagem de referência cacheada.

    Será retornado por:
    - app.utils.reference_cache.cache_reference_image() (Fase 1.2)
    """
    cache_key: str
    original_url: HttpUrl
    cached_at: datetime
    image_type: str
```

### Critérios de Aceitação

- [ ] Arquivo criado em `app/schemas/reference_assets.py`
- [ ] Imports de pydantic funcionam (pydantic instalado)
- [ ] Schema `ReferenceImageInput` valida URLs corretamente
- [ ] Schema `ReferenceImageInput` rejeita tipos inválidos
- [ ] Schema `ReferenceImageMetadata` serializa para JSON
- [ ] Nenhum import de arquivos que serão criados em fases futuras
```

---

### Exemplo 2: Modificação de Arquivo Existente

```markdown
## Fase 2.2: Estender `app/server.py` - Função `run_preflight()`

### Objetivo
Adicionar suporte para resolução de imagens de referência no preflight.

### Código Atual (o que já existe)

**Arquivo**: `app/server.py`
**Função**: `run_preflight()` (linhas 93-166)

**Signature atual**:
```python
async def run_preflight(request: RunPreflightRequest) -> dict:
    # Valida e normaliza input
    # Retorna initial_state com plano fixo
```

**Schema atual**: `RunPreflightRequest` em `app/schemas.py` (linhas 45-52)
```python
class RunPreflightRequest(BaseModel):
    landing_page_url: str
    objetivo_final: str
    perfil_cliente: str
    formato_anuncio: str
    foco: Optional[str] = None
```

### Modificações Planejadas (o que será alterado)

#### 1. Estender Schema `RunPreflightRequest`

**Local**: `app/schemas.py` linha 52 (após campo `foco`)

**Adicionar**:
```python
class RunPreflightRequest(BaseModel):
    # ... campos existentes ...
    foco: Optional[str] = None
    reference_image_url: Optional[HttpUrl] = None  # NOVO CAMPO
```

**Importar**: `from pydantic import HttpUrl` (adicionar ao import existente linha 3)

#### 2. Modificar Lógica de `run_preflight()`

**Local**: `app/server.py` após linha 120 (validação de formato)

**Adicionar bloco**:
```python
# Resolver imagem de referência se fornecida
reference_metadata = None
if request.reference_image_url:
    from app.utils.reference_cache import cache_reference_image  # Fase 1.2
    reference_metadata = await cache_reference_image(request.reference_image_url)

# Incluir metadados no initial_state
initial_state["reference_image"] = reference_metadata
```

### Dependências

**Código existente** (será utilizado):
- Função `run_preflight()` em `app/server.py:93` (será modificada)
- Schema `RunPreflightRequest` em `app/schemas.py:45` (será estendido)

**Código novo** (de fases anteriores deste plano):
- Função `cache_reference_image()` de `app/utils/reference_cache.py` (Fase 1.2)
- Schema `ReferenceImageMetadata` de `app/schemas/reference_assets.py` (Fase 1.1)

**Bibliotecas**:
- `pydantic.HttpUrl` (já disponível em requirements.txt)

### Integrações

**Este código modificado será usado por**:
- Frontend `InputForm.tsx` (Fase 3.1) - enviará `reference_image_url` no request
- Agente `ImageAssetsAgent` - lerá `reference_image` do state (Fase 2.3)

### Diff Resumido

```diff
# app/schemas.py
  class RunPreflightRequest(BaseModel):
      landing_page_url: str
      objetivo_final: str
      perfil_cliente: str
      formato_anuncio: str
      foco: Optional[str] = None
+     reference_image_url: Optional[HttpUrl] = None

# app/server.py
  async def run_preflight(request: RunPreflightRequest) -> dict:
      # ... validações existentes ...

+     # Resolver referência visual se fornecida
+     reference_metadata = None
+     if request.reference_image_url:
+         from app.utils.reference_cache import cache_reference_image
+         reference_metadata = await cache_reference_image(request.reference_image_url)
+
      initial_state = {
          "landing_page_url": request.landing_page_url,
          # ... campos existentes ...
+         "reference_image": reference_metadata,
      }
```

### Critérios de Aceitação

- [ ] Campo `reference_image_url` aceita URLs válidas
- [ ] Campo `reference_image_url` rejeita URLs malformadas
- [ ] Quando `reference_image_url` é None, preflight funciona normalmente
- [ ] Quando fornecida, função `cache_reference_image()` é chamada
- [ ] Metadados são incluídos em `initial_state["reference_image"]`
- [ ] Testes existentes de `run_preflight()` continuam passando
```

---

## Anti-Padrões Comuns

### ❌ Anti-Padrão 1: Dependência Fantasma

```markdown
## Fase 2: Implementar Upload

O endpoint `/upload/reference-image` validará o request usando `ReferenceImageInput`.
```

**Problema**: Não fica claro se `ReferenceImageInput` existe ou será criado.

**Correção**:
```markdown
## Fase 2: Implementar Upload

Criar endpoint `POST /upload/reference-image` em `app/server.py` que:
- Usará schema `ReferenceImageInput` criado na Fase 1
- Validará request body com validações de URL e tipo
```

---

### ❌ Anti-Padrão 2: Integração Ambígua

```markdown
Integrar com `app/utils/vision.py` para análise de imagens.
```

**Problema**: "Integrar com" sugere que `vision.py` já existe.

**Correção**:
```markdown
Criar módulo `app/utils/vision.py` com funções:
- `analyze_image_style()` - detecta cores/composição usando Vision AI
- `extract_image_metadata()` - extrai dimensões/formato

Este módulo será importado por `ImageAssetsAgent` (Fase 3).
```

---

### ❌ Anti-Padrão 3: Ordem Sem Justificativa

```markdown
## Fases

1. Frontend
2. Backend
3. Schemas
```

**Problema**: Ordem ilógica (schemas devem vir antes).

**Correção**:
```markdown
## Fases

### Fase 1: Schemas e Tipos
Criar estruturas de dados base.
**Razão**: Schemas devem existir antes de serem usados por backend/frontend.

### Fase 2: Backend API
Implementar endpoints e lógica.
**Razão**: API deve estar funcional antes de frontend consumir.

### Fase 3: Frontend
Desenvolver componentes UI.
**Razão**: UI depende de API estar operacional para testes.
```

---

### ❌ Anti-Padrão 4: Mistura de Criação e Uso

```markdown
Criar `reference_cache.py` que o endpoint usará para fazer upload.
```

**Problema**: Mistura criação (reference_cache) com uso (endpoint) na mesma frase.

**Correção**:
```markdown
### Fase 1: Criar `app/utils/reference_cache.py`
Implementar módulo de cache com funções:
- `cache_reference_image(url)` - baixa e cacheia imagem

### Fase 2: Criar endpoint `/upload/reference-image`
Este endpoint importará e usará `cache_reference_image()` da Fase 1.
```

---

## Glossário de Termos

| Termo | Significado | Exemplo |
|-------|-------------|---------|
| **Entrega** | Código que será criado/modificado pelo plano | "Criar schema `ReferenceImageInput`" |
| **Dependência** | Código que já existe e será utilizado | "Importará `FastAPI` (já em app/server.py:5)" |
| **Integração** | Conexão entre entregas do plano | "`endpoint_X` usará `schema_Y` (Fase 1)" |
| **Pré-requisito** | Dependência externa necessária | "Requer `google-cloud-vision>=3.4.0`" |
| **Fase** | Grupo de entregas com ordem lógica | "Fase 1: Schemas (base para Fase 2)" |
| **Bloqueador** | Dependência citada mas ausente no código | "P0: `utils/vision.py` não encontrado" |

---

## Validação do Plano

### Teste Manual de Linguagem

Para cada elemento do plano, perguntar:

1. **É uma entrega ou dependência?**
   - Se entrega → Usar "Criar", "Implementar", "Desenvolver"
   - Se dependência → Citar caminho/linha do código existente

2. **A ordem faz sentido?**
   - Schemas antes de endpoints?
   - Utils antes de quem os usa?
   - Backend antes de frontend?

3. **As integrações estão claras?**
   - Cada arquivo criado lista "quem usará este código"?
   - Integrações citam fase específica?

### Validação Automatizada

Rodar `plan-code-validator` antes de implementar:

```bash
# Validar plano contra código atual
plan-code-validator plano_implementacao.md
```

**Resultado esperado**:
- ✅ P0 = 0 (nenhum bloqueador crítico)
- ✅ Entregas = N (elementos claramente marcados como "criar")
- ✅ Precision > 90% (matching de dependências correto)

Se `P0 > 0`: revisar linguagem das seções com bloqueadores.

---

## Conclusão

**Princípio de Ouro**:
> "Seja explícito sobre o que existe e o que será criado. Use linguagem declarativa para entregas, cite caminhos/linhas para dependências."

Seguindo este guia, seus planos serão:
- ✅ Validáveis automaticamente (sem falsos P0)
- ✅ Implementáveis sem ambiguidade
- ✅ Rastreáveis (cada entrega tem origem e destino claro)
- ✅ Ordenados logicamente (dependências antes de uso)
