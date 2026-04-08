import re
from typing import Dict, List
from config_production import settings

DEFAULT_BLOCKLIST = [
    "suicide",
    "self-harm",
    "kill yourself",
    "child exploitation",
    "sexual assault",
    "make a bomb",
    "build a bomb",
]

DEFAULT_PATTERNS = [
    r"\bkill\s+yourself\b",
    r"\bself\-?harm\b",
    r"\bmake\s+(?:a|an)\s+bomb\b",
    r"\bbuild\s+(?:a|an)\s+bomb\b",
    r"\bchild\s+(?:abuse|exploitation|porn)\b",
    r"\bsexual\s+assault\b",
]


def _split_csv(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _safe_preview(text: str, limit: int = 180) -> str:
    cleaned = text.replace("\n", " ").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "..."


class AbuseFilter:
    def __init__(self) -> None:
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in DEFAULT_PATTERNS]

    def _blocklist_terms(self) -> List[str]:
        return [t.lower() for t in (DEFAULT_BLOCKLIST + _split_csv(settings.PROMPT_BLOCKLIST))]

    def check(self, prompt: str | None) -> Dict[str, object]:
        if not settings.PROMPT_FILTER_ENABLED:
            return {"allowed": True, "reason": None, "matches": [], "preview": None}

        if not prompt:
            return {"allowed": True, "reason": None, "matches": [], "preview": None}

        if settings.PROMPT_MAX_CHARS and len(prompt) > settings.PROMPT_MAX_CHARS:
            return {
                "allowed": False,
                "reason": "Prompt too long",
                "matches": [f"length>{settings.PROMPT_MAX_CHARS}"],
                "preview": _safe_preview(prompt)
            }

        lowered = prompt.lower()
        for term in self._blocklist_terms():
            if term and term in lowered:
                return {
                    "allowed": False,
                    "reason": "Prohibited content",
                    "matches": [term],
                    "preview": _safe_preview(prompt)
                }

        for pattern in self._compiled_patterns:
            if pattern.search(prompt):
                return {
                    "allowed": False,
                    "reason": "Prohibited content",
                    "matches": [pattern.pattern],
                    "preview": _safe_preview(prompt)
                }

        return {"allowed": True, "reason": None, "matches": [], "preview": None}


abuse_filter = AbuseFilter()
