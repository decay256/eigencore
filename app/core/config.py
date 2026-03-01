from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Eigencore"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://eigencore:eigencore@localhost:5432/eigencore"
    
    # JWT
    secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # OAuth - Steam
    steam_api_key: str | None = None
    steam_redirect_uri: str = "http://localhost:8000/auth/steam/callback"
    
    # OAuth - Discord
    discord_client_id: str | None = None
    discord_client_secret: str | None = None
    discord_redirect_uri: str = "http://localhost:8000/auth/discord/callback"
    
    # OAuth - Google
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    
    # Email Service - Resend API
    resend_api_key: str | None = None
    resend_from_email: str = "EigenCore <onboarding@resend.dev>"
    
    # Frontend URL for email links
    frontend_url: str = "http://localhost:8080"
    base_url: str = "http://localhost:8080"  # Legacy, use frontend_url
    
    # CORS
    cors_origins: str = "http://localhost:8080,http://localhost:3000"  # Comma-separated allowed origins
    
    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
