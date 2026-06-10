"""Small deterministic intent classifier for Grade 9 chemistry questions."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.arabic_normalizer import normalize_arabic


@dataclass(frozen=True)
class ClassifiedIntent:
    intent: str
    entity: str | None = None
    property: str | None = None
    confidence: float = 0.75
    route: str = "rag"


_FOLLOWUP_TRIGGERS = (
    "اشرح بطريقه ابسط",
    "اشرح بطريقه اخري",
    "اشرح ببساطه",
    "لم افهم",
    "try differently",
    "explain this differently",
    "simpler example",
    "rephrase",
)

_FORMULA_TRIGGERS = ("رمز", "الصيغه", "صيغه", "formula")
_EQUATION_TRIGGERS = ("معادله", "وازن", "اكتب المعادله")
_REACTION_TRIGGERS = ("يتفاعل", "تفاعل", "تتفاعل", "مع حمض", "الناتج", "ناتج")
_LESSON_TRIGGERS = ("درس", "الدرس", "ماذا يحتوي")
_EXERCISE_TRIGGERS = ("حل", "مساله", "تمرين", "سوال", "السوال", "اختر")
_SAFETY_TRIGGERS = (
    "نضيف الحمض الى الماء",
    "اضف الحمض الى الماء",
    "وليس العكس",
    "لماذا نضيف الحمض",
    "الماء الى الحمض",
    "احتياطات",
    "السلامه",
)

_ENTITY_ALIASES = {
    "الماء": ("الماء", "ماء", "h2o"),
    "الحموض": ("الحموض", "الاحماض", "حمض", "h+"),
    "الأسس": ("الاسس", "القواعد", "قاعده", "oh-"),
    "حمض الكبريت": ("حمض الكبريت", "h2so4"),
    "حمض كلور الماء": ("حمض كلور الماء", "حمض الهيدروكلوريك", "hcl"),
    "هيدروكسيد الصوديوم": ("هيدروكسيد الصوديوم", "naoh"),
    "كلوريد الصوديوم": ("كلوريد الصوديوم", "ملح الطعام", "nacl"),
    "أكسيد الكالسيوم": ("اكسيد الكالسيوم", "cao"),
    "النحاس": ("النحاس", "نحاس", "cu"),
}


def detect_entity(question: str) -> str | None:
    normalized = normalize_arabic(question).lower()
    for entity, aliases in _ENTITY_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return entity
    return None


def classify_intent(question: str, action: str | None = None) -> ClassifiedIntent:
    normalized = normalize_arabic(question).lower()
    entity = detect_entity(question)
    action_value = (action or "").strip().lower()

    if action_value in {"rephrase_previous", "try_differently", "simplify_previous"} or any(
        trigger in normalized for trigger in _FOLLOWUP_TRIGGERS
    ):
        return ClassifiedIntent("followup_rephrase", entity=entity, confidence=0.98, route="followup_rephrase")

    if "حمض" in normalized and "ماء" in normalized and any(trigger in normalized for trigger in _SAFETY_TRIGGERS):
        return ClassifiedIntent("safety_question", entity="السلامة المخبرية", confidence=0.98, route="safety_rule")

    if "عباد الشمس" in normalized or ("لون" in normalized and any(term in normalized for term in ("حمضي", "اساسي", "قاعد"))):
        property_name = "litmus_color"
        if any(term in normalized for term in ("حمضي", "حمض", "الحموض", "الاحماض")):
            entity = "المحاليل الحمضية"
        elif any(term in normalized for term in ("اساسي", "الاسس", "قاعد")):
            entity = "المحاليل الأساسية"
        return ClassifiedIntent("property_lookup", entity=entity, property=property_name, confidence=0.95, route="dictionary_first")

    if any(trigger in normalized for trigger in _FORMULA_TRIGGERS):
        return ClassifiedIntent("formula_lookup", entity=entity, confidence=0.92, route="dictionary_first")

    if any(trigger in normalized for trigger in _REACTION_TRIGGERS):
        return ClassifiedIntent("reaction_lookup", entity=entity, confidence=0.88, route="chemistry_rule")

    if any(trigger in normalized for trigger in _EQUATION_TRIGGERS):
        return ClassifiedIntent("equation_lookup", entity=entity, confidence=0.88, route="dictionary_first")

    if any(trigger in normalized for trigger in _LESSON_TRIGGERS):
        return ClassifiedIntent("lesson_navigation", entity=entity, confidence=0.8, route="dictionary_first")

    if any(trigger in normalized for trigger in _EXERCISE_TRIGGERS):
        route = "math_solver" if "hcl" in normalized and "تركيز" in normalized else "rag"
        return ClassifiedIntent("exercise_solving", entity=entity, confidence=0.78, route=route)

    if any(trigger in normalized for trigger in ("ما هو", "ما هي", "ماهو", "ماهي", "عرف", "تعريف")):
        return ClassifiedIntent("definition_lookup", entity=entity, confidence=0.9, route="dictionary_first")

    return ClassifiedIntent("general_explanation", entity=entity, confidence=0.65)
