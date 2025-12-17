"""Application configuration using Pydantic Settings"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Trybe API"
    APP_VERSION: str = "0.1.0"
    VERSION: str = "0.5.0"  # For Sentry release tracking
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://trybe_user:trybe_password_dev@localhost:5432/trybe_db"
    )
    DB_ECHO: bool = Field(default=False)
    DB_POOL_SIZE: int = Field(default=20)
    DB_MAX_OVERFLOW: int = Field(default=40)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = None

    # JWT Authentication
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:5173,http://localhost:3000")

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return ["http://localhost:5173", "http://localhost:3000"]

    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = Field(default="sk_test_placeholder")  # Stripe secret key for backend
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = Field(default="noreply@trybe.app")
    FROM_NAME: str = Field(default="Trybe Platform")

    # WhatsApp (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    # File Upload
    MAX_UPLOAD_SIZE: int = Field(default=10485760)  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: str = Field(default="jpg,jpeg,png,gif,pdf,doc,docx")

    def get_allowed_extensions(self) -> List[str]:
        """Parse allowed upload extensions from comma-separated string"""
        if isinstance(self.ALLOWED_UPLOAD_EXTENSIONS, str):
            return [ext.strip() for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",")]
        return ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx"]

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    # Session
    SESSION_EXPIRE_HOURS: int = Field(default=24)

    # Platform Settings
    PLATFORM_FEE_PERCENTAGE: float = Field(default=8.0)
    STRIPE_FEE_PERCENTAGE: float = Field(default=2.9)
    STRIPE_FEE_FIXED: float = Field(default=0.30)

    # Firebase / Push Notifications
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None

    # Sentry
    SENTRY_DSN: Optional[str] = None

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"


# Global settings instance
settings = Settings()
