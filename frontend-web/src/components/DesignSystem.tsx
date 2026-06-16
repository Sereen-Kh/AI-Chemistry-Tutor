import { useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import type { AiAskResponse, AnswerFormat, FlashcardItem, LearningMode, LessonItem, SourceCitation } from '../types';
import { ChemistryFlask } from './ChemistryFlask';
import { AvatarGuide } from './AvatarGuide';
import { notificationsApi } from '../api';


interface ButtonProps {
  children: ReactNode;
  type?: 'button' | 'submit';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
  style?: React.CSSProperties;
  ariaLabel?: string;
}

export const Button = ({ children, type = 'button', variant = 'primary', disabled, onClick, className = '', style, ariaLabel }: ButtonProps) => (
  <button type={type} disabled={disabled} onClick={onClick} className={`ed-btn ed-btn-${variant} ${className}`} style={style} aria-label={ariaLabel}>
    {children}
  </button>
);

export const Card = ({ children, className = '', style }: { children: ReactNode; className?: string; style?: React.CSSProperties }) => (
  <section className={`ed-card ${className}`} style={style}>{children}</section>
);

export const ProgressBar = ({ value, tone = 'blue' }: { value: number; tone?: string }) => (
  <div className="progress-track" role="progressbar" aria-label={`نسبة التقدم ${value}%`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.max(0, Math.min(value, 100))}>
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

const sourceQuality = (score?: number): { label: string; tone: string } | null => {
  if (typeof score !== 'number') return null;
  if (score >= 0.75) return { label: 'مطابقة عالية', tone: 'teal' };
  if (score >= 0.6) return { label: 'مطابقة جيدة', tone: 'blue' };
  if (score >= 0.45) return { label: 'مطابقة متوسطة', tone: 'gold' };
  return null;
};

const formulaPattern = /(C1\s*[×x*]\s*V1\s*=\s*C2\s*[×x*]\s*V2|C_?m\s*=\s*m\s*\/\s*V|Cg\s*=\s*m\s*\/\s*V|C\s*=\s*n\s*\/\s*V|n\s*=\s*m\s*\/\s*M|H₂O|H2O|H₂SO₄|H2SO4|HCl|NaOH|CaCO₃|CaCO3|CO₂|CO2|NH₃|NH3|CH₄|CH4|OH-|H\+|\d+(?:[.,]\d+)?\s*(?:mol\/L|g\/L|g\/mol|mL|L|mol|g)\b)/g;
const isFormulaLike = (part: string): boolean => new RegExp(formulaPattern.source).test(part);

export const FormattedText = ({ text }: { text: string }) => {
  const parts = text.split(formulaPattern).filter(Boolean);
  return (
    <>
      {parts.map((part, index) => (
        isFormulaLike(part) ? (
          <span key={`${part}-${index}`} className="formula">{part}</span>
        ) : (
          <span key={`${part}-${index}`}>{part}</span>
        )
      ))}
    </>
  );
};

export const SourceCard = ({ source }: { source: SourceCitation }) => {
  const quality = sourceQuality(source.score);
  const sourceTypeLabel = source.title.includes('الحلول')
    ? 'من كتاب الحلول'
    : source.title.includes('عام')
      ? 'شرح عام'
      : 'من كتاب الكيمياء';
  return (
    <article className="source-card">
      <div>
        <strong>{sourceTypeLabel}</strong>
        <span>صفحة {source.page ?? '-'}</span>
      </div>
      <small>{source.title}</small>
      {source.quote && <p><FormattedText text={source.quote} /></p>}
      {quality && <StatusPill tone={quality.tone}>{quality.label}</StatusPill>}
    </article>
  );
};

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
  actions,
}: {
  role: 'user' | 'assistant';
  content: string;
  response?: AiAskResponse;
  actions?: ReactNode;
}) => (
  <article className={`chat-bubble ${role}`}>
    {role === 'assistant' && response && (
      <div className="answer-evidence-bar">
        <StatusPill tone={response.sources.length ? 'teal' : 'gold'}>
          {response.sources.length ? 'إجابة مدعومة بمصادر' : 'لم أجد دليلاً كافياً في المصادر'}
        </StatusPill>
        <span>
          {typeof response.confidence === 'number'
            ? `ثقة المصدر ${Math.round(response.confidence * 100)}%`
            : 'ثقة المصدر غير متاحة'}
        </span>
      </div>
    )}
    <p><FormattedText text={content} /></p>
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
        <strong>{response.video_title || 'اقتراح فيديو قصير سيظهر هنا عند توفره.'}</strong>
        <span>{response.video_source || 'وسائط داعمة'}</span>
      </div>
    )}
    {response?.sources.length ? (
      <div className="source-evidence-panel">
        <div className="source-evidence-head">
          <strong>لوحة الأدلة</strong>
          <span>مصادر الإجابة من الكتاب أو كتاب الحلول</span>
        </div>
        <div className="source-grid">
        {response.sources.map((source) => <SourceCard key={`${source.chunk_id}-${source.page}`} source={source} />)}
        </div>
      </div>
    ) : null}
    {actions && <div className="answer-action-row">{actions}</div>}
  </article>
);

