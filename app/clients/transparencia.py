"""Cliente da API de Dados do Portal da Transparência (CGU).

Docs: https://api.portaldatransparencia.gov.br/swagger-ui/index.html
Exige a chave gratuita no header `chave-api-dados`. Datas no formato dd/MM/yyyy.
Paginação por `pagina` (começa em 1, 15 registros por página); a API não
informa total de registros. Limite: ~90 req/min das 6h às 24h, ~300 req/min
de madrugada.
"""

from datetime import date
from typing import Any

from app.http import GovClient

AUTH_HEADER = "chave-api-dados"


def fmt_date(d: date | None) -> str | None:
    return d.strftime("%d/%m/%Y") if d else None


def page(raw: Any, pagina: int) -> dict[str, Any]:
    dados = raw or []
    return {"fonte": "portal_transparencia", "pagina": pagina, "quantidade": len(dados), "dados": dados}


class TransparenciaClient(GovClient):
    source = "portal_transparencia"

    def __init__(self, base_url: str, api_key: str, **kwargs: Any):
        super().__init__(base_url, headers={AUTH_HEADER: api_key}, **kwargs)

    async def contratos(
        self, *, codigo_orgao: str, data_inicial: date | None = None, data_final: date | None = None, pagina: int = 1
    ) -> dict[str, Any]:
        raw = await self.get(
            "/contratos",
            {
                "codigoOrgao": codigo_orgao,
                "dataInicial": fmt_date(data_inicial),
                "dataFinal": fmt_date(data_final),
                "pagina": pagina,
            },
        )
        return page(raw, pagina)

    async def contratos_por_fornecedor(
        self, *, cpf_cnpj: str, codigo_orgao: str | None = None, pagina: int = 1
    ) -> dict[str, Any]:
        raw = await self.get(
            "/contratos/cpf-cnpj",
            {"cpfCnpj": cpf_cnpj, "codigoOrgao": codigo_orgao, "pagina": pagina},
        )
        return page(raw, pagina)

    async def licitacoes(
        self, *, codigo_orgao: str, data_inicial: date | None = None, data_final: date | None = None, pagina: int = 1
    ) -> dict[str, Any]:
        raw = await self.get(
            "/licitacoes",
            {
                "codigoOrgao": codigo_orgao,
                "dataInicial": fmt_date(data_inicial),
                "dataFinal": fmt_date(data_final),
                "pagina": pagina,
            },
        )
        return page(raw, pagina)

    async def ceis(
        self, *, cpf_cnpj: str | None = None, nome: str | None = None, pagina: int = 1
    ) -> dict[str, Any]:
        """Cadastro de Empresas Inidôneas e Suspensas."""
        raw = await self.get(
            "/ceis", {"codigoSancionado": cpf_cnpj, "nomeSancionado": nome, "pagina": pagina}
        )
        return page(raw, pagina)

    async def cnep(
        self, *, cpf_cnpj: str | None = None, nome: str | None = None, pagina: int = 1
    ) -> dict[str, Any]:
        """Cadastro Nacional de Empresas Punidas (Lei Anticorrupção)."""
        raw = await self.get(
            "/cnep", {"codigoSancionado": cpf_cnpj, "nomeSancionado": nome, "pagina": pagina}
        )
        return page(raw, pagina)
