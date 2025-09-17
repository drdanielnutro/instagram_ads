# Plano de Autenticação e Controle de Acesso (Frontend + Backend)

## Objetivo

Definir uma estratégia prática e segura para autenticar usuários no frontend e autorizar o acesso às funcionalidades (geração de anúncios, download dos JSONs). O plano cobre dois caminhos:
- Caminho rápido para testes (dev): autenticação simples com usuário/senha ou allowlist local (apenas para testes controlados).
- Caminho recomendado para produção: Login com Google (OIDC) usando Firebase Authentication (ou Google Identity Services), com verificação de ID Token no backend e allowlist por e‑mail.

Nota: Este plano não substitui o fluxo de geração já implementado. Ele adiciona uma “porta” de autenticação e política de autorização por usuário.

---

## Requisitos e Decisões

- Cada usuário autenticado deve ter um identificador estável (userId), idealmente derivado do e‑mail verificado (ex.: `uid` do Firebase Auth).
- Sessão de geração permanece por `sessionId` (UUID). Hoje o frontend já cria `sessionId` via `uuidv4()` — portanto: SIM, o `sessionId` já é diferente e variável a cada execução.
- Permissões mínimas: todos os usuários autenticados podem usar; opcionalmente, introduzir uma lista de e‑mails permitidos (allowlist) para fase “usuários selecionados”.
- Download dos arquivos:
  - Dev: stream local com checagem de login.
  - Prod: Signed URL (tempo curto) para objetos no GCS, emitida apenas para usuários autenticados/autorizados.

---

## Opção A (Dev/Prototipagem): Usuário/Senha ou Allowlist Local

Quando usar: para testar rapidamente múltiplos usuários ao mesmo tempo, sem configurar provedores externos.

- Armazenamento de credenciais (apenas testes):
  - Arquivo `auth.users.json` (não versionado):
    ```json
    {
      "users": [
        { "email": "alice@example.com", "password_hash": "$2b$12$..." , "roles": ["user"] },
        { "email": "admin@example.com", "password_hash": "$2b$12$...", "roles": ["admin"] }
      ],
      "allowlist": ["alice@example.com", "admin@example.com"]
    }
    ```
  - Hash de senha com bcrypt (nunca guardar senha em texto). Para DEV, pode gerar com CLI python/bcrypt.
- Fluxo:
  1) Frontend exibe página de Login (rota `/login`).
  2) Envia email+senha para endpoint `/auth/login` → backend valida hash + allowlist e retorna um `session_token` (JWT assinado pela app) e `userId`.
  3) Frontend guarda o token em memória (ou `localStorage` se necessário) e inclui `Authorization: Bearer <token>` em todas as chamadas.
  4) Backend (FastAPI): middleware que valida o token nos endpoints sensíveis (`/run`, `/run_sse`, `/sessions/...`, `/final_delivery/...`).
- Vantagens: simples para validar cenários multiusuário.
- Desvantagens: não escalável, sem 2FA, exige gestão de senha (mesmo com hash). Não recomendado para produção.

---

## Opção B (Recomendada Prod): Login com Google (Firebase Auth)

Quando usar: produção/estágio com SSO Google; reduz gestão de senha e facilita allowlist por e‑mail.

- Passos (Console do Firebase):
  1) Criar projeto no Firebase (pode usar o mesmo projeto GCP).
  2) Habilitar método de login “Google” (e opcionalmente “E‑mail/Senha” se quiser fallback).
  3) Obter credenciais Web (config `apiKey`, `authDomain`, `projectId` etc.).
- Frontend:
  - Instalar SDK Firebase Web: `npm i firebase`
  - Inicializar o Firebase Auth no app e expor botões de “Sign in with Google”.
  - Após login, obter o ID Token do Firebase (`user.getIdToken()`), anexar em `Authorization: Bearer <ID_TOKEN>` a cada requisição.
- Backend:
  - Verificar ID Token com Firebase Admin SDK (ou `google-auth`): valida emissor, assinatura e expiração; extrair `email`/`uid`.
  - Aplicar allowlist por e‑mail: checar se `email` ∈ `ALLOWLIST_EMAILS` (env) ou persistido em Firestore.
  - Associar `userId` = `uid` (ou e‑mail) no state/sessões.
- Vantagens: sem senha local, robusto, fácil permitir/desabilitar e‑mails.
- Desvantagens: requer setup inicial; demanda verificação de token no backend.

### Alternativa: Google Identity Services (GIS) One‑Tap
- Similar ao Firebase Auth, mas sem o restante do ecossistema Firebase. Ainda exige verificação de JWT no backend (biblioteca `google-auth`), client_id e configuração Oauth.

---

## Controle de Acesso (Allowlist e Papéis)

- Allowlist (usuários selecionados):
  - Fase inicial: variáveis de ambiente `ALLOWLIST_EMAILS="alice@example.com,bob@acme.com"`.
  - Fase seguinte: persistir em Firestore (`allowlist` por documento), com endpoint admin para CRUD.
