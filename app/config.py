from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pncp_base_url: str = "https://pncp.gov.br/api/consulta"
    transparencia_base_url: str = "https://api.portaldatransparencia.gov.br/api-de-dados"
    portal_transparencia_api_key: str = ""

    http_timeout: float = 30.0
    http_max_retries: int = 3
    user_agent: str = "appbuilder-gov-integration/0.1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
