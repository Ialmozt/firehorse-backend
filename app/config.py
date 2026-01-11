import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings:
    """Application settings loaded from environment variables"""
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Proxy
    PROXY_HOST: str = os.getenv("PROXY_HOST", "host.docker.internal")
    PROXY_PORT: int = int(os.getenv("PROXY_PORT", "7891"))
    USE_PROXY: bool = os.getenv("USE_PROXY", "true").lower() == "true"
    PROXY_TYPE: str = os.getenv("PROXY_TYPE", "socks5")  # socks5 or http
    
    # Database
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "5432"))
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "postgres")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "postgres")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    
    # SSH Tunnel for PostgreSQL (if needed)
    SSH_TUNNEL_ENABLED: bool = os.getenv("SSH_TUNNEL_ENABLED", "false").lower() == "true"
    SSH_HOST: str = os.getenv("SSH_HOST", "localhost")
    SSH_PORT: int = int(os.getenv("SSH_PORT", "22"))
    SSH_USER: str = os.getenv("SSH_USER", "")
    SSH_KEY_PATH: str = os.getenv("SSH_KEY_PATH", "")
    
    # DeepSeek
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    
    # Application
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    INGRESS_SECRET: str = os.getenv("INGRESS_SECRET", "")
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    
    @property
    def proxy_url(self) -> Optional[str]:
        """Return proxy URL for HTTP requests"""
        if self.USE_PROXY:
            if self.PROXY_TYPE == "socks5":
                return f"socks5://{self.PROXY_HOST}:{self.PROXY_PORT}"
            else:
                return f"http://{self.PROXY_HOST}:{self.PROXY_PORT}"
        return None
    
    @property
    def socks_proxy_url(self) -> Optional[str]:
        """Return SOCKS5 proxy URL specifically"""
        if self.USE_PROXY and self.PROXY_TYPE == "socks5":
            return f"socks5://{self.PROXY_HOST}:{self.PROXY_PORT}"
        return None
    
    @property
    def database_url(self) -> str:
        """Return database connection string"""
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

settings = Settings()

if __name__ == "__main__":
    print(f"SUPABASE_URL: {settings.SUPABASE_URL}")
    print(f"Proxy: {settings.proxy_url if settings.USE_PROXY else 'DISABLED'}")
    print(f"LOG_LEVEL: {settings.LOG_LEVEL}")
