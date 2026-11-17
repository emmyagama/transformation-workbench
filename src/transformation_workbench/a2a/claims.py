"""Deterministic guard against unsupported financial and implementation claims."""

from __future__ import annotations

import re
from collections.abc import Iterable

UNVALIDATED_HYPOTHESIS_PATTERN = re.compile(
    r"\b(?:hypothesis|hypothetical|unvalidated|unverified|"
    r"not\s+validated|not\s+measured|proposed\s+target|target\s+only)\b",
    re.IGNORECASE,
)

UNSUPPORTED_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("currency amount", re.compile(r"\$\s*\d", re.IGNORECASE)),
    ("currency amount", re.compile(r"\b(?:usd|dollars?|euros?)\b", re.IGNORECASE)),
    (
        "savings claim",
        re.compile(r"\b(?:save|saves|saved|saving|savings)\b", re.IGNORECASE),
    ),
    ("ROI claim", re.compile(r"\bROI\b", re.IGNORECASE)),
    (
        "ROI claim",
        re.compile(r"\breturn on investment\b", re.IGNORECASE),
    ),
    (
        "cost reduction claim",
        re.compile(
            r"\b(?:cost|costs)\s+(?:reduction|savings?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "cost reduction claim",
        re.compile(
            r"\breduce\s+(?:costs?|spend|headcount|fte|revenue|profit|effort)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "financial impact claim",
        re.compile(r"\b(?:revenue|profit|margin)\b", re.IGNORECASE),
    ),
    (
        "productivity claim",
        re.compile(
            r"\bproductivity\s+(?:gain|increase|improvement)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "efficiency claim",
        re.compile(
            r"\befficiency\s+(?:gain|increase|improvement)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "guarantee claim",
        re.compile(r"\bguarantee(?:d|s)?\b", re.IGNORECASE),
    ),
    (
        "implementation claim",
        re.compile(
            r"\b(?:we\s+(?:have\s+)?implemented|has\s+been\s+implemented|"
            r"fully\s+implemented|already\s+implemented|production[- ]ready)\b",
            re.IGNORECASE,
        ),
    ),
)

IMPACT_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "percentage impact claim",
        re.compile(
            r"\b(?:reduce|reduces|reduced|reduction|cut|cuts|lower|lowers|"
            r"decrease|decreases|increase|increases|improve|improves|raise|"
            r"raises|accelerate|accelerates|save|saves)\b[^.\n]{0,80}?"
            r"\b\d+(?:\.\d+)?\s*%",
            re.IGNORECASE,
        ),
    ),
    (
        "percentage impact claim",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*%\s*(?:reduction|decrease|increase|"
            r"improvement|faster|fewer|more|less|slower)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "impact claim",
        re.compile(
            r"\b(?:halve|halves|halved|double|doubles|doubled|triple|"
            r"triples|tripled)\b[^.\n]{0,60}?\b(?:cycle\s+time|backlog|"
            r"rework|throughput|productivity|effort|cost|volume|sla|"
            r"service\s+level)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "impact claim",
        re.compile(
            r"\b(?:cut|reduce|reduces|reduced)\b[^.\n]{0,40}?\bin\s+half\b",
            re.IGNORECASE,
        ),
    ),
    (
        "percentage impact claim",
        re.compile(
            r"\b(?:achieve|achieves|achieved|reach|reaches|reached|deliver|"
            r"delivers|delivered)\b[^.\n]{0,50}?\b\d+(?:\.\d+)?\s*%",
            re.IGNORECASE,
        ),
    ),
    (
        "impact claim",
        re.compile(
            r"\b(?:reduce|reduces|reduced|cut|cuts|lower|lowers|decrease|"
            r"decreases|increase|increases|improve|improves|accelerate|"
            r"accelerates)\b[^.\n]{0,60}?\b(?:cycle\s+time|backlog|rework|"
            r"throughput|productivity|effort|sla|service\s+level)\b",
            re.IGNORECASE,
        ),
    ),
)


class UnsupportedClaimError(ValueError):
    """Raised when generated text makes an unsupported claim."""

    def __init__(self, field: str, claim: str) -> None:
        super().__init__(f"Unsupported claim in {field}: {claim}.")
        self.field = field
        self.claim = claim


def assert_supported_text(text: str, field: str) -> None:
    """Reject a single text field that contains an unsupported claim."""
    for claim, pattern in UNSUPPORTED_CLAIM_PATTERNS:
        if pattern.search(text):
            raise UnsupportedClaimError(field, claim)
    for claim, pattern in IMPACT_CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            sentence = _sentence_around(text, match.start())
            if not UNVALIDATED_HYPOTHESIS_PATTERN.search(sentence):
                raise UnsupportedClaimError(field, claim)


def _sentence_around(text: str, index: int) -> str:
    start = max(
        text.rfind(".", 0, index),
        text.rfind("\n", 0, index),
        text.rfind(";", 0, index),
    ) + 1
    endings = [
        position
        for position in (
            text.find(".", index),
            text.find("\n", index),
            text.find(";", index),
        )
        if position != -1
    ]
    end = min(endings) if endings else len(text)
    return text[start:end]


def assert_supported_chunks(chunks: Iterable[str], field: str) -> None:
    """Reject the first chunk that contains an unsupported claim."""
    for chunk in chunks:
        assert_supported_text(chunk, field)