const formatOptions: Array<{ value: AnswerFormat; label: string; icon: string }> = [
  { value: 'text', label: 'نص', icon: 'T' },
  { value: 'audio', label: 'صوت', icon: 'A' },
  { value: 'image', label: 'صورة', icon: 'I' },
  { value: 'video', label: 'فيديو قصير', icon: 'V' },
];

const learningModeOptions: Array<{ value: LearningMode; label: string; icon: string }> = [
  { value: 'text', label: 'نص', icon: 'T' },
  { value: 'image', label: 'صورة', icon: 'I' },
  { value: 'audio', label: 'صوت', icon: 'A' },
  { value: 'video', label: 'فيديو', icon: 'V' },
  { value: 'reel', label: 'فيديو قصير', icon: 'R' },
  { value: 'interactive', label: 'تفاعلي', icon: 'X' },
  { value: 'quiz', label: 'اختبار', icon: 'Q' },
  { value: 'flashcards', label: 'بطاقات', icon: 'F' },
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
        aria-label={`صيغة الإجابة: ${option.label}${value === option.value ? '، محددة' : ''}`}
      >
        <span>{option.icon}</span>
        {option.label}
      </button>
    ))}
  </div>
);

export const LearningModeSelector = ({
  value,
  onChange,
}: {
  value: LearningMode[];
  onChange: (modes: LearningMode[]) => void;
}) => {
  const toggle = (mode: LearningMode) => {
    if (mode === 'text') {
      onChange(['text', ...value.filter((item) => item !== 'text')]);
      return;
    }
    const next = value.includes(mode) ? value.filter((item) => item !== mode) : [...value, mode];
    onChange(next.includes('text') ? next : ['text', ...next]);
  };

  return (
    <div className="format-selector" aria-label="اختيار أنماط التعلم">
      {learningModeOptions.map((option) => (
        <button
          key={option.value}
          type="button"
          className={value.includes(option.value) ? 'active' : ''}
          onClick={() => toggle(option.value)}
          aria-pressed={value.includes(option.value)}
          aria-label={`نمط التعلم: ${option.label}${value.includes(option.value) ? '، محدد' : ''}`}
        >
          <span>{option.icon}</span>
          {option.label}
        </button>
      ))}
    </div>
  );
};

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

const QuizIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 11h6M9 15h3" />
    <path d="M8 3H6a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-2" />
    <path d="M9 3h6v4H9z" />
  </svg>
);

const SearchBookIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
    <path d="M8 8h5M8 11h3" />
  </svg>
);

const CardsIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="5" width="12" height="14" rx="2" />
    <path d="M8 5V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-2" />
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

const HomeworkIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 4h16v16H4z" />
    <path d="M8 8h8M8 12h6M8 16h4" />
  </svg>
);

const AdminIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3 4 6v6c0 5 3.4 8.5 8 9 4.6-.5 8-4 8-9V6l-8-3Z" />
    <path d="M9 12h6M12 9v6" />
  </svg>
);

const ProfileIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
);

const BellIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
  </svg>
);

const navItems = [
  { to: '/dashboard', label: 'الرئيسية', icon: <HomeIcon />, tone: 'teal' },
  { to: '/lessons', label: 'الدروس', icon: <LessonsIcon />, tone: 'green' },
  { to: '/ask-ai', label: 'اسأل الذكاء', icon: <AskAiIcon />, tone: 'purple' },
  { to: '/rag-search', label: 'بحث الكتاب', icon: <SearchBookIcon />, tone: 'cyan' },
  { to: '/quizzes', label: 'اختبار', icon: <QuizIcon />, tone: 'gold' },
  { to: '/flashcards', label: 'بطاقات', icon: <CardsIcon />, tone: 'coral' },
  { to: '/study-plan', label: 'الخطة', icon: <LessonsIcon />, tone: 'blue' },
  { to: '/notifications', label: 'الإشعارات', icon: <BellIcon />, tone: 'gold' },
  { to: '/lab', label: 'المختبر', icon: <LabIcon />, tone: 'teal' },
  { to: '/homework', label: 'الواجبات', icon: <HomeworkIcon />, tone: 'blue' },
  { to: '/admin/rag', label: 'إدارة RAG', icon: <AdminIcon />, tone: 'slate' },
  { to: '/profile', label: 'ملفي', icon: <ProfileIcon />, tone: 'slate' },
];

