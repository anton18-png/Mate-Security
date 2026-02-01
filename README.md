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
- Python 3.9+
- PyInstaller

# Инструкция по установке Mate-Security

## Предварительные требования

### 1. Установи Python 3.8 или новее
Скачай с [python.org](https://www.python.org/downloads/) и установи с галочкой "Add Python to PATH"

### 2. Установи Git (опционально)
Скачай с [git-scm.com](https://git-scm.com/download/win)

## Установка и сборка

### Шаг 1: Получение исходного кода

#### Вариант A — Скачать ZIP-архив
1. Перейди на [GitHub репозиторий](https://github.com/anton18-png/Mate-Security)
2. Нажми "Code" → "Download ZIP"
3. Распакуй архив в удобное место

#### Вариант B — Клонировать через Git
```bash
git clone https://github.com/anton18-png/Mate-Security.git
cd Mate-Security
```

### Шаг 2: Установка зависимостей Python
```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Шаг 3: Подготовка утилит
1. **Распакуй архив Utils.7z** в папку проекта:
   ```
   Mate-Security/
   ├── Utils/           ← папка после распаковки Utils.7z
   │   └── свежие файлы и утилиты
   ├── main.pyw
   └── ...
   ```

### Шаг 4: Сборка в .exe файл

```bash
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

**Результат:** Папка `Mate-Security` появится в `dist/`

## Перенос в системную папку

### Шаг 5: Копирование файлов
1. Создай папку `C:\Apps\Mate-Security\`
2. Скопируй `dist/Mate-Security` в `C:\Apps\`
3. Убедись, что папка пустая, кроме exe файла

## Установка ClamAV и загрузка баз данных

### Шаг 6: Установка ClamAV через postinstall.bat

1. Убедись, что в `C:\Apps\Mate-Security\` лежит `Mate-Security.exe`
2. Создай в этой же папке файл `postinstall.bat` с содержимым:

```batch
@echo off
chcp 65001
echo ========================================
echo   Установка Mate-Security
echo ========================================
echo.

echo Шаг 1: Установка ClamAV...
echo.

REM Загрузка ClamAV
curl -g -k -L -# -o "%CD%\_internal\Utils\clamav.zip" "https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.1/clamav-1.5.1.win.x64.zip"

REM Распаковка ClamAV
"%CD%\_internal\Utils\7za.exe" x "%CD%\_internal\Utils\clamav.zip" -o"%CD%\_internal\Utils" -y
robocopy "%CD%\_internal\Utils\clamav-1.5.1.win.x64" "%CD%\_internal\Utils\clamav" /E /MOVE /COPY:DAT /R:0 /W:0

REM Очистка временных файлов
rd /S /Q "%CD%\_internal\Utils\clamav-1.5.1.win.x64"
del /Q "%CD%\_internal\Utils\clamav.zip"

echo.
echo Шаг 2: Загрузка баз данных ClamAV...
echo.

REM Создание папки для баз данных
mkdir "%CD%\_internal\database" 2>nul

REM Загрузка основных баз данных
curl -g -k -L -# -o "%CD%\_internal\database\main.cvd" "https://unlix.ru/clamav/main.cvd"
curl -g -k -L -# -o "%CD%\_internal\database\daily.cvd" "https://unlix.ru/clamav/daily.cvd"
curl -g -k -L -# -o "%CD%\_internal\database\bytecode.cvd" "https://unlix.ru/clamav/bytecode.cvd"

echo Загрузка конфигов с GitHub...
REM Скачиваем конфиги напрямую из репозитория
curl -g -k -L -# -o "%CD%\_internal\Utils\clamav\clamav.conf" "https://raw.githubusercontent.com/anton18-png/Mate-Security/main/config/clamav.conf"
curl -g -k -L -# -o "%CD%\_internal\Utils\clamav\freshclam.conf" "https://raw.githubusercontent.com/anton18-png/Mate-Security/main/config/freshclam.conf"

REM Создаем пустые лог-файлы
echo. > "%CD%\_internal\Utils\clamav\clamd.log"
echo. > "%CD%\_internal\Utils\clamav\freshclam.log"

echo.
echo ========================================
echo   Установка завершена!
echo ========================================
echo.
echo Файлы расположены:
echo   ClamAV:        %CD%\_internal\Utils\clamav\
echo   Базы данных:   %CD%\_internal\database\
echo   Логи:          %CD%\_internal\logs\
echo.
pause
```

3. **Запусти postinstall.bat от имени администратора:**
   - Найди файл `postinstall.bat` в `C:\Apps\Mate-Security\`
   - Правой кнопкой → "Запуск от имени администратора"
   - Скрипт автоматически:
     1. Скачает и установит ClamAV
     2. Загрузит базы данных с unlix.ru
     3. Настроит все папки
     4. Скопирует базы данных в нужные места

## Альтернативная ручная установка

### Если нет интернета или нужна ручная настройка:

#### Шаг A: Установка ClamAV вручную
1. Скачай ClamAV с [официального сайта](https://www.clamav.net/downloads):
   - Или прямую ссылку: `https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.1/clamav-1.5.1.win.x64.zip`

2. Распакуй в папку:
   ```
   C:\Apps\Mate-Security\_internal\Utils\clamav\
   ```

#### Шаг B: Загрузка баз данных вручную
1. Создай папку: `C:\Apps\Mate-Security\_internal\database\`

2. Загрузи базы данных (выбери один вариант):

   **Вариант 1: Через браузер**
   - Открой в браузере:
     - https://unlix.ru/clamav/main.cvd
     - https://unlix.ru/clamav/daily.cvd  
     - https://unlix.ru/clamav/bytecode.cvd
   - Сохрани все три файла в `C:\Apps\Mate-Security\_internal\database\`

   **Вариант 2: Через curl**
   ```powershell
   cd C:\Apps\Mate-Security\_internal\database
   curl -L -o main.cvd https://unlix.ru/clamav/main.cvd
   curl -L -o daily.cvd https://unlix.ru/clamav/daily.cvd
   curl -L -o bytecode.cvd https://unlix.ru/clamav/bytecode.cvd
   ```

#### Шаг C: Настройка конфигов ClamAV
Убедись, что в `C:\Apps\Mate-Security\_internal\clamav\` есть файлы:
   - `clamav.conf` — основной конфиг
   - `freshclam.conf` — для обновления баз

## Структура проекта

```
Mate-Security/
├── main.pyw              # точка входа
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

