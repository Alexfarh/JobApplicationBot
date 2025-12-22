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
    
    # Auth
    secret_key: str
    magic_link_ttl_minutes: int = 30
    
    # App
    debug: bool = False


settings = Settings()