const bottomNavItems = navItems.filter((item) =>
  ['/dashboard', '/lessons', '/ask-ai', '/notifications', '/profile'].includes(item.to),
);

const routeTitles: Record<string, { eyebrow: string; title: string }> = {
  '/dashboard': { eyebrow: 'مختبر التعلم', title: 'الرئيسية' },
  '/lessons': { eyebrow: 'منهج الكيمياء', title: 'الدروس' },
  '/study-plan': { eyebrow: 'تنظيم المذاكرة', title: 'خطة الدراسة' },
  '/ask-ai': { eyebrow: 'معلّم RAG', title: 'اسأل الذكاء الاصطناعي' },
  '/rag-search': { eyebrow: 'مصادر الكتاب', title: 'البحث في الكتاب' },
  '/quizzes': { eyebrow: 'تدريب امتحاني', title: 'الاختبارات' },
  '/flashcards': { eyebrow: 'مراجعة ذكية', title: 'البطاقات التعليمية' },
  '/lab': { eyebrow: 'مختبر كيمياء', title: 'المختبر' },
  '/guided-lab': { eyebrow: 'مختبر تفاعلي', title: 'حل المسائل الموجه' },
  '/lab/equation-balancer': { eyebrow: 'مختبر كيمياء', title: 'موازن المعادلات' },
  '/homework': { eyebrow: 'حل الواجبات', title: 'مساعد الواجبات' },
  '/admin/rag': { eyebrow: 'إدارة RAG', title: 'لوحة RAG' },
  '/admin/rag/reembed': { eyebrow: 'إدارة RAG', title: 'إعادة التضمين' },
  '/admin/rag/evaluation': { eyebrow: 'إدارة RAG', title: 'تقييم RAG' },
  '/admin/rag/query-logs': { eyebrow: 'إدارة RAG', title: 'سجلات الاستعلام' },
  '/admin/sources': { eyebrow: 'إدارة المصادر', title: 'مصادر RAG' },
  '/profile': { eyebrow: 'التفضيلات', title: 'الملف الشخصي' },
  '/notifications': { eyebrow: 'تنبيهات النظام', title: 'الإشعارات' },
};

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
  const location = useLocation();
  const dynamicRouteTitle = location.pathname.startsWith('/guided-lab/session')
    ? { eyebrow: 'مختبر تفاعلي', title: 'جلسة حل موجهة' }
    : undefined;
  const routeTitle = routeTitles[location.pathname] ?? dynamicRouteTitle ?? routeTitles['/dashboard'];
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const list = await notificationsApi.getNotifications();
        const unread = list.filter(n => n.status === 'unread').length;
        setUnreadCount(unread);
      } catch (err) {
        console.error(err);
      }
    };
    void fetchUnread();

    const handleUpdate = () => void fetchUnread();
    window.addEventListener('notifications-updated', handleUpdate);
    return () => {
      window.removeEventListener('notifications-updated', handleUpdate);
    };
  }, []);

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
            <NavLink key={item.to} to={item.to} data-tone={item.tone} className={({ isActive }) => (isActive ? 'active' : '')}>
              <span>{item.icon}</span>
              {item.label}
              {item.to === '/notifications' && unreadCount > 0 && (
                <span style={{
                  background: 'var(--coral)',
                  color: '#fff',
                  fontSize: '10px',
                  fontWeight: 'bold',
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: 'auto',
                  border: '1px solid var(--bg2)'
                }}>{unreadCount}</span>
              )}
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
            <p className="eyebrow">{routeTitle.eyebrow}</p>
            <strong>{routeTitle.title} · {userName}</strong>
          </div>
          <div className="shell-topbar-actions" style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <Link to="/notifications" className="topbar-bell-btn" aria-label="الإشعارات" title="الإشعارات">
              <span style={{ fontSize: '16px' }}>🔔</span>
              {unreadCount > 0 && <span className="topbar-bell-badge">{unreadCount}</span>}
            </Link>
            <StatusPill tone="teal">RAG</StatusPill>
            <StatusPill tone="purple">فيديو قصير</StatusPill>
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
        {bottomNavItems.map((item) => (
          <NavLink key={item.to} to={item.to} data-tone={item.tone} className={({ isActive }) => (isActive ? 'active' : '')}>
            <span style={{ position: 'relative', display: 'inline-flex' }}>
              {item.icon}
              {item.to === '/notifications' && unreadCount > 0 && (
                <span className="bottom-nav-badge">{unreadCount}</span>
              )}
            </span>
            {item.label}
          </NavLink>
        ))}
      </motion.nav>
    </div>
  );
};
