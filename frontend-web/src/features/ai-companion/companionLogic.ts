import type { CompanionAction, LearningContext } from './types';

const lessonRoute = (context: LearningContext) => (
  context.activeLessonId ? `/lessons/${context.activeLessonId}` : '/lessons'
);

const quizRoute = (context: LearningContext) => (
  context.activeLessonId ? `/quiz?lessonId=${context.activeLessonId}` : '/quiz'
);

const flashcardRoute = (context: LearningContext) => (
  context.activeLessonId ? `/flashcards?lessonId=${context.activeLessonId}` : '/flashcards'
);

export const buildCompanionMessage = (context: LearningContext): string => {
  if (context.currentPage === 'lessons') {
    return 'ابدأ من ترتيب الكتاب: وحدة → فصل → درس → موضوع.';
  }

  if (context.currentPage === 'lesson_detail') {
    return `أنت الآن في درس ${context.activeLessonTitleAr || 'الكيمياء الحالي'}. يمكنني تلخيص الأهداف أو فتح اختبار قصير.`;
  }

  if (context.currentPage === 'study_plan') {
    return 'سأساعدك في تنظيم خطة الدراسة حسب الدروس ونقاط الضعف.';
  }

  if (context.currentPage === 'book_search') {
    return 'ابحث في الكتاب، وسأساعدك في فهم الصفحات والمواضيع.';
  }

  if (context.currentPage === 'quiz') {
    return 'يمكنني مساعدتك في توليد اختبار من الدروس المحددة.';
  }

  if (context.currentPage === 'flashcards') {
    return 'يمكنني مساعدتك في إنشاء بطاقات مراجعة ذكية.';
  }

  if (context.currentPage === 'ask_ai') {
    return 'اسألني عن أي درس أو مسألة كيميائية.';
  }

  if (context.currentPage === 'lab') {
    return 'جرّب أدوات المختبر لفهم التفاعلات والمعادلات.';
  }

  if (context.currentPage === 'homework') {
    return 'اكتب المسألة أولاً، ثم يمكن تحويل الحل إلى جلسة حل موجهة.';
  }

  if (context.currentPage === 'notifications') {
    return 'ابدأ بالتنبيهات المرتبطة بالامتحان أو درس اليوم.';
  }

  return context.dailyMission?.titleAr
    ? `مهمة اليوم: ${context.dailyMission.titleAr}`
    : 'ابدأ من مهمة اليوم، ثم انتقل إلى الدرس أو التدريب المناسب.';
};

export const buildCompanionSuggestions = (context: LearningContext): CompanionAction[] => {
  if (context.currentPage === 'lessons') {
    return [
      { id: 'book-order', label: 'افتح ترتيب الكتاب', kind: 'book_order', targetRoute: '/lessons' },
      { id: 'explain-lesson', label: 'اشرح هذا الدرس', kind: 'explain_lesson', targetRoute: lessonRoute(context) },
      { id: 'show-topics', label: 'اعرض المواضيع داخل الدرس', kind: 'show_topics', targetRoute: lessonRoute(context) },
      { id: 'quiz-lesson', label: 'اختبرني في هذا الدرس', kind: 'quiz', targetRoute: quizRoute(context) },
    ];
  }

  if (context.currentPage === 'lesson_detail') {
    return [
      { id: 'explain-lesson', label: 'لخص أهداف الدرس', kind: 'explain_lesson', targetRoute: `/ask-ai?question=${encodeURIComponent(`لخص أهداف درس ${context.activeLessonTitleAr || 'الكيمياء'}`)}` },
      { id: 'quiz-lesson', label: 'اختبرني في هذا الدرس', kind: 'quiz', targetRoute: quizRoute(context) },
      { id: 'cards-lesson', label: 'اصنع بطاقات للدرس', kind: 'flashcards', targetRoute: flashcardRoute(context) },
    ];
  }

  if (context.currentPage === 'study_plan') {
    return [
      { id: 'plan-today', label: 'ماذا أدرس اليوم؟', kind: 'plan_today', targetRoute: '/study-plan' },
      { id: 'sort-plan', label: 'رتّب خطتي', kind: 'plan_today', targetRoute: '/study-plan' },
      { id: 'weak-focus', label: 'ركّز على نقاط الضعف', kind: 'weak_topics', targetRoute: '/quiz?mode=weak_lessons' },
      { id: 'exam-review', label: 'جهز مراجعة قبل الامتحان', kind: 'exam_review', targetRoute: '/study-plan' },
    ];
  }

  if (context.currentPage === 'quiz') {
    return [
      { id: 'explain-error', label: 'اشرح خطئي', kind: 'ask_ai', targetRoute: '/ask-ai?question=اشرح لي خطئي في السؤال الأخير' },
      { id: 'similar-question', label: 'أعطني سؤالاً مشابهاً', kind: 'quiz', targetRoute: '/quiz' },
      { id: 'review-topic', label: 'راجع هذا الموضوع', kind: 'flashcards', targetRoute: '/flashcards' },
    ];
  }

  if (context.currentPage === 'flashcards') {
    return [
      { id: 'due-cards', label: 'راجع البطاقات المستحقة', kind: 'flashcards', targetRoute: '/flashcards' },
      { id: 'cards-lesson', label: 'اصنع بطاقات من هذا الدرس', kind: 'flashcards', targetRoute: flashcardRoute(context) },
      { id: 'quick-quiz', label: 'اختبار سريع بعد المراجعة', kind: 'quiz', targetRoute: quizRoute(context) },
    ];
  }

  return [
    { id: 'ask-ai', label: 'اسأل المعلّم', kind: 'ask_ai', targetRoute: '/ask-ai' },
    { id: 'guided-solver', label: 'ابدأ الحل خطوة بخطوة', kind: 'homework_to_solver', targetRoute: '/guided-lab' },
    { id: 'today-plan', label: 'افتح خطة اليوم', kind: 'plan_today', targetRoute: '/study-plan' },
  ];
};
