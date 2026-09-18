"""
Tools + routing logic for the LangGraph side of the app.
Quick factual questions stay in the normal tool-calling loop (Tavily search
bound to the LLM). Anything that sounds like a request for a report/deep dive
gets routed to the CrewAI crew instead, before the LLM is even called.
"""

import re
from langchain_community.tools.tavily_search import TavilySearchResults

tavily_tool = TavilySearchResults(max_results=5)

tools = [tavily_tool]

# Keywords/phrases that signal "I want a structured report, not a quick answer."
_DEEP_RESEARCH_PATTERNS = [
    r"\breport\b",
    r"\bdeep dive\b",
    r"\bin[- ]depth\b",
    r"\bresearch\b",
    r"\banalysis\b",
    r"\bcomprehensive\b",
    r"\bwrite up\b",
    r"\bbriefing\b",
    r"\bsummary of everything\b",
]
_DEEP_RESEARCH_RE = re.compile("|".join(_DEEP_RESEARCH_PATTERNS), re.IGNORECASE)


def needs_deep_research(text: str) -> bool:
    """
    Heuristic classifier: does this look like a request for a full report
    (→ CrewAI crew) rather than a quick factual lookup (→ single Tavily call)?

    This is intentionally simple (regex + length) so it's fast and free to run
    on every turn. Swap it for a tiny LLM classification call if you want
    better accuracy later.
    """
    if not text:
        return False
    if _DEEP_RESEARCH_RE.search(text):
        return True
    # Long, open-ended questions are also usually asking for more than a one-liner.
    if len(text.split()) > 25:
        return True
    return False


def extract_topic(text: str) -> str:
    """Cleans up filler phrasing so the crew gets a clean topic string."""
    cleaned = re.sub(_DEEP_RESEARCH_RE, "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(give me|can you|please|a|an|the|on|about|for me)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ?.!")
    return cleaned or text
