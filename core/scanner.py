import os
import tempfile
from pathlib import Path
from typing import List, Dict, Callable

from .constants import CLAM_DIR, DB_DIR
from .utils import launcher_run, kill_related_processes
from .quarantine import quarantine_file


def filter_excluded(paths: List[str]) -> List[str]:
    """Исключает пути, начинающиеся с c:/apps (жёстко зашито)"""
    filtered = []
    for p in paths:
        norm = Path(p).resolve().as_posix().lower()
        if norm.startswith("c:/apps"):
            continue
        filtered.append(p)
    return filtered


def run_clamscan(
    paths: List[str],
    quarantine_password: str,
    log_callback: Callable[[str], None],
    ask_user_action: Callable[[str, str], bool],
) -> None:
    """
    Запускает сканирование с помощью clamscan.exe.
    Использует --file-list для обхода ограничения Windows на длину командной строки.
    """
    # Список целевых расширений (опасные файлы)
    TARGET_EXTENSIONS = {
        # Исполняемые и скрипты
        '.exe', '.scr', '.bat', '.cmd', '.vbs', '.js', '.jse', '.vbe',
        '.msi', '.msp', '.msc', '.mst', '.hta', '.com', '.pif', '.ps1',
        '.psm1', '.psd1', '.sh', '.bash', '.py', '.pyc', '.pyw', '.rb',
        '.pl', '.perl', '.jar', '.class', '.wsf', '.wsc', '.reg',
        # Документы с макросами
        '.docm', '.xlsm', '.pptm', '.dotm', '.xltm', '.potm', '.sldm',
        '.doc', '.xls', '.ppt', '.docx', '.xlsx', '.pptx', '.rtf',
        # PDF и архивы
        '.pdf', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.cab',
        # Другие потенциально опасные
        '.odt', '.ods', '.odp', '.mdb', '.accdb', '.sqlite', '.db',
        '.mp3', '.mp4', '.avi', '.mkv', '.jpg', '.png', '.gif',
    }

    clamscan_exe = CLAM_DIR / "clamscan.exe"
    if not clamscan_exe.exists():
        log_callback("Ошибка: clamscan.exe не найден в Utils/clamav/\n")
        return

    clamscan = str(clamscan_exe)
    db_opt = f"--database={DB_DIR}"

    filtered_paths = filter_excluded(paths)
    if not filtered_paths:
        log_callback("Нет путей для сканирования (все исключены).\n")
        return

    # Собираем только файлы с нужными расширениями
    valid_paths: List[str] = []
    for path_str in filtered_paths:
        path = Path(path_str)
        if not path.exists():
            log_callback(f"Путь не существует: {path_str}\n")
            continue

        if path.is_file():
            ext = path.suffix.lower()
            if ext in TARGET_EXTENSIONS:
                valid_paths.append(str(path))
                log_callback(f"Добавлен файл: {path_str}\n")
            # else: можно закомментировать, если не нужен спам в лог
        elif path.is_dir():
            log_callback(f"Сканирование директории: {path_str} (рекурсивно)...\n")
            for ext in TARGET_EXTENSIONS:
                for file_path in path.rglob(f"*{ext}"):
                    if file_path.is_file():
                        valid_paths.append(str(file_path))

    if not valid_paths:
        log_callback("Не найдено файлов с целевыми расширениями.\n")
        return

    total_files = len(valid_paths)
    log_callback(f"Всего файлов для сканирования: {total_files}\n")

    # Создаём временный файл со списком путей
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as tf:
            for p in valid_paths:
                tf.write(p + '\n')
            temp_file = tf.name

        # Формируем короткую команду
        cmd = [
            clamscan,
            "-r",               # рекурсивно (хотя при file-list это не обязательно)
            "-i",               # выводить только заражённые
            "--bell",           # звуковой сигнал при находке
            f"--file-list={temp_file}",
            db_opt
        ]

        log_callback("Запуск ClamAV...\n")
        proc = launcher_run(cmd)

        infected: List[Dict[str, str]] = []

        for line in proc.stdout:
            line = line.strip()
            if line:
                log_callback(line + "\n")

            if " FOUND" in line:
                try:
                    # Разделяем по " FOUND"
                    before_found, after_found = line.rsplit(" FOUND", 1)

                    # Теперь берём всё до последнего двоеточия перед " FOUND"
                    if ":" in before_found:
                        path_part, virus_part = before_found.rsplit(":", 1)
                        path = path_part.strip()
                        virus = (virus_part + after_found).strip()  # на случай, если вирус с пробелами
                    else:
                        path = before_found.strip()
                        virus = after_found.strip()

                    infected.append({"path": path, "virus": virus})
                    log_callback(f"[DEBUG] Распарсено: путь='{path}', вирус='{virus}'\n")

                except Exception as e:
                    log_callback(f"[ОШИБКА ПАРСИНГА] {line} → {e}\n")

        if infected:
            log_callback(f"\nОбнаружено угроз: {len(infected)}\n")
            for item in infected:
                log_callback(f"  {item['path']} → {item['virus']}\n")

            for item in infected:
                path = item["path"]
                virus = item["virus"]
                if ask_user_action(path, virus):
                    quarantine_file(path, virus, quarantine_password, log_callback)
                else:
                    kill_related_processes(path, log_callback)
                    try:
                        os.remove(path)
                        log_callback(f"Файл удалён: {path}\n")
                    except Exception as e:
                        log_callback(f"Не удалось удалить файл {path}: {e}\n")
        else:
            log_callback("\nСканирование завершено. Заражённых файлов не найдено.\n")

    except Exception as e:
        log_callback(f"Критическая ошибка при сканировании: {str(e)}\n")
    finally:
        # Обязательно удаляем временный файл
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                log_callback(f"Не удалось удалить временный файл {temp_file}\n")


__all__ = ['run_clamscan', 'filter_excluded']