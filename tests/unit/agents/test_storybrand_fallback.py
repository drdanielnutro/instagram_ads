from types import SimpleNamespace
import json
from pathlib import Path

import pytest

from app.agents.storybrand_fallback import (
    FallbackStorybrandCompiler,
    PersistStorybrandSectionsAgent,
    _normalize_gender,
    fallback_input_collector_callback,
)
from app.agents.fallback_compiler import _normalize_cta, _extract_ctas
from app.agents.storybrand_sections import build_storybrand_section_configs

SECTION_CONFIGS = build_storybrand_section_configs()


def test_normalize_gender_variants():
    assert _normalize_gender("masc") == "masculino"
    assert _normalize_gender("Mulheres") == "feminino"
    assert _normalize_gender("neutro") == ""


def test_fallback_input_collector_success():
    state = {
        "nome_empresa": "Clínica",
        "o_que_a_empresa_faz": "Ajudamos pessoas a emagrecer",
        "sexo_cliente_alvo": "masculino",
        "storybrand_audit_trail": [],
        "fallback_input_review": {
            "nome_empresa": {"value": "Clínica"},
            "o_que_a_empresa_faz": {"value": "Ajudamos pessoas a emagrecer"},
            "sexo_cliente_alvo": {"value": "masculino"},
        },
    }
    ctx = SimpleNamespace(state=state)
    fallback_input_collector_callback(ctx)
    assert state["sexo_cliente_alvo"] == "masculino"
    assert any(event["stage"] == "collector" for event in state["storybrand_audit_trail"])


def test_fallback_input_collector_invalid_gender():
    state = {
        "nome_empresa": "Clínica",
        "o_que_a_empresa_faz": "Ajudamos pessoas a emagrecer",
        "sexo_cliente_alvo": "neutro",
        "storybrand_audit_trail": [],
        "fallback_input_review": {
            "nome_empresa": {"value": "Clínica"},
            "o_que_a_empresa_faz": {"value": "Ajudamos pessoas a emagrecer"},
            "sexo_cliente_alvo": {"value": "neutro"},
        },
    }
    ctx = SimpleNamespace(state=state, events=[])
    with pytest.raises(RuntimeError):
        fallback_input_collector_callback(ctx)


@pytest.mark.asyncio
async def test_fallback_compiler_populates_analysis():
    compiler = FallbackStorybrandCompiler()
    state = {
        "storybrand_character": "Empreendedores digitais",
        "exposition_1": "Antes, eles sofriam com vendas",
        "inciting_incident_1": "Perderam faturamento",
        "exposition_2": "Tentaram várias estratégias",
        "inciting_incident_2": "Campanhas sem retorno",
        "unmet_needs_summary": "Precisam de previsibilidade",
        "storybrand_problem_external": "Falta de clientes",
        "storybrand_problem_internal": "Insegurança",
        "storybrand_problem_philosophical": "Não é justo bons negócios quebrarem",
        "storybrand_guide": "Somos especialistas",
        "storybrand_value_proposition": "Ajudamos a escalar vendas",
        "storybrand_plan": "Diagnóstico > Plano > Execução",
        "storybrand_action": "Agende uma consultoria",
        "storybrand_failure": "Continuar perdendo dinheiro",
        "storybrand_success": "Mais receita",
        "storybrand_identity": "Empreendedor confiante",
        "landing_page_context": {},
    }
    ctx = SimpleNamespace(session=SimpleNamespace(state=state))

    async for _ in compiler._run_async_impl(ctx):
        pass

    analysis = state["storybrand_analysis"]
    assert analysis["completeness_score"] == 1.0
    assert state["landing_page_context"]["storybrand_completeness"] == 1.0
    assert "storybrand_summary" in state
    assert "storybrand_ad_context" in state


