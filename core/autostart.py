import os
import winreg


AUTOSTART_NAME = "Mate-Security"
AUTOSTART_CMD = r'"C:\Apps\Mate-Security\Mate-Security.exe" --background'
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def enable_autostart() -> None:
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH)
    winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, AUTOSTART_CMD)
    winreg.CloseKey(key)


def disable_autostart() -> None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, AUTOSTART_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def is_autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, AUTOSTART_NAME)
        winreg.CloseKey(key)
        return value == AUTOSTART_CMD
    except FileNotFoundError:
        return False
    except OSError:
        return False

