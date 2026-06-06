"""Arabic and chemistry notation normalization used before RAG routing."""

from __future__ import annotations

import re

_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TATWEEL_RE = re.compile(r"\u0640+")
_PUNCTUATION_RE = re.compile(r"[؟?!.،,؛;:()\[\]{}\"'`]+")
_SPACE_RE = re.compile(r"\s+")

_SUBSCRIPT_TRANSLATION = str.maketrans(
    {
        "₀": "0",
        "₁": "1",
        "₂": "2",
        "₃": "3",
        "₄": "4",
        "₅": "5",
        "₆": "6",
        "₇": "7",
        "₈": "8",
        "₉": "9",
    }
)

_SUPERSCRIPT_TRANSLATION = str.maketrans(
    {
        "⁰": "0",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
        "⁺": "+",
        "⁻": "-",
    }
)

_ARABIC_DIGITS_TRANSLATION = str.maketrans(
    {
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)

_ARABIC_LETTER_TRANSLATION = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
        "ة": "ه",
    }
)


def normalize_arabic(text: str | None) -> str:
    """Return normalized Arabic text with chemistry subscripts/superscripts flattened."""
    if not text:
        return ""

    normalized = text.translate(_SUBSCRIPT_TRANSLATION)
    normalized = normalized.translate(_SUPERSCRIPT_TRANSLATION)
    normalized = normalized.translate(_ARABIC_DIGITS_TRANSLATION)
    normalized = normalized.translate(_ARABIC_LETTER_TRANSLATION)
    normalized = _DIACRITICS_RE.sub("", normalized)
    normalized = _TATWEEL_RE.sub("", normalized)
    normalized = _PUNCTUATION_RE.sub(" ", normalized)
    normalized = _SPACE_RE.sub(" ", normalized)
    return normalized.strip()

