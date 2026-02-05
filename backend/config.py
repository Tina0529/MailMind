"""
Configuration settings for MailMind AI
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Zoho Mail (IMAP/SMTP - deprecated, using OAuth instead)
    ZOHO_EMAIL: str = "denyab@sparticle.com"
    ZOHO_APP_PASSWORD: Optional[str] = None

    # Zoho OAuth credentials
    ZOHO_CLIENT_ID: Optional[str] = None
    ZOHO_CLIENT_SECRET: Optional[str] = None
    ZOHO_REDIRECT_URI: str = "http://localhost:3000/oauth/callback"

    # Claude API
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/emails.db"

    # Frontend URL for CORS
    FRONTEND_URL: str = "http://localhost:3000"

    # IMAP Settings for Zoho (deprecated)
    IMAP_SERVER: str = "imap.zoho.com"
    IMAP_PORT: int = 993

    # SMTP Settings for Zoho (deprecated)
    SMTP_SERVER: str = "smtp.zoho.com"
    SMTP_PORT: int = 465

    # Learning settings
    LEARN_EMAIL_COUNT: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
