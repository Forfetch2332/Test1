from typing import Any, Dict, List


def normalize_hints(raw) -> List[str]:
    """
    Привести raw к списку непустых строк.
    Принимает список любых элементов, приводит к str и отбрасывает пустые.
    """
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for i, item in enumerate(raw):
        try:
            s = "" if item is None else str(item)
        except Exception:
            continue
        s = s.strip()
        if s:
            out.append(s)
    return out


def extract_hints_from_lesson(data: Dict[str, Any]) -> List[str]:
    """
    Извлечь подсказки из lesson-объекта.
    Поддерживаем:
      - поле "hints": список строк
      - поле "notes": список объектов с ключом "hint"
    Возвращаем список строк (возможно пустой).
    """
    if not isinstance(data, dict):
        return []

    # Прямые hints (если это список строк или смешанный список со строками)
    raw_hints = data.get("hints", [])
    if isinstance(raw_hints, list) and any(isinstance(x, str) for x in raw_hints):
        return normalize_hints(raw_hints)

    # notes -> [{"hint": "..."}]
    notes = data.get("notes", [])
    if isinstance(notes, list):
        extracted: List[str] = []
        for n in notes:
            if not isinstance(n, dict):
                continue
            h = n.get("hint")
            if isinstance(h, str) and h.strip():
                extracted.append(h.strip())
        return extracted

    return []