@pytest.mark.asyncio
@pytest.mark.usefixtures("tmp_path")
async def test_persist_storybrand_sections_enabled(tmp_path, monkeypatch):
    """Test that StoryBrand sections are persisted when feature flag is enabled."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DELIVERIES_BUCKET", "")

    # Mock config.persist_storybrand_sections = True
    from app import config as config_module
    monkeypatch.setattr(config_module.config, "persist_storybrand_sections", True)

    # Prepare state with 16 sections
    state = {
        "storybrand_audit_trail": [
            {"stage": "writer", "status": "completed", "section_key": "storybrand_character"}
        ],
        "storybrand_enriched_inputs": {
            "nome_empresa": {"value": "Exemplo SA", "source": "user"}
        },
    }

    # Add all 16 sections to state
    for cfg in SECTION_CONFIGS:
        state[cfg.state_key] = f"Conteúdo da seção {cfg.state_key}"

    session = SimpleNamespace(id="sess-storybrand-1", user_id="user-sb-1", state=state)
    ctx = SimpleNamespace(session=session)

    # Run the agent
    agent = PersistStorybrandSectionsAgent()
    async for _ in agent._run_async_impl(ctx):
        pass

    # Validate local file was created
    assert "storybrand_sections_saved_path" in state
    local_path = Path(state["storybrand_sections_saved_path"])
    assert local_path.exists()
    assert local_path.parent.name == "storybrand"
    assert local_path.name == "sess-storybrand-1.json"

    # Validate JSON content
    with local_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert "sections" in payload
    assert "audit" in payload
    assert "enriched_inputs" in payload
    assert "timestamp_utc" in payload

    # Validate all 16 sections are present
    sections = payload["sections"]
    assert len(sections) == len(SECTION_CONFIGS)
    for cfg in SECTION_CONFIGS:
        assert cfg.state_key in sections
        assert sections[cfg.state_key] == f"Conteúdo da seção {cfg.state_key}"

    # Validate audit and enriched inputs
    assert payload["audit"][0]["stage"] == "writer"
    assert payload["enriched_inputs"]["nome_empresa"]["value"] == "Exemplo SA"


@pytest.mark.asyncio
@pytest.mark.usefixtures("tmp_path")
async def test_persist_storybrand_sections_disabled(tmp_path, monkeypatch):
    """Test that no file is created when feature flag is disabled."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DELIVERIES_BUCKET", "")

    # Mock config.persist_storybrand_sections = False
    from app import config as config_module
    monkeypatch.setattr(config_module.config, "persist_storybrand_sections", False)

    state = {}
    for cfg in SECTION_CONFIGS:
        state[cfg.state_key] = f"Conteúdo da seção {cfg.state_key}"

    session = SimpleNamespace(id="sess-disabled-1", user_id="user-disabled-1", state=state)
    ctx = SimpleNamespace(session=session)

    # Run the agent
    agent = PersistStorybrandSectionsAgent()
    async for _ in agent._run_async_impl(ctx):
        pass

    # Validate no file was created
    assert "storybrand_sections_saved_path" not in state
    artifacts_dir = Path("artifacts/storybrand")
    if artifacts_dir.exists():
        assert not (artifacts_dir / "sess-disabled-1.json").exists()


