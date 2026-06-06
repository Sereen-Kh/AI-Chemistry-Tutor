import type { ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import type { AiAskResponse, AnswerFormat, FlashcardItem, LessonItem, SourceCitation } from '../types';
import { ChemistryFlask } from './ChemistryFlask';
import { AvatarGuide } from './AvatarGuide';

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
    {onRetry && <Button variant="ghost" onClick={onRetry}>إعادة المحاولة</Button>}
  </div>
);

export const LoadingSkeleton = ({ rows = 3 }: { rows?: number }) => (
  <div className="skeleton-stack" aria-label="جار التحميل">
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
      <span>صفحة {source.page ?? '-'}</span>
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
    <p className="eyebrow">مهمة اليوم</p>
    <h2>{title}</h2>
    <p>{meta}</p>
    <Link className="card-link-button" to={to}>ابدأ المهمة</Link>
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
  completed: 'تم',
  current: 'الآن',
  locked: 'مغلق',
  weak: 'ضعيف',
};

export const LessonCard = ({ lesson }: { lesson: LessonItem }) => (
  <article className={`lesson-card ${lesson.status}`}>
    <span>{lessonStatusLabel[lesson.status]}</span>
    <div>
      <strong>{lesson.title}</strong>
      <small>{lesson.duration} دقيقة</small>
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
    <span>{flipped ? 'الإجابة' : 'السؤال'}</span>
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
    {response?.format === 'audio' && !response.audio_url && <StatusPill tone="gold">توليد الصوت قيد المعالجة.</StatusPill>}
    {response?.audio_url && <audio controls src={response.audio_url} />}
    {response?.source_page_image_url && (
      <figure className="answer-media">
        <img src={response.source_page_image_url} alt="صفحة المصدر من كتاب الكيمياء" />
        <figcaption>صفحة المصدر من الكتاب</figcaption>
      </figure>
    )}
    {response?.image_url && (
      <figure className="answer-media">
        <img src={response.image_url} alt="صورة شرح مولدة بالذكاء الاصطناعي" />
        <figcaption>صورة شرح مولدة</figcaption>
      </figure>
    )}
    {response?.format === 'video' && (
      <div className="video-card">
        <strong>{response.video_title || 'اقتراح Reel قصير سيظهر هنا عند توفره.'}</strong>
        <span>{response.video_source || 'EduMind'}</span>
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
  { value: 'text', label: 'نص', icon: 'T' },
  { value: 'audio', label: 'صوت', icon: 'A' },
  { value: 'image', label: 'صورة', icon: 'I' },
  { value: 'video', label: 'Reel', icon: 'R' },
];

export const AnswerFormatSelector = ({
  value,
  onChange,
}: {
  value: AnswerFormat;
  onChange: (format: AnswerFormat) => void;
}) => (
  <div className="format-selector" aria-label="اختيار صيغة الإجابة">
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
  <main className="auth-layout" dir="rtl">
    <AvatarGuide expression="welcome" waypoint="top-left" message="أهلاً، أنا مرشدك الهجين في مختبر EduMind." />
    <section className="auth-visual" aria-label="معاينة EduMind">
      <div className="mini-phone">
        <ChemistryFlask color="green" level={65} size={150} />
        <div className="mini-phone-card mission-preview">
          <small>مهمة اليوم</small>
          <strong>فهم الحموض مع مصادر من الكتاب</strong>
          <span>18 دقيقة · 45 نقطة</span>
        </div>
        <div className="mini-stat-row">
          <span>5 أيام متتالية</span>
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

const HomeIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const LessonsIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
    <path d="M6 6h10M6 10h10"/>
  </svg>
);

const AskAiIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/>
  </svg>
);

const LabIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 2h12M6 2v4l8 12a2 2 0 0 1-1.7 2.8H5.7A2 2 0 0 1 4 18L12 6V2" />
  </svg>
);

const ProfileIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
);

const navItems = [
  { to: '/dashboard', label: 'الرئيسية', icon: <HomeIcon /> },
  { to: '/study-plan', label: 'الخطة', icon: <LessonsIcon /> },
  { to: '/ask-ai', label: 'اسأل الذكاء', icon: <AskAiIcon /> },
  { to: '/lab/equation-balancer', label: 'المختبر', icon: <LabIcon /> },
  { to: '/profile', label: 'ملفي', icon: <ProfileIcon /> },
];

const RouteTransitionOutlet = () => {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        className="route-transition"
        initial={{ opacity: 0, y: 14, filter: 'blur(4px)' }}
        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
        exit={{ opacity: 0, y: -8, filter: 'blur(4px)' }}
        transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
      >
        <Outlet />
      </motion.div>
    </AnimatePresence>
  );
};

export const AppShell = ({ userName, onLogout }: { userName: string; onLogout: () => void }) => {
  const navigate = useNavigate();

  return (
    <div className="app-shell" dir="rtl">
      <motion.aside
        className="sidebar-nav"
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
      >
        <button className="app-brand" type="button" onClick={() => navigate('/dashboard')}>
          <span>EM</span>
          <div>
            <strong>EduMind</strong>
            <small>مختبر الكيمياء الذكي</small>
          </div>
        </button>
        <nav aria-label="التنقل الرئيسي">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <AvatarGuide waypoint="sidebar" />
        <div className="sidebar-footer">
          <span>{userName}</span>
          <small>جاهز لمهمة كيمياء جديدة</small>
          <Button variant="ghost" onClick={onLogout}>تسجيل الخروج</Button>
        </div>
      </motion.aside>
      <motion.main
        className="app-main"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.28 }}
      >
        <header className="shell-topbar">
          <div>
            <p className="eyebrow">مختبر التعلم</p>
            <strong>مرحباً، {userName}</strong>
          </div>
          <div className="shell-topbar-actions">
            <StatusPill tone="teal">RAG</StatusPill>
            <StatusPill tone="purple">Reel</StatusPill>
            <StatusPill tone="coral">تجارب</StatusPill>
          </div>
        </header>
        <RouteTransitionOutlet />
      </motion.main>
      <motion.nav
        className="bottom-nav"
        aria-label="تنقل الجوال"
        initial={{ y: 72 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      >
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </motion.nav>
    </div>
  );
};
