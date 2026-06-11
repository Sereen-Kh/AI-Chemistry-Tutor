"""Deterministic safety rules for Grade 9 chemistry questions."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.query_router import normalize_query


ACID_TO_WATER_REWRITE = "تحذير أضف الحمض إلى الماء وليس العكس احتياطات السلامة حرارة تطاير غليان"

_ACID_TO_WATER_ANSWER = (
    "نضيف الحمض إلى الماء ببطء لأن امتزاج الحمض بالماء يطلق حرارة كبيرة. "
    "إذا أضفنا الماء إلى الحمض المركز فقد تسخن كمية الماء الصغيرة بسرعة، "
    "مما قد يسبب غلياناً مفاجئاً أو تطاير الحمض. "
    "لذلك القاعدة الآمنة هي: أضف الحمض إلى الماء وليس العكس."
)

_ACID_TO_WATER_TRIGGERS = (
    "نضيف الحمض الي الماء",
    "نضيف الحمض الى الماء",
    "اضف الحمض الي الماء",
    "اضف الحمض الى الماء",
    "اضافه الحمض الي الماء",
    "اضافه الحمض الى الماء",
    "وليس العكس",
    "لماذا نضيف الحمض",
    "الماء الي الحمض",
    "الماء الى الحمض",
    "لا نضيف الماء",
    "نضيف الماء الي الحمض",
    "نضيف الماء الى الحمض",
    "احتياطات",
    "السلامه",
)


@dataclass(frozen=True)
class SafetyRuleAnswer:
    intent: str
    route: str
    answer: str
    confidence: float
    page_numbers: list[int]
    matched_terms: list[str]
    suggested_next_action: str


def is_acid_to_water_safety_question(question: str) -> bool:
    """Return true when the question asks about the acid-to-water safety rule."""
    normalized = normalize_query(question)
    if not ("حمض" in normalized and "ماء" in normalized):
        return False
    return any(trigger in normalized for trigger in _ACID_TO_WATER_TRIGGERS)


def answer_safety_rule(question: str) -> SafetyRuleAnswer | None:
    """Return a deterministic safety answer when the rule is known."""
    normalized = normalize_query(question)
    matched = [trigger for trigger in _ACID_TO_WATER_TRIGGERS if trigger in normalized]
    if not matched or not is_acid_to_water_safety_question(question):
        return None
    return SafetyRuleAnswer(
        intent="safety_question",
        route="safety_rule",
        answer=_ACID_TO_WATER_ANSWER,
        confidence=0.98,
        page_numbers=[7],
        matched_terms=matched,
        suggested_next_action="يمكنك أن تسأل عن احتياطات استعمال الحموض أو طريقة تمديد حمض مركز.",
    )