@pytest.mark.asyncio
@pytest.mark.usefixtures("tmp_path")
async def test_persist_storybrand_sections_gcs_upload(tmp_path, monkeypatch):
    """Test that GCS upload is triggered when DELIVERIES_BUCKET is configured."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DELIVERIES_BUCKET", "gs://test-bucket")

    # Mock config.persist_storybrand_sections = True
    from app import config as config_module
    monkeypatch.setattr(config_module.config, "persist_storybrand_sections", True)

    # Mock _upload_to_gcs - patch in storybrand_fallback module where it's imported
    uploaded_data = []

    def mock_upload_to_gcs(bucket_uri, dest_path, data):
        uploaded_data.append({"bucket_uri": bucket_uri, "dest_path": dest_path, "data": data})
        return f"gs://test-bucket/{dest_path}"

    from app.agents import storybrand_fallback as sb_module
    monkeypatch.setattr(sb_module, "_upload_to_gcs", mock_upload_to_gcs)

    state = {
        "storybrand_audit_trail": [],
        "storybrand_enriched_inputs": {},
    }
    for cfg in SECTION_CONFIGS:
        state[cfg.state_key] = f"Conteúdo {cfg.state_key}"

    session = SimpleNamespace(id="sess-gcs-1", user_id="user-gcs-1", state=state)
    ctx = SimpleNamespace(session=session)

    # Run the agent
    agent = PersistStorybrandSectionsAgent()
    async for _ in agent._run_async_impl(ctx):
        pass

    # Validate GCS upload was called
    assert len(uploaded_data) == 1
    upload = uploaded_data[0]
    assert upload["bucket_uri"] == "gs://test-bucket"
    assert upload["dest_path"] == "deliveries/user-gcs-1/sess-gcs-1/storybrand_sections.json"

    # Validate state has GCS URI
    assert "storybrand_sections_gcs_uri" in state
    assert state["storybrand_sections_gcs_uri"] == "gs://test-bucket/deliveries/user-gcs-1/sess-gcs-1/storybrand_sections.json"

    # Validate uploaded data contains sections
    uploaded_json = json.loads(upload["data"].decode("utf-8"))
    assert len(uploaded_json["sections"]) == len(SECTION_CONFIGS)


# ============================================================================
# TESTES P0: Normalização de CTAs
# ============================================================================


def test_normalize_cta_exact_match():
    """CTA válido exato deve retornar inalterado."""
    assert _normalize_cta("Saiba mais") == "Saiba mais"
    assert _normalize_cta("Enviar mensagem") == "Enviar mensagem"
    assert _normalize_cta("Ligar") == "Ligar"
    assert _normalize_cta("Comprar agora") == "Comprar agora"
    assert _normalize_cta("Cadastre-se") == "Cadastre-se"


def test_normalize_cta_case_insensitive():
    """CTA válido com case diferente deve normalizar para Title Case oficial."""
    assert _normalize_cta("SAIBA MAIS") == "Saiba mais"
    assert _normalize_cta("saiba mais") == "Saiba mais"
    assert _normalize_cta("enviar mensagem") == "Enviar mensagem"
    assert _normalize_cta("ENVIAR MENSAGEM") == "Enviar mensagem"
    assert _normalize_cta("ligar") == "Ligar"
    assert _normalize_cta("COMPRAR AGORA") == "Comprar agora"
    assert _normalize_cta("cadastre-se") == "Cadastre-se"


def test_normalize_cta_synonyms():
    """Sinônimos conhecidos devem mapear para CTA oficial."""
    assert _normalize_cta("agendar") == "Enviar mensagem"
    assert _normalize_cta("agendar avaliação") == "Enviar mensagem"
    assert _normalize_cta("fale conosco") == "Enviar mensagem"
    assert _normalize_cta("entre em contato") == "Enviar mensagem"
    assert _normalize_cta("compre agora") == "Comprar agora"
    assert _normalize_cta("inscreva-se") == "Cadastre-se"
    # Case insensitive synonym matching
    assert _normalize_cta("AGENDAR") == "Enviar mensagem"
    assert _normalize_cta("Fale Conosco") == "Enviar mensagem"


def test_normalize_cta_fallback_by_objective():
    """CTA inválido com objetivo válido deve usar CTA do objetivo."""
    assert _normalize_cta("clique aqui", "agendamentos") == "Enviar mensagem"
    assert _normalize_cta("xyz123", "leads") == "Cadastre-se"
    assert _normalize_cta("invalid", "vendas") == "Comprar agora"
    assert _normalize_cta("???", "contato") == "Enviar mensagem"
    assert _normalize_cta("foobar", "awareness") == "Saiba mais"


def test_normalize_cta_default():
    """CTA inválido sem objetivo válido deve usar 'Saiba mais'."""
    assert _normalize_cta("invalid cta") == "Saiba mais"
    assert _normalize_cta("xyz123") == "Saiba mais"
    assert _normalize_cta("???") == "Saiba mais"
    # CTA inválido com objetivo inválido também usa default
    assert _normalize_cta("invalid", "objetivo_inexistente") == "Saiba mais"


def test_normalize_cta_empty():
    """None e strings vazias devem retornar 'Saiba mais' sem log."""
    assert _normalize_cta(None) == "Saiba mais"
    assert _normalize_cta("") == "Saiba mais"
    assert _normalize_cta("   ") == "Saiba mais"  # whitespace só também vira empty após strip


def test_extract_ctas_with_normalization():
    """Integração: _extract_ctas deve normalizar ambos os CTAs."""
    # Caso normal: dois CTAs válidos
    action_text = "Enviar mensagem\nSaiba mais"
    primary, secondary = _extract_ctas(action_text, "agendamentos")
    assert primary == "Enviar mensagem"
    assert secondary == "Saiba mais"

    # Caso com sinônimos
    action_text = "agendar\ncompre agora"
    primary, secondary = _extract_ctas(action_text, "vendas")
    assert primary == "Enviar mensagem"  # agendar → Enviar mensagem
    assert secondary == "Comprar agora"  # compre agora → Comprar agora

    # Caso com CTA inválido (usa fallback contextual)
    action_text = "invalid_cta\nSaiba mais"
    primary, secondary = _extract_ctas(action_text, "leads")
    assert primary == "Cadastre-se"  # fallback para objetivo "leads"
    assert secondary == "Saiba mais"

    # Caso vazio
    primary, secondary = _extract_ctas("", "agendamentos")
    assert primary == "Saiba mais"
    assert secondary == "Saiba mais"

    # Caso com apenas um CTA
    action_text = "Ligar"
    primary, secondary = _extract_ctas(action_text, "contato")
    assert primary == "Ligar"
    assert secondary == "Saiba mais"  # default para backup vazio
