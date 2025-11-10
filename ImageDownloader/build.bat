@echo off
setlocal

REM Папка проекта — укажи свою:
cd D:\projects\ImageDownloader

REM venv
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate

REM Зависимости
pip install --upgrade pip
pip install -r requirements.txt

REM Очистка
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

REM Сборка (один файл, без консоли). Добавь --icon image.ico если будет иконка.
pyinstaller --name ImageDownloader --onefile --noconsole --icon image.ico image_downloader.py

echo.
echo Build done: dist\ImageDownloader.exe
pause
endlocal
