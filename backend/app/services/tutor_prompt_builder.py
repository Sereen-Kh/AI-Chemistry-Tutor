"""Build system-prompt instructions for tutor presentation preferences."""

from __future__ import annotations

from app.models.enums import ExplanationMethod, StudentInterest, TeachingLevel
from app.services.preference_mapping import (
    normalize_explanation_method,
    normalize_student_interests,
    normalize_teaching_level,
)

_INTEREST_LABELS_AR = {
    StudentInterest.FOOTBALL.value: "كرة القدم",
    StudentInterest.CARS.value: "السيارات",
    StudentInterest.COOKING.value: "الطبخ",
    StudentInterest.GAMING.value: "الألعاب",
    StudentInterest.DAILY_LIFE.value: "الحياة اليومية",
    StudentInterest.LABORATORY.value: "المختبر",
    StudentInterest.NATURE.value: "الطبيعة",
}


def build_teaching_instruction(
    teaching_level: str,
    explanation_method: str,
    student_interests: list[str],
) -> str:
    """Return Arabic system instructions for answer style, not source selection.

    The returned text is appended to grounded RAG prompts. It only controls
    presentation after retrieval; it must never override citations or scientific
    correctness from the trusted textbook/solution-book context.
    """
    level = normalize_teaching_level(teaching_level)
    method = normalize_explanation_method(explanation_method)
    interests = normalize_student_interests(student_interests)

    lines = [
        "تعليمات أسلوب الشرح:",
        "- لا تغيّر الحقائق العلمية ولا تستبدل مصادر الكتاب بسبب تفضيلات الطالب.",
        "- إذا كان السياق المسترجع ضعيفاً أو غير كافٍ، قل بوضوح: لم أجد دليلاً كافياً في الكتب المرفوعة للإجابة بدقة.",
    ]

    if level == TeachingLevel.SIMPLE.value:
        lines.extend(
            [
                "- مستوى الشرح: مبسط. استخدم جملاً قصيرة ومفردات سهلة.",
                "- اشرح المصطلحات العلمية قبل استخدامها عندما يكون ذلك مفيداً.",
                "- تجنب التعقيد العلمي غير الضروري.",
            ]
        )
    elif level == TeachingLevel.ACADEMIC.value:
        lines.extend(
            [
                "- مستوى الشرح: أكاديمي. استخدم صياغة علمية رسمية قريبة من لغة الكتاب والامتحان.",
                "- حافظ على الوضوح المناسب لطالب صف تاسع.",
            ]
        )
    else:
        lines.extend(
            [
                "- مستوى الشرح: قياسي. اشرح بمستوى الصف التاسع مع تفاصيل متوازنة.",
                "- استخدم مصطلحات المنهاج عندما تكون مناسبة.",
            ]
        )

    if method == ExplanationMethod.STEP_BY_STEP.value:
        lines.extend(
            [
                "- طريقة الشرح: خطوة بخطوة. قسم الحل إلى خطوات مرقمة.",
                "- في المسائل الحسابية اكتب القانون ثم التعويض ثم النتيجة مع الواحدة.",
            ]
        )
    elif method == ExplanationMethod.HINTS_FIRST.value:
        lines.extend(
            [
                "- طريقة الشرح: تلميحات أولاً. ابدأ بتلميحات موجهة قبل الحل الكامل.",
                "- اسأل سؤالاً إرشادياً واحداً عندما يكون مناسباً.",
                "- لا تكشف الحل النهائي مباشرة إلا إذا كان السؤال يطلب جواباً مباشراً.",
            ]
        )
    elif method == ExplanationMethod.EXAM_MODE.value:
        lines.extend(
            [
                "- طريقة الشرح: نمط امتحاني. اجعل الإجابة موجزة ورسمية ومنظمة مثل جواب نموذجي.",
                "- تجنب التشبيهات والأمثلة الجانبية إلا للضرورة.",
            ]
        )
    elif method == ExplanationMethod.REAL_LIFE_EXAMPLE.value:
        lines.extend(
            [
                "- طريقة الشرح: مثال من الحياة. أجب علمياً أولاً، ثم أضف تشبيهاً واحداً فقط إذا كان مناسباً.",
                "- لا تجعل التشبيه بديلاً عن الإجابة العلمية.",
            ]
        )
        if interests:
            labels = "، ".join(_INTEREST_LABELS_AR.get(item, item) for item in interests)
            lines.append(f"- عند إضافة تشبيه، فضّل اهتمامات الطالب التالية إن كانت مناسبة: {labels}.")
    else:
        lines.append("- طريقة الشرح: مباشر. أجب بوضوح دون مقدمات طويلة.")

    return "\n".join(lines)
