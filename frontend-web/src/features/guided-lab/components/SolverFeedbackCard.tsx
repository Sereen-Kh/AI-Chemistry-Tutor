import { Button, Card, StatusPill } from '../../../components/DesignSystem';
import type { SubmitStepAnswerResponse } from '../types';

const errorTypeLabel = (type: string): string =>
  ({
    forgot_ml_to_l_conversion: 'خطأ شائع: نسيان تحويل mL إلى L',
    needs_retry: 'تحتاج الإجابة إلى مراجعة',
  })[type] ?? type;

export const SolverFeedbackCard = ({
  feedback,
  onNext,
  onHint,
}: {
  feedback: SubmitStepAnswerResponse;
  onNext: () => void;
  onHint: () => void;
}) => (
  <Card className={`solver-feedback-card ${feedback.is_correct ? 'correct' : 'incorrect'}`}>
    <div className="solver-feedback-head">
      <StatusPill tone={feedback.is_correct ? 'teal' : 'coral'}>
        {feedback.is_correct ? 'إجابة صحيحة' : 'حاول مرة أخرى'}
      </StatusPill>
      {feedback.detected_error_type && <span>{errorTypeLabel(feedback.detected_error_type)}</span>}
    </div>
    <p>{feedback.feedback}</p>
    <div className="guided-card-actions">
      {feedback.is_correct ? (
        <Button onClick={onNext}>{feedback.session_status === 'completed' ? 'ملخص الحل' : 'الخطوة التالية'}</Button>
      ) : (
        <Button variant="secondary" onClick={onHint}>أظهر تلميحاً</Button>
      )}
    </div>
  </Card>
);
