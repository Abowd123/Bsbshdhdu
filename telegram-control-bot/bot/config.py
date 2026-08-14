from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """إعدادات بوت التحكم — تُقرأ من .env فقط، لا قيم افتراضية للأسرار."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # توكن بوت تيليجرام (من BotFather)
    TELEGRAM_BOT_TOKEN: str

    # الـ user_id الوحيد المسموح له بالتحدث مع البوت. أي شخص آخر يُتجاهل تمامًا.
    TELEGRAM_ALLOWED_USER_ID: int

    # عنوان REST API الخاص بالباك اند (داخل شبكة docker-compose)
    WOLFHOST_API_BASE_URL: str = "http://backend:8000/api/v1"

    # مفتاح API ثابت (نفس BOT_CONTROL_API_KEY في .env الرئيسي للمشروع)
    WOLFHOST_API_KEY: str

    # مهلة الاتصال بالـ API (ثواني)
    API_TIMEOUT_SECONDS: float = 30.0

    # الحد الأقصى لحجم الملف الذي يمكن تحميله عبر تيليجرام (تيليجرام نفسه يحدد 20MB للبوتات القياسية)
    MAX_TELEGRAM_FILE_MB: int = 20

    # عدد العناصر في كل صفحة عند استخدام القوائم المُقسّمة (Pagination)
    PAGE_SIZE: int = 6

    # الفاصل الزمني (ثانية) لتحديث السجلات الحية عند تفعيل وضع "Live"
    LOG_LIVE_REFRESH_SECONDS: float = 4.0

    # الحد الأقصى لعدد الأسطر المعروضة من السجلات في رسالة واحدة (حدود تيليجرام 4096 حرف)
    LOG_TAIL_DEFAULT: int = 100


settings = Settings()
