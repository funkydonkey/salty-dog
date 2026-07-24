"""Конфигурация приложения из переменных окружения."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VAULT_PATH: str = ""
    PORT: int = 8000
    APP_ENV: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
