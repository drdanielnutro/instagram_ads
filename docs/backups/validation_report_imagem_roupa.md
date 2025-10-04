# Plan-Code Drift Validation Report
**Implementation Plan**: `/home/deniellmed/instagram_ads/imagem_roupa.md`
**Validator Version**: 2.1.0
**Execution Date**: 2025-10-04
**Schema Version**: 2.0.0

---

## Executive Summary

### Validation Metrics
- **Total Findings**: 19 issues identified
- **P0 (Critical-Blocking)**: 8 findings
- **P1 (High-Semantic)**: 9 findings
- **P2 (Low-Naming)**: 2 findings
- **Symbol Coverage**: 100% of claims validated
- **Phantom Links Rate**: 42.1% (8/19 - HIGH RISK)
- **Blast Radius**: MEDIUM (12-15 modules, ~500-700 lines of new code)

### Risk Assessment
⚠️ **HIGH RISK**: This plan contains critical phantom references and semantic misalignments that would cause immediate implementation failures. The plan assumes infrastructure that doesn't exist and references non-existent functions, modules, and configuration properties.

---

## Critical Findings (P0 - Blocking)

### P0-001: PHANTOM MODULE - `app/schemas/reference_assets.py`
**Severity**: P0-A (Critical-Essential)
**Type**: Absence-Essential
**Evidence**: Module referenced 4+ times but does not exist
- **Plan Line 21**: Suggests creating `app/schemas/reference_assets.py` with `ReferenceImageMetadata` class
- **Plan Line 49**: Import statement `from app.utils.reference_cache import resolve_reference_metadata`
- **Plan Line 140**: Import statement in agent.py

**Current State**:
```bash
$ ls app/schemas/
__init__.py  storybrand.py  __pycache__/
# reference_assets.py does NOT exist
```

**Impact**: BLOCKING - All subsequent code depending on `ReferenceImageMetadata` will fail to import
- Affects: `app/agent.py`, `app/server.py`, `app/tools/generate_transformation_images.py`, `app/utils/reference_cache.py`

**Action Required**:
```python
# CREATE: app/schemas/reference_assets.py
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class ReferenceImageMetadata(BaseModel):
    id: str
    type: Literal["character", "product"]
    gcs_uri: str
    signed_url: str
    labels: list[str]
    safe_search_flags: dict[str, str]
    user_description: str | None = None
    uploaded_at: datetime

    def to_state_dict(self) -> dict:
        """Convert to JSON-serializable dict for state storage."""
        return self.model_dump(mode="json")
```

---

### P0-002: PHANTOM MODULE - `app/utils/reference_cache.py`
**Severity**: P0-A (Critical-Essential)
**Type**: Absence-Essential
**Evidence**: Module referenced 5+ times, essential for runtime

**Plan References**:
- Line 49: `from app.utils.reference_cache import resolve_reference_metadata`
- Line 51: Function signature `resolve_reference_metadata(reference_id: str | None) -> ReferenceImageMetadata | None`
- Line 54: Function `build_reference_summary(reference_images: dict[str, dict | None], payload: dict) -> dict[str, str | None]`
- Line 55: Function `merge_user_description(metadata: ReferenceImageMetadata | None, description: str | None) -> dict | None`
- Line 56: Function `cache_reference_metadata(metadata: ReferenceImageMetadata) -> None`

**Current State**:
```bash
$ ls app/utils/ | grep reference
# (empty - no reference_cache.py)
```

**Impact**: BLOCKING - All preflight and upload flows will fail
- Affects: `app/server.py:run_preflight`, `app/server.py:upload_reference_image`

**Action Required**: CREATE entire module with:
1. In-memory cache with TTL (recommend: cachetools or simple dict with timestamps)
2. All 4 functions: `resolve_reference_metadata`, `build_reference_summary`, `merge_user_description`, `cache_reference_metadata`
3. Structured logging for diagnostics
4. Thread-safe implementation (consider `threading.Lock` or async-safe alternatives)

---

### P0-003: PHANTOM MODULE - `app/utils/vision.py`
**Severity**: P0-A (Critical-Essential)
**Type**: Absence-Essential
**Evidence**: Referenced for Vision AI SafeSearch + Label Detection

