import os
from pathlib import Path
from typing import List, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .scanner import run_clamscan


class EventHandler(FileSystemEventHandler):
    def __init__(self, parent):
        self.parent = parent

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            event_path = event.src_path
            path = Path(event_path)
            if self.parent.should_monitor_event(event_path) and self.parent.should_scan_file(path):
                self.parent.log_callback(f"New file detected: {event_path}\n")
                run_clamscan(
                    [event_path],
                    self.parent.quarantine_password,
                    self.parent.log_callback,
                    self.parent.ask_user_action,
                )


class RealTimeMonitor:
    def __init__(
        self,
        quarantine_password: str,
        log_callback: Callable[[str], None],
        ask_user_action: Callable[[str, str], bool],
        paths: Optional[List[str]] = None,
        economy_mode: bool = False,
    ):
        if paths is None:
            # Default to monitoring all logical drives (as per prompt: all disks)
            self.paths = [chr(x) + ':\\' for x in range(65, 91) if os.path.exists(chr(x) + ':\\')]
            # Note: Monitoring all drives recursively can be resource-intensive. Consider limiting to user-specific folders like Downloads for better performance.
            # Alternative default: str(Path.home() / 'Downloads')
            log_callback("Real-time monitoring initialized with default paths (all drives).\n")
        else:
            self.paths = paths

        self.quarantine_password = quarantine_password
        self.log_callback = log_callback
        self.ask_user_action = ask_user_action
        self.observer = Observer()
        self.economy_mode = economy_mode
        self.event_handler = EventHandler(self)
        self.set_target_extensions()
        self.exclude_temp = self.economy_mode  # Exclude temp paths in economy mode

    def set_target_extensions(self) -> None:
        if self.economy_mode:
            # Lightweight: fewer extensions, as per prompt's "экономный режим"
            self.target_extensions = {
                '.exe', '.scr', '.bat', '.cmd', '.vbs', '.js', '.jse', '.vbe',
                '.msi', '.msp', '.msc', '.mst', '.hta', '.com', '.pif', '.ps1',
                '.psm1', '.psd1', '.sh', '.bash', '.py', '.pyc', '.pyw', '.rb',
                '.pl', '.perl', '.jar', '.class', '.wsf', '.wsc', '.reg',
                '.docm', '.xlsm', '.pptm', '.dotm', '.xltm', '.potm', '.sldm',
                '.pdf',
                '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.cab',
            }
        else:
            # Standard: all extensions from the provided code
            self.target_extensions = {
                '.exe', '.scr', '.bat', '.cmd', '.vbs', '.js', '.jse', '.vbe',
                '.msi', '.msp', '.msc', '.mst', '.hta', '.com', '.pif', '.ps1',
                '.psm1', '.psd1', '.sh', '.bash', '.py', '.pyc', '.pyw', '.rb',
                '.pl', '.perl', '.jar', '.class', '.wsf', '.wsc', '.reg',
                '.docm', '.xlsm', '.pptm', '.dotm', '.xltm', '.potm', '.sldm',
                '.doc', '.xls', '.ppt', '.docx', '.xlsx', '.pptx', '.rtf',
                '.pdf',
                '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.cab',
                '.iso', '.img', '.dmg', '.arj', '.lzh', '.z', '.lz',
                '.lnk', '.inf', '.cpl', '.dll', '.sys', '.drv', '.ocx', '.ax',
                '.acm', '.olb', '.tlb', '.efi', '.boot', '.mbr',
                '.ini', '.cfg', '.conf', '.config', '.xml', '.json', '.yml', '.yaml',
                '.url', '.website', '.scf', '.library-ms', '.searchconnector-ms',
                '.odt', '.ods', '.odp', '.odb', '.odg', '.odf',
                '.mdb', '.accdb', '.accde', '.accdt', '.accdr', '.sqlite', '.db',
                '.mp3', '.wav', '.flac', '.aac', '.wma', '.mp4', '.avi', '.mkv',
                '.mov', '.wmv', '.flv', '.webm', '.m4a', '.ogg', '.jpg', '.jpeg',
                '.png', '.gif', '.bmp', '.tiff', '.svg',
                '.html', '.htm', '.php', '.asp', '.aspx', '.jsp', '.action',
                '.swf', '.fla', '.swc', '.air', '.apk', '.appx', '.appxbundle',
                '.xap', '.gadget', '.cpl', '.ocx', '.jar', '.app', '.dmg',
                '.vhd', '.vhdx', '.vmdk', '.ova', '.ovf',
                '.bak', '.old', '.backup', '.sav', '.save',
                '.sql', '.mdf', '.ldf', '.ndf'
            }

    def set_economy_mode(self, enabled: bool) -> None:
        if self.economy_mode == enabled:
            return
        was_running = self.observer.is_alive()
        if was_running:
            self.stop()
        self.economy_mode = enabled
        self.exclude_temp = enabled
        self.set_target_extensions()
        if was_running:
            self.start()
        self.log_callback(f"Economy mode {'enabled' if enabled else 'disabled'}.\n")

    def should_scan_file(self, file_path: Path) -> bool:
        ext = file_path.suffix.lower()
        return ext in self.target_extensions

    def should_monitor_event(self, event_path: str) -> bool:
        if self.exclude_temp and 'temp' in event_path.lower():
            return False
        return True

    def start(self) -> None:
        if self.observer.is_alive():
            return
        for path_str in self.paths:
            p = Path(path_str)
            if p.exists() and p.is_dir():
                self.observer.schedule(self.event_handler, str(p), recursive=True)
                self.log_callback(f"Monitoring path: {path_str} (recursive)\n")
            else:
                self.log_callback(f"Invalid path for monitoring: {path_str}\n")
        if self.observer.event_queue:  # Only start if something is scheduled
            self.observer.start()
            self.log_callback("Started real-time monitoring.\n")
        else:
            self.log_callback("No valid paths to monitor.\n")

    def stop(self) -> None:
        if not self.observer.is_alive():
            return
        self.observer.stop()
        self.observer.join()
        self.log_callback("Stopped real-time monitoring.\n")