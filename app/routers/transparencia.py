import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.transparencia import TransparenciaClient
from app.deps import get_transparencia

router = APIRouter(prefix="/transparencia", tags=["Portal da Transparência"])

Pagina = Annotated[int, Query(ge=1)]
CodigoOrgao = Annotated[str, Query(description="Código SIAFI do órgão (ex.: 26000 = Ministério da Educação)")]
Documento = Annotated[str, Query(pattern=r"^(\d{11}|\d{14})$", description="CPF ou CNPJ, só dígitos")]


def _check_range(inicio: date | None, fim: date | None) -> None:
    if inicio and fim and fim < inicio:
        raise HTTPException(422, "data_final deve ser maior ou igual a data_inicial")


@router.get("/contratos")
async def contratos(
    codigo_orgao: CodigoOrgao,
    data_inicial: date | None = None,
    data_final: date | None = None,
    pagina: Pagina = 1,
    api: TransparenciaClient = Depends(get_transparencia),
):
    _check_range(data_inicial, data_final)
    return await api.contratos(
        codigo_orgao=codigo_orgao, data_inicial=data_inicial, data_final=data_final, pagina=pagina
    )


@router.get("/contratos/fornecedor/{cpf_cnpj}")
async def contratos_por_fornecedor(
    cpf_cnpj: str,
    codigo_orgao: str | None = None,
    pagina: Pagina = 1,
    api: TransparenciaClient = Depends(get_transparencia),
):
    return await api.contratos_por_fornecedor(cpf_cnpj=cpf_cnpj, codigo_orgao=codigo_orgao, pagina=pagina)


@router.get("/licitacoes")
async def licitacoes(
    codigo_orgao: CodigoOrgao,
    data_inicial: date | None = None,
    data_final: date | None = None,
    pagina: Pagina = 1,
    api: TransparenciaClient = Depends(get_transparencia),
):
    """O Portal limita o período a no máximo 1 mês por consulta."""
    _check_range(data_inicial, data_final)
    return await api.licitacoes(
        codigo_orgao=codigo_orgao, data_inicial=data_inicial, data_final=data_final, pagina=pagina
    )


@router.get("/sancoes/ceis")
async def ceis(
    cpf_cnpj: Documento | None = None,
    nome: str | None = None,
    pagina: Pagina = 1,
    api: TransparenciaClient = Depends(get_transparencia),
):
    return await api.ceis(cpf_cnpj=cpf_cnpj, nome=nome, pagina=pagina)


@router.get("/sancoes/cnep")
async def cnep(
    cpf_cnpj: Documento | None = None,
    nome: str | None = None,
    pagina: Pagina = 1,
    api: TransparenciaClient = Depends(get_transparencia),
):
    return await api.cnep(cpf_cnpj=cpf_cnpj, nome=nome, pagina=pagina)


@router.get("/sancoes/{cpf_cnpj}")
async def sancoes(cpf_cnpj: str, api: TransparenciaClient = Depends(get_transparencia)):
    """Consulta CEIS e CNEP de uma vez e diz se o fornecedor tem sanção registrada."""
    if not (cpf_cnpj.isdigit() and len(cpf_cnpj) in (11, 14)):
        raise HTTPException(422, "Informe CPF (11) ou CNPJ (14 dígitos), só números")
    ceis_res, cnep_res = await asyncio.gather(api.ceis(cpf_cnpj=cpf_cnpj), api.cnep(cpf_cnpj=cpf_cnpj))
    return {
        "cpf_cnpj": cpf_cnpj,
        "sancionado": bool(ceis_res["dados"] or cnep_res["dados"]),
        "ceis": ceis_res["dados"],
        "cnep": cnep_res["dados"],
        "observacao": "Mostra só a 1ª página de cada cadastro (até 15 registros).",
    }