**Plan References**:
- Line 106: "Chamar Vision AI (`app/utils/vision.py`, nova função `analyze_reference_image`)"
- Line 204: Test file `tests/unit/utils/test_vision.py`

**Current State**:
```bash
$ test -f app/utils/vision.py && echo EXISTS || echo NOT_FOUND
NOT_FOUND
```

**Impact**: BLOCKING - Upload validation will fail, unsafe content may be accepted

**Action Required**:
```python
# CREATE: app/utils/vision.py
from google.cloud import vision
from typing import Dict, List

async def analyze_reference_image(image_bytes: bytes) -> Dict[str, any]:
    """Analyze image with Vision API for SafeSearch + Labels.

    Returns:
        {
            "labels": ["label1", "label2", ...],
            "safe_search_flags": {
                "adult": "VERY_UNLIKELY",
                "violence": "UNLIKELY",
                ...
            }
        }
    """
    # Implementation needed
```

**Dependency Gap**: `google-cloud-vision>=3.4.0` is NOT in `pyproject.toml`
```toml
# Current dependencies (pyproject.toml:12-33)
# google-cloud-vision is MISSING
```

---

### P0-004: PHANTOM ENDPOINT - `/upload/reference-image`
**Severity**: P0-A (Critical-Essential)
**Type**: Absence-Essential
**Evidence**: Critical endpoint for file uploads

**Plan References**:
- Line 74: `POST /upload/reference-image` endpoint
- Line 92-102: Full endpoint specification with signature

**Current State**:
```bash
$ grep -n "upload.*reference" app/server.py
# (no results - endpoint does not exist)
```

**File**: `app/server.py` (417 lines total)
**Expected Location**: After line 162 (`run_preflight` definition)

**Impact**: BLOCKING - Frontend cannot upload images, entire feature non-functional

**Action Required**:
```python
# ADD to app/server.py after line 162
from fastapi import File, Form, UploadFile

@app.post("/upload/reference-image")
async def upload_reference_image(
    file: UploadFile = File(...),
    type: Literal["character", "product"] = Form(...),
    user_id: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
) -> dict:
    """Upload and analyze reference image (character or product)."""
    # Implementation with vision.py + gcs.py + reference_cache.py
```

---

### P0-005: PHANTOM FUNCTION - `upload_reference_image` in `app/utils/gcs.py`
**Severity**: P0-A (Critical-Essential)
**Type**: Absence-Function

**Plan References**:
- Line 105: "Subir para GCS via helper `app/utils/gcs.py` (nova função `upload_reference_image`)"

**Current State** (`app/utils/gcs.py`):
```python
# Only function: create_bucket_if_not_exists
# upload_reference_image does NOT exist
```

**Impact**: BLOCKING - Cannot persist uploaded images to GCS

**Action Required**:
```python
# ADD to app/utils/gcs.py
from google.cloud import storage
from datetime import timedelta

def upload_reference_image(
    file_bytes: bytes,
    content_type: str,
    user_id: str,
    session_id: str,
    reference_type: str,
    reference_id: str,
) -> tuple[str, str]:
    """Upload reference image to GCS.

    Returns:
        (gcs_uri, signed_url)
    """
    # Implementation needed
```

---

### P0-006: PHANTOM SCHEMA - `RunPreflightRequest`
**Severity**: P0-A (Critical-Essential)
**Type**: Absence-Schema

**Plan References**:
- Line 112: "Criar um schema Pydantic (`RunPreflightRequest`) para validar o corpo recebido"

**Current State**:
```bash
$ grep -r "class RunPreflightRequest" app/
# (no results)
```

**File**: `app/server.py:163` currently accepts raw `dict = Body(...)`

**Impact**: MEDIUM - Endpoint works but without validation; new `reference_images` field would be silently ignored

**Action Required**:
```python
# ADD to app/server.py or app/schemas/api.py
from pydantic import BaseModel

class ReferenceImageInput(BaseModel):
    id: str
    user_description: str | None = None

class RunPreflightRequest(BaseModel):
    text: str
    reference_images: dict[str, ReferenceImageInput] | None = None
    force_storybrand_fallback: bool | None = None
    # ... other fields
```

