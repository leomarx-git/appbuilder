from fastapi import HTTPException, Request

from app.clients.pncp import PNCPClient
from app.clients.transparencia import TransparenciaClient


def get_pncp(request: Request) -> PNCPClient:
    return request.app.state.pncp


def get_transparencia(request: Request) -> TransparenciaClient:
    client = request.app.state.transparencia
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="PORTAL_TRANSPARENCIA_API_KEY não configurada. Cadastre em "
            "https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email",
        )
    return client
