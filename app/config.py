from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None  # Alias for compatibility
    
    # DeepSeek API
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    
    # Kwork (optional for testing)
    KWORK_API_KEY: Optional[str] = None
    KWORK_WEBHOOK_SECRET: Optional[str] = None
    
    # App
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database (optional)
    DATABASE_HOST: Optional[str] = None
    DATABASE_PORT: Optional[str] = None
    DATABASE_NAME: Optional[str] = None
    DATABASE_USER: Optional[str] = None
    DATABASE_PASSWORD: Optional[str] = None
    
    # Proxy (optional)
    PROXY_HOST: Optional[str] = None
    PROXY_PORT: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Ingress secret
    INGRESS_SECRET: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use SUPABASE_SERVICE_KEY as fallback for SUPABASE_SERVICE_ROLE_KEY
        if not self.SUPABASE_SERVICE_ROLE_KEY and self.SUPABASE_SERVICE_KEY:
            self.SUPABASE_SERVICE_ROLE_KEY = self.SUPABASE_SERVICE_KEY

settings = Settings()
