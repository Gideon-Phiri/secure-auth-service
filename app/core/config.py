from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@db:5432/authdb",
        description="Database connection URL",
    )
    SECRET_KEY: str = Field(
        default="changeme", description="Secret key for JWT token generation"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15, description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiration time in days"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    DEBUG: bool = Field(default=False, description="Debug mode")
    MAX_LOGIN_ATTEMPTS: int = Field(
        default=5, description="Maximum login attempts before lockout"
    )
    LOCKOUT_DURATION_MINUTES: int = Field(
        default=15, description="Account lockout duration in minutes"
    )

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
