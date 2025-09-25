import pytest

from helpers.user_extract_data import extract_user_input


class DummyExtraction:
    def __init__(self, cls: str, text: str, attrs: dict | None = None) -> None:
        self.extraction_class = cls
        self.extraction_text = text
        self.attributes = attrs or {}


class DummyResult:
    def __init__(self, extractions):
        self.extractions = extractions


@pytest.fixture
def patch_langextract(monkeypatch):
    from helpers import user_extract_data as ued

    def _apply(extractions):
        def fake_extract(**kwargs):  # type: ignore
            return DummyResult(extractions)

        monkeypatch.setattr(ued.lx, "extract", fake_extract)

    return _apply


def test_extract_user_input_returns_new_fields(patch_langextract, monkeypatch):
    monkeypatch.setenv('ENABLE_NEW_INPUT_FIELDS', 'true')
    monkeypatch.setenv('PREFLIGHT_SHADOW_MODE', 'false')
    patch_langextract(
        [
            DummyExtraction("landing_page_url", "https://example.com"),
            DummyExtraction("objetivo_final", "mensagens", {"normalized": "agendamentos"}),
            DummyExtraction("perfil_cliente", "mulheres empreendedoras"),
            DummyExtraction("formato_anuncio", "reels", {"normalized": "Reels"}),
            DummyExtraction("nome_empresa", "Empresa Teste"),
            DummyExtraction(
                "o_que_a_empresa_faz",
                "Consultoria de marketing para pequenos negócios",
            ),
            DummyExtraction("sexo_cliente_alvo", "mulheres", {"normalized": "feminino"}),
        ]
    )

    result = extract_user_input("dummy text")

    assert result["success"] is True
    assert result["data"]["nome_empresa"] == "Empresa Teste"
    assert result["data"]["o_que_a_empresa_faz"] == "Consultoria de marketing para pequenos negócios"
    assert result["normalized"]["sexo_cliente_alvo_norm"] == "feminino"


def test_extract_user_input_missing_required_fields_returns_errors(patch_langextract, monkeypatch):
    monkeypatch.setenv('ENABLE_NEW_INPUT_FIELDS', 'true')
    monkeypatch.setenv('PREFLIGHT_SHADOW_MODE', 'false')
    patch_langextract(
        [
            DummyExtraction("landing_page_url", "https://example.com"),
            DummyExtraction("objetivo_final", "vendas", {"normalized": "vendas"}),
            DummyExtraction("perfil_cliente", "público geral"),
            DummyExtraction("formato_anuncio", "stories", {"normalized": "Stories"}),
        ]
    )

    result = extract_user_input("dummy text")

    assert result["success"] is False
    fields_with_error = {error["field"] for error in result["errors"]}
    assert {"nome_empresa", "o_que_a_empresa_faz", "sexo_cliente_alvo"}.issubset(fields_with_error)


def test_extract_user_input_rejects_neutro_gender(patch_langextract, monkeypatch):
    monkeypatch.setenv('ENABLE_NEW_INPUT_FIELDS', 'true')
    monkeypatch.setenv('PREFLIGHT_SHADOW_MODE', 'false')
    patch_langextract(
        [
            DummyExtraction("landing_page_url", "https://example.com"),
            DummyExtraction("objetivo_final", "vendas", {"normalized": "vendas"}),
            DummyExtraction("perfil_cliente", "público geral"),
            DummyExtraction("formato_anuncio", "stories", {"normalized": "Stories"}),
            DummyExtraction("nome_empresa", "Empresa"),
            DummyExtraction("o_que_a_empresa_faz", "Loja de eletrônicos"),
            DummyExtraction("sexo_cliente_alvo", "neutro", {"normalized": None}),
        ]
    )

    result = extract_user_input("dummy text")

    assert result["success"] is False
    assert any(error["field"] == "sexo_cliente_alvo" for error in result["errors"])
