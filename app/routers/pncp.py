from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.pncp import MODALIDADES, PNCPClient
from app.deps import get_pncp

router = APIRouter(prefix="/pncp", tags=["PNCP"])

Pagina = Annotated[int, Query(ge=1)]
TamanhoPagina = Annotated[int, Query(ge=10, le=50, description="PNCP aceita de 10 a 50")]
CNPJ = Annotated[str | None, Query(pattern=r"^\d{14}$", description="CNPJ do órgão, só dígitos")]
UF = Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")]


def _check_range(inicio: date, fim: date) -> None:
    if fim < inicio:
        raise HTTPException(422, "data_final deve ser maior ou igual a data_inicial")


@router.get("/modalidades")
async def modalidades() -> dict[int, str]:
    return MODALIDADES


@router.get("/contratacoes")
async def contratacoes(
    data_inicial: date,
    data_final: date,
    modalidade: Annotated[int, Query(description="Código da modalidade; veja /pncp/modalidades")],
    uf: UF = None,
    codigo_municipio_ibge: str | None = None,
    cnpj_orgao: CNPJ = None,
    codigo_unidade: str | None = None,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 50,
    pncp: PNCPClient = Depends(get_pncp),
):
    """Contratações (editais/avisos) publicadas no período."""
    _check_range(data_inicial, data_final)
    return await pncp.contratacoes_publicadas(
        data_inicial=data_inicial,
        data_final=data_final,
        modalidade=modalidade,
        uf=uf.upper() if uf else None,
        codigo_municipio_ibge=codigo_municipio_ibge,
        cnpj_orgao=cnpj_orgao,
        codigo_unidade=codigo_unidade,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@router.get("/contratacoes/abertas")
async def contratacoes_abertas(
    data_final: Annotated[date, Query(description="Propostas abertas até esta data")],
    modalidade: int | None = None,
    uf: UF = None,
    codigo_municipio_ibge: str | None = None,
    cnpj_orgao: CNPJ = None,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 50,
    pncp: PNCPClient = Depends(get_pncp),
):
    """Contratações com período de recebimento de propostas em aberto."""
    return await pncp.contratacoes_com_proposta_aberta(
        data_final=data_final,
        modalidade=modalidade,
        uf=uf.upper() if uf else None,
        codigo_municipio_ibge=codigo_municipio_ibge,
        cnpj_orgao=cnpj_orgao,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@router.get("/contratacoes/{cnpj_orgao}/{ano}/{sequencial}")
async def contratacao(cnpj_orgao: str, ano: int, sequencial: int, pncp: PNCPClient = Depends(get_pncp)):
    result = await pncp.contratacao(cnpj_orgao, ano, sequencial)
    if result is None:
        raise HTTPException(404, "Contratação não encontrada no PNCP")
    return result


@router.get("/contratos")
async def contratos(
    data_inicial: date,
    data_final: date,
    cnpj_orgao: CNPJ = None,
    codigo_unidade: str | None = None,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 50,
    pncp: PNCPClient = Depends(get_pncp),
):
    """Contratos e empenhos publicados no período."""
    _check_range(data_inicial, data_final)
    return await pncp.contratos(
        data_inicial=data_inicial,
        data_final=data_final,
        cnpj_orgao=cnpj_orgao,
        codigo_unidade=codigo_unidade,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@router.get("/atas")
async def atas(
    data_inicial: date,
    data_final: date,
    cnpj_orgao: CNPJ = None,
    codigo_unidade: str | None = None,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 50,
    pncp: PNCPClient = Depends(get_pncp),
):
    """Atas de registro de preço com vigência no período."""
    _check_range(data_inicial, data_final)
    return await pncp.atas(
        data_inicial=data_inicial,
        data_final=data_final,
        cnpj_orgao=cnpj_orgao,
        codigo_unidade=codigo_unidade,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )
