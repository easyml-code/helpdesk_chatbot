from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    ANON_KEY: str
    JWT_SECRET: str
    SUPABASE_HOST: str
    SUPABASE_DB: str = "postgres"
    POSTGRES_PASSWORD: str
    SUPABASE_PORT: int = 5432
    SUPABASE_USER: str = "postgres"
    VENDOR_EMAIL: str
    VENDOR_PASSWORD: str
    GROQ_API_KEY: str
    LLM_MODEl: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE: float
    LLM_MAX_TOKENS: int

    class Config:
        env_file = ".env"
        extra = "allow"
        env_file_encoding = "utf-8"

settings = Settings()