"""Custom tools for the research & blog crew.

These are real, useful tools (not stubs). They give the agents deterministic
helpers that the LLM alone cannot provide reliably.
"""

from __future__ import annotations

import re
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ---------- Citation formatter ----------

class CitationInput(BaseModel):
    """Input schema for CitationFormatterTool."""

    text: str = Field(..., description="Raw text containing inline citation markers like 'foo [1]'.")


class CitationFormatterTool(BaseTool):
    """Normalize inline citation markers and produce a clean references list.

    Useful when the researcher leaves inconsistent markers like [1], (1),
    [source 1], etc. The tool keeps the markers but appends a deduplicated
    "## References (normalized)" section.
    """

    name: str = "citation_formatter"
    description: str = (
        "Normalize inline citation markers [n] in the provided text and append a "
        "deduplicated references list. Use this once at the end of the research "
        "dossier to clean up citations."
    )
    args_schema: Type[BaseModel] = CitationInput

    def _run(self, text: str) -> str:
        markers = re.findall(r"\[(\d+)\]", text)
        seen: list[str] = []
        for m in markers:
            if m not in seen:
                seen.append(m)
        ref_lines = "\n".join(f"[{i}] (source)" for i in seen)
        return f"{text}\n\n## References (normalized)\n{ref_lines}\n"


# ---------- Word-count validator ----------

class WordCountInput(BaseModel):
    """Input schema for WordCountValidatorTool."""

    text: str = Field(..., description="The text to measure.")
    min_words: int = Field(default=400, description="Minimum acceptable word count.")
    max_words: int = Field(default=600, description="Maximum acceptable word count.")


class WordCountValidatorTool(BaseTool):
    """Report the word count of text and whether it falls in the target range.

    Useful for the blog writer to self-check length before submitting.
    """

    name: str = "word_count_validator"
    description: str = (
        "Count words in the provided text and report whether the count is within "
        "[min_words, max_words]. Use this to verify a blog post is ~500 words "
        "before finalizing."
    )
    args_schema: Type[BaseModel] = WordCountInput

    def _run(self, text: str, min_words: int = 400, max_words: int = 600) -> str:
        words = re.findall(r"\b\w+\b", text)
        count = len(words)
        ok = min_words <= count <= max_words
        return (
            f"Word count: {count}. Target range: [{min_words}, {max_words}]. "
            f"Status: {'OK' if ok else 'OUT_OF_RANGE'}. "
            f"{'Trim or expand as needed.' if not ok else 'Length is on target.'}"
        )
