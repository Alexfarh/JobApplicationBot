from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database
    database_url: str
    
    # Email
    email_mode: str = "dev"  # dev | prod
    sendgrid_api_key: str = ""  # Required for prod mode
    
    # Auth
    secret_key: str
    magic_link_ttl_minutes: int = 30
    
    # CORS (comma-separated list of allowed origins)
    allowed_origins: str = ""  # e.g., "https://yourdomain.com,https://app.yourdomain.com"
    
    # Frontend URL for magic links (defaults to first allowed_origin or localhost)
    frontend_url: str = ""
    
    # App
    debug: bool = False
    
    def get_frontend_url(self) -> str:
        """Get frontend URL, falling back to first allowed_origin or localhost."""
        if self.frontend_url:
            return self.frontend_url
        if self.allowed_origins:
            return self.allowed_origins.split(',')[0].strip()
        return "http://localhost:3000"


settings = Settings()
