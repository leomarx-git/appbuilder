"""Cliente da API de Consultas do PNCP (Portal Nacional de Contratações Públicas).

Docs: https://pncp.gov.br/api/consulta/swagger-ui/index.html
API pública, sem autenticação. Datas no formato yyyyMMdd.
"""

from datetime import date
from typing import Any

from app.http import GovClient

# Tabela de domínio "Modalidade de Contratação" do PNCP.
MODALIDADES = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
}


def fmt_date(d: date | None) -> str | None:
    return d.strftime("%Y%m%d") if d else None


def normalize_page(raw: Any, pagina: int) -> dict[str, Any]:
    """Converte o envelope paginado do PNCP (ou 204) num formato estável."""
    if not raw:
        return {"fonte": "pncp", "pagina": pagina, "total_registros": 0, "total_paginas": 0, "dados": []}
    return {
        "fonte": "pncp",
        "pagina": raw.get("numeroPagina", pagina),
        "total_registros": raw.get("totalRegistros", 0),
        "total_paginas": raw.get("totalPaginas", 0),
        "dados": raw.get("data") or [],
    }


class PNCPClient(GovClient):
    source = "pncp"

    async def contratacoes_publicadas(
        self,
        *,
        data_inicial: date,
        data_final: date,
        modalidade: int,
        uf: str | None = None,
        codigo_municipio_ibge: str | None = None,
        cnpj_orgao: str | None = None,
        codigo_unidade: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 50,
    ) -> dict[str, Any]:
        raw = await self.get(
            "/v1/contratacoes/publicacao",
            {
                "dataInicial": fmt_date(data_inicial),
                "dataFinal": fmt_date(data_final),
                "codigoModalidadeContratacao": modalidade,
                "uf": uf,
                "codigoMunicipioIbge": codigo_municipio_ibge,
                "cnpj": cnpj_orgao,
                "codigoUnidadeAdministrativa": codigo_unidade,
                "pagina": pagina,
                "tamanhoPagina": tamanho_pagina,
            },
        )
        return normalize_page(raw, pagina)

    async def contratacoes_com_proposta_aberta(
        self,
        *,
        data_final: date,
        modalidade: int | None = None,
        uf: str | None = None,
        codigo_municipio_ibge: str | None = None,
        cnpj_orgao: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 50,
    ) -> dict[str, Any]:
        raw = await self.get(
            "/v1/contratacoes/proposta",
            {
                "dataFinal": fmt_date(data_final),
                "codigoModalidadeContratacao": modalidade,
                "uf": uf,
                "codigoMunicipioIbge": codigo_municipio_ibge,
                "cnpj": cnpj_orgao,
                "pagina": pagina,
                "tamanhoPagina": tamanho_pagina,
            },
        )
        return normalize_page(raw, pagina)

    async def contratacao(self, cnpj_orgao: str, ano: int, sequencial: int) -> dict[str, Any] | None:
        return await self.get(f"/v1/orgaos/{cnpj_orgao}/compras/{ano}/{sequencial}")

    async def contratos(
        self,
        *,
        data_inicial: date,
        data_final: date,
        cnpj_orgao: str | None = None,
        codigo_unidade: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 50,
    ) -> dict[str, Any]:
        raw = await self.get(
            "/v1/contratos",
            {
                "dataInicial": fmt_date(data_inicial),
                "dataFinal": fmt_date(data_final),
                "cnpjOrgao": cnpj_orgao,
                "codigoUnidadeAdministrativa": codigo_unidade,
                "pagina": pagina,
                "tamanhoPagina": tamanho_pagina,
            },
        )
        return normalize_page(raw, pagina)

    async def atas(
        self,
        *,
        data_inicial: date,
        data_final: date,
        cnpj_orgao: str | None = None,
        codigo_unidade: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 50,
    ) -> dict[str, Any]:
        raw = await self.get(
            "/v1/atas",
            {
                "dataInicial": fmt_date(data_inicial),
                "dataFinal": fmt_date(data_final),
                "cnpj": cnpj_orgao,
                "codigoUnidadeAdministrativa": codigo_unidade,
                "pagina": pagina,
                "tamanhoPagina": tamanho_pagina,
            },
        )
        return normalize_page(raw, pagina)
