# Plano de Acesso StoryBrand Sections via GCS

**Data:** 2025-10-12
**Status:** Em Análise
**Objetivo:** Permitir acesso posterior às 16 seções StoryBrand salvas no GCS via API segura

---

## 📋 Plano Original

### 1. Auditoria Atual
Revisar `PersistStorybrandSectionsAgent` (`app/agents/storybrand_fallback.py`) para mapear o fluxo local+GCS e o payload registrado em `meta.json`. Confirmar que apenas URI é salvo (`storybrand_sections_gcs_uri`).

### 2. Autorização
Decidir estratégia de controle privilegiando **Signed URLs on demand** (cenário atual sem auth robusta). Mapear requisito "mesmo usuário" → exigir `user_id/session_id` no meta e validar antes de gerar a URL; registrar que IAM direto fica para uma fase posterior quando houver autenticação formal.

### 3. Persistência Garantida
Definir TTL zero (sem expiração) até criar lifecycle controlada; documentar que GCS mantém arquivo indefinidamente.

### 4. API Acesso Futuro
Esboçar nova rota `GET /storybrand/sections` usando `user_id/session_id` → valida ownership via meta + gera signed URL de curta duração (configurável).

### 5. Update no Agent
Preparar código para armazenar metadados adicionais (ex: `storybrand_sections_signed_url` opcional) ou helper central `.utils` que gera signed URL quando chamado.

### 6. Segurança
Logar acesso, aplicar `signed_url_ttl` configurável, assegurar que valores em meta não expõem credenciais.

### 7. Testes
Planejar unitários que simulam gravação + geração de signed URL, e integração garantindo retorno 200 só para o owner; regredir fallback disabled path.

### 8. Documentação
Atualizar README/AGENTS/playbook com fluxo de acesso futuro; registrar uso de `storybrand_sections_gcs_uri` e endpoint planejado.

---

## ✅ Avaliação: Pontos Fortes

### 1. Alinhamento com Arquitetura
- O plano se integra naturalmente com o fluxo existente:
  - `PersistStorybrandSectionsAgent` já salva no GCS
  - `meta.json` já registra `storybrand_sections_gcs_uri`
  - Flag `PERSIST_STORYBRAND_SECTIONS` controla funcionalidade

### 2. Estrutura Metodológica
- Cobre todas as fases essenciais do ciclo de desenvolvimento
- Sequência lógica: auditoria → autorização → implementação → testes → docs

### 3. Segurança First
- Considera IAM, signed URLs, logging e proteção de credenciais desde o início
- Prevê validação de ownership antes de conceder acesso

### 4. Cobertura de Testes
- Planeja testes unitários e de integração
- Inclui regressão do path `fallback disabled`
- Considera cenários de segurança (acesso não autorizado)

---

## ⚠️ Gaps Críticos a Resolver

### 1. Requisito de Negócio Ausente

**Questões Não Respondidas:**
- ❓ **Quem** vai consumir `/storybrand/sections`?
  - Frontend atual?
  - Dashboard interno?
  - API externa para parceiros?
- ❓ **Frequência** de acesso?
  - Esporádico (revisão manual ocasional)
  - Regular (listagem de histórico)
  - Intensivo (analytics em batch)
- ❓ **Contexto de uso**?
  - Revisão humana de qualidade
  - Análise posterior para melhorias
  - Exportação para cliente final
- ❓ **SLA esperado**?
  - Latência aceitável para gerar signed URL
  - Timeout máximo para download

**Impacto:** Sem essas respostas, não é possível escolher entre IAM vs. Signed URLs de forma fundamentada.

---

### 2. Decisão de Autorização em Aberto

O sistema atual não possui autenticação (requests são tratadas com `user_id="anonymous"` quando o cliente não envia). Para evoluir rapidamente e permitir uso por sessão, adotar **Signed URLs** com TTL curto, geradas sob demanda após validar `user_id`. Registrar que, quando houver auth formal (JWT/OAuth), podemos migrar para IAM.

---

### 3. User Management Não Mapeado

O plano assume `user_id` mas não verifica:

