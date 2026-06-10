"""Final answer verification for high-risk short chemistry facts."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.arabic_normalizer import normalize_arabic


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    reason: str | None = None

    def as_dict(self) -> dict:
        return {"passed": self.passed, "reason": self.reason}


def verify_answer(question: str, answer: str) -> VerificationResult:
    q = normalize_arabic(question).lower()
    a = normalize_arabic(answer).lower()

    if "اكسيد الكالسيوم" in q or "cao" in q:
        ok = all(term in a for term in ("cao", "h2o", "ca oh 2")) or ("cao" in a and "h2o" in a and "ca(oh)2" in answer.lower())
        return VerificationResult(ok, None if ok else "CaO + water answer must include CaO, H2O, and Ca(OH)2")
    if "رمز" in q and ("الماء" in q or "h2o" in q):
        return VerificationResult("h2o" in a, None if "h2o" in a else "water formula answer must contain H2O")
    if ("ما هو" in q or "ماهي" in q or "ما هي" in q) and ("الماء" in q or "h2o" in q):
        ok = "h2o" in a and ("ذرتي هيدروجين" in a or "ذرتي هدروجين" in a) and "ذره اكسجين" in a
        return VerificationResult(ok, None if ok else "water definition must include H2O and composition")
    if "الحموض" in q or "الاحماض" in q:
        ok = ("h+" in a or "ايونات الهدروجين" in a or "ايونات الهيدروجين" in a)
        return VerificationResult(ok, None if ok else "acid answer must mention H+ or hydrogen ions")
    if "الاسس" in q or "القواعد" in q:
        ok = ("oh-" in a or "ايونات الهدروكسيد" in a)
        return VerificationResult(ok, None if ok else "base answer must mention OH- or hydroxide ions")
    if "عباد الشمس" in q and any(term in q for term in ("حمضي", "حمض", "الحموض")):
        return VerificationResult("الاحمر" in a, None if "الاحمر" in a else "acidic litmus answer must mention red")
    if "عباد الشمس" in q and any(term in q for term in ("اساسي", "الاسس", "قاعد")):
        return VerificationResult("الازرق" in a, None if "الازرق" in a else "basic litmus answer must mention blue")
    # Safety: acid-to-water question must mention heat/splashing/boiling/safety
    if ("نضيف الحمض" in q or "اضف الحمض" in q or "الماء الى الحمض" in q or "وليس العكس" in q) and "حمض" in q and "ماء" in q:
        ok = any(term in a for term in ("حراره", "تطاير", "غليان", "سلامه"))
        return VerificationResult(ok, None if ok else "safety answer must mention heat, splashing, boiling, or safety")
    # Math: HCl concentration exercise answer must contain computed values
    if "hcl" in q and "تركيز" in q and any(term in q for term in ("احسب", "حل", "مساله", "تمرين", "اوجد")):
        ok = "g/l" in a and "mol/l" in a and "cm" in a
        return VerificationResult(ok, None if ok else "concentration exercise answer must contain g/L, mol/L, and Cm")
    # Molar concentration definition
    if "تركيز" in q and ("مولي" in q or "موليه" in q) and any(term in q for term in ("ما هو", "ماهو", "ماهي", "ما هي", "تعريف", "عرف")):
        ok = ("c = n / v" in a or "c=n/v" in a or "c = n/v" in a) and "mol/l" in a
        return VerificationResult(ok, None if ok else "molar concentration definition must contain C = n / V and mol/L")
    # Copper + dilute acid → no reaction
    if ("نحاس" in q or "cu" in q) and "حمض" in q and any(term in q for term in ("تفاعل", "يتفاعل", "تتفاعل")):
        ok = "لا يحدث تفاعل" in a or "لا تفاعل" in a
        return VerificationResult(ok, None if ok else "copper + dilute acid answer must state no reaction")
    return VerificationResult(True)
