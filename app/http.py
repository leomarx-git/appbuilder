"""Cliente HTTP compartilhado com retry para as APIs do governo.

As duas APIs são instáveis em horário de pico e o Portal da Transparência
aplica limite de requisições por minuto (HTTP 429), então tentamos de novo
com backoff exponencial em 429/5xx e em erros de rede.
"""

import asyncio
from typing import Any

import httpx

RETRY_STATUS = {429, 500, 502, 503, 504}


class UpstreamError(Exception):
    """Falha ao consultar uma API externa."""

    def __init__(self, source: str, status_code: int | None, message: str):
        self.source = source
        self.status_code = status_code
        self.message = message
        super().__init__(f"{source}: {message} (status={status_code})")


class GovClient:
    source = "gov"

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        backoff_base: float = 1.0,
    ):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"Accept": "application/json", **(headers or {})},
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._client.get(path, params=clean)
            except httpx.TransportError as exc:
                last_exc = exc
            else:
                if resp.status_code == 204:
                    return None
                if resp.status_code < 400:
                    return resp.json() if resp.content else None
                if resp.status_code not in RETRY_STATUS:
                    raise UpstreamError(self.source, resp.status_code, _error_text(resp))
                last_exc = UpstreamError(self.source, resp.status_code, _error_text(resp))

            if attempt < self.max_retries:
                await asyncio.sleep(self._delay(attempt, last_exc))

        if isinstance(last_exc, UpstreamError):
            raise last_exc
        raise UpstreamError(self.source, None, f"falha de rede: {last_exc}")

    def _delay(self, attempt: int, exc: Exception | None) -> float:
        return self.backoff_base * (2**attempt)


def _error_text(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict):
            return str(body.get("message") or body.get("erro") or body.get("error") or body)
        return str(body)
    except ValueError:
        return resp.text[:500] or resp.reason_phrase
