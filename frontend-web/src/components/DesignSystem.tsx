import type { ReactNode } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import type { AiAskResponse, AnswerFormat, FlashcardItem, LessonItem, SourceCitation } from '../types';

interface ButtonProps {
  children: ReactNode;
  type?: 'button' | 'submit';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
}

export const Button = ({ children, type = 'button', variant = 'primary', disabled, onClick, className = '' }: ButtonProps) => (
  <button type={type} disabled={disabled} onClick={onClick} className={`ed-btn ed-btn-${variant} ${className}`}>
    {children}
  </button>
);

export const Card = ({ children, className = '' }: { children: ReactNode; className?: string }) => (
  <section className={`ed-card ${className}`}>{children}</section>
);

export const ProgressBar = ({ value, tone = 'blue' }: { value: number; tone?: string }) => (
  <div className="progress-track" aria-label={`Progress ${value}%`}>
    <span className={`progress-fill tone-${tone}`} style={{ width: `${Math.max(0, Math.min(value, 100))}%` }} />
  </div>
);

export const StatusPill = ({ children, tone = 'blue' }: { children: ReactNode; tone?: string }) => (
  <span className={`status-pill tone-${tone}`}>{children}</span>
);

export const ErrorBanner = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div className="error-banner" role="alert">
    <span>{message}</span>
    {onRetry && <Button variant="ghost" onClick={onRetry}>Retry</Button>}
  </div>
);

export const LoadingSkeleton = ({ rows = 3 }: { rows?: number }) => (
  <div className="skeleton-stack" aria-label="Loading">
    {Array.from({ length: rows }, (_, index) => (
      <span key={index} className="skeleton-line" />
    ))}
  </div>
);