#### Checklist de Validação
- [ ] Sistema atual rastreia usuários?
  - Verificar `app/models/` e schemas Pydantic
  - Buscar por `user_id` em `app/`
- [ ] Há relação `user → session` persistida?
  - Verificar `meta.json` atual em `app/callbacks/persist_outputs.py:48-68`
  - Confirmar se `session_id` é único globalmente ou por usuário
- [ ] Frontend envia `user_id` nas requisições?
  - Verificar `frontend/src/services/` e chamadas API
  - Confirmar se há estado de autenticação no React

**Investigação Preliminar:**
```bash
# Verificar rastreamento de usuários
grep -r "user_id" app/ --include="*.py"

# Verificar autenticação existente
grep -r "OAuth\|JWT\|@login_required" app/server.py

# Verificar estrutura do meta.json
cat app/callbacks/persist_outputs.py | grep -A10 "meta.json"
```

---

### 4. TTL Zero = Risco de Custo Infinito

**Problema:**
```
"TTL zero (sem expiração) até criar lifecycle controlada"
```

❌ **Perigoso:** GCS sem lifecycle policy = custos crescem indefinidamente
❌ **Risco:** Arquivos órfãos de sessões falhas acumulam sem limpeza

**Recomendação:**
```python
# app/.env
STORYBRAND_SECTIONS_RETENTION_DAYS=180  # 6 meses padrão
STORYBRAND_SECTIONS_RETENTION_CRITICAL_DAYS=365  # Para sessões marcadas

# Implementação sugerida
def get_gcs_lifecycle_condition():
    retention_days = int(os.getenv("STORYBRAND_SECTIONS_RETENTION_DAYS", 180))
    return {
        "action": {"type": "Delete"},
        "condition": {"age": retention_days}
    }
```

**Plano de Lifecycle:**
1. **Fase 1 (imediato):** TTL de 180 dias configurável via env
2. **Fase 2 (futuro):** Endpoint para marcar sessões como "critical" (TTL 365 dias)
3. **Fase 3 (futuro):** Dashboard para revisar/estender TTL manualmente
4. **Monitoramento:** Alerta se storage GCS > X GB/mês

---

### 5. Ordem de Execução Não Otimizada

**Sequência Atual:**
```
Auditoria → Autorização → API → Testes → Docs
```

**Problema:** Bloqueante na frente (autorização) impede paralelização

**Sequência Otimizada:**

```
FASE 0: Discovery & Requirements (ADICIONAR - BLOQUEANTE)
├── Mapear autenticação existente
├── Definir caso de uso exato
├── Escolher estratégia de autorização
└── Validar user management

FASE 1: Análise Técnica (PARALELA)
├── Auditoria do código atual
└── Esboçar contratos da API (OpenAPI spec)

FASE 2: Implementação (SEQUENCIAL)
├── Implementar endpoint
├── Implementar testes
└── Atualizar documentação

FASE 3: Validação (SEQUENCIAL)
├── Code review
├── Teste de carga
└── Deploy staging
```

---

## 🔧 Recomendações de Melhoria

### FASE 0: Discovery & Requirements (ADICIONAR)

**Objetivo:** Coletar informações necessárias para decisões fundamentadas

