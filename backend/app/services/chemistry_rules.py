"""Deterministic Grade 9 chemistry rules used before generic RAG."""

from __future__ import annotations

from dataclasses import dataclass
import re


_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TATWEEL_RE = re.compile(r"\u0640+")
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

ACTIVITY_SERIES = [
    "K",
    "Ca",
    "Na",
    "Mg",
    "Al",
    "Zn",
    "Fe",
    "Ni",
    "Sn",
    "Pb",
    "H",
    "Cu",
    "Hg",
    "Ag",
    "Pt",
    "Au",
]

_HYDROGEN_INDEX = ACTIVITY_SERIES.index("H")


@dataclass(frozen=True)
class MetalInfo:
    symbol: str
    name_ar: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class AcidInfo:
    key: str
    formula: str
    name_ar: str
    aliases: tuple[str, ...]
    uses_activity_rule: bool = True


@dataclass(frozen=True)
class ReactionRuleResult:
    """A deterministic answer for a recognized textbook-level reaction."""

    intent: str
    answer: str
    confidence: float
    page_numbers: list[int]
    metal_symbol: str
    metal_name_ar: str
    acid_formula: str
    acid_name_ar: str
    equation: str
    reaction_happens: bool
    explanation: str
    warnings: list[str]
    suggested_next_action: str | None = None


METALS = (
    MetalInfo("Cu", "النحاس", ("نحاس", "النحاس", "cu")),
    MetalInfo("Ag", "الفضة", ("فضه", "الفضه", "فضة", "الفضة", "ag")),
    MetalInfo("Au", "الذهب", ("ذهب", "الذهب", "au")),
    MetalInfo("Pt", "البلاتين", ("بلاتين", "البلاتين", "pt")),
    MetalInfo("Zn", "الزنك", ("زنك", "الزنك", "خارصين", "الخارصين", "zn")),
    MetalInfo("Fe", "الحديد", ("حديد", "الحديد", "fe")),
    MetalInfo("Mg", "المغنزيوم", ("مغنزيوم", "المغنزيوم", "مغنيزيوم", "mg")),
    MetalInfo("Al", "الألمنيوم", ("المنيوم", "الالمنيوم", "ألمنيوم", "الألمنيوم", "al")),
    MetalInfo("Na", "الصوديوم", ("صوديوم", "الصوديوم", "na")),
    MetalInfo("K", "البوتاسيوم", ("بوتاسيوم", "البوتاسيوم", "k")),
    MetalInfo("Ca", "الكالسيوم", ("كالسيوم", "الكالسيوم", "ca")),
    MetalInfo("Pb", "الرصاص", ("رصاص", "الرصاص", "pb")),
    MetalInfo("Sn", "القصدير", ("قصدير", "القصدير", "sn")),
)

ACIDS = (
    AcidInfo(
        "h2so4",
        "H2SO4(dilute)",
        "حمض الكبريت الممدد",
        ("حمض الكبريت الممدد", "حمض الكبريت الممدّد", "حمض الكبريت", "h2so4"),
    ),
    AcidInfo(
        "hcl",
        "HCl",
        "حمض كلور الماء",
        ("حمض كلور الماء", "كلور الماء", "حمض الهيدروكلوريك", "hcl"),
    ),
    AcidInfo(
        "hno3",
        "HNO3(dilute)",
        "حمض الآزوت الممدد",
        ("حمض الازوت الممدد", "حمض الآزوت الممدد", "حمض الازوت", "حمض الآزوت", "hno3"),
        uses_activity_rule=False,
    ),
)

_EQUATIONS: dict[tuple[str, str], str] = {
    ("Zn", "hcl"): "Zn + 2HCl → ZnCl2 + H2↑",
    ("Fe", "hcl"): "Fe + 2HCl → FeCl2 + H2↑",
    ("Mg", "hcl"): "Mg + 2HCl → MgCl2 + H2↑",
    ("Al", "hcl"): "2Al + 6HCl → 2AlCl3 + 3H2↑",
    ("Ca", "hcl"): "Ca + 2HCl → CaCl2 + H2↑",
    ("Na", "hcl"): "2Na + 2HCl → 2NaCl + H2↑",
    ("K", "hcl"): "2K + 2HCl → 2KCl + H2↑",
    ("Zn", "h2so4"): "Zn + H2SO4(dilute) → ZnSO4 + H2↑",
    ("Fe", "h2so4"): "Fe + H2SO4(dilute) → FeSO4 + H2↑",
    ("Mg", "h2so4"): "Mg + H2SO4(dilute) → MgSO4 + H2↑",
    ("Al", "h2so4"): "2Al + 3H2SO4(dilute) → Al2(SO4)3 + 3H2↑",
    ("Ca", "h2so4"): "Ca + H2SO4(dilute) → CaSO4 + H2↑",
    ("Na", "h2so4"): "2Na + H2SO4(dilute) → Na2SO4 + H2↑",
    ("K", "h2so4"): "2K + H2SO4(dilute) → K2SO4 + H2↑",
}