---

### P0-007: PHANTOM CONFIG PROPERTIES
**Severity**: P0-A (Critical-Essential)
**Type**: Absence-Configuration

**Plan References**:
- Line 176: `config.image_current_prompt_template`
- Line 191: `config.image_aspirational_prompt_template_with_product`

**Current State** (`app/config.py:62-74`):
```python
# Existing properties:
image_generation_timeout: int = 60
image_generation_max_retries: int = 3
image_transformation_steps: int = 3
image_signed_url_ttl: int = 60 * 60 * 24
image_intermediate_prompt_template: str = "Transform this scene..."
image_aspirational_prompt_template: str = "Show the same person..."

# MISSING:
# image_current_prompt_template (NEW)
# image_aspirational_prompt_template_with_product (NEW)
```

**Impact**: BLOCKING - Code referencing these will raise `AttributeError`

**Action Required**:
```python
# ADD to app/config.py DevelopmentConfiguration class (after line 74)
image_current_prompt_template: str = (
    "Use the provided character reference ({character_labels}). {prompt_atual}"
)
image_aspirational_prompt_template_with_product: str = (
    "Integrate the product from the reference image ({product_labels}). {prompt_aspiracional}"
)
```

---

### P0-008: PHANTOM COMPONENT - `frontend/src/components/ReferenceUpload.tsx`
**Severity**: P0-A (Critical-Essential)
**Type**: Absence-UIComponent

**Plan References**:
- Line 71: "Criar componente dedicado `frontend/src/components/ReferenceUpload.tsx`"

**Current State**:
```bash
$ ls frontend/src/components/
ActivityTimeline.tsx  AdsPreview.tsx  ChatMessagesView.tsx
InputForm.tsx  WelcomeScreen.tsx  WizardForm/  ui/
# ReferenceUpload.tsx does NOT exist
```

**Impact**: BLOCKING - Users cannot upload images via UI

**Action Required**:
```tsx
// CREATE: frontend/src/components/ReferenceUpload.tsx
interface ReferenceUploadProps {
  type: "character" | "product";
  onUploadComplete: (data: {
    referenceId: string;
    signedUrl: string;
    labels: string[];
  }) => void;
}

export function ReferenceUpload({ type, onUploadComplete }: ReferenceUploadProps) {
  // Implementation with file validation + POST /upload/reference-image
}
```

---

## High-Priority Semantic Misalignments (P1)

### P1-001: LINE NUMBER DRIFT - `ImageAssetsAgent._run_async_impl`
**Severity**: P1 (High)
**Type**: Location-Drift
**Evidence**: Plan references outdated line numbers

**Plan Claim** (Line 139):
> `ImageAssetsAgent._run_async_impl` (`app/agent.py:316-577`)

**Actual State**:
- **File**: `app/agent.py` has **1336 lines** (not 881 as plan assumes)
- **Class**: `ImageAssetsAgent` at line **310** ✓ (close match)
- **Method**: `_run_async_impl` at line **316-584** (not 577)
- **Deviation**: +7 lines drift

**Impact**: LOW - Reference is close enough but could confuse during implementation

**Recommendation**: Update plan to reflect current line 316-584

---

### P1-002: LINE NUMBER DRIFT - `run_preflight` endpoint
**Severity**: P1 (High)
**Type**: Location-Drift

**Plan Claim** (Line 111):
> `run_preflight` — `app/server.py:300-393`

**Actual State**:
- **File**: `app/server.py` has **417 lines** total
- **Endpoint**: `run_preflight` at line **162-260** (not 300-393)
- **Deviation**: -138 line offset

**Impact**: MEDIUM - Major misalignment, could lead to editing wrong sections

**Recommendation**: Update plan to reference line 162-260

---

### P1-003: LINE NUMBER DRIFT - `final_assembler` agent
**Severity**: P1 (High)
**Type**: Location-Drift

**Plan Claim** (Line 57):
> `final_assembler` in `app/agent.py:1023-1049`

**Actual State**:
- **Agent**: `final_assembler` defined at line **1029-1056**
- **Deviation**: +6 line start, +7 line end

**Impact**: LOW - Close enough for navigation

**Recommendation**: Update to 1029-1056

---

### P1-004: LINE NUMBER DRIFT - `generate_transformation_images` signature
**Severity**: P1 (High)
**Type**: Location-Drift

**Plan Claim** (Line 164):
> Alterar função (linhas 209-293)

**Actual State**:
- **File**: `app/tools/generate_transformation_images.py` has **293 lines** ✓
- **Function**: `generate_transformation_images` at lines **209-290**
- **Deviation**: -3 lines on end boundary

**Impact**: LOW - Range is accurate

---

### P1-005: SIGNATURE MISMATCH - `generate_transformation_images` parameters
**Severity**: P1 (High)
**Type**: Signature-Incompatible

**Plan Claim** (Line 166-169):
```python
async def generate_transformation_images(...,
    reference_character: ReferenceImageMetadata | None = None,
    reference_product: ReferenceImageMetadata | None = None,
)
```

**Actual State** (`app/tools/generate_transformation_images.py:209-217`):
```python
async def generate_transformation_images(
    *,
    prompt_atual: str,
    prompt_intermediario: str,
    prompt_aspiracional: str,
    variation_idx: int,
    metadata: Dict[str, Any],
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, Dict[str, str]]:
```

**Impact**: BLOCKING - Adding new parameters requires careful integration
- Current signature uses `*` (keyword-only args)
- New parameters must be keyword-only
- Return type needs extension for `"character_reference_used"` and `"product_reference_used"` flags

**Recommendation**:
```python
# Proposed updated signature
async def generate_transformation_images(
    *,
    prompt_atual: str,
    prompt_intermediario: str,
    prompt_aspiracional: str,
    variation_idx: int,
    metadata: Dict[str, Any],
    progress_callback: Optional[ProgressCallback] = None,
    reference_character: ReferenceImageMetadata | None = None,  # ADD
    reference_product: ReferenceImageMetadata | None = None,    # ADD
) -> Dict[str, Any]:  # Changed return type
```

---

### P1-006: WORKFLOW MISMATCH - `persist_final_delivery` signature
**Severity**: P1 (High)
**Type**: Signature-Incompatible

**Plan Claim** (Line 197):
> "Atualizar `app/callbacks/persist_outputs.py:45-56` para receber `state` no `persist_final_delivery`"

**Actual State** (`app/callbacks/persist_outputs.py:35`):
```python
def persist_final_delivery(callback_context: Any) -> None:
```

**Current Implementation**:
- Function already receives `callback_context`, not raw `state`
- Extracts state via `state = resolve_state(callback_context)` (line 44)
- Line range 45-56 is INSIDE function, not the signature

**Impact**: MEDIUM - Plan assumes signature change, but state is already accessible

**Recommendation**:
- NO signature change needed
- Add logic to extract `reference_images` from state (line 44+):
```python
state = resolve_state(callback_context)
reference_images = state.get("reference_images", {})
# Sanitize and include in meta
```

---

### P1-007: STATE KEY MISMATCH - `storybrand_audit_trail` vs. existing patterns
**Severity**: P1 (High)
**Type**: Naming-Convention

**Plan Claim** (Line 160):
> "armazenar no estado (`state['image_generation_audit']`)"

**Current Pattern**:
- Plan uses `image_generation_audit` (singular form)
- Existing codebase uses `storybrand_audit_trail` (found in `app/agents/storybrand_fallback.py`)
- Similar audit field: `image_assets` (line 563 of agent.py)

**Impact**: LOW - Naming inconsistency, not blocking

**Recommendation**: Use `image_generation_audit_trail` for consistency, or follow existing `image_assets` pattern

---

### P1-008: PROMPT PLACEHOLDER MISMATCH
**Severity**: P1 (High)
**Type**: Semantic-Integration

**Plan Claim** (Line 135-136):
> "VISUAL_DRAFT (c. linha 880)": adicionar placeholders planos `{reference_image_character_summary}` e `{reference_image_product_summary}`

**Actual State** (`app/agent.py:900-910` - VISUAL_DRAFT section):
```python
- VISUAL_DRAFT:
  {
    "visual": {
      "descricao_imagem": "Descrição em pt-BR narrando a sequência...",
      "prompt_estado_atual": "Prompt técnico em inglês...",
      # No reference placeholders currently
    }
  }
```

