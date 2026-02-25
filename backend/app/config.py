from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Online Paper Reader"
    PROJECT_VERSION: str = "2.2.0"

    # 数据库配置
    DATABASE_URL: str = "postgresql://paperuser:password123@localhost:5432/paper_reader"

    # JWT 配置
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO 配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "papers"

    # 文件上传配置
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: set = {".pdf"}
    UPLOAD_DIR: str = "uploads"
    TRASH_RETENTION_DAYS: int = 30  # Days before auto-deleting trash items

    # 代理配置
    HTTP_PROXY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
