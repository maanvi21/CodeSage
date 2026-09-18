import os
import re
from datetime import datetime

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def save_report(topic: str, content: str) -> str:
    """Saves the full CrewAI report as a timestamped markdown file. Returns the file path."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:60] or "report"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}_{slug}.md"
    path = os.path.join(REPORTS_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Research Report: {topic}\n\n")
        f.write(f"_Generated {datetime.now().isoformat(timespec='seconds')}_\n\n")
        f.write(content)

    return path
