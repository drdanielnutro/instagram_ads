# Professor Virtual - Contexto do Projeto

> **Última atualização**: 08 de Agosto de 2025  
> **Versão**: 3.0 - Documentação completa com deployment em produção

## Links Rápidos
- [Como Testar o Sistema](#como-testar-o-sistema-completo)
- [Estrutura de Requisições](#estrutura-de-requisições-adk)
- [Troubleshooting](#troubleshooting---problemas-comuns)
- [Configuração GCS](#configuração-do-google-cloud-storage)
- [Deployment em Produção](#deployment-em-produção-cloud-run)

## Visão Geral

Sistema educacional que utiliza IA para criar experiências de aprendizado personalizadas. O professor virtual interage com alunos através de texto, voz e imagem, adaptando suas respostas ao contexto e necessidades individuais de cada estudante.

## Arquitetura e Decisões Técnicas

### Google ADK - Conceitos Fundamentais

O Google Assistant Development Kit (ADK) é um framework para construir agents de IA. Diferente de APIs REST tradicionais, o ADK gerencia automaticamente:

- **Artifacts**: Dados gerados pelo agent durante execução (transcrições, análises, áudios sintetizados). São versionados e vinculados à sessão do usuário.
- **Tools**: Funções assíncronas que o agent pode invocar para realizar tarefas específicas.
- **Sessões**: Contexto persistente entre interações com o mesmo usuário.

### Processamento de Arquivos no ADK

O ADK possui dois modos de operação que afetam como arquivos são processados:

1. **Modo Developer (API Key)**:
   - Não suporta URIs do GCS (`gs://...`) diretamente
   - Requer upload de arquivos via Files API ou envio inline
   - Mais simples para desenvolvimento local

2. **Modo Vertex AI (OAuth)**:
   - Ativado com `GOOGLE_GENAI_USE_VERTEXAI=TRUE`
   - Suporta URIs do GCS nativamente via `Part.from_uri()`
   - O Gemini acessa arquivos diretamente do storage sem download
   - Essencial para produção com arquivos grandes

### Decisões Arquiteturais do Projeto

1. **Uso Exclusivo de Gemini Multimodal**:
   - TODAS as análises (texto, imagem, áudio) usam Gemini
   - NÃO usa APIs separadas (Vision API, Speech-to-Text, etc.)
   - Garante consistência e reduz complexidade

2. **Arquitetura de Referências**:
   - Arquivos enviados permanecem no GCS
   - Tools recebem URIs, não fazem download
   - Artifacts são criados apenas para dados NOVOS gerados

3. **Servidor Híbrido para Uploads**:
   - ADK não expõe endpoints de upload nativos
   - Solução: FastAPI + ADK no mesmo servidor
   - Frontend obtém Signed URLs para upload direto ao GCS

4. **Deployment em Produção**:
   - Container Docker otimizado com multi-stage build
   - Cloud Run para auto-scaling e alta disponibilidade
   - Separação clara entre configurações dev/prod
   - Autenticação flexível (token fixo ou Google Identity JWT)
   
   **Implementação do Servidor Híbrido**:
   - **Arquivo principal**: `professor-virtual/professor_virtual/hybrid_server.py`
     - Combina ADK Runner com FastAPI customizado usando `get_fast_api_app()`
     - Expõe endpoint `/api/custom/get-upload-url` para gerar Signed URLs
     - Usa modelo Pydantic `UploadRequest` para validação de dados
     - Configura cliente GCS com Service Account explicitamente
     - Valida existência de `sa-key.json` antes de iniciar
     - Configura autenticação OAuth2 com suporte real a Google Identity JWT
     - Em desenvolvimento usa token fixo, em produção pode usar JWT
     - Integra com Google Cloud Storage para uploads diretos
   
   - **Script de execução**: `professor-virtual/run_hybrid.py`
     - Ponto de entrada para iniciar o servidor híbrido
     - Configura uvicorn na porta 8000 com hot-reload
     - Adiciona path correto para importar módulos do projeto
     - Razão de existir: Separar configuração de execução da lógica do servidor
     - Detecção automática de ambiente (produção desativa reload)
     - Todas as configurações vêm do módulo config.py centralizado

### O que é o hybrid_server.py?

O `hybrid_server.py` é um **servidor híbrido** que combina duas tecnologias:

1. **Google ADK Runner**: Framework do Google para executar agents de IA
2. **FastAPI customizado**: Endpoints adicionais para funcionalidades que o ADK não oferece nativamente

#### Por que precisamos de um servidor híbrido?

O ADK Runner sozinho **não expõe endpoints para upload de arquivos**. Ele apenas tem endpoints para:
- `/run` - Executar o agent com mensagens (endpoint principal)
- `/run_sse` - Executar com Server-Sent Events (streaming)
- `/status` - Verificar status do agent
- `/apps/{app_name}/users/{user_id}/sessions` - Gerenciar sessões

Mas o sistema precisa permitir que usuários façam upload de arquivos (imagens, áudios). A solução foi criar um servidor híbrido que:
- Mantém todos os endpoints do ADK funcionando normalmente
- Adiciona endpoints customizados para gerar URLs de upload

**🚀 IMPORTANTE**: Quando você executa `poetry run python run_hybrid.py`, você está rodando:
- ✅ O agent Professor Virtual completo (definido em `agent.py`)
- ✅ Todos os endpoints padrão do ADK (`/run`, `/run_sse`, etc.)
- ✅ Os endpoints customizados (`/api/custom/get-upload-url`)
- ✅ **Tudo em um único processo!**

Não é necessário rodar o agent separadamente - o servidor híbrido É o sistema completo.

### Como funciona o sistema de uploads?

#### 1. **Servidor que hospeda os arquivos: Google Cloud Storage (GCS)**

Os arquivos **NÃO são hospedados no servidor Python**. Eles vão direto para o Google Cloud Storage:

- **Bucket**: `professor-virtual-uploads-467918`
- **Região**: `southamerica-east1` (São Paulo)
- **Estrutura**: `{user_id}/{session_id}/{filename}`

#### 2. **Fluxo de Upload com Signed URLs**

O `hybrid_server.py` implementa o endpoint `/api/custom/get-upload-url` que:

1. **Recebe do frontend**:
   ```json
   {
     "filename": "exercicio.jpg",
     "user_id": "user123", 
     "session_id": "session456",
     "mime_type": "image/jpeg"
   }
   ```

2. **Gera uma Signed URL** (linha 86-95):
   - URL temporária válida por 15 minutos
   - Permite PUT direto no GCS
   - Adiciona metadados (user_id, session_id)

3. **Retorna para o frontend**:
   ```json
   {
     "upload_url": "https://storage.googleapis.com/...",
     "gcs_uri": "gs://professor-virtual-uploads-467918/user123/session456/exercicio.jpg",
     "expires_in": 900
   }
   ```

4. **Frontend faz upload DIRETO para o GCS** (não passa pelo servidor Python)

#### 3. **Configurações Atuais do Servidor**

**Autenticação GCS** (linhas 12-32):
- Usa Service Account com arquivo `sa-key.json`
- Procura primeiro em `GOOGLE_APPLICATION_CREDENTIALS`
- Se não encontrar, usa `./sa-key.json` como padrão

**Segurança** (linhas 43-55):
- OAuth2 com Bearer Token
- Desenvolvimento: Token fixo configurado em AUTH_TOKEN
- Produção: Suporte a Google Identity JWT real
- Validação de filename contra path traversal
- Sanitização de nomes de arquivo

**Configuração do ADK** (linhas 35-40):
- `agents_dir="./"` - Procura agents no diretório atual
- `session_service_uri="sqlite:///sessions.db"` - Sessões em SQLite
- `allow_origins` - Configurável via ALLOWED_ORIGINS (vírgula-separado)
- `web=False` - Evita conflitos com rotas customizadas

#### 4. **Variáveis de Ambiente Relevantes**

Do arquivo `.env.production.example`:
- `UPLOAD_BUCKET`: Bucket para uploads de usuários (padrão: `professor-virtual-uploads-467918`)
- `ARTIFACTS_BUCKET`: Bucket para artifacts do ADK (padrão: `adk-professor-virtual-artifacts`)
- `GOOGLE_APPLICATION_CREDENTIALS`: Caminho para service account (`./sa-key.json`)
- `GOOGLE_GENAI_USE_VERTEXAI`: Deve ser TRUE para processar arquivos do GCS
- `IS_PRODUCTION`: Define se usa GCS para artifacts (True) ou memória (False)
- `PYTHON_ENV`: Define ambiente (production/development)
- `AUTH_TOKEN`: Token para autenticação básica
- `ALLOWED_ORIGINS`: Domínios permitidos para CORS (vírgula-separado)
- `USE_OIDC`: Habilita autenticação via Google Identity JWT
- `GOOGLE_IDENTITY_CLIENT_ID`: Client ID para OAuth2 (se USE_OIDC=True)

## Backend: Python com Google ADK

- **Framework**: ADK Runner com processamento assíncrono
- **Modelo de IA**: Gemini Pro/Flash (multimodal)
- **Armazenamento - DOIS Buckets GCS**: 
  
  1. **Bucket de Uploads** (`professor-virtual-uploads-467918`):
     - Recebe arquivos enviados pelos usuários (imagens, áudios)
     - Configurado via `UPLOAD_BUCKET` no `.env`
     - Estrutura: `{user_id}/{session_id}/{filename}`
     - Acessado via Signed URLs geradas pelo servidor
  
  2. **Bucket de Artifacts** (`adk-professor-virtual-artifacts`):
     - Armazena dados GERADOS pelo agent (transcrições, análises, sínteses)
     - Configurado via `ARTIFACTS_BUCKET` no `.env`
     - Gerenciado automaticamente pelo ADK
     - Usado quando `IS_PRODUCTION=True` ou modo Vertex AI
  
  - **Desenvolvimento**: InMemory (artifacts em memória, sem GCS)
  - **Produção**: Ambos os buckets ativos

- **Configuração Crítica**: `GOOGLE_GENAI_USE_VERTEXAI=TRUE` permite que o Gemini processe arquivos diretamente do GCS usando URIs `gs://`

**⚠️ IMPORTANTE**: Ambos os buckets devem ser criados seguindo o guia em `docs/CONFIGURACAO_GCS_BUCKETS.md`

## Frontend: Flutter (Mobile/Web)

- **Comunicação**: HTTP REST com backend ADK
- **Capacidades**: Gravação de áudio, captura de imagem, reprodução de mídia
- **UI Dinâmica**: Respostas do backend modificam interface em tempo real

## Estrutura do Código

### Diretório Raiz (professor-virtual/)
- **professor_virtual/**: Módulo principal do agent educacional
- **deployment/**: Scripts para deploy em produção
- **eval/**: Testes de avaliação do comportamento do agent
- **tests/**: Testes unitários
- **pyproject.toml**: Configuração e dependências Python

### Módulo Principal (professor_virtual/)
- **agent.py**: Lógica central - coordena interações e decisões
- **config.py**: Configurações centralizadas usando Pydantic (credenciais, parâmetros, buckets)
- **hybrid_server.py**: Servidor híbrido ADK + FastAPI para uploads
- **prompts/**: Sistema de prompts dinâmicos que se adaptam ao contexto
- **entities/**: Modelos de dados (Student, Lesson, etc.)
- **shared_libraries/**: Código compartilhado entre componentes

**⚠️ IMPORTANTE**: O nome do app nas requisições é `professor_virtual` (sem "_app"). 
Embora `config.py` defina `app_name = "professor_virtual_app"`, o ADK registra o agent usando o nome do diretório.

## Ferramentas Implementadas (tools/)

### 1. transcrever_audio/
**Como funciona**: Recebe nome de artifact OU URI do GCS (gs://...) e usa Gemini multimodal para converter fala em texto. Detecta automaticamente o tipo de entrada:
- Se começar com "gs://": usa Part.from_uri() (requer GOOGLE_GENAI_USE_VERTEXAI=TRUE)
- Caso contrário: busca artifact pelo nome

**Por que Gemini**: Mantém contexto da conversa e entende nuances educacionais melhor que APIs de transcrição genéricas.

### 2. analisar_necessidade_visual/
**Como funciona**: Analisa o contexto da conversa e determina se a resposta seria melhor com apoio visual (diagrama, gráfico, etc.).

**Decisão de design**: Ferramenta separada para permitir que o agent decida proativamente quando elementos visuais agregam valor pedagógico.

### 3. analisar_imagem_educacional/
**Como funciona**: Usa capacidades de visão do Gemini para analisar imagens. Aceita:
- Nome de artifact: busca imagem salva anteriormente
- URI do GCS (gs://...): acessa diretamente do storage (requer GOOGLE_GENAI_USE_VERTEXAI=TRUE)

**Diferencial**: Não apenas identifica conteúdo, mas fornece feedback pedagógico contextualizado. Não usa Vision API.

### 4. gerar_audio_tts/
**Como funciona**: Converte respostas textuais em áudio sintetizado para alunos com preferência auditiva ou dificuldades de leitura.

**Implementação**: Usa Google TTS quando Gemini Audio ainda não está disponível, mas migração planejada para manter tudo no ecossistema Gemini.

### 5. upload_arquivo/
**Status atual**: DEPRECATED. A tool agora retorna erro informativo direcionando para o novo fluxo.

**Razão**: Viola o princípio de que "arquivos enviados já estão no destino final" ao criar artifacts desnecessários.

**Novo fluxo**: Usar Signed URLs conforme documentado em "Como o Sistema Processa Uploads".

## Como o Sistema Processa Uploads

1. **Frontend solicita URL de upload**:
   ```python
   POST /api/custom/get-upload-url
   Authorization: Bearer test_token
   Content-Type: application/json
   
   {
     "filename": "exercicio.jpg",
     "user_id": "user123",
     "session_id": "session456",
     "mime_type": "image/jpeg"
   }
   ```

2. **Backend retorna Signed URL**:
   ```json
   {
     "upload_url": "https://storage.googleapis.com/...",
     "gcs_uri": "gs://professor-virtual-uploads-467918/user123/exercicio.jpg"
   }
   ```

3. **Frontend faz upload direto para GCS** (não passa pelo servidor)

4. **Frontend invoca agent com URI**:
   ```json
   POST /run
   {
     "appName": "professor_virtual",
     "userId": "user123",
     "sessionId": "uuid-da-sessao-atual",
     "newMessage": {
       "parts": [{
         "text": "Analise meu exercício",
         "fileData": {
           "fileUri": "gs://professor-virtual-uploads-467918/user123/exercicio.jpg"
         }
       }]
     }
   }
   ```

5. **Tool processa usando Part.from_uri()**:
   ```python
   # Com GOOGLE_GENAI_USE_VERTEXAI=TRUE
   image_part = Part.from_uri(
       file_uri=gcs_uri,
       mime_type="image/jpeg"
   )
   # Gemini acessa direto do GCS, sem download!
   ```

## Processamento de Arquivos pelas Tools

As tools `transcrever_audio` e `analisar_imagem_educacional` agora suportam dois modos:

### Modo Artifact (compatibilidade)
- Recebem nome do artifact como string
- Buscam arquivo previamente salvo
- Funcionam em ambos os modos (Developer/Vertex AI)

### Modo GCS URI (recomendado para produção)
- Recebem URI direto: `gs://bucket/path/file.ext`
- Requer `GOOGLE_GENAI_USE_VERTEXAI=TRUE`
- Gemini acessa arquivo diretamente, sem download
- Melhor performance e escalabilidade

**Detecção automática**: As tools verificam se o parâmetro começa com "gs://" para escolher o modo apropriado.

## Princípios de Design

1. **Multimodal First**: Toda interação pode combinar texto, áudio e imagem
2. **Contexto Pedagógico**: Respostas consideram nível do aluno e objetivo educacional
3. **Eficiência**: Arquivos processados por referência, não cópia
4. **Unificação**: Um modelo (Gemini) para todas as modalidades

## Configuração para Desenvolvimento

### Modo Developer (Desenvolvimento Local Simples)
```bash
# .env para desenvolvimento básico
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=sua-api-key-aqui
IS_PRODUCTION=False
```
**Quando usar**: Testes de conversação, desenvolvimento de prompts, lógica do agent.
**Limitações**: Não suporta upload de arquivos via gs://.

### Modo Vertex AI (Desenvolvimento com Uploads)
```bash
# .env para desenvolvimento completo
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=professor-virtual-467918
GOOGLE_CLOUD_LOCATION=southamerica-east1
GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json
UPLOAD_BUCKET=professor-virtual-uploads-467918
ARTIFACTS_BUCKET=adk-professor-virtual-artifacts
IS_PRODUCTION=False
```
**Quando usar**: Testar uploads de imagem/áudio, integração com frontend, fluxo completo.
**Vantagem**: Ambiente idêntico à produção.

### Como Alternar Entre Modos
1. Para modo simples: Mude `GOOGLE_GENAI_USE_VERTEXAI` para `FALSE`
2. Para modo completo: Mude para `TRUE` (GOOGLE_APPLICATION_CREDENTIALS já está configurado)
3. Reinicie o servidor: `poetry run python run_hybrid.py`

O modo de produção é essencial para processar arquivos grandes eficientemente, pois o Gemini acessa diretamente do GCS sem precisar baixar para o servidor.

## Configuração do Google Cloud Storage

### Informações do Projeto
- **Project ID**: `professor-virtual-467918`
- **Bucket Name**: `professor-virtual-uploads-467918`
- **Região**: `southamerica-east1` (São Paulo)
- **Service Account**: `professor-virtual-sa@professor-virtual-467918.iam.gserviceaccount.com`
- **Arquivo de Credenciais**: `sa-key.json` (não commitado no Git)

### Estrutura do Bucket
```
professor-virtual-uploads-467918/
├── user_id/
│   └── session_id/
│       ├── audio_file.wav
│       └── image_file.jpg
```

### CORS Configuration
O bucket está configurado para aceitar uploads diretos do navegador:
- **Origins permitidas**: `http://localhost:*`, domínio de produção
- **Métodos**: PUT, GET
- **Headers**: Content-Type, x-goog-*

### Setup Inicial do GCS (Passo a Passo)

#### 1. Instalar gcloud CLI
```bash
# macOS
brew install --cask google-cloud-sdk

# Linux/Windows
curl https://sdk.cloud.google.com | bash
```

#### 2. Configurar Projeto e Autenticar
```bash
gcloud config set project professor-virtual-467918
gcloud auth login
```

#### 3. Criar Bucket
```bash
gsutil mb -p professor-virtual-467918 -c STANDARD -l southamerica-east1 gs://professor-virtual-uploads-467918
```

#### 4. Configurar CORS
```bash
# Criar arquivo cors.json
cat > cors.json << 'EOF'
[
  {
    "origin": ["http://localhost:*", "https://seu-dominio.com"],
    "method": ["PUT", "GET"],
    "responseHeader": ["Content-Type", "x-goog-*"],
    "maxAgeSeconds": 3600
  }
]
EOF

# Aplicar ao bucket
gsutil cors set cors.json gs://professor-virtual-uploads-467918
```

#### 5. Criar Service Account
```bash
# Criar conta
gcloud iam service-accounts create professor-virtual-sa \
    --display-name="Professor Virtual Service Account"

# Conceder permissões
gcloud projects add-iam-policy-binding professor-virtual-467918 \
    --member="serviceAccount:professor-virtual-sa@professor-virtual-467918.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Gerar chave
gcloud iam service-accounts keys create sa-key.json \
    --iam-account=professor-virtual-sa@professor-virtual-467918.iam.gserviceaccount.com
```

#### 6. Proteger Credenciais
```bash
# Adicionar ao .gitignore
echo "sa-key.json" >> .gitignore
```

### Segurança
- **Nunca commite** o arquivo `sa-key.json`
- Use `roles/storage.objectCreator` em vez de `objectAdmin` para maior segurança
- Configure lifecycle policies para deletar arquivos antigos automaticamente

## Execução do Sistema

### Servidor Híbrido (Desenvolvimento)
Para executar o servidor que combina ADK com endpoints customizados:

```bash
cd professor-virtual
poetry run python run_hybrid.py
```

Isso inicia:
- ADK Runner nas rotas padrão (`/run`, `/run_sse`, `/list-apps`, etc.)
- FastAPI endpoints customizados em `/api/custom/*`
- Servidor uvicorn na porta 8000 com auto-reload

**Por que dois arquivos?**
- `hybrid_server.py`: Contém toda a lógica de configuração e roteamento
- `run_hybrid.py`: Script simples apenas para execução, facilitando desenvolvimento e testes

## Deployment em Produção (Cloud Run)

### Visão Geral
O sistema está preparado para deployment no Google Cloud Run com arquitetura otimizada para produção.

### Arquivos de Deployment
- **Dockerfile**: Build multi-stage otimizado com Poetry
- **.dockerignore**: Exclui arquivos desnecessários da imagem
- **.env.production.example**: Template com todas as variáveis necessárias
- **deployment/deploy.sh**: Script automatizado de deploy
- **deployment/rollback.sh**: Script para reverter versões

### Processo de Deploy
1. **Preparação**:
   ```bash
   cp .env.production.example .env.production
   # Editar .env.production com valores reais
   ```

2. **Deploy**:
   ```bash
   cd professor-virtual
   chmod +x deployment/deploy.sh
   ./deployment/deploy.sh
   ```

3. **Rollback** (se necessário):
   ```bash
   cd professor-virtual/deployment
   chmod +x rollback.sh
   ./rollback.sh
   ```

### Configurações de Produção
- **Servidor**: Gunicorn com 4 workers Uvicorn
- **Memória**: 2GB RAM
- **CPU**: 2 vCPUs
- **Timeout**: 300 segundos
- **Auto-scaling**: 0-10 instâncias
- **Região**: southamerica-east1 (São Paulo)

### Autenticação em Produção
O sistema suporta dois modos de autenticação:

1. **Token Fixo** (APIs internas):
   - Configurar `AUTH_TOKEN` no `.env.production`
   - Header: `Authorization: Bearer seu-token-aqui`

2. **Google Identity JWT** (usuários finais):
   - Configurar `USE_OIDC=True`
   - Configurar `GOOGLE_IDENTITY_CLIENT_ID`
   - Frontend deve implementar fluxo OAuth2

### Diferenças Dev vs Prod
| Aspecto | Desenvolvimento | Produção |
|---------|----------------|-----------|
| Reload | Automático | Desativado |
| CORS | Aberto (*) | Domínios específicos |
| Servidor | Uvicorn único | Gunicorn + workers |
| Artifacts | Memória | GCS |
| Logs | Console | Cloud Logging |

## Como Testar o Sistema Completo

### Conceitos Fundamentais

#### Sessões no ADK
- **O que são**: Contextos persistentes que mantêm o histórico de conversas entre usuário e agent
- **Onde são criadas**: SEMPRE pelo frontend (ou cliente da API) antes de iniciar uma conversa
- **Por quê**: 
  - Permite múltiplas conversas simultâneas e isoladas
  - Mantém contexto entre mensagens
  - Gerencia estado da conversa (perfil do aluno, histórico, etc.)
- **Duração**: Persistem entre requisições até serem explicitamente deletadas
- **Identificação**: Cada sessão tem um UUID único

#### Estrutura de Comunicação ADK
O ADK usa uma estrutura específica para mensagens baseada no formato do Gemini:
- Mensagens são compostas de **"parts"** (partes)
- Cada part pode ter diferentes tipos: `text`, `fileData`, etc.
- `role` define quem está falando (`user` ou `model`)
- Suporta multimodalidade (texto + imagem/áudio na mesma mensagem)

### Passo a Passo para Testar

#### 1. Iniciar o Servidor
```bash
cd professor-virtual
poetry run python run_hybrid.py
```

Aguarde a mensagem de inicialização. O servidor estará disponível em `http://localhost:8000`

#### 2. Verificar Endpoints Disponíveis
```bash
# Documentação interativa (Swagger UI)
open http://localhost:8000/docs

# Listar apps disponíveis
curl http://localhost:8000/list-apps
# Resposta esperada: ["deployment", "docs", "eval", "professor_virtual", "tests"]
```

#### 3. Criar uma Sessão (OBRIGATÓRIO)
**Importante**: Toda conversa precisa de uma sessão. O frontend deve criar uma ao iniciar.

```bash
# Criar nova sessão
curl -X POST "http://localhost:8000/apps/professor_virtual/users/USER_ID/sessions" \
  -H "Content-Type: application/json" \
  -d '{}'

# Resposta incluirá o session_id (UUID)
# Exemplo: {"id":"8855a9c0-196a-4bb7-8434-276be57425c9", ...}
```

**Guarde o `id` retornado - você precisará dele para todas as próximas requisições!**

#### 4. Conversar com o Agent
```bash
# Substitua SESSION_ID pelo ID retornado no passo anterior
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "professor_virtual",
    "userId": "USER_ID",
    "sessionId": "SESSION_ID",
    "newMessage": {
      "parts": [{
        "text": "Olá professor, pode me ajudar com frações?"
      }]
    }
  }'
```

**Estrutura da Resposta**: Array de eventos contendo as ações do agent e sua resposta em texto.

### Script de Teste Completo
Crie um arquivo `test_professor.sh`:

```bash
#!/bin/bash

# 1. Criar sessão
echo "Criando nova sessão..."
SESSION_RESPONSE=$(curl -s -X POST "http://localhost:8000/apps/professor_virtual/users/aluno123/sessions" \
  -H "Content-Type: application/json" \
  -d '{}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.id')
echo "Sessão criada: $SESSION_ID"

# 2. Enviar mensagem
echo -e "\nEnviando mensagem..."
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d "{
    \"appName\": \"professor_virtual\",
    \"userId\": \"aluno123\",
    \"sessionId\": \"$SESSION_ID\",
    \"newMessage\": {
      \"parts\": [{
        \"text\": \"Me explique o que são frações\"
      }]
    }
  }" | jq '.[].content.parts[0].text' 2>/dev/null
```

### Fluxo de Integração Frontend

#### 1. Inicialização (ao abrir o app)
```javascript
// Frontend cria sessão ao iniciar
async function iniciarConversa(userId) {
  const response = await fetch(
    `http://localhost:8000/apps/professor_virtual/users/${userId}/sessions`,
    { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' }
  );
  const session = await response.json();
  return session.id; // Guardar para usar nas mensagens
}
```

#### 2. Enviar Mensagem
```javascript
async function enviarMensagem(userId, sessionId, texto) {
  const response = await fetch('http://localhost:8000/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      appName: 'professor_virtual',
      userId: userId,
      sessionId: sessionId,
      newMessage: {
        parts: [{ text: texto }]
      }
    })
  });
  return await response.json();
}
```

#### 3. Finalização (opcional)
```javascript
// Deletar sessão ao fechar
async function finalizarConversa(userId, sessionId) {
  await fetch(
    `http://localhost:8000/apps/professor_virtual/users/${userId}/sessions/${sessionId}`,
    { method: 'DELETE' }
  );
}
```

### Testando com Arquivos (Upload + Análise)

#### 1. Obter URL para Upload
```bash
curl -X POST http://localhost:8000/api/custom/get-upload-url \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "exercicio.jpg",
    "user_id": "aluno123",
    "session_id": "SESSION_ID_ATUAL",
    "mime_type": "image/jpeg"
  }'
```

#### 2. Upload do Arquivo
O frontend deve fazer PUT diretamente na URL retornada (não passa pelo servidor Python).

#### 3. Enviar Arquivo para Análise
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "professor_virtual",
    "userId": "aluno123",
    "sessionId": "SESSION_ID_ATUAL",
    "newMessage": {
      "parts": [{
        "text": "Analise este exercício de matemática",
        "fileData": {
          "fileUri": "gs://professor-virtual-uploads-467918/aluno123/SESSION_ID/exercicio.jpg"
        }
      }]
    }
  }'
```

### Estrutura de Requisições ADK

#### POST /run - Conversação Síncrona
```json
{
  "appName": "professor_virtual",      // Nome do app (sem "_app")
  "userId": "identificador_usuario",   // ID único do usuário
  "sessionId": "uuid-da-sessao",       // Obtido ao criar sessão
  "newMessage": {
    "parts": [{                        // Array de partes da mensagem
      "text": "texto da mensagem",
      "fileData": {                    // Opcional - para arquivos
        "fileUri": "gs://bucket/path/arquivo.ext"
      }
    }],
    "role": "user"                     // Opcional - padrão é "user"
  }
}
```

#### POST /run_sse - Streaming de Respostas
Mesma estrutura do `/run`, mas retorna Server-Sent Events para respostas em tempo real.
Útil para respostas longas ou quando quiser mostrar o texto sendo "digitado".

### Monitoramento e Debug

#### Logs do Servidor
No terminal onde o servidor está rodando, você verá:
- Requisições HTTP recebidas
- Logs de debug do agent
- Erros e exceções
- Tempo de processamento

#### Verificar Sessões Ativas
```bash
# Listar sessões de um usuário
curl "http://localhost:8000/apps/professor_virtual/users/USER_ID/sessions"
```

#### Inspecionar Estado da Sessão
```bash
# Ver detalhes de uma sessão específica
curl "http://localhost:8000/apps/professor_virtual/users/USER_ID/sessions/SESSION_ID"
```

## Troubleshooting - Problemas Comuns

### Erro: "Session not found"
**Causa**: Tentando enviar mensagem sem criar sessão primeiro ou usando session_id inválido.

**Solução**:
1. Sempre crie uma sessão antes de enviar mensagens
2. Verifique se o session_id está correto
3. Confirme que a sessão ainda existe (não foi deletada)

```bash
# Criar nova sessão
curl -X POST "http://localhost:8000/apps/professor_virtual/users/USER_ID/sessions" \
  -H "Content-Type: application/json" -d '{}'
```

### Erro: "App not found"
**Causa**: Usando nome incorreto do app nas requisições.

**Solução**:
- Use `professor_virtual` (sem "_app")
- Verifique apps disponíveis: `curl http://localhost:8000/list-apps`

### Erro: "Invalid message structure" ou "Extra inputs not permitted"
**Causa**: Estrutura incorreta da mensagem no body da requisição.

**Solução - Estrutura correta**:
```json
{
  "appName": "professor_virtual",
  "userId": "user123",
  "sessionId": "uuid-válido",
  "newMessage": {
    "parts": [{
      "text": "sua mensagem"
    }]
  }
}
```

### Erro: "CORS policy" (no browser)
**Causa**: Frontend tentando acessar API de origem diferente.

**Soluções**:
1. **Desenvolvimento**: Configurar `ALLOWED_ORIGINS=*` no `.env`
2. **Produção**: Adicionar domínios específicos:
   ```bash
   ALLOWED_ORIGINS=https://app.exemplo.com,https://www.exemplo.com
   ```
3. **Alternativa**: Usar proxy no frontend development server

### Erro: "Service Account key not found"
**Causa**: Arquivo `sa-key.json` não encontrado ou `GOOGLE_APPLICATION_CREDENTIALS` não configurado.

**Soluções**:
1. Verificar se `sa-key.json` existe no diretório do projeto
2. Configurar no `.env`:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json
   ```
3. Ou exportar como variável de ambiente:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/caminho/completo/sa-key.json
   ```

### Erro: "Extra inputs are not permitted" no config.py
**Causa**: Variável no `.env` que não está definida na classe Config.

**Solução**: Adicionar o campo em `config.py`:
```python
class Config(BaseSettings):
    # ... outros campos ...
    NOME_DA_VARIAVEL: str | None = Field(default=None)
```

### Agent não responde ou resposta vazia
**Causas possíveis**:
1. `GOOGLE_API_KEY` inválida (modo Developer)
2. Credenciais GCP não configuradas (modo Vertex AI)
3. Agent não carregado corretamente

**Debug**:
```bash
# Verificar se agent está carregado
curl http://localhost:8000/list-apps
# Deve incluir "professor_virtual"

# Verificar logs do servidor
# Procure por erros de inicialização
```

### Upload de arquivo falha
**Causa**: Bucket GCS não configurado ou sem permissões.

**Verificações**:
1. Confirmar que bucket existe:
   ```bash
   gsutil ls gs://professor-virtual-uploads-467918
   ```
2. Verificar CORS:
   ```bash
   gsutil cors get gs://professor-virtual-uploads-467918
   ```
3. Testar permissões:
   ```bash
   echo "test" > test.txt
   gsutil cp test.txt gs://professor-virtual-uploads-467918/test.txt
   ```

### "Part.from_uri() failing"
**Causa**: Modo Developer não suporta URIs `gs://`.

**Solução**: Mudar para modo Vertex AI:
```bash
# No .env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=professor-virtual-467918
```

### Servidor não inicia
**Causas comuns**:
1. Porta 8000 já em uso
2. Dependências não instaladas
3. Erro de importação

**Debug**:
```bash
# Verificar porta
lsof -i :8000

# Reinstalar dependências
poetry install

# Testar importação
poetry run python -c "from professor_virtual.hybrid_server import app"
```

### Performance lenta
**Causas**:
1. Modo Developer tem rate limits
2. Arquivos grandes sendo processados
3. Muitas sessões antigas acumuladas

**Otimizações**:
1. Usar modo Vertex AI para produção
2. Limitar tamanho de arquivos
3. Implementar limpeza de sessões antigas

### Erro: "Invalid token" em produção
**Causa**: Token incorreto ou modo de autenticação mal configurado.

**Soluções**:
1. Verificar `AUTH_TOKEN` no `.env.production`
2. Se usando JWT, verificar `USE_OIDC` e `GOOGLE_IDENTITY_CLIENT_ID`
3. Confirmar header Authorization no request

### Deploy falha no Cloud Run
**Causa**: Configuração incorreta ou APIs não habilitadas.

**Verificações**:
1. APIs habilitadas: Cloud Build, Cloud Run, Artifact Registry
2. Variáveis no `.env.production` estão corretas
3. Service Account tem permissões necessárias
4. Dockerfile está na raiz do diretório professor-virtual

## Dicas Gerais de Debug

1. **Sempre verifique os logs do servidor** - A maioria dos erros aparece claramente nos logs
2. **Use o Swagger UI** (`/docs`) para testar endpoints interativamente
3. **Teste incrementalmente** - Primeiro sessão, depois mensagem simples, depois com arquivo
4. **Mantenha o `.env` atualizado** - Muitos problemas vêm de configuração incorreta
5. **Use `curl -v`** para ver headers completos da requisição/resposta