export const PageHeader = ({
  eyebrow,
  title,
  subtitle,
  action,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) => (
  <header className="page-header">
    <div>
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
    {action}
  </header>
);

export const SourceCard = ({ source }: { source: SourceCitation }) => (
  <article className="source-card">
    <div>
      <strong>{source.title}</strong>
      <span>Page {source.page ?? '-'}</span>
    </div>
    {source.quote && <p>{source.quote}</p>}
    {typeof source.score === 'number' && <StatusPill tone="blue">{Math.round(source.score * 100)}%</StatusPill>}
  </article>
);

export const StudyMissionCard = ({
  title,
  meta,
  to,
}: {
  title: string;
  meta: string;
  to: string;
}) => (
  <Card className="mission-card">
    <p className="eyebrow">Today's study mission</p>
    <h2>{title}</h2>
    <p>{meta}</p>
    <Link className="card-link-button" to={to}>Start mission</Link>
  </Card>
);

export const RecommendationCard = ({
  label,
  title,
  description,
  tone,
}: {
  label: string;
  title: string;
  description: string;
  tone: string;
}) => (
  <article className="recommendation-card">
    <StatusPill tone={tone}>{label}</StatusPill>
    <strong>{title}</strong>
    <span>{description}</span>
  </article>
);

const lessonStatusLabel: Record<LessonItem['status'], string> = {
  completed: 'Done',
  current: 'Now',
  locked: 'Lock',
  weak: 'Weak',
};

export const LessonCard = ({ lesson }: { lesson: LessonItem }) => (
  <article className={`lesson-card ${lesson.status}`}>
    <span>{lessonStatusLabel[lesson.status]}</span>
    <div>
      <strong>{lesson.title}</strong>
      <small>{lesson.duration} min</small>
    </div>
  </article>
);

export const Flashcard = ({
  card,
  flipped,
  onFlip,
}: {
  card: FlashcardItem;
  flipped: boolean;
  onFlip: () => void;
}) => (
  <button type="button" className={flipped ? 'flashcard flipped' : 'flashcard'} onClick={onFlip}>
    <span>{flipped ? 'Back' : 'Front'}</span>
    <strong>{flipped ? card.back : card.front}</strong>
    {!flipped && card.hint && <small>{card.hint}</small>}
  </button>
);

export const ChatMessage = ({
  role,
  content,
  response,
}: {
  role: 'user' | 'assistant';
  content: string;
  response?: AiAskResponse;
}) => (
  <article className={`chat-bubble ${role}`}>
    <p>{content}</p>
    {response?.format === 'audio' && !response.audio_url && <StatusPill tone="gold">Audio generation is still processing.</StatusPill>}
    {response?.audio_url && <audio controls src={response.audio_url} />}
    {response?.source_page_image_url && (
      <figure className="answer-media">
        <img src={response.source_page_image_url} alt="Source page from chemistry book" />
        <figcaption>Source page from the textbook</figcaption>
      </figure>
    )}
    {response?.image_url && (
      <figure className="answer-media">
        <img src={response.image_url} alt="AI-generated explanation" />
        <figcaption>AI-generated explanation image</figcaption>
      </figure>
    )}
    {response?.format === 'video' && (
      <div className="video-card">
        <strong>{response.video_title || 'No suitable video found yet. Try text or image explanation.'}</strong>
        <span>{response.video_source || 'internal'}</span>
      </div>
    )}
    {response?.sources.length ? (
      <div className="source-grid">
        {response.sources.map((source) => <SourceCard key={`${source.chunk_id}-${source.page}`} source={source} />)}
      </div>
    ) : null}
  </article>
);

const formatOptions: Array<{ value: AnswerFormat; label: string; icon: string }> = [
  { value: 'text', label: 'Text', icon: 'T' },
  { value: 'audio', label: 'Audio', icon: 'A' },
  { value: 'image', label: 'Image', icon: 'I' },
  { value: 'video', label: 'Video', icon: 'V' },
];

export const AnswerFormatSelector = ({
  value,
  onChange,
}: {
  value: AnswerFormat;
  onChange: (format: AnswerFormat) => void;
}) => (
  <div className="format-selector" aria-label="Answer format selector">
    {formatOptions.map((option) => (
      <button
        key={option.value}
        type="button"
        className={value === option.value ? 'active' : ''}
        onClick={() => onChange(option.value)}
        aria-pressed={value === option.value}
      >
        <span>{option.icon}</span>
        {option.label}
      </button>
    ))}
  </div>
);

export const AuthLayout = ({ children, title, subtitle }: { children: ReactNode; title: string; subtitle: string }) => (
  <main className="auth-layout">
    <section className="auth-visual" aria-label="EduMind preview">
      <div className="mini-phone">
        <div className="mini-phone-top">
          <span>9:41</span>
          <span>EduMind</span>
        </div>
        <div className="mini-phone-card mission-preview">
          <small>Today's mission</small>
          <strong>Master acids with RAG sources</strong>
          <span>18 min · 45 XP</span>
        </div>
        <div className="mini-stat-row">
          <span>5 streak</span>
          <span>1,240 XP</span>
        </div>
      </div>
    </section>
    <section className="auth-panel">
      <div className="brand-mark">EduMind</div>
      <h1>{title}</h1>
      <p>{subtitle}</p>
      {children}
    </section>
  </main>
);

const navItems = [
  { to: '/dashboard', label: 'Home', icon: 'H' },
  { to: '/study-plan', label: 'Lessons', icon: 'L' },
  { to: '/ask-ai', label: 'Ask AI', icon: 'AI' },
  { to: '/lab/equation-balancer', label: 'Lab', icon: 'Lab' },
  { to: '/profile', label: 'Profile', icon: 'P' },
];

export const AppShell = ({ userName, onLogout }: { userName: string; onLogout: () => void }) => {
  const navigate = useNavigate();

  return (
    <div className="app-shell">
      <aside className="sidebar-nav">
        <button className="app-brand" type="button" onClick={() => navigate('/dashboard')}>
          <span>EM</span>
          <strong>EduMind</strong>
        </button>
        <nav aria-label="Primary navigation">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>{userName}</span>
          <Button variant="ghost" onClick={onLogout}>Logout</Button>
        </div>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
      <nav className="bottom-nav" aria-label="Mobile navigation">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
};
