import configparser
from pathlib import Path
from typing import Optional

from .constants import SETTINGS_INI, ensure_dirs


class Settings:
    """
    Класс для хранения и управления всеми настройками приложения.
    Сохраняет данные в user_data/settings.ini
    """

    def __init__(self) -> None:
        # UI / Внешний вид
        self.appearance_mode: str = "System"      # Light / Dark / System
        self.color_theme: str = "green"           # green / blue / dark-blue и т.д.

        # Безопасность / Карантин
        self.quarantine_password: str = "clamav"
        self.crypto_cipher: str = "aes-256-cbc"

        # Защита в реальном времени
        self.realtime_enabled: bool = False
        self.economy_mode: bool = False

        # Можно добавить в будущем:
        # self.monitor_paths: list[str] = []           # пути для мониторинга
        # self.excluded_folders: list[str] = []        # дополнительные исключения
        # self.auto_update_db: bool = True             # автообновление баз

        self._config = configparser.ConfigParser()
        self.load()

    def load(self) -> None:
        """Загружает настройки из файла (если файл существует)"""
        ensure_dirs()

        if not SETTINGS_INI.exists():
            self.save()  # создаём файл с дефолтными значениями
            return

        try:
            self._config.read(SETTINGS_INI, encoding="utf-8")

            # UI
            if self._config.has_section("ui"):
                self.appearance_mode = self._config.get("ui", "appearance_mode", fallback="System")
                self.color_theme = self._config.get("ui", "color_theme", fallback="green")

            # Security / Карантин
            if self._config.has_section("security"):
                self.quarantine_password = self._config.get("security", "quarantine_password", fallback="clamav")
                self.crypto_cipher = self._config.get("security", "crypto_cipher", fallback="aes-256-cbc")

            # Protection / Защита в реальном времени
            if self._config.has_section("protection"):
                self.realtime_enabled = self._config.getboolean("protection", "realtime_enabled", fallback=False)
                self.economy_mode = self._config.getboolean("protection", "economy_mode", fallback=False)

        except Exception as e:
            print(f"Ошибка при чтении настроек: {e}")
            # Если файл повреждён — оставляем дефолтные значения и перезапишем при save()

    def save(self) -> None:
        """Сохраняет текущие настройки в файл"""
        try:
            ensure_dirs()

            # UI
            if not self._config.has_section("ui"):
                self._config.add_section("ui")
            self._config.set("ui", "appearance_mode", self.appearance_mode)
            self._config.set("ui", "color_theme", self.color_theme)

            # Security
            if not self._config.has_section("security"):
                self._config.add_section("security")
            self._config.set("security", "quarantine_password", self.quarantine_password)
            self._config.set("security", "crypto_cipher", self.crypto_cipher)

            # Protection
            if not self._config.has_section("protection"):
                self._config.add_section("protection")
            self._config.set("protection", "realtime_enabled", str(self.realtime_enabled).lower())
            self._config.set("protection", "economy_mode", str(self.economy_mode).lower())

            with open(SETTINGS_INI, "w", encoding="utf-8") as f:
                self._config.write(f)

        except PermissionError:
            print("Нет прав на запись в settings.ini — проверьте права доступа к папке user_data")
        except Exception as e:
            print(f"Ошибка при сохранении настроек: {e}")

    def reset_to_defaults(self) -> None:
        """Сброс всех настроек к значениям по умолчанию"""
        self.appearance_mode = "System"
        self.color_theme = "green"
        self.quarantine_password = "clamav"
        self.crypto_cipher = "aes-256-cbc"
        self.realtime_enabled = False
        self.economy_mode = False
        self.save()

    def get_monitor_paths(self) -> list[Path]:
        """
        В будущем здесь можно возвращать список папок для мониторинга.
        Пока возвращаем стандартные (например, все диски или Downloads).
        """
        # Пока заглушка — можно потом сделать настраиваемым
        from pathlib import Path
        import string
        drives = [f"{d}:\\" for d in string.ascii_uppercase if Path(f"{d}:\\").exists()]
        return [Path(d) for d in drives]
        # Альтернатива: return [Path.home() / "Downloads"]