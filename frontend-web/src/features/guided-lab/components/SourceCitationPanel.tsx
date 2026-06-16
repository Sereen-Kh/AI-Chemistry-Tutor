import { Card, StatusPill } from '../../../components/DesignSystem';
import type { SourceReference } from '../types';

const sourceLabel = (sourceType: string): string =>
  ({
    textbook: 'كتاب الكيمياء',
    solution_book: 'كتاب الحلول',
    exam: 'نموذج امتحاني',
  })[sourceType] ?? sourceType;

const contentTypeLabel = (contentType?: string): string => {
  if (!contentType) return '';
  return ({
    formula: 'قانون',
    calculation: 'حساب',
    definition: 'تعريف',
    exercise_answer: 'حل تمرين',
    solution: 'حل',
    text: 'نص',
  })[contentType] ?? contentType;
};

export const SourceCitationPanel = ({ sources }: { sources: SourceReference[] }) => (
  <Card className="solver-source-panel">
    <div className="section-title">
      <h2>المصادر</h2>
      <span>{sources.length ? 'مقاطع تدعم خطوات الحل.' : 'لا توجد مصادر بعد.'}</span>
    </div>
    <div className="solver-source-list">
      {sources.map((source) => (
        <article key={`${source.chunk_id}-${source.page_number ?? 'p'}`} className="solver-source-card">
          <div>
            <strong>{sourceLabel(source.source_type)}</strong>
            {source.page_number && <span>صفحة {source.page_number}</span>}
          </div>
          {source.content_type && <StatusPill tone="blue">{contentTypeLabel(source.content_type)}</StatusPill>}
          {source.preview && <p>{source.preview}</p>}
          {source.image_url && (
            <a href={source.image_url} target="_blank" rel="noreferrer" className="card-link-button">
              اعرض صفحة المصدر
            </a>
          )}
        </article>
      ))}
    </div>
  </Card>
);