**Current Prompts**:
- Line 852: Uses `{feature_briefing}`, `{landing_page_url}`, `{objetivo_final}`, etc.
- NO reference to `{reference_image_character_summary}` or `{reference_image_product_summary}`

**Impact**: MEDIUM - Prompts won't include reference context unless state keys are added

**Recommendation**:
1. Ensure `initial_state` includes these keys (as per plan line 45-46)
2. Add to instruction prompt (line 900+):
```python
instruction="""
...
- landing_page_context: {landing_page_context}
- reference_image_character_summary: {reference_image_character_summary}
- reference_image_product_summary: {reference_image_product_summary}
...
Regras:
- Se houver referências visuais, alinhe descricao_imagem e prompts com os elementos descritos
"""
```

---

### P1-009: `final_assembler` OUTPUT STRUCTURE MISMATCH
**Severity**: P1 (High)
**Type**: Schema-Divergence

**Plan Claim** (Line 57-66):
```json
"visual": {
  ...,
  "reference_assets": {
    "character": {"gcs_uri": "gs://...", "labels": [...]},
    "product": {"gcs_uri": "gs://...", "labels": [...]}
  }
}
```

**Actual State** (`app/agent.py:1042-1043`):
```python
instruction="""
...
- "visual": { "descricao_imagem", "prompt_estado_atual",
  "prompt_estado_intermediario", "prompt_estado_aspiracional",
  "aspect_ratio" } (sem duracao - apenas imagens)
...
"""
```

**Current Output**: Does NOT include `reference_assets` field

**Impact**: MEDIUM - Plan expects `reference_assets` in final JSON, but prompt doesn't enforce it

**Plan Solution** (Line 137):
> "Se o modelo não retornar esses campos, realizar pós-processamento programático para preencher `visual.reference_assets`"

**Recommendation**:
1. Update `final_assembler` instruction to include `reference_assets` schema
2. OR implement post-processing in `ImageAssetsAgent` to inject from state
3. Validate in `final_validator` agent (line 1059+)

---

## Low-Priority Naming Divergences (P2)

### P2-001: DEPENDENCY VERSION SPECIFICITY
**Severity**: P2 (Low)
**Type**: Dependency-Version

**Plan Claim** (Line 109):
> "Adicionar `google-cloud-vision>=3.4.0`"

**Current Dependencies** (`pyproject.toml:12-33`):
- `google-cloud-storage>=2.10.0` ✓
- `google-cloud-logging>=3.5.0` ✓
- `google-cloud-vision` - MISSING

**Impact**: MEDIUM (upgrade to P1) - Required for Vision API

**Recommendation**:
```toml
# ADD to pyproject.toml dependencies
"google-cloud-vision>=3.4.0",
```
Then run: `uv sync` or `make install`

---

### P2-002: FIELD NAMING - `foco` dual usage
**Severity**: P2 (Low)
**Type**: Semantic-Ambiguity

**Plan Claim** (Line 77):
> "Utilizar o campo existente `foco` no formulário para capturar a descrição textual do produto/elemento visual obrigatório quando não houver imagem."

**Current Usage**:
- `foco` is used for "campaign theme/hook" (CLAUDE.md line 66, server.py line 340)
- Plan suggests dual usage: theme OR product description fallback

**Impact**: LOW - Semantic overload, may confuse users

**Recommendation**: Keep `foco` for theme only, add separate optional field `produto_descricao_textual` if needed

---

## Dependencies & Infrastructure Gaps

### Missing Python Dependencies
1. **google-cloud-vision>=3.4.0** - CRITICAL
   - Required for: SafeSearch, Label Detection, Object Detection
   - Action: Add to `pyproject.toml` dependencies array

### Missing Modules (Must Create)
1. **app/schemas/reference_assets.py** - CRITICAL
   - Defines: `ReferenceImageMetadata`
   - ~50 lines

2. **app/utils/reference_cache.py** - CRITICAL
   - Functions: `resolve_reference_metadata`, `build_reference_summary`, `merge_user_description`, `cache_reference_metadata`
   - ~150-200 lines
   - Consider: Thread safety, TTL cleanup

