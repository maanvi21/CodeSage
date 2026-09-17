"""
LangChain @tool wrappers. These are the functions the LLM is allowed to
call. The docstring of each tool is what the model reads to decide when
and how to use it — keep them clear and specific.
"""

from langchain_core.tools import tool
import storage


@tool
def add_note_tool(text: str) -> str:
    """Save a note for the user. Use this when the user asks you to
    remember, note down, or jot something."""
    note = storage.add_note(text)
    return f"Saved note {note['id']}: {note['text']}"


@tool
def list_notes_tool() -> str:
    """List all saved notes. Use this when the user asks what notes they
    have, or to show/recall their notes."""
    notes = storage.list_notes()
    if not notes:
        return "No notes saved yet."
    return "\n".join(f"[{n['id']}] {n['text']} (saved {n['created_at']})" for n in notes)


@tool
def delete_note_tool(note_id: str) -> str:
    """Delete a note by its id. Use this when the user asks to remove or
    delete a specific note. You need the note's id, which list_notes_tool
    returns in brackets, e.g. [a1b2c3d4]."""
    ok = storage.delete_note(note_id)
    return f"Deleted note {note_id}." if ok else f"No note found with id {note_id}."


@tool
def add_reminder_tool(text: str, when: str) -> str:
    """Save a reminder for the user with a time description, e.g.
    when='tomorrow 3pm' or when='2026-09-20'. Use this when the user asks
    to be reminded of something. This only stores the reminder — it does
    not send notifications."""
    reminder = storage.add_reminder(text, when)
    return f"Saved reminder {reminder['id']}: {reminder['text']} ({reminder['when']})"


@tool
def list_reminders_tool() -> str:
    """List all saved reminders. Use this when the user asks what
    reminders they have."""
    reminders = storage.list_reminders()
    if not reminders:
        return "No reminders saved yet."
    return "\n".join(f"[{r['id']}] {r['text']} — {r['when']}" for r in reminders)


@tool
def delete_reminder_tool(reminder_id: str) -> str:
    """Delete a reminder by its id. Use this when the user asks to remove
    or cancel a specific reminder."""
    ok = storage.delete_reminder(reminder_id)
    return f"Deleted reminder {reminder_id}." if ok else f"No reminder found with id {reminder_id}."


ALL_TOOLS = [
    add_note_tool,
    list_notes_tool,
    delete_note_tool,
    add_reminder_tool,
    list_reminders_tool,
    delete_reminder_tool,
]
