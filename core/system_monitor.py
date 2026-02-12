import psutil
import GPUtil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
import threading
import time
from collections import deque
import os
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import customtkinter as ctk
from tkinter import ttk
import queue
import platform
import cpuinfo

class SystemStats:
    """Сбор статистики системы"""
    
    def __init__(self, max_history: int = 60):
        self.max_history = max_history
        self.cpu_history = deque(maxlen=max_history)
        self.ram_history = deque(maxlen=max_history)
        self.gpu_history = deque(maxlen=max_history)
        self.network_history = deque(maxlen=max_history)
        self.disk_io_history = deque(maxlen=max_history)
        
        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_time = time.time()
        
    def get_cpu_info(self) -> Dict:
        """Получить информацию о CPU"""
        try:
            cpu_freq = psutil.cpu_freq()
            return {
                'percent': psutil.cpu_percent(interval=0.1, percpu=True),
                'percent_total': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count(),
                'count_logical': psutil.cpu_count(logical=True),
                'freq_current': cpu_freq.current if cpu_freq else 0,
                'freq_min': cpu_freq.min if cpu_freq else 0,
                'freq_max': cpu_freq.max if cpu_freq else 0,
                'name': cpuinfo.get_cpu_info().get('brand_raw', 'Unknown'),
                'load_avg': [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()] if hasattr(psutil, 'getloadavg') else []
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_ram_info(self) -> Dict:
        """Получить информацию о RAM"""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                'total': mem.total,
                'available': mem.available,
                'percent': mem.percent,
                'used': mem.used,
                'free': mem.free,
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percent': swap.percent
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_gpu_info(self) -> List[Dict]:
        """Получить информацию о GPU"""
        gpus = []
        try:
            gpu_list = GPUtil.getGPUs()
            for gpu in gpu_list:
                gpus.append({
                    'name': gpu.name,
                    'load': gpu.load * 100,
                    'memory_total': gpu.memoryTotal,
                    'memory_used': gpu.memoryUsed,
                    'memory_free': gpu.memoryFree,
                    'temperature': gpu.temperature,
                    'driver': gpu.driver
                })
        except Exception as e:
            gpus.append({'error': str(e)})
        return gpus
    
    def get_network_info(self) -> Dict:
        """Получить информацию о сети"""
        try:
            net_io = psutil.net_io_counters()
            current_time = time.time()
            time_delta = current_time - self.last_time
            
            # Скорость в байтах в секунду
            bytes_sent = net_io.bytes_sent - self.last_net_io.bytes_sent
            bytes_recv = net_io.bytes_recv - self.last_net_io.bytes_recv
            
            sent_speed = bytes_sent / time_delta if time_delta > 0 else 0
            recv_speed = bytes_recv / time_delta if time_delta > 0 else 0
            
            self.last_net_io = net_io
            self.last_time = current_time
            
            # Информация о сетевых интерфейсах
            interfaces = []
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == 2:  # AF_INET
                        interfaces.append({
                            'name': name,
                            'ip': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                        break
            
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout,
                'sent_speed': sent_speed,
                'recv_speed': recv_speed,
                'interfaces': interfaces
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_disk_info(self) -> Dict:
        """Получить информацию о дисках"""
        try:
            # Информация о разделах
            partitions = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partitions.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    })
                except:
                    continue
            
            # I/O статистика
            disk_io = psutil.disk_io_counters()
            if disk_io and self.last_disk_io:
                current_time = time.time()
                time_delta = current_time - self.last_time
                
                read_speed = (disk_io.read_bytes - self.last_disk_io.read_bytes) / time_delta if time_delta > 0 else 0
                write_speed = (disk_io.write_bytes - self.last_disk_io.write_bytes) / time_delta if time_delta > 0 else 0
                
                self.last_disk_io = disk_io
            else:
                read_speed = write_speed = 0
                self.last_disk_io = disk_io
            
            return {
                'partitions': partitions,
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0,
                'read_count': disk_io.read_count if disk_io else 0,
                'write_count': disk_io.write_count if disk_io else 0,
                'read_speed': read_speed,
                'write_speed': write_speed
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_process_info(self) -> List[Dict]:
        """Получить информацию о процессах"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time']):
                try:
                    pinfo = proc.info
                    pinfo['cpu_percent'] = proc.cpu_percent(interval=0)
                    pinfo['memory_percent'] = proc.memory_percent()
                    pinfo['memory_rss'] = proc.memory_info().rss
                    pinfo['threads'] = proc.num_threads()
                    pinfo['username'] = proc.username()
                    processes.append(pinfo)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            processes.append({'error': str(e)})
        
        # Сортируем по использованию CPU
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return processes[:50]  # Топ 50 процессов
    
    def update_history(self):
        """Обновить историю показателей"""
        self.cpu_history.append(self.get_cpu_info().get('percent_total', 0))
        self.ram_history.append(self.get_ram_info().get('percent', 0))
        
        gpus = self.get_gpu_info()
        if gpus and 'error' not in gpus[0]:
            self.gpu_history.append(gpus[0].get('load', 0))
        
        net_info = self.get_network_info()
        if 'error' not in net_info:
            self.network_history.append(net_info.get('recv_speed', 0) / 1024)  # KB/s
        
        disk_info = self.get_disk_info()
        if 'error' not in disk_info:
            self.disk_io_history.append(disk_info.get('read_speed', 0) / 1024)  # KB/s


class FileSystemChangeHandler(FileSystemEventHandler):
    """Обработчик изменений файловой системы"""
    
    def __init__(self, callback: Callable[[str, str, str], None]):
        super().__init__()
        self.callback = callback
        self.change_queue = queue.Queue()
        self._running = True
        self._processor_thread = threading.Thread(target=self._process_changes, daemon=True)
        self._processor_thread.start()
    
    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self.change_queue.put(('created', event.src_path, datetime.now()))
    
    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            self.change_queue.put(('deleted', event.src_path, datetime.now()))
    
    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self.change_queue.put(('modified', event.src_path, datetime.now()))
    
    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            self.change_queue.put(('moved', f"{event.src_path} -> {event.dest_path}", datetime.now()))
    
    def _process_changes(self):
        """Обработка изменений в отдельном потоке"""
        while self._running:
            try:
                change_type, path, timestamp = self.change_queue.get(timeout=0.5)
                self.callback(change_type, path, timestamp)
            except queue.Empty:
                continue
    
    def stop(self):
        self._running = False


class SystemMonitorTab:
    """Вкладка полного мониторинга системы"""
    
    def __init__(self, parent, log_callback: Optional[Callable] = None):
        self.parent = parent
        self.log_callback = log_callback
        self.stats = SystemStats()
        
        # Флаги мониторинга
        self.monitoring_enabled = False
        self.fs_monitoring_enabled = False
        
        # Наблюдатель файловой системы
        self.fs_observer = None
        self.fs_handler = None
        
        # Поток обновления статистики
        self.update_thread = None
        self.update_interval = 1000  # мс
        
        # Создание интерфейса
        self._create_widgets()
        
        # Запуск мониторинга по умолчанию
        self._start_monitoring()
    
    def _create_widgets(self):
        """Создание виджетов вкладки"""
        
        # Основной контейнер с вкладками внутри вкладки
        self.notebook = ctk.CTkTabview(self.parent)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Создаем вкладки
        self.overview_tab = self.notebook.add("Обзор")
        self.cpu_ram_tab = self.notebook.add("CPU и RAM")
        self.gpu_tab = self.notebook.add("GPU")
        self.disk_tab = self.notebook.add("Диски")
        self.network_tab = self.notebook.add("Сеть")
        self.processes_tab = self.notebook.add("Процессы")
        self.fs_changes_tab = self.notebook.add("Файловая система")
        
        # Заполняем вкладки содержимым
        self._build_overview_tab()
        self._build_cpu_ram_tab()
        self._build_gpu_tab()
        self._build_disk_tab()
        self._build_network_tab()
        self._build_processes_tab()
        self._build_fs_changes_tab()
    
    def _build_overview_tab(self):
        """Вкладка обзора - основные показатели"""
        
        # Верхняя панель управления
        control_frame = ctk.CTkFrame(self.overview_tab)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.monitor_switch = ctk.CTkSwitch(
            control_frame,
            text="Мониторинг системы",
            command=self._toggle_monitoring
        )
        self.monitor_switch.select()
        self.monitor_switch.pack(side="left", padx=10)
        
        self.fs_monitor_switch = ctk.CTkSwitch(
            control_frame,
            text="Мониторинг файловой системы",
            command=self._toggle_fs_monitoring
        )
        self.fs_monitor_switch.pack(side="left", padx=10)
        
        # Метка последнего обновления
        self.last_update_label = ctk.CTkLabel(
            control_frame,
            text="Обновлено: --:--:--",
            font=("Segoe UI", 11)
        )
        self.last_update_label.pack(side="right", padx=10)
        
        # Основные показатели в карточках
        metrics_frame = ctk.CTkFrame(self.overview_tab)
        metrics_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Создаем сетку 2x2 для карточек
        metrics_frame.grid_columnconfigure((0, 1), weight=1)
        metrics_frame.grid_rowconfigure((0, 1), weight=1)
        
        # Карточка CPU
        cpu_card = self._create_metric_card(metrics_frame, "Процессор (CPU)", 0, 0)
        self.cpu_percent_label = self._add_metric_label(cpu_card, "Загрузка:", "0%")
        self.cpu_temp_label = self._add_metric_label(cpu_card, "Температура:", "N/A")
        self.cpu_freq_label = self._add_metric_label(cpu_card, "Частота:", "0 MHz")
        self.cpu_count_label = self._add_metric_label(cpu_card, "Ядра:", "0")
        
        # Карточка RAM
        ram_card = self._create_metric_card(metrics_frame, "Оперативная память (RAM)", 0, 1)
        self.ram_percent_label = self._add_metric_label(ram_card, "Загрузка:", "0%")
        self.ram_used_label = self._add_metric_label(ram_card, "Использовано:", "0 GB")
        self.ram_total_label = self._add_metric_label(ram_card, "Всего:", "0 GB")
        self.ram_swap_label = self._add_metric_label(ram_card, "Swap:", "0%")
        
        # Карточка GPU
        gpu_card = self._create_metric_card(metrics_frame, "Видеокарта (GPU)", 1, 0)
        self.gpu_name_label = self._add_metric_label(gpu_card, "Модель:", "N/A")
        self.gpu_load_label = self._add_metric_label(gpu_card, "Загрузка:", "0%")
        self.gpu_memory_label = self._add_metric_label(gpu_card, "Память:", "0/0 MB")
        self.gpu_temp_label = self._add_metric_label(gpu_card, "Температура:", "0°C")
        
        # Карточка Сеть
        network_card = self._create_metric_card(metrics_frame, "Сеть", 1, 1)
        self.net_sent_label = self._add_metric_label(network_card, "Отправлено:", "0 MB")
        self.net_recv_label = self._add_metric_label(network_card, "Получено:", "0 MB")
        self.net_speed_sent_label = self._add_metric_label(network_card, "Скорость отпр.:", "0 KB/s")
        self.net_speed_recv_label = self._add_metric_label(network_card, "Скорость пол.:", "0 KB/s")
        
        # Информация о системе
        system_info_frame = ctk.CTkFrame(self.overview_tab)
        system_info_frame.pack(fill="x", padx=10, pady=10)
        
        system_info = ctk.CTkLabel(
            system_info_frame,
            text=f"Система: {platform.system()} {platform.release()} | "
                 f"Версия: {platform.version()} | "
                 f"Узел: {platform.node()}",
            font=("Segoe UI", 10)
        )
        system_info.pack(pady=5)
    
    def _create_metric_card(self, parent, title, row, col):
        """Создание карточки с метриками"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(anchor="w", padx=10, pady=5)
        
        return card
    
    def _add_metric_label(self, parent, label, value):
        """Добавление метрики в карточку"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        
        name_label = ctk.CTkLabel(frame, text=label, width=120, anchor="w")
        name_label.pack(side="left")
        
        value_label = ctk.CTkLabel(frame, text=value, anchor="e")
        value_label.pack(side="right")
        
        return value_label
    
    def _build_cpu_ram_tab(self):
        """Вкладка CPU и RAM"""
        
        # CPU информация
        cpu_frame = ctk.CTkFrame(self.cpu_ram_tab)
        cpu_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        cpu_title = ctk.CTkLabel(
            cpu_frame,
            text="Информация о процессоре",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        cpu_title.pack(anchor="w", padx=10, pady=5)
        
        # Детальная информация о CPU
        self.cpu_info_text = ctk.CTkTextbox(cpu_frame, height=150)
        self.cpu_info_text.pack(fill="x", padx=10, pady=5)
        
        # Загрузка по ядрам
        cores_label = ctk.CTkLabel(
            cpu_frame,
            text="Загрузка по ядрам:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        cores_label.pack(anchor="w", padx=10, pady=5)
        
        self.cores_frame = ctk.CTkFrame(cpu_frame)
        self.cores_frame.pack(fill="x", padx=10, pady=5)
        
        # RAM информация
        ram_frame = ctk.CTkFrame(self.cpu_ram_tab)
        ram_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ram_title = ctk.CTkLabel(
            ram_frame,
            text="Информация о памяти",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        ram_title.pack(anchor="w", padx=10, pady=5)
        
        self.ram_info_text = ctk.CTkTextbox(ram_frame, height=120)
        self.ram_info_text.pack(fill="x", padx=10, pady=5)
    
    def _build_gpu_tab(self):
        """Вкладка GPU"""
        
        # Информация о GPU
        self.gpu_info_text = ctk.CTkTextbox(self.gpu_tab, height=200)
        self.gpu_info_text.pack(fill="x", padx=10, pady=10)
        
        # График использования (заглушка, можно добавить реальный график)
        gpu_chart_label = ctk.CTkLabel(
            self.gpu_tab,
            text="График использования GPU (будет добавлен в следующей версии)",
            font=("Segoe UI", 12)
        )
        gpu_chart_label.pack(pady=20)
    
    def _build_disk_tab(self):
        """Вкладка дисков"""
        
        # Информация о дисках
        self.disk_info_text = ctk.CTkTextbox(self.disk_tab, height=200)
        self.disk_info_text.pack(fill="x", padx=10, pady=10)
        
        # Скорость чтения/записи
        disk_io_frame = ctk.CTkFrame(self.disk_tab)
        disk_io_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        io_title = ctk.CTkLabel(
            disk_io_frame,
            text="Скорость чтения/записи",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        io_title.pack(anchor="w", padx=10, pady=5)
        
        self.disk_read_label = ctk.CTkLabel(
            disk_io_frame,
            text="Чтение: 0 KB/s",
            font=("Segoe UI", 12)
        )
        self.disk_read_label.pack(anchor="w", padx=10, pady=2)
        
        self.disk_write_label = ctk.CTkLabel(
            disk_io_frame,
            text="Запись: 0 KB/s",
            font=("Segoe UI", 12)
        )
        self.disk_write_label.pack(anchor="w", padx=10, pady=2)
    
    def _build_network_tab(self):
        """Вкладка сети"""
        
        # Информация о сети
        self.network_info_text = ctk.CTkTextbox(self.network_tab, height=150)
        self.network_info_text.pack(fill="x", padx=10, pady=10)
        
        # Сетевые интерфейсы
        interfaces_title = ctk.CTkLabel(
            self.network_tab,
            text="Сетевые интерфейсы",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        interfaces_title.pack(anchor="w", padx=10, pady=5)
        
        self.interfaces_text = ctk.CTkTextbox(self.network_tab, height=150)
        self.interfaces_text.pack(fill="x", padx=10, pady=5)
    
    def _build_processes_tab(self):
        """Вкладка процессов"""
        
        # Таблица процессов
        columns = ("PID", "Имя", "CPU %", "RAM %", "Память", "Потоки", "Пользователь", "Статус")
        
        # Контейнер для Treeview с прокруткой
        tree_frame = ctk.CTkFrame(self.processes_tab)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Style для Treeview
        style = ttk.Style()
        style.configure("SystemMonitor.Treeview", rowheight=25, font=("Segoe UI", 10))
        style.configure("SystemMonitor.Treeview.Heading", font=("Segoe UI", 11, "bold"))
        
        self.process_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=20,
            style="SystemMonitor.Treeview"
        )
        
        # Настройка колонок
        self.process_tree.heading("PID", text="PID")
        self.process_tree.heading("Имя", text="Имя процесса")
        self.process_tree.heading("CPU %", text="CPU %")
        self.process_tree.heading("RAM %", text="RAM %")
        self.process_tree.heading("Память", text="Память (MB)")
        self.process_tree.heading("Потоки", text="Потоки")
        self.process_tree.heading("Пользователь", text="Пользователь")
        self.process_tree.heading("Статус", text="Статус")
        
        self.process_tree.column("PID", width=60)
        self.process_tree.column("Имя", width=200)
        self.process_tree.column("CPU %", width=70)
        self.process_tree.column("RAM %", width=70)
        self.process_tree.column("Память", width=100)
        self.process_tree.column("Потоки", width=70)
        self.process_tree.column("Пользователь", width=120)
        self.process_tree.column("Статус", width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)
        
        self.process_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _build_fs_changes_tab(self):
        """Вкладка изменений файловой системы"""
        
        # Кнопки управления
        control_frame = ctk.CTkFrame(self.fs_changes_tab)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.watch_path_var = ctk.StringVar(value="C:\\")
        path_entry = ctk.CTkEntry(
            control_frame,
            textvariable=self.watch_path_var,
            placeholder_text="Путь для мониторинга",
            width=300
        )
        path_entry.pack(side="left", padx=5)
        
        browse_btn = ctk.CTkButton(
            control_frame,
            text="Обзор",
            command=self._browse_watch_path,
            width=80
        )
        browse_btn.pack(side="left", padx=5)
        
        start_watch_btn = ctk.CTkButton(
            control_frame,
            text="Начать мониторинг",
            command=self._start_fs_monitoring,
            width=150
        )
        start_watch_btn.pack(side="left", padx=5)
        
        clear_btn = ctk.CTkButton(
            control_frame,
            text="Очистить",
            command=self._clear_fs_log,
            width=80
        )
        clear_btn.pack(side="right", padx=5)
        
        # Лог изменений
        log_label = ctk.CTkLabel(
            self.fs_changes_tab,
            text="Журнал изменений файловой системы:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        log_label.pack(anchor="w", padx=10, pady=5)
        
        self.fs_log_text = ctk.CTkTextbox(self.fs_changes_tab)
        self.fs_log_text.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _browse_watch_path(self):
        """Выбор пути для мониторинга"""
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Выберите папку для мониторинга")
        if path:
            self.watch_path_var.set(path)
    
    def _start_fs_monitoring(self):
        """Запуск мониторинга файловой системы"""
        path = self.watch_path_var.get()
        if not Path(path).exists():
            self._log_fs_event("Ошибка: Путь не существует")
            return
        
        self._stop_fs_monitoring()
        
        try:
            self.fs_handler = FileSystemChangeHandler(self._log_fs_event)
            self.fs_observer = Observer()
            self.fs_observer.schedule(self.fs_handler, path, recursive=True)
            self.fs_observer.start()
            self.fs_monitoring_enabled = True
            self._log_fs_event(f"Мониторинг запущен: {path}")
        except Exception as e:
            self._log_fs_event(f"Ошибка запуска мониторинга: {e}")
    
    def _stop_fs_monitoring(self):
        """Остановка мониторинга файловой системы"""
        if self.fs_observer:
            self.fs_observer.stop()
            self.fs_observer.join()
            self.fs_observer = None
        
        if self.fs_handler:
            self.fs_handler.stop()
            self.fs_handler = None
        
        self.fs_monitoring_enabled = False
    
    def _log_fs_event(self, change_type: str, path: str = "", timestamp: datetime = None):
        """Логирование изменений файловой системы"""
        if not hasattr(self, 'fs_log_text'):
            return
        
        if timestamp is None:
            timestamp = datetime.now()
        
        time_str = timestamp.strftime("%H:%M:%S")
        
        # Иконки для разных типов событий
        icons = {
            'created': '➕',
            'deleted': '❌',
            'modified': '✏️',
            'moved': '➡️'
        }
        
        icon = icons.get(change_type, '•')
        
        def _append():
            self.fs_log_text.insert("end", f"[{time_str}] {icon} {change_type.upper()}: {path}\n")
            self.fs_log_text.see("end")
        
        if hasattr(self.fs_log_text, 'after'):
            self.fs_log_text.after(0, _append)
    
    def _clear_fs_log(self):
        """Очистка лога файловой системы"""
        self.fs_log_text.delete("1.0", "end")
    
    def _start_monitoring(self):
        """Запуск мониторинга системы"""
        self.monitoring_enabled = True
        self.update_thread = threading.Thread(target=self._update_stats_loop, daemon=True)
        self.update_thread.start()
    
    def _stop_monitoring(self):
        """Остановка мониторинга системы"""
        self.monitoring_enabled = False
    
    def _toggle_monitoring(self):
        """Переключение мониторинга"""
        if self.monitor_switch.get():
            self._start_monitoring()
        else:
            self._stop_monitoring()
    
    def _toggle_fs_monitoring(self):
        """Переключение мониторинга файловой системы"""
        if self.fs_monitor_switch.get():
            self._start_fs_monitoring()
        else:
            self._stop_fs_monitoring()
    
    def _update_stats_loop(self):
        """Цикл обновления статистики"""
        while self.monitoring_enabled:
            try:
                self._update_all_stats()
                time.sleep(self.update_interval / 1000)
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"Ошибка мониторинга: {e}")
    
    def _update_all_stats(self):
        """Обновление всей статистики"""
        
        # Обновление истории
        self.stats.update_history()
        
        # Получение текущих данных
        cpu_info = self.stats.get_cpu_info()
        ram_info = self.stats.get_ram_info()
        gpu_info = self.stats.get_gpu_info()
        net_info = self.stats.get_network_info()
        disk_info = self.stats.get_disk_info()
        processes = self.stats.get_process_info()
        
        # Обновление UI в главном потоке
        self.parent.after(0, lambda: self._update_ui(
            cpu_info, ram_info, gpu_info, net_info, disk_info, processes
        ))
    
    def _update_ui(self, cpu_info, ram_info, gpu_info, net_info, disk_info, processes):
        """Обновление интерфейса"""
        
        # Обновление времени
        self.last_update_label.configure(
            text=f"Обновлено: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        # Обновление CPU
        if 'error' not in cpu_info:
            self.cpu_percent_label.configure(text=f"{cpu_info.get('percent_total', 0):.1f}%")
            self.cpu_freq_label.configure(text=f"{cpu_info.get('freq_current', 0):.0f} MHz")
            self.cpu_count_label.configure(text=f"{cpu_info.get('count_logical', 0)}")
            
            # Информация о CPU
            cpu_text = f"Модель: {cpu_info.get('name', 'N/A')}\n"
            cpu_text += f"Загрузка: {cpu_info.get('percent_total', 0):.1f}%\n"
            cpu_text += f"Частота: {cpu_info.get('freq_current', 0):.0f} MHz (Мин: {cpu_info.get('freq_min', 0):.0f}, Макс: {cpu_info.get('freq_max', 0):.0f})\n"
            cpu_text += f"Ядер физических: {cpu_info.get('count', 0)}, логических: {cpu_info.get('count_logical', 0)}\n"
            
            if cpu_info.get('load_avg'):
                cpu_text += f"Средняя загрузка: {cpu_info['load_avg'][0]:.1f}%, {cpu_info['load_avg'][1]:.1f}%, {cpu_info['load_avg'][2]:.1f}%\n"
            
            self.cpu_info_text.delete("1.0", "end")
            self.cpu_info_text.insert("1.0", cpu_text)
            
            # Загрузка по ядрам
            for widget in self.cores_frame.winfo_children():
                widget.destroy()
            
            per_cpu = cpu_info.get('percent', [])
            for i, percent in enumerate(per_cpu):
                frame = ctk.CTkFrame(self.cores_frame)
                frame.pack(fill="x", pady=1)
                
                label = ctk.CTkLabel(frame, text=f"Ядро {i}:", width=60)
                label.pack(side="left", padx=5)
                
                progress = ctk.CTkProgressBar(frame, width=200)
                progress.pack(side="left", padx=5)
                progress.set(percent / 100)
                
                percent_label = ctk.CTkLabel(frame, text=f"{percent:.1f}%", width=50)
                percent_label.pack(side="left", padx=5)
        
        # Обновление RAM
        if 'error' not in ram_info:
            total_gb = ram_info.get('total', 0) / (1024**3)
            used_gb = ram_info.get('used', 0) / (1024**3)
            free_gb = ram_info.get('free', 0) / (1024**3)
            
            self.ram_percent_label.configure(text=f"{ram_info.get('percent', 0):.1f}%")
            self.ram_used_label.configure(text=f"{used_gb:.2f} GB")
            self.ram_total_label.configure(text=f"{total_gb:.2f} GB")
            self.ram_swap_label.configure(text=f"{ram_info.get('swap_percent', 0):.1f}%")
            
            ram_text = f"Всего RAM: {total_gb:.2f} GB\n"
            ram_text += f"Использовано: {used_gb:.2f} GB ({ram_info.get('percent', 0):.1f}%)\n"
            ram_text += f"Свободно: {free_gb:.2f} GB\n"
            ram_text += f"Доступно: {ram_info.get('available', 0) / (1024**3):.2f} GB\n"
            ram_text += f"Swap всего: {ram_info.get('swap_total', 0) / (1024**3):.2f} GB\n"
            ram_text += f"Swap использовано: {ram_info.get('swap_used', 0) / (1024**3):.2f} GB ({ram_info.get('swap_percent', 0):.1f}%)"
            
            self.ram_info_text.delete("1.0", "end")
            self.ram_info_text.insert("1.0", ram_text)
        
        # Обновление GPU
        if gpu_info and 'error' not in gpu_info[0]:
            gpu = gpu_info[0]
            self.gpu_name_label.configure(text=gpu.get('name', 'N/A'))
            self.gpu_load_label.configure(text=f"{gpu.get('load', 0):.1f}%")
            self.gpu_memory_label.configure(
                text=f"{gpu.get('memory_used', 0):.0f}/{gpu.get('memory_total', 0):.0f} MB"
            )
            self.gpu_temp_label.configure(text=f"{gpu.get('temperature', 0):.0f}°C")
            
            gpu_text = f"Модель: {gpu.get('name', 'N/A')}\n"
            gpu_text += f"Загрузка: {gpu.get('load', 0):.1f}%\n"
            gpu_text += f"Память: {gpu.get('memory_used', 0):.0f}/{gpu.get('memory_total', 0):.0f} MB ({gpu.get('memory_used', 0)/gpu.get('memory_total', 1)*100:.1f}%)\n"
            gpu_text += f"Температура: {gpu.get('temperature', 0):.0f}°C\n"
            gpu_text += f"Драйвер: {gpu.get('driver', 'N/A')}"
            
            self.gpu_info_text.delete("1.0", "end")
            self.gpu_info_text.insert("1.0", gpu_text)
        
        # Обновление сети
        if 'error' not in net_info:
            sent_gb = net_info.get('bytes_sent', 0) / (1024**3)
            recv_gb = net_info.get('bytes_recv', 0) / (1024**3)
            
            self.net_sent_label.configure(text=f"{sent_gb:.2f} GB")
            self.net_recv_label.configure(text=f"{recv_gb:.2f} GB")
            self.net_speed_sent_label.configure(text=f"{net_info.get('sent_speed', 0) / 1024:.1f} KB/s")
            self.net_speed_recv_label.configure(text=f"{net_info.get('recv_speed', 0) / 1024:.1f} KB/s")
            
            net_text = f"Отправлено: {sent_gb:.2f} GB\n"
            net_text += f"Получено: {recv_gb:.2f} GB\n"
            net_text += f"Скорость отправки: {net_info.get('sent_speed', 0) / 1024:.1f} KB/s\n"
            net_text += f"Скорость получения: {net_info.get('recv_speed', 0) / 1024:.1f} KB/s\n"
            net_text += f"Пакетов отправлено: {net_info.get('packets_sent', 0)}\n"
            net_text += f"Пакетов получено: {net_info.get('packets_recv', 0)}\n"
            net_text += f"Ошибок: IN={net_info.get('errin', 0)} OUT={net_info.get('errout', 0)}\n"
            net_text += f"Потерь: IN={net_info.get('dropin', 0)} OUT={net_info.get('dropout', 0)}"
            
            self.network_info_text.delete("1.0", "end")
            self.network_info_text.insert("1.0", net_text)
            
            # Интерфейсы
            interfaces_text = ""
            for iface in net_info.get('interfaces', []):
                interfaces_text += f"Интерфейс: {iface.get('name', 'N/A')}\n"
                interfaces_text += f"  IP: {iface.get('ip', 'N/A')}\n"
                interfaces_text += f"  Маска: {iface.get('netmask', 'N/A')}\n"
                interfaces_text += f"  Broadcast: {iface.get('broadcast', 'N/A')}\n\n"
            
            self.interfaces_text.delete("1.0", "end")
            self.interfaces_text.insert("1.0", interfaces_text or "Нет активных интерфейсов")
        
        # Обновление дисков
        if 'error' not in disk_info:
            self.disk_read_label.configure(text=f"Чтение: {disk_info.get('read_speed', 0) / 1024:.1f} KB/s")
            self.disk_write_label.configure(text=f"Запись: {disk_info.get('write_speed', 0) / 1024:.1f} KB/s")
            
            disk_text = ""
            for part in disk_info.get('partitions', []):
                total_gb = part.get('total', 0) / (1024**3)
                used_gb = part.get('used', 0) / (1024**3)
                free_gb = part.get('free', 0) / (1024**3)
                
                disk_text += f"Диск: {part.get('device', 'N/A')}\n"
                disk_text += f"  Точка монтирования: {part.get('mountpoint', 'N/A')}\n"
                disk_text += f"  ФС: {part.get('fstype', 'N/A')}\n"
                disk_text += f"  Всего: {total_gb:.2f} GB\n"
                disk_text += f"  Использовано: {used_gb:.2f} GB ({part.get('percent', 0):.1f}%)\n"
                disk_text += f"  Свободно: {free_gb:.2f} GB\n\n"
            
            self.disk_info_text.delete("1.0", "end")
            self.disk_info_text.insert("1.0", disk_text)
        
        # Обновление процессов
        self._update_processes(processes)
    
    def _update_processes(self, processes):
        """Обновление списка процессов"""
        # Очистка
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        
        # Добавление новых данных
        for proc in processes:
            if 'error' in proc:
                continue
            
            pid = proc.get('pid', '')
            name = proc.get('name', '')[:50]
            cpu = f"{proc.get('cpu_percent', 0):.1f}"
            ram_percent = f"{proc.get('memory_percent', 0):.1f}"
            memory_mb = proc.get('memory_rss', 0) / (1024**2)
            threads = proc.get('threads', 0)
            username = proc.get('username', '')[:20]
            status = proc.get('status', '')
            
            self.process_tree.insert(
                "",
                "end",
                values=(pid, name, cpu, ram_percent, f"{memory_mb:.1f}", threads, username, status)
            )
    
    def stop_all_monitoring(self):
        """Остановка всех видов мониторинга"""
        self.monitoring_enabled = False
        self._stop_fs_monitoring()