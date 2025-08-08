from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://trading_user:secure_password_123@postgres:5432/trading_db"
    
    # Redis
    REDIS_URL: str = "redis://default:redis_password_123@redis:6379/0"
    
    # Security
    SECRET_KEY: str = "your_super_secret_jwt_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Environment
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000"
    ]
    
    # Trusted hosts for production
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "*.amazonaws.com"
    ]
    
    # BitGet API Configuration
    BITGET_API_KEY: str = ""
    BITGET_SECRET_KEY: str = ""
    BITGET_PASSPHRASE: str = ""
    BITGET_SANDBOX: bool = False
    
    # Trading Bot Integration
    AWS_TRADING_BOT_URL: str = "http://localhost:8001"
    AWS_TRADING_BOT_API_KEY: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Cache TTL (seconds)
    CACHE_TTL_SHORT: int = 300    # 5 minutes
    CACHE_TTL_MEDIUM: int = 1800  # 30 minutes
    CACHE_TTL_LONG: int = 3600    # 1 hour
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
EOF < /dev/null
