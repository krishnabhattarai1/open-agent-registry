"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OAR_")

    database_url: str = "postgresql+asyncpg://oar:oar_dev@localhost:5432/oar"
    api_key_prefix: str = "oar_"
    page_size_default: int = 20
    page_size_max: int = 100

    # Extension flags (all off by default)
    enable_semantic_search: bool = False
    enable_federation: bool = False
    enable_webhooks: bool = False


settings = Settings()
