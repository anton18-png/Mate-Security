import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict, Optional

from .constants import USER_DATA_DIR, UTILS_DIR


DB_DEFAULT_PATH = USER_DATA_DIR / "passwords.db"


class CryptoEngine:
    """Шифрование/дешифрование с помощью OpenSSL"""
    def __init__(self, cipher: str) -> None:
        self.cipher = cipher

    def _openssl_path(self) -> str:
        exe = UTILS_DIR / "openssl" / "openssl.exe"
        if not exe.exists():
            raise FileNotFoundError(f"OpenSSL executable not found: {exe}")
        return str(exe)

    def encrypt(self, data: bytes, password: str, out_path: str) -> None:
        openssl = self._openssl_path()
        cmd = [
            openssl, self.cipher,
            "-a", "-salt", "-pbkdf2",
            "-in", "-", "-out", out_path,
            "-pass", f"pass:{password}",
        ]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(input=data)
        if proc.returncode != 0:
            raise RuntimeError(f"OpenSSL encryption failed: {stderr.decode(errors='ignore')}")

    def decrypt(self, in_path: str, password: str) -> bytes:
        openssl = self._openssl_path()
        cmd = [
            openssl, self.cipher,
            "-a", "-d", "-salt", "-pbkdf2",
            "-in", in_path, "-out", "-",
            "-pass", f"pass:{password}",
        ]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"OpenSSL decryption failed: {stderr.decode(errors='ignore')}")
        return stdout


class PasswordDatabase:
    """
    Менеджер паролей:
    - хранит записи в зашифрованном виде
    - каждая запись: name, url, username, password, notes, created, updated
    """
    def __init__(self, cipher: str):
        self.crypto = CryptoEngine(cipher)
        self.path = str(DB_DEFAULT_PATH)
        self.items: List[Dict[str, str]] = []
        self._last_master_password: Optional[str] = None  # кэш для текущей сессии (опционально)

    def load(self, master_password: str) -> None:
        """Загружает и расшифровывает базу"""
        if not os.path.exists(self.path):
            self.items = []
            return

        try:
            data = self.crypto.decrypt(self.path, master_password)
            self.items = json.loads(data.decode("utf-8"))
            self._last_master_password = master_password  # сохраняем для текущей сессии
        except Exception as e:
            raise RuntimeError(f"Не удалось расшифровать базу паролей. Неверный мастер-пароль? ({str(e)})")

    def save(self, master_password: str = None) -> None:
        """Сохраняет и шифрует базу"""
        if master_password is None:
            if self._last_master_password is None:
                raise ValueError("Мастер-пароль не был указан и не кэширован")
            master_password = self._last_master_password

        data = json.dumps(self.items, ensure_ascii=False, indent=2).encode("utf-8")

        tmp_fd, tmp_name = tempfile.mkstemp(dir=os.path.dirname(self.path))
        os.close(tmp_fd)

        try:
            self.crypto.encrypt(data, master_password, tmp_name)
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            shutil.move(tmp_name, self.path)
            self._last_master_password = master_password  # обновляем кэш
        except Exception:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise

    def add_entry(
        self,
        name: str,
        username: str,
        password: str,
        url: str = "",
        notes: str = ""
    ) -> None:
        """Добавляет новую запись"""
        now = datetime.now().isoformat(timespec="seconds")
        entry = {
            "name": name.strip(),
            "url": url.strip(),
            "username": username.strip(),
            "password": password.strip(),
            "notes": notes.strip(),
            "created": now,
            "updated": now
        }
        self.items.append(entry)

    def update_entry(self, index: int, **kwargs) -> None:
        """Обновляет существующую запись по индексу"""
        if not 0 <= index < len(self.items):
            raise IndexError("Запись не найдена")
        now = datetime.now().isoformat(timespec="seconds")
        entry = self.items[index]
        for key, value in kwargs.items():
            if key in entry:
                entry[key] = value.strip()
        entry["updated"] = now

    def delete_entry(self, index: int) -> None:
        """Удаляет запись по индексу"""
        if not 0 <= index < len(self.items):
            raise IndexError("Запись не найдена")
        del self.items[index]

    def get_entry(self, index: int) -> Optional[Dict[str, str]]:
        if 0 <= index < len(self.items):
            return self.items[index].copy()
        return None

    def search(self, query: str) -> List[Dict[str, str]]:
        """Простой поиск по имени, url, логину"""
        query = query.lower().strip()
        if not query:
            return self.items.copy()
        return [
            item for item in self.items
            if query in item.get("name", "").lower()
            or query in item.get("url", "").lower()
            or query in item.get("username", "").lower()
        ]