from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase Config
    SUPABASE_URL: str
    SUPABASE_KEY: str
    ANON_KEY: str
    JWT_SECRET: str
    SUPABASE_HOST: str
    SUPABASE_DB: str = "postgres"
    POSTGRES_PASSWORD: str
    SUPABASE_PORT: int = 5432
    SUPABASE_USER: str = "postgres"
    
    # Auth Config
    VENDOR_EMAIL: str
    VENDOR_PASSWORD: str
    
    # LLM Config
    GROQ_API_KEY: str
    LLM_MODEl: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 8000
    
    # Chat Session Config
    MAX_CONTEXT_MULTIPLIER: int = 10  # Chat limit = 10 * LLM_MAX_TOKENS
    SESSION_TIMEOUT_MINUTES: int = 5  # Session ends after 5 minutes of inactivity
    AUTO_SAVE_INTERVAL_MINUTES: int = 3  # Auto-save messages every 3 minutes
    CHAT_HISTORY_LIMIT: int = 50  # Number of recent chats to load
    MESSAGE_HISTORY_LIMIT: int = 100  # Number of messages to load per chat

    class Config:
        env_file = ".env"
        extra = "allow"
        env_file_encoding = "utf-8"

settings = Settings()