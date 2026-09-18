"""Simple pyttsx3 wrapper, same as the original voice-assistant."""

import pyttsx3

_engine = pyttsx3.init()
_engine.setProperty("rate", 180)


def speak(text: str) -> None:
    if not text:
        return
    _engine.say(text)
    _engine.runAndWait()


def speak_summary(full_text: str, max_sentences: int = 3) -> None:
    """
    For long reports, only speak a short spoken summary rather than reading
    the whole thing aloud. The full text still gets saved to disk separately.
    """
    sentences = [s.strip() for s in full_text.replace("\n", " ").split(".") if s.strip()]
    summary = ". ".join(sentences[:max_sentences])
    if summary and not summary.endswith("."):
        summary += "."
    speak(summary or "Here's a summary. The full report has been saved.")
