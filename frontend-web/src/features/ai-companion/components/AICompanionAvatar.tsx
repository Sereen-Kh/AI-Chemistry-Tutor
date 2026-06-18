import type { LearningContext } from '../types';

const initialsForPage = (page: LearningContext['currentPage']) => {
  if (page === 'study_plan') return 'خ';
  if (page === 'quiz') return 'اخ';
  if (page === 'flashcards') return 'بط';
  if (page === 'lessons' || page === 'lesson_detail') return 'در';
  return 'AI';
};

export const AICompanionAvatar = ({ context }: { context: LearningContext }) => (
  <span className="ai-companion-avatar-core" aria-hidden="true">
    <span className="ai-companion-avatar-orbit orbit-one" />
    <span className="ai-companion-avatar-orbit orbit-two" />
    <span className="ai-companion-avatar-face">{initialsForPage(context.currentPage)}</span>
  </span>
);
