from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/ces"
    ANTHROPIC_API_KEY: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
