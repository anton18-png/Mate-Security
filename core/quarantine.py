import os
from datetime import datetime
from typing import Callable

from .constants import QUARANTINE_DIR, UTILS_DIR
from .utils import kill_related_processes, load_quarantine_meta, save_quarantine_meta, launcher_run


def quarantine_file(file_path: str, virus_name: str, password: str, log_callback: Callable[[str], None]) -> None:
    if not os.path.exists(file_path):
        log_callback(f"Файл уже недоступен: {file_path}\n")
        return

    kill_related_processes(file_path, log_callback)

    seven_zip = str(UTILS_DIR / "7za.exe")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(file_path) or "infected"
    safe_base = base_name.replace(":", "_").replace("\\", "_").replace("/", "_")
    archive_name = f"{ts}_{safe_base}.7z"
    archive_path = QUARANTINE_DIR / archive_name

    log_callback(f"Перемещение в карантин: {file_path}\n")
    pwd = password or "clamav"
    cmd = [seven_zip, "a", f"-p{pwd}", "-y", str(archive_path), file_path]
    proc = launcher_run(cmd)
    for line in proc.stdout:
        log_callback(line)
    proc.wait()

    if proc.returncode == 0:
        try:
            os.remove(file_path)
        except Exception as e:
            log_callback(f"Не удалось удалить оригинальный файл: {e}\n")

        items = load_quarantine_meta()
        items.append(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "original_path": file_path,
                "archive_path": str(archive_path),
                "reason": virus_name,
            }
        )
        save_quarantine_meta(items)
        log_callback("Файл успешно помещён в карантин.\n")
    else:
        log_callback("Ошибка при архивации файла. Операция отменена.\n")

