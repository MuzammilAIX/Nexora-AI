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

    # Gmail OAuth (Google Cloud Console -> APIs & Services -> Credentials)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = (
        "http://127.0.0.1:8001/api/v1/integrations/gmail/callback"
    )

    # Fernet key for encrypting OAuth tokens at rest in integration_credentials.
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    OAUTH_TOKEN_ENCRYPTION_KEY: str = ""
    TAVILY_API_KEY: str = ""
    DATABASE_URL: str = "postgresql+psycopg://nexora_user:change_me@localhost:5432/nexora_db"

    JWT_SECRET: str = "change_me_in_production_use_a_long_random_string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # Integrations
    HUBSPOT_ACCESS_TOKEN: str = ""
    FERNET_KEY: str = ""
    RESEND_API_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"

    # Gmail SMTP (used while no domain is verified in Resend)
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    MAIL_FROM_NAME: str = "Nexora AI"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
