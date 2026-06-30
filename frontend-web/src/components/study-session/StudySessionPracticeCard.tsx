import { useState } from 'react';
import { Link } from 'react-router-dom';
import { quizzesApi } from '../../api';
import { Button, Card, StatusPill } from '../DesignSystem';
import type { GeneratedQuizQuestion, LessonCatalogItem } from '../../types';

export const StudySessionPracticeCard = ({ lesson }: { lesson: LessonCatalogItem }) => {
  const [questions, setQuestions] = useState<GeneratedQuizQuestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    setLoading(true);
    setError('');
    try {
      const generated = await quizzesApi.generateQuiz({
        mode: 'single_lesson',
        lessonIds: [lesson.id],
        questionsPerLesson: 3,
        totalQuestions: 3,
        difficulty: 'mixed',
        questionTypes: ['mcq', 'true_false', 'short_answer'],
        includeSourcePage: true,
        requireExplanation: true,
        avoidDuplicateQuestions: true,
      });
      setQuestions(generated.slice(0, 3));
    } catch {
      setError('تعذر توليد اختبار قصير من الخادم الآن.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="session-practice" className="study-session-anchor">
      <Card className="study-session-card">
      <div className="study-section-head">
        <strong>تدرب باختبار قصير</strong>
        <StatusPill tone="gold">3 أسئلة</StatusPill>
      </div>

      <p className="study-session-muted">
        اختبر فهمك قبل إنهاء الجلسة. الأسئلة مرتبطة بالدرس الحالي ومصادر الكتاب عندما تكون متاحة.
      </p>

      <div className="study-session-actions-row">
        <Button onClick={() => void generate()} disabled={loading}>
          {loading ? 'جار التوليد...' : 'ولّد اختباراً سريعاً'}
        </Button>
        <Link
          to={`/quiz?auto=true&mode=single_lesson&lessonId=${lesson.id}&questions=5&difficulty=mixed`}
          className="ed-btn ed-btn-secondary"
        >
          افتح صفحة الاختبار
        </Link>
      </div>

      {error && <div className="study-session-inline-error" role="alert">{error}</div>}

      {questions.length > 0 && (
        <div className="study-session-preview-list">
          {questions.map((question, index) => (
            <article key={question.id}>
              <span>سؤال {index + 1}</span>
              <strong>{question.question}</strong>
              {question.options?.length ? (
                <div className="study-session-choice-preview">
                  {question.options.slice(0, 4).map((option) => <em key={option}>{option}</em>)}
                </div>
              ) : (
                <p>{question.explanation}</p>
              )}
            </article>
          ))}
        </div>
      )}
      </Card>
    </section>
  );
};
