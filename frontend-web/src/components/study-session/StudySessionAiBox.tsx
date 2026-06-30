import { useMemo, useState } from 'react';
import { aiApi } from '../../api';
import { Button, Card, StatusPill } from '../DesignSystem';
import type { AiAskResponse, LessonCatalogItem, StudyPlanProgress, StudyPlanScheduledLessonProgress, UserPreferences } from '../../types';

const suggestedQuestions = [
  'اشرح لي الفكرة الأساسية بطريقة بسيطة',
  'ما أهم المصطلحات في هذا الدرس؟',
  'اعطني مثالاً محلولاً من نفس الدرس',
];

export const StudySessionAiBox = ({
  lesson,
  scheduledLesson,
  planProgress,
  preferences,
}: {
  lesson: LessonCatalogItem;
  scheduledLesson?: StudyPlanScheduledLessonProgress;
  planProgress: StudyPlanProgress | null;
  preferences?: UserPreferences;
}) => {
  const [question, setQuestion] = useState(`اشرح لي درس ${lesson.title_ar}`);
  const [answer, setAnswer] = useState<AiAskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const context = useMemo(() => {
    const status = scheduledLesson?.status ? `حالة الدرس في الخطة: ${scheduledLesson.status}.` : '';
    const progress = planProgress
      ? `تقدم خطة الدراسة: ${Math.round(planProgress.completion_percent)}%، الحالة: ${planProgress.track_status}.`
      : '';
    return `سياق الجلسة: الدرس الحالي هو "${lesson.title_ar}". ${status} ${progress}`;
  }, [lesson.title_ar, planProgress, scheduledLesson?.status]);

  const ask = async (value = question) => {
    const trimmed = value.trim();
    if (!trimmed) return;

    setLoading(true);
    setError('');
    try {
      const response = await aiApi.ask({
        question: `${trimmed}\n\n${context}`,
        subject: preferences?.subject || 'chemistry',
        grade: preferences?.grade || '9',
        lesson_id: lesson.id,
        answer_format: preferences?.answerFormat || 'text',
        teaching_style: preferences?.teachingStyle || 'real_life',
        teaching_level: preferences?.teachingLevel || 'standard',
        explanation_method: preferences?.explanationMethod || 'step_by_step',
        learning_modes: preferences?.learningModes || ['text', 'quiz', 'flashcards'],
        student_interests: preferences?.studentInterests || ['daily_life'],
        language: preferences?.language || 'ar',
        answer_scope: 'book_only',
        source_types: ['textbook'],
      });
      setAnswer(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'تعذر الحصول على إجابة الآن.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="session-ai" className="study-session-anchor">
      <Card className="study-session-card">
      <div className="study-section-head">
        <strong>اسأل AI</strong>
        <StatusPill tone="purple">مرتبط بالدرس</StatusPill>
      </div>

      <div className="study-session-ai-prompts">
        {suggestedQuestions.map((item) => (
          <button
            type="button"
            key={item}
            onClick={() => {
              setQuestion(item);
              void ask(item);
            }}
          >
            {item}
          </button>
        ))}
      </div>

      <form
        className="study-session-ai-form"
        onSubmit={(event) => {
          event.preventDefault();
          void ask();
        }}
      >
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          aria-label="اكتب سؤالاً عن الدرس"
        />
        <Button type="submit" disabled={loading}>
          {loading ? 'جار السؤال...' : 'اسأل عن الدرس'}
        </Button>
      </form>

      {error && <div className="study-session-inline-error" role="alert">{error}</div>}

      {answer && (
        <article className="study-session-ai-answer">
          <strong>إجابة المرشد</strong>
          <p>{answer.answer}</p>
          {answer.sources?.length > 0 && (
            <div className="study-session-source-list">
              {answer.sources.slice(0, 3).map((source) => (
                <span key={`${source.chunk_id}-${source.page ?? 'page'}`}>
                  {source.title}{source.page ? ` · صفحة ${source.page}` : ''}
                </span>
              ))}
            </div>
          )}
        </article>
      )}
      </Card>
    </section>
  );
};
