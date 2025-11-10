# content_validator.py
from typing import Any, Dict, Tuple

def _err(msg: str) -> Tuple[bool, str]:
    return False, msg

def validate_lesson(data: Dict[str, Any]) -> Tuple[bool, str | None]:
    if not isinstance(data, dict):
        return _err("Lesson must be a JSON object")

    # Required
    if "title" not in data or not isinstance(data["title"], str) or not data["title"].strip():
        return _err("Lesson.title is required and must be a non-empty string")
    if "example" not in data or not isinstance(data["example"], str):
        return _err("Lesson.example is required and must be a string")

    #Optional
    if "summary" in data and not isinstance(data["summary"], str):
        return _err("Lesson.summary must be a string")

    if "text" in data:
        if not isinstance(data["text"], list):
            return _err("Lesson.text must be a list of strings")
        for i, item in enumerate(data["text"]):
            if not isinstance(item, str):
                return _err(f"Lessons.text[{i}] must be a string")

    if "notes" in data:
        if not isinstance(data["notes"], list):
            return _err("Lesson.notes must be a list of objects")
        for i, note in enumerate(data["notes"]):
            if not isinstance(note, dict):
                return _err(f"Lesson.notes[{i}] must be an object")
            if "hint" not in note or not isinstance(note["hint"], str):
                return _err(f"Lesson.notes[{i}].hint is required and must be a string")

    return True, None

def validate_task(data: Dict[str, Any]) -> Tuple[bool, str | None]:
    if not isinstance(data, dict):
        return _err("Task must be a JSON object")

    # Required
    if "title" not in data or not isinstance(data["title"], str) or not data["title"].strip():
        return _err("Task.title is required and must be a non-empty string")
    if "statement" not in data and not isinstance(data["statement"], str):
        return _err("Task.statement is required and must be a string")
    if "template" not in data or not isinstance(data["template"], str):
        return _err("Task.template is required and must be a string")
    if "check" not in data or not isinstance(data["check"], dict):
        return _err("Task.check is required and must be an object")

    check = data["check"]
    if "type" not in check or not isinstance(check["type"], str):
        return _err("Task.check.type is required and must be a string")

    ctype = check["type"]
    if ctype == "stdout_equals":
        if "expected" not in check or not isinstance(check["expected"], str):
            return _err("Task.check.expected is required and must be a string for stdout_equals")
    else:
        return _err(f"Unsupported check.type: {ctype}")

    if "hints" in data:
        if not isinstance(data["hints"], list):
            return _err("Task.hints must be a list of strings")
        for i, h in enumerate(data["hints"]):
            if not isinstance(h, str):
                return _err(f"Task.hints[{i}] must be a string")

    return True, None