from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.clients.pncp import PNCPClient
from app.clients.transparencia import TransparenciaClient
from app.config import Settings, get_settings
from app.http import UpstreamError
from app.routers import pncp, transparencia


def create_app(settings: Settings | None = None, **client_kwargs) -> FastAPI:
    settings = settings or get_settings()
    common = {
        "timeout": settings.http_timeout,
        "max_retries": settings.http_max_retries,
        **client_kwargs,
    }

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pncp = PNCPClient(settings.pncp_base_url, **common)
        app.state.transparencia = (
            TransparenciaClient(settings.transparencia_base_url, settings.portal_transparencia_api_key, **common)
            if settings.portal_transparencia_api_key
            else None
        )
        yield
        await app.state.pncp.aclose()
        if app.state.transparencia:
            await app.state.transparencia.aclose()

    app = FastAPI(
        title="AppBuilder – APIs Governamentais",
        description="Fachada REST para o PNCP e o Portal da Transparência.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(UpstreamError)
    async def upstream_error(_: Request, exc: UpstreamError):
        status = 504 if exc.status_code is None else 502
        if exc.status_code in (401, 403):
            msg = "Chave da API recusada pela fonte. Verifique PORTAL_TRANSPARENCIA_API_KEY."
        else:
            msg = exc.message
        return JSONResponse(
            status_code=status,
            content={"detail": msg, "fonte": exc.source, "status_fonte": exc.status_code},
        )

    @app.get("/health", tags=["infra"])
    async def health():
        return {"status": "ok", "transparencia_configurada": bool(settings.portal_transparencia_api_key)}

    app.include_router(pncp.router)
    app.include_router(transparencia.router)
    return app


app = create_app()