_REACTION_TRIGGERS = (
    "معادله",
    "المعادله",
    "تفاعل",
    "يتفاعل",
    "تتفاعل",
    "ناتج",
    "الناتج",
    "ينتج",
    "مع حمض",
    "ازاحه",
    "احلال",
)


def normalize_chemistry_text(text: str) -> str:
    """Normalize Arabic text and formula notation for deterministic matching."""
    normalized = text.lower().translate(_SUBSCRIPT_TRANSLATION).translate(_ARABIC_DIGITS_TRANSLATION)
    normalized = _DIACRITICS_RE.sub("", normalized)
    normalized = _TATWEEL_RE.sub("", normalized)
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ؤ": "و",
        "ئ": "ي",
        "ى": "ي",
        "ة": "ه",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _contains_alias(normalized_query: str, aliases: tuple[str, ...]) -> bool:
    return any(normalize_chemistry_text(alias) in normalized_query for alias in aliases)


def detect_metal_and_acid(query: str) -> tuple[MetalInfo | None, AcidInfo | None]:
    """Return recognized metal and acid reactants, if both are present."""
    normalized = normalize_chemistry_text(query)
    metal = next((item for item in METALS if _contains_alias(normalized, item.aliases)), None)
    acid = next((item for item in ACIDS if _contains_alias(normalized, item.aliases)), None)
    return metal, acid


def is_reaction_query(query: str) -> bool:
    normalized = normalize_chemistry_text(query)
    return any(trigger in normalized for trigger in _REACTION_TRIGGERS)


def _is_above_hydrogen(symbol: str) -> bool:
    if symbol not in ACTIVITY_SERIES:
        return False
    return ACTIVITY_SERIES.index(symbol) < _HYDROGEN_INDEX


def answer_metal_dilute_acid_reaction(query: str) -> ReactionRuleResult | None:
    """Answer metal + dilute acid reactions using the activity series rule."""
    if not is_reaction_query(query):
        return None

    metal, acid = detect_metal_and_acid(query)
    if metal is None or acid is None:
        return None

    if not acid.uses_activity_rule:
        equation = f"{metal.symbol} + {acid.formula} → يحتاج إلى تحقق من نص الكتاب"
        explanation = (
            "حمض الآزوت حمض مؤكسد، لذلك لا أعطي حكماً آلياً بقاعدة إزاحة الهيدروجين وحدها."
        )
        return ReactionRuleResult(
            intent="clarification",
            answer=(
                f"{equation}\n\n"
                f"{explanation}\n"
                "أحتاج صفحة الدرس أو نص السؤال الكامل لأعطي المعادلة المدرسية المطلوبة بدقة."
            ),
            confidence=0.72,
            page_numbers=[],
            metal_symbol=metal.symbol,
            metal_name_ar=metal.name_ar,
            acid_formula=acid.formula,
            acid_name_ar=acid.name_ar,
            equation=equation,
            reaction_happens=False,
            explanation=explanation,
            warnings=["حمض الآزوت لا يعالج بقاعدة الحموض الممددة البسيطة وحدها."],
            suggested_next_action="أرسل صفحة السؤال أو اسأل عن حمض كلور الماء/حمض الكبريت الممدد.",
        )

    happens = _is_above_hydrogen(metal.symbol)
    if happens:
        equation = _EQUATIONS.get((metal.symbol, acid.key), f"{metal.symbol} + {acid.formula} → ملح + H2↑")
        explanation = (
            f"{metal.name_ar} أعلى من الهيدروجين في سلسلة النشاط الكيميائي، "
            "لذلك يزيح الهيدروجين من الحمض الممدد ويتحرر غاز H2."
        )
        answer = (
            f"{equation}\n\n"
            f"يحدث تفاعل بين {metal.name_ar} و{acid.name_ar}.\n"
            f"السبب: {explanation}"
        )
    else:
        equation = f"{metal.symbol} + {acid.formula} → لا يحدث تفاعل"
        explanation = (
            f"{metal.name_ar} أقل نشاطاً من الهيدروجين في سلسلة النشاط الكيميائي، "
            "لذلك لا يستطيع إزاحة الهيدروجين من الحموض الممددة."
        )
        answer = (
            f"{equation}\n\n"
            f"لا يحدث تفاعل بين {metal.name_ar} و{acid.name_ar}.\n"
            f"السبب: {explanation}"
        )

    warnings = [
        "هذه القاعدة تخص الحموض الممددة في مستوى الصف التاسع؛ الحموض المركزة قد تعطي سلوكاً مختلفاً."
    ]
    return ReactionRuleResult(
        intent="reaction_query",
        answer=f"{answer}\n\nملاحظة: {warnings[0]}",
        confidence=0.93,
        page_numbers=[32, 34],
        metal_symbol=metal.symbol,
        metal_name_ar=metal.name_ar,
        acid_formula=acid.formula,
        acid_name_ar=acid.name_ar,
        equation=equation,
        reaction_happens=happens,
        explanation=explanation,
        warnings=warnings,
        suggested_next_action="يمكنك أن تسأل عن سلسلة النشاط الكيميائي أو عن تفاعل معدن آخر مع حمض ممدد.",
    )
