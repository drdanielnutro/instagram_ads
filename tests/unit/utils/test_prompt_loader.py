from pathlib import Path

import pytest

from app.utils.prompt_loader import PromptLoader, PromptNotFoundError, PromptRenderError


@pytest.fixture
def loader():
    base = Path("prompts/storybrand_fallback")
    return PromptLoader(base, required_prompts={"collector"})


def test_loader_returns_prompt(loader):
    prompt = loader.get_prompt("collector")
    assert "Curador de Inputs Essenciais" in prompt


def test_loader_renders_variables(loader):
    rendered = loader.render(
        "collector",
        {
            "nome_empresa": "Acme",
            "o_que_a_empresa_faz": "Ajudamos pessoas",
            "sexo_cliente_alvo": "masculino",
            "landing_page_context": {"foo": "bar"},
        },
    )
    assert "Acme" in rendered


def test_loader_raises_for_missing_prompt():
    with pytest.raises(PromptNotFoundError):
        PromptLoader(Path("prompts/storybrand_fallback"), required_prompts={"does_not_exist"})


def test_loader_raises_for_missing_key(loader):
    with pytest.raises(PromptRenderError):
        loader.render("collector", {"nome_empresa": "Acme"})
