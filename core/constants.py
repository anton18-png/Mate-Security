import os
import sys
from pathlib import Path

# корень проекта: ...\ClamAV, а не ...\ClamAV\core
BASE_DIR = Path(
    getattr(
        sys,
        "_MEIPASS",
        Path(__file__).resolve().parent.parent,
    )
)
UTILS_DIR = BASE_DIR / "Utils"
CLAM_DIR = UTILS_DIR / "clamav"
DB_DIR = BASE_DIR / "database"
USER_DATA_DIR = BASE_DIR / "user_data"
LOGS_DIR = USER_DATA_DIR / "logs"
SETTINGS_INI = USER_DATA_DIR / "settings.ini"
QUARANTINE_DIR = USER_DATA_DIR / "quarantine"
QUARANTINE_META = QUARANTINE_DIR / "quarantine.json"

TEMP_DIR = Path(os.getenv("TEMP", r"C:\Windows\Temp"))


def ensure_dirs() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    if not QUARANTINE_META.exists():
        QUARANTINE_META.write_text("[]", encoding="utf-8")

