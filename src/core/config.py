from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str = Field(
        validation_alias=AliasChoices("SUPABASE_KEY", "SUPABASE_PUBLISHABLE_KEY")
    )
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8081,http://127.0.0.1:8081,http://localhost:19006"
    )
    api_secret_token: str = "yalla-secret-token"  # Static fallback token for MVP security validation

    # TheFork integration — empty api_key activates mock mode for MVP demos
    thefork_api_key: str = ""
    thefork_base_url: str = "https://api.thefork.io/manager/v1"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