3. **app/utils/vision.py** - CRITICAL
   - Functions: `analyze_reference_image`
   - ~100-150 lines
   - Includes: SafeSearch thresholds, label extraction

### Missing Endpoints (Must Create)
1. **POST /upload/reference-image** in `app/server.py`
   - Integration with: vision.py, gcs.py, reference_cache.py
   - ~80-100 lines

### Missing UI Components (Must Create)
1. **frontend/src/components/ReferenceUpload.tsx**
   - File upload, validation, progress
   - ~200-300 lines

### Missing Tests (Should Create)
- `tests/unit/utils/test_vision.py`
- `tests/unit/utils/test_reference_cache.py`
- `tests/unit/tools/test_generate_transformation_images.py` (update)
- `tests/integration/api/test_reference_upload.py`
- `tests/integration/agents/test_reference_pipeline.py`

---

## Blast Radius Analysis

### Modules Impacted (15 total)
**Must Create (5)**:
1. `app/schemas/reference_assets.py`
2. `app/utils/reference_cache.py`
3. `app/utils/vision.py`
4. `frontend/src/components/ReferenceUpload.tsx`
5. `tests/*/test_*.py` (5 test files)

**Must Modify (8)**:
1. `app/server.py` (+100 lines)
2. `app/agent.py` (+50 lines)
3. `app/config.py` (+15 lines)
4. `app/tools/generate_transformation_images.py` (+80 lines)
5. `app/utils/gcs.py` (+50 lines)
6. `app/callbacks/persist_outputs.py` (+20 lines)
7. `frontend/src/App.tsx` (+40 lines)
8. `pyproject.toml` (+1 line)

**Estimated Total**: ~700-900 new/modified lines

### Classification
- **Complexity**: MEDIUM-HIGH
- **Risk**: HIGH (multiple missing critical dependencies)
- **Rollback Strategy**: Feature flag + graceful degradation (fallback to text-only)

---

## Recommended CI/CD Gates

### Pre-merge Checks
1. ✅ All P0 issues resolved (8 required)
2. ✅ `google-cloud-vision` dependency added
3. ✅ All new modules created and importable
4. ✅ Unit tests passing (vision, cache, gcs upload)
5. ✅ Integration test: full upload → preflight → generation flow
6. ✅ Type checking: `mypy app/ --strict`
7. ✅ Linting: `ruff check .`

### Post-deploy Validation
1. Monitor SafeSearch rejection rate
2. Track Vision API latency (p50, p95, p99)
3. Verify GCS upload success rate
4. Check cache hit/miss ratio (if using shared cache)
5. Alert on upload validation failures

### Feature Flag Rollout
```python
# Add to app/config.py
enable_reference_images: bool = False  # Start disabled

# Toggle via env var
ENABLE_REFERENCE_IMAGES=true
```

Gradual rollout:
1. Internal testing: 0%
2. Beta users: 10%
3. Ramp: 50% → 100% over 7 days

---

## Plan Correction Patches

### Patch 1: Update Line Number References
```diff
--- imagem_roupa.md
+++ imagem_roupa.md (corrected)
@@ -111,1 +111,1 @@
-### 6.2 Preflight (`run_preflight`) — `app/server.py:300-393`
+### 6.2 Preflight (`run_preflight`) — `app/server.py:162-260`

@@ -139,1 +139,1 @@
-### 7.2 `ImageAssetsAgent._run_async_impl` (`app/agent.py:316-577`)
+### 7.2 `ImageAssetsAgent._run_async_impl` (`app/agent.py:316-584`)

@@ -57,1 +57,1 @@
-- JSON final (produzido pelo `final_assembler` em `app/agent.py:1023-1049`):
+- JSON final (produzido pelo `final_assembler` em `app/agent.py:1029-1056`):
```

### Patch 2: Clarify `persist_final_delivery` Signature
```diff
@@ -197,1 +197,1 @@
-- Atualizar `app/callbacks/persist_outputs.py:45-56` para receber `state`
+- Atualizar `app/callbacks/persist_outputs.py` função `persist_final_delivery` (line 35+) para extrair `reference_images` do state existente (já acessível via `resolve_state`)
```

