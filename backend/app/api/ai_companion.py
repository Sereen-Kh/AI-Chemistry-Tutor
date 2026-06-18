"""Context-aware AI companion placeholder endpoints."""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.ai_companion import CompanionActionResponse, CompanionRequest, CompanionResponse

router = APIRouter(prefix="/ai/companion", tags=["ai-companion"])


def _message(page: str, lesson_title: str | None, unit_title: str | None, scroll_section: str | None) -> str:
    if page == "lessons":
        return f"أنت الآن في {unit_title or 'منهج الكيمياء'}. اتبع ترتيب الكتاب خطوة بخطوة."
    if page == "lesson_detail":
        return f"أنت الآن في درس {lesson_title or 'الكيمياء الحالي'}. يمكنني تلخيصه أو تحويله إلى تدريب."
    if page == "study_plan":
        if scroll_section == "weak":
            return "هذه نقطة ضعف في الخطة. تدريب قصير الآن سيكون مفيداً."
        return "سأساعدك في اختيار درس اليوم وترتيب المراجعة قبل الامتحان."
    if page == "quiz":
        return "بعد كل خطأ يمكنني شرح السبب وإعطاء سؤال مشابه."
    if page == "flashcards":
        return "ابدأ بالبطاقات المستحقة ثم اصنع بطاقات من الدرس الحالي."
    return "ابدأ من مهمة اليوم، وسأقترح الخطوة التعليمية المناسبة."


def _actions(page: str, lesson_id: int | None, lesson_title: str | None) -> list[CompanionActionResponse]:
    if page in {"lessons", "lesson_detail"}:
        return [
            CompanionActionResponse(
                id="explain-lesson",
                label="اشرح هذا الدرس",
                kind="explain_lesson",
                targetRoute=f"/ask-ai?question=اشرح لي درس {lesson_title or 'الكيمياء الحالي'}",
            ),
            CompanionActionResponse(
                id="quiz-lesson",
                label="اختبرني في هذا الدرس",
                kind="quiz",
                targetRoute=f"/quizzes?lessonId={lesson_id}" if lesson_id else "/quizzes",
            ),
            CompanionActionResponse(
                id="cards-lesson",
                label="أنشئ بطاقات مراجعة",
                kind="flashcards",
                targetRoute=f"/flashcards?lessonId={lesson_id}" if lesson_id else "/flashcards",
            ),
        ]
    if page == "study_plan":
        return [
            CompanionActionResponse(id="today-plan", label="ماذا أدرس اليوم؟", kind="plan_today", targetRoute="/study-plan"),
            CompanionActionResponse(id="weak-focus", label="ركّز على نقاط الضعف", kind="weak_topics", targetRoute="/quizzes?mode=weak_lessons"),
        ]
    return [
        CompanionActionResponse(id="ask-ai", label="اسأل المعلّم", kind="ask_ai", targetRoute="/ask-ai"),
        CompanionActionResponse(id="guided", label="ابدأ الحل خطوة بخطوة", kind="homework_to_solver", targetRoute="/guided-lab"),
    ]


@router.post("/suggest", response_model=CompanionResponse)
async def suggest_companion_action(request: CompanionRequest, _user_id: int = Depends(get_current_user_id)):
    context = request.context
    return CompanionResponse(
        message=_message(context.currentPage, context.activeLessonTitleAr, context.activeUnitTitleAr, context.scrollSection),
        suggestedActions=_actions(context.currentPage, context.activeLessonId, context.activeLessonTitleAr),
        responseMode="action",
    )


@router.post("/message", response_model=CompanionResponse)
async def send_companion_message(request: CompanionRequest, _user_id: int = Depends(get_current_user_id)):
    context = request.context
    prefix = f"سأربط سؤالك بسياق {context.activeLessonTitleAr or context.activeUnitTitleAr or 'التعلم الحالي'}."
    return CompanionResponse(
        message=f"{prefix} {_message(context.currentPage, context.activeLessonTitleAr, context.activeUnitTitleAr, context.scrollSection)}",
        suggestedActions=_actions(context.currentPage, context.activeLessonId, context.activeLessonTitleAr),
        responseMode="text",
    )
