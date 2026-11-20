from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Nexora AI"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    TAVILY_API_KEY: str = ""
    DATABASE_URL: str = "postgresql+psycopg://nexora_user:change_me@localhost:5432/nexora_db"

    JWT_SECRET: str = "change_me_in_production_use_a_long_random_string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # Integrations
    HUBSPOT_ACCESS_TOKEN: str = ""
    FERNET_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
