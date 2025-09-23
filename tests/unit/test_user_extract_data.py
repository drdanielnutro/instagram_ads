import pytest

from helpers.user_extract_data import extract_user_input

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


def test_extract_user_input_returns_new_fields(patch_langextract):
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


def test_extract_user_input_gender_default_neutro(patch_langextract):
    patch_langextract(
        [
            DummyExtraction("landing_page_url", "https://example.com"),
            DummyExtraction("objetivo_final", "vendas", {"normalized": "vendas"}),
            DummyExtraction("perfil_cliente", "público geral"),
            DummyExtraction("formato_anuncio", "stories", {"normalized": "Stories"}),
            DummyExtraction("nome_empresa", "Empresa"),
            DummyExtraction("o_que_a_empresa_faz", "Loja de eletrônicos"),
        ]
    )

    result = extract_user_input("dummy text")

    assert result["normalized"]["sexo_cliente_alvo_norm"] == "neutro"
    assert result["data"].get("sexo_cliente_alvo") is None
    assert result["success"] is True
