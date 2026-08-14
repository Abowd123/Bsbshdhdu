from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Wolf Host"
    ENVIRONMENT: str = "production"
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str
    REDIS_URL: str

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    DOCKER_NETWORK_NAME: str = "wolfhost_bots_net"
    DOCKER_IMAGE_PYTHON: str = "python:3.12-slim"
    BOTS_STORAGE_PATH: str = "/var/wolfhost/bots"

    # حدود ثابتة للاستخدام الشخصي (مستخدم واحد، بدون نظام خطط/فوترة)
    MAX_BOTS: int = 20
    BOT_CPU_LIMIT: float = 1.0
    BOT_RAM_LIMIT_MB: int = 1024
    BOT_STORAGE_LIMIT_MB: int = 10240
    BOT_PROCESS_LIMIT: int = 128

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@wolfhost.local"

    MAX_UPLOAD_SIZE_MB: int = 200

    RATE_LIMIT_PER_MINUTE: int = 60

    ADMIN_EMAIL: str = ""

    # مفتاح API ثابت لاستخدام تكاملات خارجية (مثل بوت تيليجرام التحكمي)
    # يمنح صاحب الحساب (ADMIN_EMAIL) نفس صلاحيات get_current_user دون تسجيل دخول JWT
    BOT_CONTROL_API_KEY: str = ""


settings = Settings()
