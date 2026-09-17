"""
Tiny JSON-file storage for the personal assistant.
Not a real database — good enough for a single-user, single-machine demo.
"""

import json
import os
import uuid
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "assistant_data.json")


def _load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"notes": [], "reminders": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_note(text: str) -> dict:
    data = _load()
    note = {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "created_at": datetime.now().isoformat(timespec="minutes"),
    }
    data["notes"].append(note)
    _save(data)
    return note


def list_notes() -> list:
    return _load()["notes"]


def delete_note(note_id: str) -> bool:
    data = _load()
    before = len(data["notes"])
    data["notes"] = [n for n in data["notes"] if n["id"] != note_id]
    _save(data)
    return len(data["notes"]) < before


def add_reminder(text: str, when: str) -> dict:
    """`when` is free-form text like 'tomorrow 3pm' or '2026-09-20' — this
    is a simple storage demo, not a real scheduler/calendar."""
    data = _load()
    reminder = {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "when": when,
        "created_at": datetime.now().isoformat(timespec="minutes"),
    }
    data["reminders"].append(reminder)
    _save(data)
    return reminder


def list_reminders() -> list:
    return _load()["reminders"]


def delete_reminder(reminder_id: str) -> bool:
    data = _load()
    before = len(data["reminders"])
    data["reminders"] = [r for r in data["reminders"] if r["id"] != reminder_id]
    _save(data)
    return len(data["reminders"]) < before
