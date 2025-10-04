# Plano Unificado - Campos Obrigatórios Frontend + Backend

## 1. Visão Geral
Implementação coordenada para tornar os campos `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` **obrigatórios** em toda a aplicação quando `VITE_ENABLE_NEW_FIELDS=true`, garantindo validação consistente no frontend e backend.

## 2. Princípios de Validação (Contrato Único)

### Regras Compartilhadas Frontend/Backend:
- **nome_empresa**: string 2-100 caracteres, sem espaços extras
- **o_que_a_empresa_faz**: string 10-200 caracteres, permite acentuação
- **sexo_cliente_alvo**: APENAS `masculino` ou `feminino` (sem neutro)
- **Todos os 3 campos são OBRIGATÓRIOS** quando a flag está ativa

## 3. Mudanças no Backend

### 3.1 `helpers/user_extract_data.py`

#### Linha 41: Remover "neutro" do Set
```python
# ANTES:
sexoClienteValues = new Set<string>(['masculino', 'feminino', 'neutro']);

# DEPOIS:
sexoClienteValues = new Set<string>(['masculino', 'feminino']);
```

#### Linha 58-75: Atualizar prompt base
```python
base_prompt = (
    "From the user text below, extract exactly these fields if present: "
    "landing_page_url (http/https), objetivo_final, perfil_cliente, formato_anuncio, foco"
)
if include_new_fields:
    base_prompt += (
        ", nome_empresa (REQUIRED), o_que_a_empresa_faz (REQUIRED), "
        "sexo_cliente_alvo (REQUIRED: masculino or feminino only, no neutro)"
    )
# ... resto do prompt
if include_new_fields:
    base_prompt += (
        " For sexo_cliente_alvo, map ALL synonyms to either masculino or feminino. "
        "Never return 'neutro' or empty values for required fields."
    )
```

#### Linha 175: Remover exemplo com "neutro"
```python
# REMOVER exemplo 2 que inclui "todos os gêneros" → "neutro"
# Substituir por exemplo que mapeia para masculino ou feminino
```

#### Linha 288-395: Método `_convert` - Adicionar validações rígidas
```python
def _convert(self, langextract_result: Any) -> Dict[str, Any]:
    # ... código existente ...

    # NOVA SEÇÃO: Validações obrigatórias (após linha 369)
    if self.enable_new_input_fields:  # Quando flag ativa, campos são obrigatórios
        # Validar nome_empresa
        if not data["nome_empresa"] or len(data["nome_empresa"].strip()) < 2:
            errors.append({
                "field": "nome_empresa",
                "message": "Nome da empresa é obrigatório (2-100 caracteres)."
            })
        elif len(data["nome_empresa"].strip()) > 100:
            errors.append({
                "field": "nome_empresa",
                "message": "Nome da empresa deve ter no máximo 100 caracteres."
            })

        # Validar o_que_a_empresa_faz
        if not data["o_que_a_empresa_faz"] or len(data["o_que_a_empresa_faz"].strip()) < 10:
            errors.append({
                "field": "o_que_a_empresa_faz",
                "message": "Descrição da empresa é obrigatória (10-200 caracteres)."
            })
        elif len(data["o_que_a_empresa_faz"].strip()) > 200:
            errors.append({
                "field": "o_que_a_empresa_faz",
                "message": "Descrição deve ter no máximo 200 caracteres."
            })

        # Validar sexo_cliente_alvo (APENAS masculino/feminino)
        sexo_norm = normalized.get("sexo_cliente_alvo_norm")
        if sexo_norm not in {"masculino", "feminino"}:
            errors.append({
                "field": "sexo_cliente_alvo",
                "message": "Gênero do público é obrigatório (masculino ou feminino)."
            })

        # REMOVER linhas 371-373 que fazem fallback para neutro
        # REMOVER linhas 374-387 que atribuem defaults
```

#### Linha 429-475: Método `_normalize_sexo` - Remover neutro
```python
@staticmethod
def _normalize_sexo(value: str | None) -> str:
    if not value:
        return ""  # Retorna vazio para forçar erro de validação

    v = value.strip().lower()
    if not v:
        return ""

    masculino_aliases = {
        "masculino", "homem", "homens", "macho",
        "publico masculino", "male", "men"
    }
    feminino_aliases = {
        "feminino", "mulher", "mulheres",
        "publico feminino", "female", "women"
    }

    # REMOVIDO: neutro_aliases e lógica relacionada

    if v in masculino_aliases or "masc" in v or "homem" in v:
        return "masculino"
    if v in feminino_aliases or "fem" in v or "mulher" in v:
        return "feminino"

    # Se não conseguir mapear, retorna vazio para forçar erro
    return ""
```

