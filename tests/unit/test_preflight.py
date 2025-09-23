import sys
from importlib import reload

import pytest
from fastapi.testclient import TestClient


class DummyLogger:
    def log_struct(self, *args, **kwargs):
        return None


class DummyLoggingClient:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    def logger(self, *_args, **_kwargs):
        return DummyLogger()


class DummyStorageClient:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    class _DummyBucket:
        def exists(self) -> bool:
            return True

        class _DummyBlob:
            def upload_from_string(self, *_args, **_kwargs) -> None:
                return None

        def blob(self, _name: str) -> 'DummyStorageClient._DummyBucket._DummyBlob':
            return DummyStorageClient._DummyBucket._DummyBlob()

    def bucket(self, _name: str) -> 'DummyStorageClient._DummyBucket':
        return DummyStorageClient._DummyBucket()


@pytest.fixture
def preflight_client(monkeypatch):
    monkeypatch.setattr('google.auth.default', lambda *args, **kwargs: (None, 'test-project'))
    monkeypatch.setattr('google.cloud.logging.Client', DummyLoggingClient)
    monkeypatch.setattr('google.cloud.storage.Client', DummyStorageClient)

    sys.modules.pop('app.server', None)
    import app.server as server

    server = reload(server)
    client = TestClient(server.app)
    return client, server


def test_preflight_includes_new_fields(preflight_client, monkeypatch):
    client, server = preflight_client

    def fake_extract_user_input(_text):
        return {
            'success': True,
            'data': {
                'landing_page_url': 'https://example.com',
                'objetivo_final': 'agendamentos',
                'perfil_cliente': 'executivos ocupados',
                'formato_anuncio': 'Reels',
                'foco': 'Campanha sazonal',
                'nome_empresa': 'Agência Exemplo',
                'o_que_a_empresa_faz': 'Marketing para profissionais liberais',
                'sexo_cliente_alvo': 'masculino',
            },
            'normalized': {
                'formato_anuncio_norm': 'Reels',
                'objetivo_final_norm': 'agendamentos',
                'sexo_cliente_alvo_norm': 'masculino',
            },
            'errors': [],
        }

    monkeypatch.setattr(server, 'extract_user_input', fake_extract_user_input)

    response = client.post('/run_preflight', json={'text': 'dummy'})
    assert response.status_code == 200
    payload = response.json()

    initial_state = payload['initial_state']
    assert initial_state['nome_empresa'] == 'Agência Exemplo'
    assert initial_state['o_que_a_empresa_faz'] == 'Marketing para profissionais liberais'
    assert initial_state['sexo_cliente_alvo'] == 'masculino'


def test_preflight_uses_defaults_for_missing_fields(preflight_client, monkeypatch):
    client, server = preflight_client

    def fake_extract_user_input(_text):
        return {
            'success': True,
            'data': {
                'landing_page_url': 'https://example.com',
                'objetivo_final': 'vendas',
                'perfil_cliente': 'publico amplo',
                'formato_anuncio': 'Feed',
                'foco': '',
                'nome_empresa': '',
                'o_que_a_empresa_faz': '',
                'sexo_cliente_alvo': '',
            },
            'normalized': {
                'formato_anuncio_norm': 'Feed',
                'objetivo_final_norm': 'vendas',
                'sexo_cliente_alvo_norm': None,
            },
            'errors': [],
        }

    monkeypatch.setattr(server, 'extract_user_input', fake_extract_user_input)

    response = client.post('/run_preflight', json={'text': 'dummy'})
    assert response.status_code == 200
    payload = response.json()

    initial_state = payload['initial_state']
    assert initial_state['nome_empresa'] == 'Empresa'
    assert initial_state['o_que_a_empresa_faz'] == ''
    assert initial_state['sexo_cliente_alvo'] == 'neutro'
