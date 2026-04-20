from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://ces_user:ces_password@localhost:5432/ces"
    ANTHROPIC_API_KEY: str = ""
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8-hour work day

    model_config = {"env_file": ".env"}


settings = Settings()