## 4. Mudanças no Frontend

### 4.1 `frontend/src/constants/wizard.constants.ts`

#### Linha 41: Remover "neutro" do Set
```typescript
const sexoClienteValues = new Set<string>(['masculino', 'feminino']);
```

#### Linha 44-60: Remover opção Neutro
```typescript
export const SEXO_CLIENTE_OPTIONS = [
  {
    value: 'masculino',
    label: 'Masculino',
    description: 'Comunicação direcionada para homens',
  },
  {
    value: 'feminino',
    label: 'Feminino',
    description: 'Tom e referências voltados para mulheres',
  },
  // REMOVIDO: opção neutro/misto
] as const;
```

#### Linha 97: Remover `isOptional: true` de nomeEmpresaStep
```typescript
const nomeEmpresaStep: WizardStep = {
  // ... outras props
  // isOptional: true, ← REMOVER
```

#### Linha 101-105: Tornar validação obrigatória
```typescript
validate: value => {
  const trimmed = value.trim();
  if (!trimmed) {
    return 'O nome da empresa é obrigatório para personalizar seus anúncios.';
  }
  // ... resto da validação
```

#### Linha 124: Remover `isOptional: true` de descricaoEmpresaStep
```typescript
const descricaoEmpresaStep: WizardStep = {
  // ... outras props
  // isOptional: true, ← REMOVER
```

#### Linha 127-132: Tornar validação obrigatória
```typescript
validate: value => {
  const trimmed = value.trim();
  if (!trimmed) {
    return 'A descrição da empresa é obrigatória para criar anúncios relevantes.';
  }
  // ... resto da validação
```

#### Linha 226: Remover `isOptional: true` de sexoClienteStep
```typescript
const sexoClienteStep: WizardStep = {
  // ... outras props
  // isOptional: true, ← REMOVER
```

#### Linha 229-234: Tornar validação obrigatória
```typescript
validate: value => {
  const trimmed = value.trim();
  if (!trimmed) {
    return 'Selecione o gênero predominante do seu público-alvo.';
  }
  if (!sexoClienteValues.has(trimmed)) {
    return 'Escolha entre masculino ou feminino.';
  }
  return null;
```

#### Linha 222-223: Atualizar título e descrição
```typescript
title: 'Qual o gênero predominante do público?',
description: 'Selecione o gênero para personalizar a comunicação do anúncio (obrigatório).',
```

### 4.2 `frontend/src/utils/wizard.utils.ts`

#### Linha 116-119: Remover fallback para neutro
```typescript
// REMOVER este bloco completamente:
// if (fieldId === 'sexo_cliente_alvo') {
//   return [`${fieldId}: neutro`];
// }
// Apenas retornar array vazio se campo vazio
return [];
```

### 4.3 `frontend/src/components/WizardForm/steps/GenderTargetStep.tsx`

#### Linha 39-42: Atualizar mensagem para indicar obrigatoriedade
```typescript
<p className="text-sm text-muted-foreground">
  <span className="text-destructive">*</span> Selecione o gênero predominante do seu público-alvo.
  Esta informação é obrigatória para personalizar a comunicação e aumentar a efetividade do anúncio.
</p>
```

#### Linha 66-68: Remover botão "Limpar seleção"
```typescript
// REMOVER completamente o botão de limpar seleção
// <Button type="button" variant="ghost" ... onClick={handleClear}>
```

### 4.4 `frontend/src/components/WizardForm/steps/CompanyInfoStep.tsx`

Adicionar indicadores visuais de campo obrigatório (asterisco vermelho) e atualizar placeholders:
```typescript
// Adicionar asterisco no label
<Label htmlFor="nome_empresa">
  Nome da Empresa <span className="text-destructive">*</span>
</Label>

// Atualizar placeholder
placeholder="Ex: Clínica Bem Viver (obrigatório)"

// Similar para o_que_a_empresa_faz
```

## 5. Testes

