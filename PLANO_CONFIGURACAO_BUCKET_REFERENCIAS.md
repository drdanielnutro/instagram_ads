# 🔧 PLANO: Resolver Erro de Upload de Imagens de Referência

## 📋 RESUMO
Diagnosticar autenticação GCP → Verificar/criar bucket de referências → Configurar permissões → Testar upload

---

## FASE 1: DIAGNÓSTICO DE AUTENTICAÇÃO (5 min)

### 1.1 Verificar arquivo de credenciais
```bash
# Verificar se sa-key.json existe na raiz do projeto
ls -lh ./sa-key.json

# Se não existir: criar nova service account key via Console GCP
```

### 1.2 Verificar autenticação gcloud
```bash
# Ver contas autenticadas (procure * na conta ativa)
gcloud auth list

# Ver projeto ativo
gcloud config get-value project

# Se projeto diferente de instagram-ads-472021:
gcloud config set project instagram-ads-472021
```

### 1.3 Testar Application Default Credentials (ADC)
```bash
# Deve retornar um token JWT sem erro
gcloud auth application-default print-access-token

# Se falhar: re-autenticar
gcloud auth application-default login
gcloud auth application-default set-quota-project instagram-ads-472021
```

---

## FASE 2: VERIFICAR/CRIAR BUCKET (3 min)

### 2.1 Listar buckets existentes
```bash
gcloud storage buckets list --project=instagram-ads-472021
```

### 2.2 Verificar se bucket de referências existe
```bash
# Deve retornar detalhes do bucket ou erro 404
gcloud storage buckets describe gs://instagram-ads-472021-reference-images
```

### 2.3 Criar bucket (SE NÃO EXISTIR)
```bash
gcloud storage buckets create gs://instagram-ads-472021-reference-images \
  --project=instagram-ads-472021 \
  --location=us-central1 \
  --uniform-bucket-level-access
```

**Resultado esperado:**
```
Creating gs://instagram-ads-472021-reference-images/...
```

---

## FASE 3: CONFIGURAR PERMISSÕES (5 min)

### 3.1 Identificar service account do projeto
```bash
# Extrair email da service account do arquivo sa-key.json
cat sa-key.json | grep '"client_email"'
```

**Formato esperado:** `nome@instagram-ads-472021.iam.gserviceaccount.com`

### 3.2 Verificar roles atuais
```bash
# Substituir SERVICE_ACCOUNT_EMAIL pelo valor encontrado
gcloud projects get-iam-policy instagram-ads-472021 \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:SERVICE_ACCOUNT_EMAIL"
```

### 3.3 Adicionar permissões necessárias ao bucket
```bash
# Substituir SERVICE_ACCOUNT_EMAIL
gsutil iam ch serviceAccount:SERVICE_ACCOUNT_EMAIL:roles/storage.objectAdmin \
  gs://instagram-ads-472021-reference-images

# Verificar se foi aplicado
gsutil iam get gs://instagram-ads-472021-reference-images
```

**Roles necessários:**
- `roles/storage.objectAdmin` - Criar, ler, atualizar e deletar objetos
- `roles/storage.objectViewer` - Gerar signed URLs

### 3.4 (ALTERNATIVA) Adicionar permissões no projeto inteiro
```bash
# Se preferir dar acesso a todos os buckets do projeto
gcloud projects add-iam-policy-binding instagram-ads-472021 \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin"
```

---

## FASE 4: VALIDAÇÃO E TESTE (3 min)

### 4.1 Testar acesso direto ao bucket
```bash
# Upload de teste
echo "test" > /tmp/test.txt
gsutil cp /tmp/test.txt gs://instagram-ads-472021-reference-images/test.txt

# Listar conteúdo
gsutil ls gs://instagram-ads-472021-reference-images/

# Remover arquivo de teste
gsutil rm gs://instagram-ads-472021-reference-images/test.txt
```

### 4.2 Reiniciar backend com configurações atualizadas
```bash
# Ajuste o caminho para a raiz local do repositório, se necessário
cd /path/to/instagram_ads

# Parar processos existentes
pkill -f uvicorn

# Reiniciar
make dev
```

### 4.3 Testar endpoint de upload via curl
```bash
# Criar arquivo de imagem de teste (1x1 pixel PNG)
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > /tmp/test.png

# Upload via API
curl -X POST http://localhost:8000/upload/reference-image \
  -F "file=@/tmp/test.png" \
  -F "type=character" \
  -F "user_id=test_user" \
  -F "session_id=test_session"
```

**Resposta esperada:** JSON com `id`, `signed_url` e `labels`

---

## ✅ CHECKLIST DE VALIDAÇÃO

- [ ] `gcloud auth list` mostra conta ativa
- [ ] `gcloud auth application-default print-access-token` retorna token
- [ ] Bucket `instagram-ads-472021-reference-images` existe
- [ ] Service account tem role `storage.objectAdmin` no bucket
- [ ] `gsutil cp` funciona sem erros
- [ ] Backend reiniciado sem erros
- [ ] Upload via API retorna 200 OK

---

## 🚨 TROUBLESHOOTING

### Erro: "Permission denied"
```bash
# Re-autenticar
gcloud auth login
gcloud auth application-default login
```

### Erro: "Bucket already exists but owned by another project"
```bash
# Escolher outro nome
REFERENCE_IMAGES_BUCKET=gs://instagram-ads-472021-references
# Atualizar app/.env com novo nome
```

### Erro: "Service account does not have permission"
```bash
# Verificar se ADC está usando sa-key.json
echo $GOOGLE_APPLICATION_CREDENTIALS
# Deve ser: ./sa-key.json

# Verificar JSON da service account
cat sa-key.json | jq '.client_email'
```

---

## 📝 CONSIDERAÇÕES

**1 bucket é suficiente:**
O código já organiza automaticamente em subpastas:
```
reference-images/
├── {user_id}/
│   └── {session_id}/
│       ├── character/
│       │   └── ref_abc123.png
│       └── product/
│           └── ref_def456.png
```

**Não precisa de buckets separados** para character vs product - a estrutura de pastas já faz essa separação.

---

## 📂 CONFIGURAÇÃO ATUAL DO PROJETO

**Arquivo:** `app/.env`
```env
REFERENCE_IMAGES_BUCKET=gs://instagram-ads-472021-reference-images
GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json
GOOGLE_CLOUD_PROJECT=instagram-ads-472021
GOOGLE_CLOUD_LOCATION=us-central1
```

**Código responsável:**
- Upload: `app/utils/gcs.py:67-89` (função `upload_reference_image`)
- Config: `app/config.py:212-213` (carrega `REFERENCE_IMAGES_BUCKET`)
- Validação: Se bucket não configurado → RuntimeError na linha 84

---

## 🎯 PRÓXIMOS PASSOS

1. Execute os comandos da FASE 1 para verificar autenticação
2. Execute os comandos da FASE 2 para verificar/criar bucket
3. Execute os comandos da FASE 3 para configurar permissões
4. Execute os comandos da FASE 4 para validar o funcionamento
5. Marque os itens do checklist conforme concluir cada etapa
