import os, sys, json, errno
from datetime import datetime
from typing import Any, Dict, Tuple

APP_NAME = "interactive_tutorial"

def get_user_data_dir():
    if sys.platform.startswith('win'):
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == 'darwin':
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATE_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(base, APP_NAME)

def ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

def ensure_app_dirs():
    base = get_user_data_dir()
    logs = os.path.join(base, "logs")
    ensure_dir(base); ensure_dir(logs)
    return {"base": base, "logs": logs}

def log(msg):
    try:
        dirs = ensure_app_dirs()
        lp = os.path.join(dirs["logs"], "app.log")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(lp, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def resourse_path(rel: str) -> str:
    """
    Возвращает абсолютный путь к ресурсу относительно корня проекта или PyInstaller-пакета
    """
    if getattr(sys, "frozen", False):
        base = sys.MEIPASS # type: ignore
    else:
        base = os.path.abspath(".")
    return os.path.join(base, rel)

def load_json_resource(rel_path: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Загружает JSON из относительного пути (content/lessons/01_intro.json).
    Возвращает (data, error). При ошибке data=None, error=msg.
    """
    path = resourse_path(rel_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        msg = f"File not found: {rel_path}"
        log(msg)
        return None, msg
    except json.JSONDecodeError as e:
        msg = f"JSON decode error in {rel_path}: {e}"
        log(msg)
        return None, msg
    except Exception as e:
        msg = f"Error reading {rel_path}: {e}"
        log(msg)
        return None, msg

