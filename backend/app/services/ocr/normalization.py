"""Light Arabic and chemistry formula normalization for OCR post-processing.

These helpers are used during solution book ingestion to produce consistent
search fields without altering the original Arabic display text.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Subscript / superscript unicode → ASCII digit translation
# ---------------------------------------------------------------------------
_SUBSCRIPT_TABLE = str.maketrans(
    {
        "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
        "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    }
)
_SUPERSCRIPT_TABLE = str.maketrans(
    {
        "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
        "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
        "⁺": "+", "⁻": "-",
    }
)

# Arabic diacritics (tashkeel) and tatweel (kashida)
_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TATWEEL_RE = re.compile(r"\u0640+")

# Arabic letter normalization map: alef variants → bare alef, teh marbuta →
# heh, alef maqsura → yeh
_ARABIC_NORMALIZATION = str.maketrans(
    {
        "\u0623": "\u0627",  # أ → ا
        "\u0625": "\u0627",  # إ → ا
        "\u0622": "\u0627",  # آ → ا
        "\u0671": "\u0627",  # ٱ → ا
        "\u0624": "\u0648",  # ؤ → و
        "\u0626": "\u064A",  # ئ → ي
        "\u0649": "\u064A",  # ى → ي
        "\u0629": "\u0647",  # ة → ه  (optional, enable for search normalisation)
    }
)


def normalize_formula(text: str) -> str:
    """Convert unicode subscripts/superscripts and common ion notation to ASCII.

    Examples::

        >>> normalize_formula("H₂O")
        'H2O'
        >>> normalize_formula("OH⁻")
        'OH-'
        >>> normalize_formula("Ca(OH)₂")
        'Ca(OH)2'
        >>> normalize_formula("C₁ × V₁ = C₂ × V₂")
        'C1 × V1 = C2 × V2'
    """
    text = text.translate(_SUBSCRIPT_TABLE)
    text = text.translate(_SUPERSCRIPT_TABLE)
    return text


def normalize_arabic_for_search(text: str) -> str:
    """Return a search-normalized copy of *text*.

    Strips tashkeel, tatweel, and normalises alef/alef-maqsura/teh-marbuta.
    The original Arabic display text is **not** modified — only use this
    result for indexing / matching.

    Examples::

        >>> normalize_arabic_for_search("الهيدروجيِن")
        'الهيدروجين'
        >>> normalize_arabic_for_search("أكسجين")
        'اكسجين'
    """
    text = _DIACRITICS_RE.sub("", text)
    text = _TATWEEL_RE.sub("", text)
    text = text.translate(_ARABIC_NORMALIZATION)
    return text


def normalize_text(text: str) -> str:
    """Apply both formula and Arabic normalization.

    Use for building ``normalized_content`` search fields on
    solution book chunks.
    """
    return normalize_arabic_for_search(normalize_formula(text))
