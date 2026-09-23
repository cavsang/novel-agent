"""
전역 설정. .env / 환경변수를 읽어 Settings 객체로 노출한다.
"""

from __future__ import annotations

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]
OPEN_AI_KEY = os.environ["OPENAI_API_KEY"]



class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "novel_agent"
    postgres_user: str = "novel_agent"
    postgres_password: str = "change_me"
    database_url: str | None = DATABASE_URL

    redis_url: str = "redis://localhost:6379/0"

    # "memory" (STEP 1 로컬 개발) | "postgres" (STEP 2+ 영속 checkpoint)
    checkpointer_backend: str = "memory"

    llm_provider: str = "openai"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = OPEN_AI_KEY
    google_api_key: str | None = None

    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "novel-agent"

    @property
    def sqlalchemy_database_url(self) -> str:
        #if self.database_url:
        return self.database_url
        # return (
        #     f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
        #     f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        # )


settings = Settings()
