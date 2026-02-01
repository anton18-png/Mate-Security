# Mate Security 🛡️

Лёгкий, современный и полностью бесплатный антивирус для Windows на базе **ClamAV**

## Возможности

- **Ручное сканирование** файлов, папок и дисков  
- **Защита в реальном времени** (мониторинг создания файлов через watchdog)  
  - два режима: полный и экономный  
- **Карантин** заражённых файлов (7z-архив с паролем)  
- **Менеджер паролей** с шифрованием AES-256-CBC (OpenSSL)  
  - генератор паролей  
  - импорт/экспорт CSV  
  - показать/скрыть, копирование в буфер  
- **Автозагрузка** с Windows  
- **Обновление баз** ClamAV одной кнопкой  
- **Сворачивание в системный трей**  
- **Журнал событий** в нижней части окна  
- Тёмная/светлая тема + выбор цветовой схемы

## Требования

- Windows 10 / 11 (x64)  
- Python 3.9+ (если запускаешь из исходников)  
- PyInstaller (для сборки в .exe)

## Установка

### Вариант 1 — Готовый .exe (рекомендуется)

1. Скачай релиз с [Releases](https://github.com/anton18-png/Mate-Security/releases)  
2. Запусти `Mate-Security-Setup.exe`

### Вариант 2 — Из исходников

```bash
# 1. Клонируем репозиторий
git clone https://github.com/anton18-png/Mate-Security.git
cd Mate-Security

# 2. Устанавливаем зависимости
pip install -r requirements.txt

# 3. Скачиваем Mate-Security-Setup.exe, распаковываем и настраиваем конфиги ClamAV

# 4. Запускаем
python main.py

# или в фоне (в трей)
python main.py --background
```

## Сборка в один .exe

```bash
# Установи PyInstaller, если ещё нет
pip install pyinstaller

# Собери (запускай из корня проекта)
pyinstaller ^
  --noconfirm ^
  --clean ^
  --name "Mate-Security" ^
  --icon "icon.ico" ^
  --add-data "main.pyw;." ^
  --add-data "database;database" ^
  --add-data "Utils;Utils" ^
  --add-data "core;core" ^
  --add-data "gui;gui" ^
  main.pyw
```

Готовый файл появится в папке `dist`.

## Структура проекта

```
Mate-Security/
├── main.py               # точка входа
├── gui/
│   └── app.py            # основной интерфейс
├── core/
│   ├── scanner.py        # сканирование по запросу
│   ├── realtime.py       # защита в реальном времени
│   ├── quarantine.py     # карантин
│   ├── password_manager.py # менеджер паролей
│   ├── utils.py
│   ├── constants.py
│   ├── settings.py
│   └── autostart.py
├── Utils/                # внешние утилиты
│   ├── clamav/
│   ├── 7za.exe
│   ├── launcher.exe
│   └── ...
├── database/             # базы ClamAV
├── user_data/            # настройки, карантин, логи
└── icon.ico
```

## Текущий статус (февраль 2026)

- ✅ Ручное сканирование  
- ✅ Реал-тайм защита  
- ✅ Карантин  
- ✅ Менеджер паролей  
- ✅ Обновление баз  
- ✅ Трей + автозагрузка

## Лицензия MIT

---

**Mate Security** — твой бесплатный open-source щит для Windows 💚