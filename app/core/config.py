from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./sales_knowledge.db"
    chroma_path: str = "./chroma_db"
    claude_model: str = "claude-sonnet-4-6"

    class Config:
        env_file = ".env"


settings = Settings()