- Papéis (opcional): `user` e `admin`.
  - `admin` acessa página `/admin/users` para editar allowlist; operações logadas.
- Persistência:
  - DEV: arquivo `auth.users.json` e/ou env `ALLOWLIST_EMAILS`.
  - PROD: Firestore/Datastore (recomendado) + cache em memória (TTL curto).

---

## Fluxo de Login/Autorização (Recomendado)

1) Usuário acessa `/login` e autentica (Google/Firebase). Recebe `ID_TOKEN`.
2) Frontend salva `ID_TOKEN` e redireciona para `/app`.
3) Toda chamada ao backend inclui `Authorization: Bearer <ID_TOKEN>`.
4) Backend verifica o token: rejeita `401` se inválido/expirado.
5) Backend aplica allowlist por e‑mail (fase “usuários selecionados”). Se não permitido, `403`.
6) `userId` = `uid` (ou e‑mail). Cada geração cria `sessionId` (UUID) — já ocorre hoje.
7) Download do JSON (
   - DEV: stream local (checar token + allowlist).
   - PROD: gerar Signed URL GET (curta duração) para o arquivo do GCS; retornar redirect.
)

---

## Páginas/Componentes Frontend (proposta)

- `LoginPage` (`/login`): botão “Entrar com Google”.
- `AuthContext`: guarda estado (isAuthenticated, user, idToken), fornece `logout()`.
- `ProtectedRoute`: redireciona para `/login` se não autenticado.
- `AdminUsersPage` (`/admin/users`) (fase 2): permite adicionar/remover e‑mails permitidos (persistência em Firestore); apenas `admin`.
- Integração nas chamadas:
  - `createSession`, `/run_sse`, `/run_preflight`, `/final_delivery/*` enviam `Authorization: Bearer <ID_TOKEN>`.

---

## Backend (proposta)

- Middleware de Auth (FastAPI):
  - Verifica `Authorization: Bearer <token>`.
  - Se Firebase: usar Admin SDK para verificar assinatura e emitir claims (uid, email, exp). Cache leve de 5 min para reduzir chamadas.
  - Se Dev (senha/usuário): validar JWT da app (curta duração) assinado com `APP_JWT_SECRET`.
- Allowlist:
  - DEV: `ALLOWLIST_EMAILS` (env) ou `auth.users.json`.
  - PROD: Firestore (coleção `allowlist`, doc por e‑mail).
- Autorização nos endpoints sensíveis:
  - `/run`, `/run_sse`, `/apps/.../sessions/...`, `/final_delivery/meta`, `/final_delivery/download`.

---

## Perguntas Frequentes

- “Quero testar mais de um usuário ao mesmo tempo; faz sentido?”
  - Sim. Com Opção A (dev), crie 2–3 usuários no `auth.users.json` (hash) e logue em abas diferentes. Com Opção B (Firebase), permita 2–3 e‑mails na allowlist.
- “Quem tem acesso?”
  - Fase ‘usuários selecionados’: somente e‑mails na allowlist (verificados pelo IdP). Em dev, use `ALLOWLIST_EMAILS` ou arquivo local.
- “Onde armazenar a lista?”
  - Dev: arquivo local/ENV. Prod: Firestore (recomendado; logs de auditoria e IAM do projeto).
- “Mesmo usuário, sessões distintas?”
  - Sim. `sessionId` já é gerado via UUID no frontend a cada criação de sessão.

---

## Validações e Comandos (GCP)

- Firebase Auth (console):
  - Habilitar provedor Google; copiar o config Web do app (apiKey, authDomain…).
- IAM/Service Accounts (se for verificar tokens no backend com Admin SDK):
  - Habilitar `iamcredentials.googleapis.com`:
    ```bash
    gcloud services enable iamcredentials.googleapis.com
    ```
  - Configurar variáveis (backend) para apontar a credencial (ADC) correta.

---

## Roteiro de Implementação (incremental)

1) Dev rápido (opcional):
   - Adicionar `/login` simples e endpoint `/auth/login` (usuário/senha com hash)
   - Guardar JWT no frontend e validar nos endpoints sensíveis.
2) Produção recomendada:
   - Integrar Firebase Auth no frontend; obter ID Token e enviar nas requisições.
   - Backend: verificar ID Token; adicionar allowlist por e‑mail.
   - Proteger endpoints sensíveis.
3) Admin (fase 2):
   - `/admin/users`: CRUD de allowlist (Firestore) e visualização de logs de acesso.

---

## Conclusão

- Para dev/testing: a autenticação simples atende múltiplos usuários rapidamente, sem bloquear o plano de refatoração.
- Para produção: usar Login com Google (Firebase Auth) é a via mais segura e prática, com verificação de ID Token no backend e allowlist por e‑mail.
- O `sessionId` já é variável por sessão; após autenticação, passe a usar `userId` real (do IdP) em vez de `u_999`.

