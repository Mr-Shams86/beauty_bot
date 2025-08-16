import os
from dotenv import load_dotenv

load_dotenv()

def as_bool(s: str | None, default: bool = False) -> bool:
    if s is None:
        return default
    return s.lower() in {"1", "true", "yes", "y", "on"}

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
DEBUG = as_bool(os.getenv("DEBUG"), False)

# Timezone
TZ = os.getenv("TZ", "Asia/Tashkent")

# Google
GCAL_CREDENTIALS_FILE = os.getenv("GCAL_CREDENTIALS_FILE")
GCAL_CALENDAR_ID = os.getenv("GCAL_CALENDAR_ID")

# DB & Redis
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

required = {
    "BOT_TOKEN": TOKEN,
    "ADMIN_ID": ADMIN_ID_RAW,
    "GCAL_CREDENTIALS_FILE": GCAL_CREDENTIALS_FILE,
    "GCAL_CALENDAR_ID": GCAL_CALENDAR_ID,
    "DATABASE_URL": DATABASE_URL,
}
missing = [k for k, v in required.items() if not v]
if missing:
    raise RuntimeError(f"Отсутствуют переменные окружения: {', '.join(missing)}")

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError("ADMIN_ID должен быть числом")

if not os.path.exists(GCAL_CREDENTIALS_FILE):
    raise RuntimeError(f"GCAL_CREDENTIALS_FILE не найден: {GCAL_CREDENTIALS_FILE}")

if DEBUG:
    def mask(s: str, head: int = 4, tail: int = 4) -> str:
        if not s:
            return "None"
        if len(s) <= head + tail:
            return "*" * len(s)
        return f"{s[:head]}...{s[-tail:]}"

    print("⚙️  Конфиг загружен:")
    print(f"  BOT_TOKEN: {mask(TOKEN)}")
    print(f"  ADMIN_ID: {ADMIN_ID}")
    print(f"  GCAL_CREDENTIALS_FILE: {GCAL_CREDENTIALS_FILE}")
    print(f"  GCAL_CALENDAR_ID: {mask(GCAL_CALENDAR_ID, 3, 3)}")
    if DATABASE_URL:
        print(f"  DATABASE_URL: {DATABASE_URL.split('@')[-1]}")
    print(f"  REDIS: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    print(f"  TZ: {TZ}")
