"""Deterministic chemistry rules that should run before broad RAG."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.arabic_normalizer import normalize_arabic

ACTIVITY_SERIES = ["K", "Ba", "Ca", "Na", "Mg", "Al", "Mn", "Zn", "Fe", "Pb", "H", "Cu", "Ag", "Hg", "Au"]
_HYDROGEN_INDEX = ACTIVITY_SERIES.index("H")


@dataclass(frozen=True)
class ChemistryRuleAnswer:
    rule_id: str
    answer: str
    confidence: float
    page_numbers: list[int]
    equation: str | None = None


_METALS = {
    "النحاس": ("Cu", ("النحاس", "نحاس", "cu")),
    "الزنك": ("Zn", ("الزنك", "زنك", "خارصين", "الخارصين", "zn")),
    "الحديد": ("Fe", ("الحديد", "حديد", "fe")),
    "المغنزيوم": ("Mg", ("المغنزيوم", "مغنزيوم", "مغنيزيوم", "mg")),
    "الألمنيوم": ("Al", ("الالمنيوم", "المنيوم", "ألمنيوم", "الألمنيوم", "al")),
}


def answer_litmus_color(question: str) -> ChemistryRuleAnswer | None:
    normalized = normalize_arabic(question).lower()
    if "عباد الشمس" not in normalized:
        return None
    if any(term in normalized for term in ("حمضي", "حمض", "الحموض", "الاحماض")):
        return ChemistryRuleAnswer(
            rule_id="litmus_color",
            answer="تتلون ورقة عباد الشمس باللون الأحمر في المحاليل الحمضية.",
            confidence=0.95,
            page_numbers=[13],
        )
    if any(term in normalized for term in ("اساسي", "الاسس", "قاعد", "قلوي")):
        return ChemistryRuleAnswer(
            rule_id="litmus_color",
            answer="تتلون ورقة عباد الشمس باللون الأزرق في المحاليل الأساسية.",
            confidence=0.95,
            page_numbers=[23],
        )
    return None


def answer_metal_dilute_acid(question: str) -> ChemistryRuleAnswer | None:
    normalized = normalize_arabic(question).lower()
    if not any(term in normalized for term in ("تفاعل", "يتفاعل", "تتفاعل", "مع حمض", "معادله")):
        return None
    if any(term in normalized for term in ("مركز", "المركز", "ساخن", "الحار")):
        return None
    if not any(term in normalized for term in ("ممدد", "مخفف", "حمض الكبريت", "h2so4", "hcl")):
        return None

    metal_name = None
    metal_symbol = None
    for name, (symbol, aliases) in _METALS.items():
        if any(normalize_arabic(alias).lower() in normalized for alias in aliases):
            metal_name = name
            metal_symbol = symbol
            break
    if metal_name is None or metal_symbol is None:
        return None

    if ACTIVITY_SERIES.index(metal_symbol) > _HYDROGEN_INDEX:
        acid_name = "حمض الكبريت الممدد" if "كبريت" in normalized or "h2so4" in normalized else "الحمض الممدد"
        equation = f"{metal_symbol} + H₂SO₄ المخفف → لا تفاعل" if metal_symbol == "Cu" else f"{metal_symbol} + حمض ممدد → لا تفاعل"
        return ChemistryRuleAnswer(
            rule_id="metal_dilute_acid",
            answer=(
                f"لا يحدث تفاعل بين {metal_name} و{acid_name} في الظروف العادية، "
                f"لأن {metal_name} أقل نشاطاً من الهيدروجين ولا يستطيع إزاحته من الحمض.\n"
                f"{equation}"
            ),
            confidence=0.93,
            page_numbers=[32, 34],
            equation=equation,
        )
    return None

