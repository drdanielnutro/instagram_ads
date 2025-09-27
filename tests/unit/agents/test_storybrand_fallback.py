from types import SimpleNamespace

import pytest

from app.agents.storybrand_fallback import (
    FallbackStorybrandCompiler,
    _normalize_gender,
    fallback_input_collector_callback,
)


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
    ctx = SimpleNamespace(state=state)
    with pytest.raises(ValueError):
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
