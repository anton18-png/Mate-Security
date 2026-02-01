import threading
from pathlib import Path
from typing import List
import csv
import sys

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinter import ttk

from core.constants import BASE_DIR
from core.settings import Settings
from core.constants import ensure_dirs
from core.utils import load_quarantine_meta, launcher_run
from core.scanner import run_clamscan, filter_excluded
from core.realtime import RealTimeMonitor
from core.password_manager import PasswordDatabase
from core.autostart import enable_autostart, disable_autostart, is_autostart_enabled


class AntivirusApp(ctk.CTk):
    def __init__(self, start_hidden: bool = False) -> None:
        super().__init__()
        ensure_dirs()
        self.settings = Settings()
        self.password_db = PasswordDatabase(self.settings.crypto_cipher)
        self.realtime = RealTimeMonitor(
            quarantine_password=self.settings.quarantine_password,
            log_callback=self._log,
            ask_user_action=self._ask_user_action,
        )

        self.title("Mate Security")
        self.geometry("1100x700")
        self.minsize(900, 600)

        icon_path = BASE_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except Exception:
                pass

        ctk.set_default_color_theme("green")
        ctk.set_appearance_mode(self.settings.appearance_mode.lower())

        self._create_layout()

        # Обработчик закрытия окна — сворачиваем в трей
        self.protocol("WM_DELETE_WINDOW", self._on_close_to_tray)

        self.after(200, self._load_quarantine_into_table)

        self._tray_icon = None
        self._tray_thread = None

        if start_hidden:
            # старт в фоне: не показываем окно, только иконка в трее
            self.withdraw()
            self._ensure_tray()

    # ---- Layout ----
    def _create_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        sidebar = ctk.CTkFrame(self, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_rowconfigure(7, weight=1)

        logo_label = ctk.CTkLabel(
            sidebar,
            text="Mate\nSecurity",
            font=ctk.CTkFont(size=22, weight="bold"),
            justify="left",
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.btn_main = ctk.CTkButton(sidebar, text="Главная", command=self._show_main_tab)
        self.btn_quarantine = ctk.CTkButton(sidebar, text="Карантин", command=self._show_quarantine_tab)
        self.btn_passwords = ctk.CTkButton(sidebar, text="Менеджер паролей", command=self._show_passwords_tab)
        self.btn_settings = ctk.CTkButton(sidebar, text="Настройки", command=self._show_settings_tab)

        self.btn_main.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.btn_quarantine.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        self.btn_passwords.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.btn_settings.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.realtime_switch = ctk.CTkSwitch(
            sidebar,
            text="Защита в реальном времени",
            command=self._toggle_realtime,
        )
        self.realtime_switch.grid(row=5, column=0, padx=20, pady=(20, 5), sticky="w")

        self.economy_switch = ctk.CTkSwitch(
            sidebar,
            text="Экономный режим",
            command=self._toggle_economy,
        )
        self.economy_switch.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="w")

        update_btn = ctk.CTkButton(
            sidebar,
            text="Обновить базы",
            command=self._update_databases_threaded,
        )
        update_btn.grid(row=8, column=0, padx=20, pady=(10, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(
            sidebar,
            text="Готово",
            anchor="w",
            wraplength=160,
        )
        self.status_label.grid(row=9, column=0, padx=20, pady=10, sticky="sw")

        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.main_tab = ctk.CTkFrame(self.content)
        self.quarantine_tab = ctk.CTkFrame(self.content)
        self.passwords_tab = ctk.CTkFrame(self.content)
        self.settings_tab = ctk.CTkFrame(self.content)

        for tab in (self.main_tab, self.quarantine_tab, self.passwords_tab, self.settings_tab):
            tab.grid(row=0, column=0, sticky="nsew")

        self._build_main_tab()
        self._build_quarantine_tab()
        self._build_passwords_tab()
        self._build_settings_tab()

        self._show_main_tab()

    # ---- tray ----
    def _ensure_tray(self) -> None:
        if self._tray_thread and self._tray_thread.is_alive():
            return
        import pystray
        from PIL import Image

        def run_tray() -> None:
            icon_path = BASE_DIR / "icon.ico"
            if icon_path.exists():
                image = Image.open(icon_path)
            else:
                image = Image.new("RGB", (32, 32), (0, 150, 0))

            def on_show(icon, item):
                self.after(0, self._show_from_tray)

            def on_exit(icon, item):
                icon.stop()
                self.after(0, self._exit_from_tray)

            menu = pystray.Menu(
                pystray.MenuItem("Открыть Mate Security", on_show),
                pystray.MenuItem("Выход", on_exit),
            )
            self._tray_icon = pystray.Icon("MateSecurity", image, "Mate Security", menu)
            self._tray_icon.run()

        self._tray_thread = threading.Thread(target=run_tray, daemon=True)
        self._tray_thread.start()

    def _on_close_to_tray(self) -> None:
        # прячем окно и оставляем иконку в трее
        self.withdraw()
        self._ensure_tray()

    def _show_from_tray(self) -> None:
        self.deiconify()
        self.focus_force()

    def _exit_from_tray(self) -> None:
        self.destroy()

    # ---- Tab switching ----
    def _show_main_tab(self) -> None:
        self.main_tab.tkraise()
        self.status_label.configure(text="Готово")

    def _show_quarantine_tab(self) -> None:
        self.quarantine_tab.tkraise()
        self._load_quarantine_into_table()

    def _show_passwords_tab(self) -> None:
        self.passwords_tab.tkraise()

    def _show_settings_tab(self) -> None:
        self.settings_tab.tkraise()

    # ---- Main tab ----
    def _build_main_tab(self) -> None:
        self.main_tab.grid_rowconfigure(2, weight=1)
        self.main_tab.grid_columnconfigure(0, weight=1)

        top_frame = ctk.CTkFrame(self.main_tab)
        top_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        disks_label = ctk.CTkLabel(
            top_frame,
            text="Диски",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        disks_label.grid(row=0, column=0, sticky="w")

        buttons_frame = ctk.CTkFrame(top_frame)
        buttons_frame.grid(row=0, column=1, padx=10, sticky="e")

        btn_scan_file = ctk.CTkButton(buttons_frame, text="Сканировать файл", command=self._scan_files_dialog)
        btn_scan_folder = ctk.CTkButton(buttons_frame, text="Сканировать папку (рекурсивно)", command=self._scan_folder_dialog)
        btn_scan_file.grid(row=0, column=0, padx=5)
        btn_scan_folder.grid(row=0, column=1, padx=5)

        self.disks_box = ctk.CTkTextbox(top_frame, height=70)
        self.disks_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        # выпадающий список для выбора одного диска
        self.disk_combo = ctk.CTkComboBox(top_frame, values=[])
        self.disk_combo.grid(row=2, column=0, sticky="w", pady=(5, 0))
        disk_scan_btn = ctk.CTkButton(
            top_frame,
            text="Сканировать выбранный диск",
            command=self._scan_single_disk,
        )
        disk_scan_btn.grid(row=2, column=1, sticky="e", padx=5, pady=(5, 0))

        self._refresh_disks()

        mid_frame = ctk.CTkFrame(self.main_tab)
        mid_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        scan_disks_btn = ctk.CTkButton(
            mid_frame,
            text="Сканировать все перечисленные диски",
            command=self._scan_selected_disks,
        )
        scan_disks_btn.pack(side="left", padx=5, pady=5)

        log_frame = ctk.CTkFrame(self.main_tab)
        log_frame.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")

    def _refresh_disks(self) -> None:
        self.disks_box.delete("1.0", "end")
        disk_list: List[str] = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            path = f"{letter}:\\"
            if Path(path).exists():
                disk_list.append(path)
                self.disks_box.insert("end", path + "\n")
        if disk_list:
            self.disk_combo.configure(values=disk_list)
            self.disk_combo.set(disk_list[0])

    def _scan_single_disk(self) -> None:
        disk = self.disk_combo.get().strip()
        if not disk:
            messagebox.showinfo("Сканирование", "Выберите диск для сканирования.")
            return
        paths = filter_excluded([disk])
        if not paths:
            messagebox.showinfo("Сканирование", "Выбранный диск исключён политикой.")
            return
        self._start_scan(paths)

    def _scan_selected_disks(self) -> None:
        text = self.disks_box.get("1.0", "end").strip()
        paths = [line.strip() for line in text.splitlines() if line.strip()]
        paths = filter_excluded(paths)
        if not paths:
            messagebox.showinfo("Сканирование", "Нет доступных дисков для сканирования.")
            return
        self._start_scan(paths)

    def _scan_folder_dialog(self) -> None:
        folder = filedialog.askdirectory(title="Выберите папку для сканирования")
        if folder:
            self._start_scan([folder])

    def _scan_files_dialog(self) -> None:
        files = filedialog.askopenfilenames(title="Выберите файлы для сканирования")
        if files:
            self._start_scan(list(files))

    def _start_scan(self, paths: List[str]) -> None:
        self._log("\n=== Запуск сканирования ===\n")
        self.status_label.configure(text="Сканирование...")
        thread = threading.Thread(
            target=run_clamscan,
            args=(
                paths,
                self.settings.quarantine_password,
                self._log,
                self._ask_user_action,
            ),
            daemon=True,
        )
        thread.start()

    # ---- Quarantine tab ----
    def _build_quarantine_tab(self) -> None:
        from core.utils import load_quarantine_meta

        self.quarantine_tab.grid_rowconfigure(1, weight=1)
        self.quarantine_tab.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            self.quarantine_tab,
            text="Карантин",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        header.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")

        self.q_table = ctk.CTkTextbox(self.quarantine_tab)
        self.q_table.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        btns = ctk.CTkFrame(self.quarantine_tab)
        btns.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ns")

        restore_btn = ctk.CTkButton(btns, text="Разблокировать (восстановить)", command=self._restore_from_quarantine)
        delete_btn = ctk.CTkButton(btns, text="Удалить из карантина", command=self._delete_from_quarantine)

        restore_btn.pack(fill="x", pady=4)
        delete_btn.pack(fill="x", pady=4)

    def _load_quarantine_into_table(self) -> None:
        items = load_quarantine_meta()
        self.q_table.delete("1.0", "end")
        if not items:
            self.q_table.insert("end", "Карантин пуст.\n")
            return
        for idx, item in enumerate(items, start=1):
            line = (
                f"{idx}. {item.get('time', '')} | {item.get('original_path', '')} | "
                f"{item.get('reason', '')}\n"
            )
            self.q_table.insert("end", line)

    def _restore_from_quarantine(self) -> None:
        from customtkinter import CTkInputDialog
        from core.utils import load_quarantine_meta, save_quarantine_meta
        from core.quarantine import UTILS_DIR as QUTILS_DIR  # type: ignore

        items = load_quarantine_meta()
        if not items:
            messagebox.showinfo("Карантин", "Карантин пуст.")
            return

        dialog = CTkInputDialog(
            title="Разблокировать файл",
            text="Введите номер записи (из списка слева), которую нужно восстановить:",
        )
        value = dialog.get_input()
        if not value:
            return
        try:
            idx = int(value) - 1
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный номер.")
            return
        if not (0 <= idx < len(items)):
            messagebox.showerror("Ошибка", "Записи с таким номером нет.")
            return

        item = items[idx]
        archive_path = item.get("archive_path")
        original_path = item.get("original_path")
        if not archive_path or not Path(archive_path).exists():
            messagebox.showerror("Ошибка", "Архив карантина не найден.")
            return

        self._log(f"Восстановление из карантина: {original_path}\n")
        seven_zip = str(QUTILS_DIR / "7za.exe")
        target_dir = Path(original_path).parent if original_path else BASE_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        pwd = self.settings.quarantine_password or "clamav"
        cmd = [seven_zip, "x", f"-p{pwd}", "-y", archive_path, f"-o{target_dir}"]
        proc = launcher_run(cmd)
        for line in proc.stdout:
            self._log(line)
        proc.wait()

        if proc.returncode == 0:
            self._log("Файл успешно восстановлен.\n")
            try:
                Path(archive_path).unlink(missing_ok=True)
            except Exception:
                pass
            del items[idx]
            save_quarantine_meta(items)
            self._load_quarantine_into_table()
        else:
            self._log("Ошибка при восстановлении файла.\n")

    def _delete_from_quarantine(self) -> None:
        from customtkinter import CTkInputDialog
        from core.utils import load_quarantine_meta, save_quarantine_meta

        items = load_quarantine_meta()
        if not items:
            messagebox.showinfo("Карантин", "Карантин пуст.")
            return

        dialog = CTkInputDialog(
            title="Удалить из карантина",
            text="Введите номер записи (из списка слева), которую нужно удалить навсегда:",
        )
        value = dialog.get_input()
        if not value:
            return
        try:
            idx = int(value) - 1
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный номер.")
            return
        if not (0 <= idx < len(items)):
            messagebox.showerror("Ошибка", "Записи с таким номером нет.")
            return

        item = items[idx]
        archive_path = item.get("archive_path")

        if not messagebox.askyesno(
            "Подтверждение",
            "Вы уверены, что хотите удалить файл из карантина навсегда?\n"
            "Отменить это действие будет невозможно.",
        ):
            return

        if archive_path:
            Path(archive_path).unlink(missing_ok=True)

        del items[idx]
        save_quarantine_meta(items)
        self._load_quarantine_into_table()
        self._log("Запись удалена из карантина.\n")

    # ---- Password manager tab (simple UI) ----
    def _build_passwords_tab(self) -> None:
        """Создаёт и настраивает вкладку Менеджер паролей"""
        # Очистка предыдущего содержимого вкладки (на всякий случай)
        for widget in self.passwords_tab.winfo_children():
            widget.destroy()

        # Основной контейнер
        main_frame = ctk.CTkFrame(self.passwords_tab)
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Верхняя панель с кнопками и статусом
        top_panel = ctk.CTkFrame(main_frame)
        top_panel.pack(fill="x", pady=(0, 10))

        # Кнопки управления
        buttons = [
            ("Открыть базу", self._pm_open, "🔓"),
            ("Сохранить базу", self._pm_save, "💾"),
            ("Добавить запись", self._pm_add, "➕"),
            ("Удалить выбранное", self._pm_delete, "🗑️"),
            ("Экспорт CSV", self._pm_export_csv, "📤"),
            ("Импорт CSV", self._pm_import_csv, "📥"),
        ]

        for text, cmd, emoji in buttons:
            btn = ctk.CTkButton(
                top_panel,
                text=f"{emoji} {text}",
                width=140,
                command=cmd
            )
            btn.pack(side="left", padx=6)

        # Чекбокс "Показать пароли"
        self.pm_show_passwords = ctk.BooleanVar(value=False)
        show_checkbox = ctk.CTkCheckBox(
            top_panel,
            text="Показать пароли",
            variable=self.pm_show_passwords,
            command=self._pm_refresh
        )
        show_checkbox.pack(side="left", padx=(20, 0))

        # Статусная строка
        self.pm_status = ctk.CTkLabel(
            main_frame,
            text="Готово. Нажмите «Открыть базу» для начала работы",
            anchor="w",
            font=("Segoe UI", 12)
        )
        self.pm_status.pack(fill="x", pady=(0, 8))

        # Таблица (Treeview в CTkScrollableFrame)
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True)

        # Оборачиваем Treeview в ScrollableFrame
        scrollable = ctk.CTkScrollableFrame(tree_frame)
        scrollable.pack(fill="both", expand=True)

        # Сам Treeview
        style = ttk.Style()
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 11))
        style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"))

        self.pm_tree = ttk.Treeview(
            scrollable,
            columns=("site", "login", "password", "comment"),
            show="headings",
            selectmode="browse"
        )

        # Заголовки колонок
        self.pm_tree.heading("site", text="Сайт / Сервис")
        self.pm_tree.heading("login", text="Логин")
        self.pm_tree.heading("password", text="Пароль")
        self.pm_tree.heading("comment", text="Комментарий / Заметки")

        # Ширины колонок
        self.pm_tree.column("site", width=280, anchor="w")
        self.pm_tree.column("login", width=220, anchor="w")
        self.pm_tree.column("password", width=220, anchor="w")
        self.pm_tree.column("comment", width=340, anchor="w")

        self.pm_tree.pack(fill="both", expand=True, padx=4, pady=4)

        # Привязка двойного клика (опционально — можно открыть запись)
        self.pm_tree.bind("<Double-1>", self._pm_on_double_click)

        # Первичное обновление (пока пусто, пока не загрузят базу)
        self._pm_refresh()


    def _pm_set_status(self, text: str) -> None:
        if hasattr(self, "pm_status"):
            self.pm_status.configure(text=text)


    def _pm_refresh(self) -> None:
        if not hasattr(self, "pm_tree") or not self.pm_tree:
            return

        # Очистка таблицы
        for item in self.pm_tree.get_children():
            self.pm_tree.delete(item)

        show_plain = self.pm_show_passwords.get()

        if not hasattr(self.password_db, "items") or not self.password_db.items:
            self._pm_set_status("База паролей не загружена или пуста")
            return

        for entry in self.password_db.items:
            pwd_display = entry.get("password", "") if show_plain else ("●" * 12)
            self.pm_tree.insert(
                "",
                "end",
                values=(
                    entry.get("site", entry.get("name", "—")),
                    entry.get("login", entry.get("username", "—")),
                    pwd_display,
                    entry.get("comment", entry.get("notes", "—"))
                )
            )

        self._pm_set_status(f"Записей: {len(self.password_db.items)}")


    def _pm_get_master(self) -> str | None:
        """Запрашивает мастер-пароль через диалог customtkinter"""
        dialog = ctk.CTkInputDialog(
            title="Мастер-пароль",
            text="Введите мастер-пароль для доступа к базе:"
        )
        pwd = dialog.get_input()
        return pwd.strip() if pwd and pwd.strip() else None


    def _pm_open(self) -> None:
        pwd = self._pm_get_master()
        if not pwd:
            self._pm_set_status("Открытие отменено")
            return

        try:
            self.password_db.load(pwd)
            self._pm_refresh()
            self._pm_set_status("База успешно загружена ✓")
        except Exception as e:
            self._pm_set_status(f"Ошибка загрузки: {str(e)}")


    def _pm_save(self) -> None:
        pwd = self._pm_get_master()
        if not pwd:
            self._pm_set_status("Сохранение отменено")
            return

        try:
            self.password_db.save(pwd)
            self._pm_set_status("База успешно сохранена ✓")
        except Exception as e:
            self._pm_set_status(f"Ошибка сохранения: {str(e)}")


    def _pm_add(self) -> None:
        """Добавление новой записи через последовательные диалоги"""
        site = ctk.CTkInputDialog(title="Новая запись", text="Сайт / Сервис:").get_input()
        if not site:
            return

        login = ctk.CTkInputDialog(title="Новая запись", text="Логин:").get_input() or ""
        password = ctk.CTkInputDialog(title="Новая запись", text="Пароль:", show="*").get_input() or ""
        comment = ctk.CTkInputDialog(title="Новая запись", text="Комментарий / Заметки:").get_input() or ""

        if not password:
            self._pm_set_status("Добавление отменено — пароль обязателен")
            return

        self.password_db.items.append({
            "site": site.strip(),
            "login": login.strip(),
            "password": password.strip(),
            "comment": comment.strip()
        })

        self._pm_refresh()
        self._pm_set_status("Запись добавлена")


    def _pm_delete(self) -> None:
        selected = self.pm_tree.selection()
        if not selected:
            self._pm_set_status("Выберите запись для удаления")
            return

        idx = self.pm_tree.index(selected[0])
        if 0 <= idx < len(self.password_db.items):
            del self.password_db.items[idx]
            self._pm_refresh()
            self._pm_set_status("Запись удалена")


    def _pm_export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")],
            title="Экспорт паролей в CSV"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["site", "login", "password", "comment"])
                writer.writeheader()
                for item in self.password_db.items:
                    writer.writerow(item)
            self._pm_set_status(f"Экспортировано в {Path(path).name}")
        except Exception as e:
            self._pm_set_status(f"Ошибка экспорта: {e}")


    def _pm_import_csv(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")],
            title="Импорт паролей из CSV"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                imported = 0
                for row in reader:
                    self.password_db.items.append({
                        "site": row.get("site", row.get("name", "")),
                        "login": row.get("login", row.get("username", "")),
                        "password": row.get("password", ""),
                        "comment": row.get("comment", row.get("notes", ""))
                    })
                    imported += 1

            self._pm_refresh()
            self._pm_set_status(f"Импортировано {imported} записей")
        except Exception as e:
            self._pm_set_status(f"Ошибка импорта: {e}")


    def _pm_on_double_click(self, event):
        """При двойном клике можно показать запись или скопировать пароль (опционально)"""
        item = self.pm_tree.identify_row(event.y)
        if not item:
            return

        col = self.pm_tree.identify_column(event.x)
        if col == "#3":  # колонка пароля
            values = self.pm_tree.item(item, "values")
            pwd = values[2]
            if pwd and "*" not in pwd:
                self.clipboard_clear()
                self.clipboard_append(pwd)
                self._pm_set_status("Пароль скопирован в буфер обмена")

    # ---- Settings tab ----
    def _build_settings_tab(self) -> None:
        self.settings_tab.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            self.settings_tab,
            text="Настройки",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        mode_label = ctk.CTkLabel(self.settings_tab, text="Тема оформления:")
        mode_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")

        self.mode_option = ctk.CTkOptionMenu(
            self.settings_tab,
            values=["Light", "Dark", "System"],
            command=self._on_mode_change,
        )
        self.mode_option.set(self.settings.appearance_mode)
        self.mode_option.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")

        color_label = ctk.CTkLabel(self.settings_tab, text="Акцентный цвет:")
        color_label.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="w")

        self.color_option = ctk.CTkOptionMenu(
            self.settings_tab,
            values=["green", "blue", "dark-blue"],
            command=self._on_color_change,
        )
        self.color_option.set(self.settings.color_theme)
        self.color_option.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

        pwd_label = ctk.CTkLabel(self.settings_tab, text="Пароль для шифрования карантина:")
        pwd_label.grid(row=5, column=0, padx=20, pady=(10, 5), sticky="w")

        self.pwd_entry = ctk.CTkEntry(self.settings_tab, show="*")
        self.pwd_entry.insert(0, self.settings.quarantine_password)
        self.pwd_entry.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="w")

        cipher_label = ctk.CTkLabel(self.settings_tab, text="Алгоритм шифрования (OpenSSL):")
        cipher_label.grid(row=7, column=0, padx=20, pady=(10, 5), sticky="w")

        self.cipher_entry = ctk.CTkEntry(self.settings_tab)
        self.cipher_entry.insert(0, self.settings.crypto_cipher)
        self.cipher_entry.grid(row=8, column=0, padx=20, pady=(0, 10), sticky="w")
        # Автозагрузка
        auto_label = ctk.CTkLabel(self.settings_tab, text="Автозагрузка Mate Security:")
        auto_label.grid(row=9, column=0, padx=20, pady=(10, 5), sticky="w")

        auto_frame = ctk.CTkFrame(self.settings_tab)
        auto_frame.grid(row=10, column=0, padx=20, pady=(0, 10), sticky="w")

        auto_on_btn = ctk.CTkButton(auto_frame, text="Добавить в автозагрузку", command=self._enable_autostart)
        auto_off_btn = ctk.CTkButton(auto_frame, text="Удалить из автозагрузки", command=self._disable_autostart)
        auto_on_btn.pack(side="left", padx=5)
        auto_off_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(self.settings_tab, text="Сохранить настройки", command=self._save_settings)
        save_btn.grid(row=11, column=0, padx=20, pady=(20, 10), sticky="w")

    def _on_mode_change(self, choice: str) -> None:
        if choice == "System":
            ctk.set_appearance_mode("system")
        else:
            ctk.set_appearance_mode(choice.lower())
        self.settings.appearance_mode = choice

    def _on_color_change(self, choice: str) -> None:
        self.settings.color_theme = choice
        messagebox.showinfo("Тема цвета", "Изменение цвета вступит в силу после перезапуска приложения.")

    def _save_settings(self) -> None:
        self.settings.quarantine_password = self.pwd_entry.get() or "clamav"
        self.settings.crypto_cipher = self.cipher_entry.get() or "aes-256-cbc"
        self.settings.save()
        messagebox.showinfo("Настройки", "Настройки сохранены.")

    # ---- DB update ----
    def _update_databases_threaded(self) -> None:
        thread = threading.Thread(target=self._update_databases, daemon=True)
        thread.start()

    def _update_databases(self) -> None:
        from core.constants import DB_DIR, UTILS_DIR

        urls = [
            "https://unlix.ru/clamav/main.cvd",
            "https://unlix.ru/clamav/daily.cvd",
            "https://unlix.ru/clamav/bytecode.cvd",
        ]
        names = ["main.cvd", "daily.cvd", "bytecode.cvd"]
        busybox = str(UTILS_DIR / "busybox.exe")

        self.status_label.configure(text="Обновление баз данных...")
        for url, name in zip(urls, names):
            self._log(f"Загрузка {name}...\n")
            out_path = str(DB_DIR / name)
            proc = launcher_run([busybox, "wget", "-O", out_path, url])
            for line in proc.stdout:
                self._log(line)
            proc.wait()
        self.status_label.configure(text="Базы данных обновлены")
        self._log("Обновление баз завершено.\n")

    # ---- Autostart ----
    def _enable_autostart(self) -> None:
        try:
            enable_autostart()
            messagebox.showinfo("Автозагрузка", "Mate Security добавлен в автозагрузку.")
        except Exception as e:
            messagebox.showerror("Автозагрузка", f"Не удалось добавить в автозагрузку: {e}")

    def _disable_autostart(self) -> None:
        try:
            disable_autostart()
            messagebox.showinfo("Автозагрузка", "Mate Security удалён из автозагрузки.")
        except Exception as e:
            messagebox.showerror("Автозагрузка", f"Не удалось удалить из автозагрузки: {e}")

    # ---- Realtime ----
    def _toggle_realtime(self) -> None:
        if self.realtime_switch.get():
            self.realtime.start()
        else:
            self.realtime.stop()

    def _toggle_economy(self) -> None:
        self.realtime.set_economy_mode(bool(self.economy_switch.get()))

    # ---- Helpers ----
    def _log(self, text: str) -> None:
        if not hasattr(self, "log_text"):
            return

        def _append() -> None:
            self.log_text.insert("end", text)
            self.log_text.see("end")

        self.log_text.after(0, _append)

    def _ask_user_action(self, path: str, virus: str) -> bool:
        return messagebox.askyesno(
            "Обнаружен вирус",
            f"Файл:\n{path}\n\nУгроза: {virus}\n\n"
            f"Да — переместить в карантин\n"
            f"Нет — удалить файл навсегда",
        )


def run_gui() -> None:
    # поддержка флага --background / -b
    args = sys.argv[1:]
    start_hidden = ("--background" in args) or ("-b" in args)
    app = AntivirusApp(start_hidden=start_hidden)
    app.mainloop()

