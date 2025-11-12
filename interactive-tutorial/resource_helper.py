import os
import sys
import json
import traceback

# ---------- Логирование ----------
def log(msg: str) -> None:
    """Простое логирование в консоль."""
    print(f"[LOG] {msg}")

# ---------- Работа с ресурсами ----------
def resource_path(rel_path: str) -> str:
    """
    Возвращает корректный путь к ресурсу:
    - при обычном запуске: текущая рабочая директория
    - внутри exe (PyInstaller): временная папка _MEIPASS
    """
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

def load_json_resource(path: str):
    """
    Загружает JSON-файл по указанному пути.
    Возвращает (data, error), где error = None при успехе.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data, None
    except Exception as e:
        tb = traceback.format_exc()
        log(f"Ошибка загрузки JSON {path}: {e}\n{tb}")
        return None, str(e)

# ---------- Настройки (для сохранения прогресса подсказок и др.) ----------
_settings_cache = {}

def get_setting(key: str):
    """Получить сохранённое значение настройки (из памяти)."""
    return _settings_cache.get(key)

def set_setting(key: str, value):
    """Сохранить значение настройки (в памяти)."""
    _settings_cache[key] = value
    log(f"Setting saved: {key} = {value}")
