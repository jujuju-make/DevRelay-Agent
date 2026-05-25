from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DevRelay"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str 
    redis_url: str 
    chat_history_ttl_seconds: int = 86_400
    chat_history_key_prefix: str = "devrelay:chat:"

    openai_api_key: str
    openai_api_base: str | None = None
    openai_model: str

    github_token: str
    github_api_base: str = "https://api.github.com"

    serper_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()