### 5.1 Backend Tests (`tests/test_user_extract.py`)
```python
def test_required_fields_validation():
    """Testa que campos obrigatórios retornam erro quando vazios"""
    extractor = UserInputExtractor()

    # Com flag ativa, campos vazios devem gerar erro
    with patch.dict(os.environ, {'ENABLE_NEW_INPUT_FIELDS': 'true'}):
        result = extractor.extract("landing_page_url: https://test.com")
        assert result['success'] is False
        assert any(e['field'] == 'nome_empresa' for e in result['errors'])
        assert any(e['field'] == 'o_que_a_empresa_faz' for e in result['errors'])
        assert any(e['field'] == 'sexo_cliente_alvo' for e in result['errors'])

def test_no_neutro_gender():
    """Testa que neutro não é aceito como sexo_cliente_alvo"""
    extractor = UserInputExtractor()

    with patch.dict(os.environ, {'ENABLE_NEW_INPUT_FIELDS': 'true'}):
        result = extractor.extract("""
            landing_page_url: https://test.com
            nome_empresa: Test Corp
            o_que_a_empresa_faz: Consultoria empresarial
            sexo_cliente_alvo: neutro
        """)
        assert result['success'] is False
        assert any(e['field'] == 'sexo_cliente_alvo' for e in result['errors'])
```

### 5.2 Frontend Tests (`frontend/tests/wizard.test.tsx`)
```typescript
describe('Required fields validation', () => {
  beforeEach(() => {
    import.meta.env.VITE_ENABLE_NEW_FIELDS = 'true';
  });

  test('blocks submission without required fields', () => {
    const { getByText, getByRole } = render(<WizardForm />);

    // Tentar submeter sem preencher campos obrigatórios
    const submitButton = getByRole('button', { name: /enviar/i });
    fireEvent.click(submitButton);

    // Verificar mensagens de erro
    expect(getByText(/nome da empresa é obrigatório/i)).toBeInTheDocument();
    expect(getByText(/descrição da empresa é obrigatória/i)).toBeInTheDocument();
    expect(getByText(/selecione o gênero predominante/i)).toBeInTheDocument();
  });

  test('only accepts masculino or feminino for gender', () => {
    const { queryByText } = render(<GenderTargetStep {...mockProps} />);

    // Verificar que neutro não está disponível
    expect(queryByText(/neutro/i)).not.toBeInTheDocument();
    expect(queryByText(/misto/i)).not.toBeInTheDocument();
  });
});
```

## 6. Observabilidade

### 6.1 Logs Backend
```python
# Em user_extract_data.py, adicionar logging detalhado
logger.info(
    "[preflight] validation_result: required_fields=%s, errors_count=%s",
    {
        "nome_empresa": bool(data.get("nome_empresa")),
        "o_que_a_empresa_faz": bool(data.get("o_que_a_empresa_faz")),
        "sexo_cliente_alvo": normalized.get("sexo_cliente_alvo_norm")
    },
    len(errors)
)
```

### 6.2 Analytics Frontend
```typescript
// Rastrear tentativas de submissão bloqueadas
if (hasRequiredFieldErrors) {
  trackEvent('wizard_submission_blocked', {
    missing_fields: getMissingRequiredFields(formState),
    step: currentStep,
  });
}
```

## 7. Rollback Strategy

Caso necessário reverter:
1. Backend: Variável `ENABLE_NEW_INPUT_FIELDS=false` desativa validações
2. Frontend: `VITE_ENABLE_NEW_FIELDS=false` volta ao comportamento anterior
3. Ambas as flags podem ser alteradas sem deploy

## 8. Critérios de Aceite

- ✅ Frontend bloqueia submissão sem os 3 campos preenchidos
- ✅ Backend retorna `success: false` se algum campo obrigatório faltar
- ✅ Sexo "neutro" não é aceito em nenhuma camada
- ✅ Mensagens de erro são claras e consistentes
- ✅ Testes automatizados passam em ambas as camadas
- ✅ Logs permitem rastrear validações rejeitadas

## 9. Ordem de Implementação

1. **Backend primeiro** - Adicionar validações com flag de controle
2. **Testes backend** - Garantir que validações funcionam
3. **Frontend** - Atualizar UI e validações
4. **Testes frontend** - Verificar bloqueios e mensagens
5. **Teste E2E** - Validar fluxo completo com ambas as flags ativas
6. **Deploy** - Ativar flags progressivamente

## 10. Coordenação

Esta implementação deve ocorrer em **branch única** com commits separados para backend e frontend, garantindo que ambas as mudanças sejam mergeadas juntas para manter consistência.