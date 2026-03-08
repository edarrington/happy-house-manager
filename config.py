"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Session / JWT
    session_secret_key: str = "dev-secret-change-in-production"
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Cosmos DB
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database_name: str = "happy-house-manager"
    cosmos_users_container: str = "users"

    # Key Vault
    key_vault_url: str = ""

    # Azure AD (for local dev without managed identity)
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant_id: str = ""

    # App
    app_base_url: str = "http://localhost:8000"
    environment: str = "development"

    @field_validator("google_redirect_uri", mode="before")
    @classmethod
    def build_redirect_uri(cls, v, values):
        # Allow explicit override; otherwise default is fine
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
