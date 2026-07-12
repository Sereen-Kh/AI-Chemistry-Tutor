import { useState } from 'react';
import { Link } from 'react-router-dom';
import { flashcardsApi } from '../../api';
import { Button, Card, StatusPill } from '../DesignSystem';
import type { GeneratedFlashcard, LessonCatalogItem } from '../../types';

const generationErrorMessage = (error: unknown): string => {
  const maybeResponse = error as { response?: { status?: number; data?: { detail?: unknown } }; message?: string };
  const detail = maybeResponse.response?.data?.detail;
  const text = typeof detail === 'string'
    ? detail
    : detail && typeof detail === 'object' && !Array.isArray(detail)
      ? Object.values(detail as Record<string, unknown>).filter(Boolean).map(String).join(' ')
      : maybeResponse.message || '';
  if (maybeResponse.response?.status === 401 || /unauthorized|forbidden|token/i.test(text)) {
    return 'يجب تسجيل الدخول لإنشاء بطاقات.';
  }
  if (/ADMIN_APPROVAL_REQUIRED_FOR_NEEDS_REVIEW_FLASHCARDS|needs_review|blocked|غير جاهز|محظور/i.test(text)) {
    return 'هذا الدرس غير جاهز لتوليد البطاقات بعد.';
  }
  if (/INSUFFICIENT_CONTENT_FOR_FLASHCARDS|missing_ready_content|لا يوجد محتوى/i.test(text)) {
    return 'لا يوجد محتوى كافٍ لهذا الدرس.';
  }
  return 'تعذر توليد البطاقات من الخادم حالياً.';
};

export const StudySessionFlashcardsCard = ({ lesson }: { lesson: LessonCatalogItem }) => {
  const [cards, setCards] = useState<GeneratedFlashcard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    setLoading(true);
    setError('');
    try {
      const generated = await flashcardsApi.generateFlashcards({
        mode: 'single_lesson',
        lessonIds: [lesson.id],
        cardsPerLesson: 4,
        cardTypes: ['term', 'definition', 'formula', 'common_mistake'],
        difficulty: 'mixed',
        includeSourcePage: true,
        spacedRepetitionEnabled: true,
      });
      setCards(generated.slice(0, 4));
    } catch (err) {
      setError(generationErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="session-flashcards" className="study-session-anchor">
      <Card className="study-session-card">
      <div className="study-section-head">
        <strong>راجع بالبطاقات</strong>
        <StatusPill tone="teal">استرجاع سريع</StatusPill>
      </div>

      <p className="study-session-muted">
        حوّل أهم مفاهيم الدرس إلى بطاقات قصيرة قبل ضغط زر إكمال الدرس.
      </p>

      <div className="study-session-actions-row">
        <Button onClick={() => void generate()} disabled={loading}>
          {loading ? 'جار التوليد...' : 'ولّد بطاقات مراجعة'}
        </Button>
        <Link
          to={`/flashcards?auto=true&mode=single_lesson&lessonId=${lesson.id}&cards=6&difficulty=mixed`}
          className="ed-btn ed-btn-secondary"
        >
          افتح صفحة البطاقات
        </Link>
      </div>

      {error && <div className="study-session-inline-error" role="alert">{error}</div>}

      {cards.length > 0 && (
        <div className="study-session-flashcard-preview">
          {cards.map((card) => (
            <article key={card.id}>
              <strong>{card.front}</strong>
              <p>{card.back}</p>
            </article>
          ))}
        </div>
      )}
      </Card>
    </section>
  );
};
