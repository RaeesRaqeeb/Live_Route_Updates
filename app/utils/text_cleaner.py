# app/utils/text_cleaner.py
import re
from typing import Optional


class TextCleaner:
    """
    Cleans raw scraped markdown text before sending to LLM.
    Removes noise, ads, navigation leftovers, excessive whitespace.
    """

    # Patterns to remove from Pakistani news sites
    NOISE_PATTERNS = [
        r"Subscribe to.*?newsletter",
        r"Follow us on.*?$",
        r"Copyright \d{4}.*?$",
        r"All rights reserved.*?$",
        r"Advertisement",
        r"\[.*?cookie.*?\]",
        r"Click here to.*?$",
        r"Read more:.*?$",
        r"Also read:.*?$",
        r"Related:.*?$",
        r"Share this.*?$",
        r"Comments \(\d+\)",
        r"Loading\.\.\.",
        r"Please wait\.\.\.",
        r"http[s]?://\S+",           # Remove bare URLs
        r"!\[.*?\]\(.*?\)",          # Remove markdown images
        r"\[([^\]]+)\]\([^\)]+\)",   # Replace [text](url) with just text
    ]

    def clean(self, text: Optional[str]) -> str:
        """Apply all cleaning steps to scraped text."""
        if not text:
            return ""

        # ── Apply noise patterns ──────────────────────────────────────────────
        for pattern in self.NOISE_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

        # ── Normalize whitespace ──────────────────────────────────────────────
        text = re.sub(r"\n{3,}", "\n\n", text)     # Max 2 consecutive newlines
        text = re.sub(r" {2,}", " ", text)          # Max 1 consecutive space
        text = re.sub(r"\t+", " ", text)            # Replace tabs with space

        # ── Remove very short lines (likely nav remnants) ─────────────────────
        lines = text.split("\n")
        meaningful_lines = [
            line.strip()
            for line in lines
            if len(line.strip()) > 15   # Keep lines with real content
        ]
        text = "\n".join(meaningful_lines)

        return text.strip()

    def truncate_for_llm(self, text: str, max_chars: int = 3000) -> str:
        """Truncate text to fit within LLM context window."""
        if len(text) <= max_chars:
            return text
        # Try to cut at a sentence boundary
        truncated = text[:max_chars]
        last_period = truncated.rfind(".")
        if last_period > max_chars * 0.8:
            return truncated[:last_period + 1]
        return truncated + "..."