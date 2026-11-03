"""Testes do serviço: verificam como montamos as requisições para as fontes
(parâmetros, formato de data, header de autenticação) e como tratamos as
respostas e erros. As APIs externas são simuladas com respx."""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

PNCP = "https://pncp.test/api/consulta"
CGU = "https://cgu.test/api-de-dados"


def make_client(api_key: str = "chave-teste") -> TestClient:
    settings = Settings(
        pncp_base_url=PNCP,
        transparencia_base_url=CGU,
        portal_transparencia_api_key=api_key,
        http_max_retries=2,
        _env_file=None,
    )
    return TestClient(create_app(settings, backoff_base=0))


@pytest.fixture
def client():
    with make_client() as c:
        yield c


@respx.mock
def test_pncp_contratacoes_formata_parametros(client):
    route = respx.get(f"{PNCP}/v1/contratacoes/publicacao").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"numeroControlePNCP": "x"}], "totalRegistros": 1, "totalPaginas": 1, "numeroPagina": 1},
        )
    )
    r = client.get(
        "/pncp/contratacoes",
        params={"data_inicial": "2026-10-01", "data_final": "2026-10-31", "modalidade": 6, "uf": "sp"},
    )
    assert r.status_code == 200
    assert r.json() == {
        "fonte": "pncp",
        "pagina": 1,
        "total_registros": 1,
        "total_paginas": 1,
        "dados": [{"numeroControlePNCP": "x"}],
    }
    params = route.calls.last.request.url.params
    assert params["dataInicial"] == "20261001"
    assert params["dataFinal"] == "20261031"
    assert params["codigoModalidadeContratacao"] == "6"
    assert params["uf"] == "SP"
    assert "cnpj" not in params


@respx.mock
def test_pncp_204_vira_lista_vazia(client):
    respx.get(f"{PNCP}/v1/contratos").mock(return_value=httpx.Response(204))
    r = client.get("/pncp/contratos", params={"data_inicial": "2026-10-01", "data_final": "2026-10-02"})
    assert r.status_code == 200
    assert r.json()["dados"] == []
    assert r.json()["total_registros"] == 0


@respx.mock
def test_pncp_atas_usa_parametro_cnpj(client):
    route = respx.get(f"{PNCP}/v1/atas").mock(return_value=httpx.Response(204))
    client.get(
        "/pncp/atas",
        params={"data_inicial": "2026-10-01", "data_final": "2026-10-02", "cnpj_orgao": "00394445000101"},
    )
    assert route.calls.last.request.url.params["cnpj"] == "00394445000101"


def test_intervalo_invertido_e_rejeitado(client):
    r = client.get("/pncp/contratos", params={"data_inicial": "2026-10-10", "data_final": "2026-10-01"})
    assert r.status_code == 422


@respx.mock
def test_pncp_contratacao_nao_encontrada(client):
    respx.get(f"{PNCP}/v1/orgaos/00394445000101/compras/2026/5").mock(return_value=httpx.Response(204))
    assert client.get("/pncp/contratacoes/00394445000101/2026/5").status_code == 404


@respx.mock
def test_retry_em_429_e_depois_sucesso(client):
    route = respx.get(f"{PNCP}/v1/contratos").mock(
        side_effect=[httpx.Response(429), httpx.Response(503), httpx.Response(204)]
    )
    r = client.get("/pncp/contratos", params={"data_inicial": "2026-10-01", "data_final": "2026-10-02"})
    assert r.status_code == 200
    assert route.call_count == 3


@respx.mock
def test_erro_persistente_vira_502(client):
    respx.get(f"{PNCP}/v1/contratos").mock(return_value=httpx.Response(500, json={"message": "fora do ar"}))
    r = client.get("/pncp/contratos", params={"data_inicial": "2026-10-01", "data_final": "2026-10-02"})
    assert r.status_code == 502
    assert r.json() == {"detail": "fora do ar", "fonte": "pncp", "status_fonte": 500}


@respx.mock
def test_transparencia_envia_chave_e_data_brasileira(client):
    route = respx.get(f"{CGU}/contratos").mock(return_value=httpx.Response(200, json=[{"id": 1}]))
    r = client.get(
        "/transparencia/contratos",
        params={"codigo_orgao": "26000", "data_inicial": "2026-10-01", "data_final": "2026-10-31"},
    )
    assert r.status_code == 200
    assert r.json()["dados"] == [{"id": 1}]
    req = route.calls.last.request
    assert req.headers["chave-api-dados"] == "chave-teste"
    assert req.url.params["dataInicial"] == "01/10/2026"
    assert req.url.params["codigoOrgao"] == "26000"


@respx.mock
def test_sancoes_combina_ceis_e_cnep(client):
    respx.get(f"{CGU}/ceis").mock(return_value=httpx.Response(200, json=[{"id": 9}]))
    respx.get(f"{CGU}/cnep").mock(return_value=httpx.Response(200, json=[]))
    r = client.get("/transparencia/sancoes/12345678000199")
    assert r.status_code == 200
    body = r.json()
    assert body["sancionado"] is True
    assert body["ceis"] == [{"id": 9}]
    assert body["cnep"] == []


def test_sancoes_valida_documento(client):
    assert client.get("/transparencia/sancoes/123").status_code == 422


@respx.mock
def test_chave_recusada_vira_mensagem_clara(client):
    respx.get(f"{CGU}/ceis").mock(return_value=httpx.Response(401))
    r = client.get("/transparencia/sancoes/ceis", params={"cpf_cnpj": "12345678000199"})
    assert r.status_code == 502
    assert "PORTAL_TRANSPARENCIA_API_KEY" in r.json()["detail"]


def test_sem_chave_retorna_503():
    with make_client(api_key="") as c:
        r = c.get("/transparencia/sancoes/12345678000199")
        assert r.status_code == 503
        assert c.get("/health").json()["transparencia_configurada"] is False