```markdown
#### Checklist de Discovery

**A. Autenticação Atual**
- [ ] Ler `app/server.py` e identificar middleware de autenticação
- [ ] Verificar se há dependências FastAPI-Users, Authlib, ou similar
- [ ] Confirmar se endpoints atuais exigem autenticação
- [ ] Mapear como `user_id` é extraído do request (se aplicável)

**B. User Management**
- [ ] Revisar `frontend/src/services/*.ts` para ver gestão de `user_id`
- [ ] Confirmar se há estado de autenticação no frontend (Context, Redux, etc.)
- [ ] Verificar se `meta.json` já inclui `user_id` ou identificador similar
- [ ] Mapear relação `user_id → session_id` (1:N esperado)

**C. Caso de Uso**
- [ ] Entrevistar stakeholder: qual o caso de uso exato?
- [ ] Definir frequência esperada de acesso às seções
- [ ] Confirmar se acesso é humano (dashboard) ou programático (API)
- [ ] Definir SLA: latência máxima aceitável para gerar signed URL

**D. Decisão de Autorização**
- [ ] Aplicar critérios de decisão (IAM vs. Signed URLs)
- [ ] Documentar decisão formal com rationale
- [ ] Estimar esforço de implementação de cada opção
- [ ] Confirmar com time de infra/segurança
```

**Output Esperado:**
- Documento `discovery-storybrand-access.md` com respostas
- Decisão formal: IAM ou Signed URLs
- Mapeamento de user management existente

---

### Item 3 Refinado: Persistência Garantida

**Original:**
> Definir TTL zero (sem expiração) até criar lifecycle controlada

**Refinado:**
```markdown
#### 3. Persistência Garantida

**A. Lifecycle Policy Imediata**
- [ ] Definir `STORYBRAND_SECTIONS_RETENTION_DAYS=180` em `.env`
- [ ] Implementar lifecycle condition no bucket GCS
- [ ] Documentar processo de extensão de TTL para casos excepcionais
- [ ] Adicionar monitoramento de custos GCS (alerta se >50 GB/mês)

**B. Configuração GCS**
```python
# app/utils/gcs_lifecycle.py
from google.cloud import storage

def configure_storybrand_bucket_lifecycle(bucket_name: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    retention_days = int(os.getenv("STORYBRAND_SECTIONS_RETENTION_DAYS", 180))

    bucket.lifecycle_rules = [{
        "action": {"type": "Delete"},
        "condition": {
            "age": retention_days,
            "matchesPrefix": ["storybrand/sections/"]
        }
    }]

    bucket.patch()
    logger.info(f"Lifecycle configurado: {retention_days} dias")
```

**C. Extensão Manual (Futuro)**
- [ ] Endpoint `POST /storybrand/sessions/{id}/extend-ttl`
- [ ] Requer justificativa e aprovação
- [ ] Adiciona metadata `extended_until` no blob GCS
- [ ] Atualiza lifecycle condition temporariamente
```

---

### Item 6 Refinado: Segurança

**Original:**
> Logar acesso, aplicar signed_url_ttl configurável, assegurar que valores em meta não expõem credenciais.

**Refinado:**
```markdown
#### 6. Segurança

**A. Rate Limiting**
- [ ] Implementar rate limit no endpoint: 10 req/min por `user_id`
- [ ] Usar Redis ou in-memory cache (SlowAPI lib)
- [ ] Retornar HTTP 429 com `Retry-After` header

**B. Audit Log**
```python
# app/utils/audit.py
import structlog

audit_logger = structlog.get_logger("audit")

def log_storybrand_access(
    user_id: str,
    session_id: str,
    action: str,  # "generate_url", "download", "access_denied"
    ip_address: str,
    success: bool
):
    audit_logger.info(
        "storybrand_access",
        user_id=user_id,
        session_id=session_id,
        action=action,
        ip=ip_address,
        success=success,
        timestamp=datetime.utcnow().isoformat()
    )
```

**C. Signed URL TTL**
- [ ] Configurar `STORYBRAND_SIGNED_URL_TTL_MINUTES=15` em `.env`
- [ ] Validar que TTL está entre 1-60 minutos
- [ ] Documentar que URLs expiram e devem ser regeneradas

**D. Validação de Ownership**
```python
# app/services/storybrand_access.py
async def validate_session_ownership(user_id: str, session_id: str) -> bool:
    meta_path = f"artifacts/{session_id}/meta.json"

    if not os.path.exists(meta_path):
        return False

    with open(meta_path) as f:
        meta = json.load(f)

    # Assumindo que meta.json tem campo 'user_id' (validar no Discovery!)
    return meta.get("user_id") == user_id
```

**E. Sanitização de Paths**
- [ ] Validar que `session_id` é UUID válido (regex: `^[0-9a-f-]{36}$`)
- [ ] Bloquear caracteres perigosos: `../`, `~`, `\0`
- [ ] Usar `pathlib.Path.resolve()` e verificar que resultado está no bucket esperado

**F. CORS (se necessário)**
- [ ] Configurar CORS em `app/server.py` apenas se frontend externo consumir
- [ ] Whitelist explícito de origens (não usar `*`)
- [ ] Bloquear credentials se não houver necessidade
```

---

### Item 7 Refinado: Testes

**Original:**
> Planejar unitários que simulam gravação + geração de signed URL, e integração garantindo retorno 200 só para o owner; regredir fallback disabled path.

**Refinado:**
```markdown
#### 7. Testes

**A. Testes Unitários**
```python
# tests/unit/services/test_storybrand_access.py

@pytest.mark.asyncio
async def test_generate_signed_url_success(mock_gcs_client):
    """Gerar signed URL para sessão válida."""
    url = await generate_signed_url("user123", "session456")
    assert url.startswith("https://storage.googleapis.com")
    assert "X-Goog-Signature" in url

@pytest.mark.asyncio
async def test_validate_ownership_success(tmp_path):
    """Validar ownership quando user_id corresponde."""
    meta = {"user_id": "user123", "session_id": "session456"}
    (tmp_path / "meta.json").write_text(json.dumps(meta))

    result = await validate_session_ownership("user123", "session456")
    assert result is True

@pytest.mark.asyncio
async def test_validate_ownership_denied(tmp_path):
    """Negar acesso quando user_id não corresponde."""
    meta = {"user_id": "user999", "session_id": "session456"}
    (tmp_path / "meta.json").write_text(json.dumps(meta))

    result = await validate_session_ownership("user123", "session456")
    assert result is False
```

**B. Testes de Integração**
```python
# tests/integration/test_storybrand_access_api.py

@pytest.mark.asyncio
async def test_access_own_session_returns_200(client, auth_headers):
    """User A acessa sessão própria → 200 + signed URL."""
    response = await client.get(
        "/storybrand/sections/session123",
        headers=auth_headers("userA")
    )
    assert response.status_code == 200
    assert "signed_url" in response.json()

@pytest.mark.asyncio
async def test_access_other_session_returns_403(client, auth_headers):
    """User A tenta acessar sessão de User B → 403."""
    response = await client.get(
        "/storybrand/sections/session_of_userB",
        headers=auth_headers("userA")
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_fallback_disabled_returns_404(client, monkeypatch):
    """Fallback desabilitado → endpoint retorna 404."""
    monkeypatch.setenv("PERSIST_STORYBRAND_SECTIONS", "false")
    response = await client.get("/storybrand/sections/session123")
    assert response.status_code == 404
```

**C. Testes de Performance**
```python
# tests/load_test/test_storybrand_access_load.py (Locust)

class StorybrandAccessUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_signed_url(self):
        session_id = random.choice(self.session_pool)
        self.client.get(
            f"/storybrand/sections/{session_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    def on_start(self):
        # Setup: criar 100 sessões de teste
        self.session_pool = [...]
        self.token = "test_token"

# Validar: 100 usuários concorrentes → p95 <500ms
```

**D. Testes de Segurança**
```python
# tests/security/test_storybrand_access_security.py

@pytest.mark.asyncio
async def test_path_traversal_blocked(client):
    """Tentar path traversal → bloqueado."""
    malicious_ids = [
        "../../../etc/passwd",
        "session123/../../secrets",
        "session%2F..%2F..%2Fsecrets"
    ]
    for session_id in malicious_ids:
        response = await client.get(f"/storybrand/sections/{session_id}")
        assert response.status_code == 400
        assert "invalid session_id" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_rate_limit_enforced(client, auth_headers):
    """Exceder rate limit → 429."""
    for _ in range(15):  # Limite é 10/min
        response = await client.get(
            "/storybrand/sections/session123",
            headers=auth_headers("userA")
        )

    assert response.status_code == 429
    assert "retry-after" in response.headers
```

**E. Regressão**
- [ ] `test_fallback_disabled_path` → garantir que nada quebra quando flag desabilitada
- [ ] `test_legacy_meta_without_gcs_uri` → garantir graceful degradation
- [ ] `test_gcs_unavailable` → retornar 503 se GCS inacessível
```

---

## 🎯 Próximos Passos

### 1. Fase de Investigação (Estimativa: 1-2 horas)

```bash
# A. Verificar autenticação existente
grep -r "user_id" app/ --include="*.py" | head -20
grep -r "OAuth\|JWT\|@login_required\|Depends.*get_current" app/server.py

# B. Verificar estrutura meta.json atual
cat app/callbacks/persist_outputs.py | grep -A15 "meta.json"

# C. Verificar gestão de user no frontend
find frontend/src -name "*.ts" -exec grep -l "user.*id\|auth" {} \;

# D. Verificar flag atual de persistência
grep "PERSIST_STORYBRAND_SECTIONS" app/.env
```

**Output:** Documento `.claude/results/discovery-storybrand-access.json` com:
```json
{
  "has_authentication": true/false,
  "auth_method": "JWT|OAuth2|None",
  "user_id_available": true/false,
  "meta_includes_user_id": true/false,
  "frontend_tracks_user": true/false,
  "recommendation": "signed_urls|iam",
  "rationale": "..."
}
```

---

### 2. Decisão Go/No-Go

**Critérios de Aprovação:**
- ✅ Caso de uso está claro e documentado
- ✅ User management existe OU esforço de implementação é aceitável
- ✅ Decisão IAM vs. Signed URLs foi tomada
- ✅ Stakeholder aprovou TTL de 180 dias

**Se Go:** Prosseguir para Fase 1 (Auditoria Técnica)

**Se No-Go:** Escalar com documento de bloqueadores:
```markdown
## Bloqueadores para Implementação

1. **User Management Ausente**
   - Sistema atual não rastreia `user_id`
   - Esforço estimado: 2-3 sprints para implementar auth completo
   - Alternativa: usar `session_id` como identificador único (sem multi-user)

2. **Caso de Uso Ambíguo**
   - Não está claro quem vai consumir o endpoint
   - Risco: implementar solução inadequada para o uso real

3. **Decisão de Arquitetura Pendente**
   - IAM vs. Signed URLs não foi decidido
   - Bloqueador: precisa de aprovação de infra/segurança
```

---

### 3. Implementação Proposta (Se Aprovado)

```markdown
## Roadmap de Implementação

### Sprint 1: Fundação
- [ ] Implementar lifecycle policy GCS (180 dias)
- [ ] Adicionar `user_id` ao `meta.json` (se não existir)
- [ ] Criar `app/services/storybrand_access.py` com helper de signed URLs
- [ ] Testes unitários de geração de URL

### Sprint 2: API Endpoint
- [ ] Implementar `GET /storybrand/sections/{session_id}`
- [ ] Validação de ownership
- [ ] Rate limiting
- [ ] Testes de integração

### Sprint 3: Segurança & Observabilidade
- [ ] Audit logging estruturado
- [ ] Sanitização de paths
- [ ] Monitoramento de custos GCS
- [ ] Testes de segurança

### Sprint 4: Documentação & Rollout
- [ ] Atualizar README.md, AGENTS.md
- [ ] Criar playbook de troubleshooting
- [ ] Deploy staging + testes E2E
- [ ] Deploy produção com feature flag
```

---

## 📚 Referências

### Arquivos Relevantes
- `app/agents/storybrand_fallback.py:280-350` - `PersistStorybrandSectionsAgent`
- `app/callbacks/persist_outputs.py:48-68` - Geração de `meta.json`
- `app/.env` - Flags de configuração
- `AGENTS.md:63-68` - Documentação de persistência StoryBrand

### Documentação Externa
- [GCS Signed URLs](https://cloud.google.com/storage/docs/access-control/signed-urls)
- [GCS Lifecycle Management](https://cloud.google.com/storage/docs/lifecycle)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

### Decisões Pendentes
| Decisão | Status | Owner | Deadline |
|---------|--------|-------|----------|
| IAM vs. Signed URLs | ✅ Signed URLs (provisório) | Tech Lead | - |
| TTL de 180 dias | 🟡 Proposto | DevOps | - |
| Caso de uso primário | 🔴 Pendente | Product | - |
| User management | 🟡 Em investigação | Backend | - |

---

## 🔄 Changelog

| Data | Versão | Mudança |
|------|--------|---------|
| 2025-10-12 | 1.0 | Plano inicial + análise de gaps |

---

**Próxima Revisão:** Após completar investigação preliminar (Seção 9.1)