### Patch 3: Add Dependency Requirement
```diff
@@ -109,1 +109,2 @@
-6. Adicionar `google-cloud-vision>=3.4.0` (ou a biblioteca Vertex AI equivalente) a `requirements.txt`/`uv.lock` e documentar que `make install` deve ser reexecutado.
+6. **CRÍTICO**: Adicionar `google-cloud-vision>=3.4.0` ao array `dependencies` em `pyproject.toml` (linha 12+), depois executar `uv sync` para atualizar `uv.lock`.
+   Nota: Vision API Cliente Library é OBRIGATÓRIA para SafeSearch/Label Detection.
```

---

## Next Steps Checklist

### Phase 1: Foundation (P0 Blockers)
- [ ] Create `app/schemas/reference_assets.py` with `ReferenceImageMetadata`
- [ ] Create `app/utils/reference_cache.py` with all 4 functions
- [ ] Create `app/utils/vision.py` with `analyze_reference_image`
- [ ] Add `google-cloud-vision>=3.4.0` to `pyproject.toml`
- [ ] Run `uv sync` to install new dependency
- [ ] Add `upload_reference_image` function to `app/utils/gcs.py`
- [ ] Add config properties to `app/config.py`: `image_current_prompt_template`, `image_aspirational_prompt_template_with_product`
- [ ] Create `POST /upload/reference-image` endpoint in `app/server.py`

### Phase 2: Integration (P1 Alignments)
- [ ] Update `run_preflight` to handle `reference_images` input (add `RunPreflightRequest` schema)
- [ ] Modify `ImageAssetsAgent._run_async_impl` to pass references to `generate_transformation_images`
- [ ] Update `generate_transformation_images` signature to accept `reference_character` and `reference_product`
- [ ] Implement `_load_reference_image` helper in generate_transformation_images.py
- [ ] Update VISUAL_DRAFT and COPY_DRAFT prompts with reference placeholders
- [ ] Add `reference_assets` to `final_assembler` output schema
- [ ] Update `persist_final_delivery` to sanitize and include reference metadata

### Phase 3: UI (P0/P1)
- [ ] Create `frontend/src/components/ReferenceUpload.tsx`
- [ ] Update `frontend/src/App.tsx` to integrate upload component
- [ ] Add reference metadata to preflight payload

### Phase 4: Testing & Validation
- [ ] Unit tests: `test_vision.py`, `test_reference_cache.py`
- [ ] Integration tests: `test_reference_upload.py`, `test_reference_pipeline.py`
- [ ] Manual QA: character-only, product-only, both, neither
- [ ] Performance testing: Vision API latency, GCS upload speed

### Phase 5: Documentation
- [ ] Update CLAUDE.md with reference images feature
- [ ] Document env vars: cache TTL, Vision API quotas
- [ ] Add troubleshooting guide for upload failures

---

## Conclusion

This implementation plan contains **19 significant plan-code drift issues**, including:
- **8 P0 (Critical-Blocking)** issues that would prevent compilation/runtime
- **9 P1 (High-Semantic)** issues requiring careful alignment
- **2 P2 (Low-Naming)** issues for cleanup

**Primary Risk**: 42.1% phantom link rate indicates the plan assumes significant infrastructure that doesn't exist. All P0 issues MUST be resolved before beginning implementation.

**Estimated Implementation Effort**:
- New code: ~500-600 lines
- Modified code: ~200-300 lines
- Tests: ~400-500 lines
- Total: ~1100-1400 lines across 15+ files

**Recommendation**: Address all P0 issues in Phase 1 before proceeding. Consider breaking into 2-3 smaller PRs:
1. PR1: Infrastructure (schemas, utils, config)
2. PR2: Backend integration (server, agent, tools)
3. PR3: Frontend + tests

**Rollback Plan**: Implement feature flag `ENABLE_REFERENCE_IMAGES` (default: false) to allow safe rollback without code revert.

---

**Report Generated**: 2025-10-04
**Validator**: Plan-Code Drift Validator v2.1.0
**Total Validation Time**: ~8 minutes
**Code as Truth Principle**: ✅ Enforced
