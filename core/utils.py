import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Callable
import os

from .constants import BASE_DIR, UTILS_DIR, QUARANTINE_META


def launcher_run(args: List[str]) -> subprocess.Popen:
    launcher = str(UTILS_DIR / "launcher.exe")
    full_cmd = [launcher] + args
    return subprocess.Popen(
        full_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(BASE_DIR),
    )


def load_quarantine_meta() -> List[Dict[str, Any]]:
    try:
        if QUARANTINE_META.exists():
            return json.loads(QUARANTINE_META.read_text(encoding="utf-8") or "[]")
    except Exception:
        pass
    return []


def save_quarantine_meta(items: List[Dict[str, Any]]) -> None:
    QUARANTINE_META.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def kill_related_processes(file_path: str, log_callback: Callable[[str], None]) -> None:
    name = os.path.basename(file_path)
    if not name:
        return
    log_callback(f"Попытка завершить процессы: {name}\n")
    cmd = ["taskkill", "/im", name, "/f"]
    proc = launcher_run(cmd)
    for line in proc.stdout:
        log_callback(line)
    proc.wait()