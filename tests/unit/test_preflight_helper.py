import types

from helpers.user_extract_data import extract_user_input


class DummyExtraction:
    def __init__(self, cls: str, text: str, attrs: dict | None = None) -> None:
        self.extraction_class = cls
        self.extraction_text = text
        self.attributes = attrs or {}


class DummyResult:
    def __init__(self, extractions):
        self.extractions = extractions


def test_preflight_success(monkeypatch):
    # Arrange: monkeypatch langextract.extract to return a deterministic dummy result
    from helpers import user_extract_data as ued

    def fake_extract(**kwargs):  # type: ignore
        return DummyResult(
            [
                DummyExtraction("landing_page_url", "https://example.com/landing"),
                DummyExtraction("objetivo_final", "mensagens no WhatsApp", {"normalized": "agendamentos"}),
                DummyExtraction("perfil_cliente", "homens 35-50, executivos"),
                DummyExtraction("formato_anuncio", "reels", {"normalized": "Reels"}),
                DummyExtraction("foco", "não engordar no inverno"),
            ]
        )

    monkeypatch.setattr(ued.lx, "extract", fake_extract)

    # Act
    text = (
        "landing_page_url: https://example.com/landing\n"
        "objetivo_final: mensagens no WhatsApp\n"
        "perfil_cliente: homens 35-50, executivos\n"
        "formato_anuncio: Reels\n"
        "foco: não engordar no inverno\n"
    )
    result = extract_user_input(text)

    # Assert
    assert result["success"] is True
    assert result["normalized"]["formato_anuncio_norm"] == "Reels"
    assert result["normalized"]["objetivo_final_norm"] == "agendamentos"
    assert result["data"]["landing_page_url"] == "https://example.com/landing"
    assert not result["errors"]


def test_preflight_invalid_format(monkeypatch):
    from helpers import user_extract_data as ued

    def fake_extract(**kwargs):  # type: ignore
        return DummyResult(
            [
                DummyExtraction("landing_page_url", "https://example.com/landing"),
                DummyExtraction("objetivo_final", "compras"),
                DummyExtraction("perfil_cliente", "homens 35-50, executivos"),
                DummyExtraction("formato_anuncio", "anuncio rapido", {"normalized": ""}),
            ]
        )

    monkeypatch.setattr(ued.lx, "extract", fake_extract)

    text = (
        "landing_page_url: https://example.com/landing\n"
        "objetivo_final: compras\n"
        "perfil_cliente: homens 35-50, executivos\n"
        "formato_anuncio: anuncio rapido\n"
    )
    result = extract_user_input(text)

    assert result["success"] is False
    assert any(e.get("field") == "formato_anuncio" for e in result["errors"])  # invalid format

