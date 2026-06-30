import { useEffect, useState, lazy, Suspense } from 'react';
import type { FormEvent, ReactElement } from 'react';
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import {
  AUTH_EXPIRED_EVENT,
  AUTH_EXPIRED_MESSAGE,
  authApi,
  dashboardApi,
  labApi,
  notificationsApi,
  toErrorMessage,
  userApi,
} from './api';
import { ChemistryFlask } from './components/ChemistryFlask';
import { MoleculeBackground } from './components/MoleculeBackground';
import {
  AppShell,
  AuthLayout,
  Button,
  Card,
  ErrorBanner,
  LearningModeSelector,
  LoadingSkeleton,
  PageHeader,
  ProgressBar,
  RecommendationCard,
  StatusPill,
  StudyMissionCard,
} from './components/DesignSystem';
import { clearToken, getToken, loadPreferences, savePreferences } from './lib/storage';
import { AskAiPage } from './pages/AskAIPage';
import { LessonsPage, RagSearchPage } from './pages/LearningPages';

const QuizzesPage = lazy(() => import('./pages/QuizzesPage').then(module => ({ default: module.QuizzesPage })));
const FlashcardsPage = lazy(() => import('./pages/FlashcardsPage').then(module => ({ default: module.FlashcardsPage })));
const LessonDetailPage = lazy(() => import('./pages/LessonDetailPage').then(module => ({ default: module.LessonDetailPage })));
const StudyPlanPage = lazy(() => import('./pages/StudyPlanPage').then(module => ({ default: module.StudyPlanPage })));
const StudySessionPage = lazy(() => import('./pages/StudySessionPage').then(module => ({ default: module.StudySessionPage })));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage').then(module => ({ default: module.NotificationsPage })));
const NotificationSettingsPage = lazy(() => import('./pages/NotificationSettingsPage').then(module => ({ default: module.NotificationSettingsPage })));
const LabPage = lazy(() => import('./pages/LabPage').then(module => ({ default: module.LabPage })));
const HomeworkPage = lazy(() => import('./pages/HomeworkPage').then(module => ({ default: module.HomeworkPage })));
const GuidedLabPage = lazy(() => import('./features/guided-lab/pages/GuidedLabPage').then(module => ({ default: module.GuidedLabPage })));
const SolverSessionPage = lazy(() => import('./features/guided-lab/pages/SolverSessionPage').then(module => ({ default: module.SolverSessionPage })));
const RagAdminPage = lazy(() => import('./pages/admin/RagAdminPage').then(module => ({ default: module.RagAdminPage })));
const RagReembedPage = lazy(() => import('./pages/admin/RagReembedPage').then(module => ({ default: module.RagReembedPage })));
const RagEvaluationPage = lazy(() => import('./pages/admin/RagEvaluationPage').then(module => ({ default: module.RagEvaluationPage })));
const RagQueryLogsPage = lazy(() => import('./pages/admin/RagQueryLogsPage').then(module => ({ default: module.RagQueryLogsPage })));
const SourcesPage = lazy(() => import('./pages/admin/SourcesPage').then(module => ({ default: module.SourcesPage })));
import type {
  AnswerFormat,
  BalanceResult,
  ExplanationMethod,
  InterestCategory,
  LearningMode,
  StudentInterest,
  TeachingLevel,
  UserPreferences,
  UserProfile,
} from './types';

interface AuthState {
  user: UserProfile | null;
  preferences: UserPreferences;
  booting: boolean;
}

const teachingLevelLabels: Array<{ value: TeachingLevel; label: string }> = [
  { value: 'simple', label: 'مبسط' },
  { value: 'standard', label: 'قياسي' },
  { value: 'academic', label: 'أكاديمي' },
];

const explanationMethodLabels: Array<{ value: ExplanationMethod; label: string }> = [
  { value: 'direct', label: 'مباشر' },
  { value: 'step_by_step', label: 'خطوة بخطوة' },
  { value: 'hints_first', label: 'تلميحات أولاً' },
  { value: 'exam_mode', label: 'نمط امتحاني' },
  { value: 'real_life_example', label: 'مثال من الحياة' },
];

const studentInterestOptions: Array<{ value: StudentInterest; label: string; icon: string }> = [
  { value: 'football', label: 'كرة القدم', icon: 'FB' },
  { value: 'cars', label: 'السيارات', icon: 'CAR' },
  { value: 'cooking', label: 'الطبخ', icon: 'CK' },
  { value: 'gaming', label: 'الألعاب', icon: 'GM' },
  { value: 'daily_life', label: 'الحياة اليومية', icon: 'DL' },
  { value: 'laboratory', label: 'المختبر', icon: 'LAB' },
  { value: 'nature', label: 'الطبيعة', icon: 'NAT' },
];

const preferenceLabel = (value: string): string =>
  ({
    simple: 'مبسط',
    standard: 'قياسي',
    academic: 'أكاديمي',
    direct: 'مباشر',
    step_by_step: 'خطوة بخطوة',
    hints_first: 'تلميحات أولاً',
    exam_mode: 'نمط امتحاني',
    real_life_example: 'مثال من الحياة',
    text: 'نص',
    audio: 'صوت',
    image: 'صورة',
    video: 'فيديو قصير',
    reel: 'فيديو قصير',
    interactive: 'تفاعلي',
    quiz: 'اختبار',
    flashcards: 'بطاقات',
    auto: 'تلقائي',
    book_only: 'من الكتاب فقط',
    tutor_general: 'شرح عام عند الحاجة',
  })[value] ?? value;

const primaryAnswerFormat = (modes: LearningMode[]): AnswerFormat => {
  if (modes.includes('video') || modes.includes('reel')) return 'video';
  if (modes.includes('image')) return 'image';
  if (modes.includes('audio')) return 'audio';
  return 'text';
};

const legacyTeachingStyle = (level: TeachingLevel, method: ExplanationMethod): UserPreferences['teachingStyle'] => {
  if (method === 'real_life_example') return 'real_life';
  if (method === 'exam_mode' || level === 'academic') return 'exam';
  if (level === 'simple') return 'simple';
  return 'real_life';
};

const normalizeModes = (modes: LearningMode[]): LearningMode[] => {
  const unique = Array.from(new Set(modes));
  return unique.includes('text') ? unique : ['text', ...unique];
};

const preferencesFromUser = (user: UserProfile, current: UserPreferences): UserPreferences => {
  const teachingLevel = user.teaching_level ?? current.teachingLevel;
  const explanationMethod = user.explanation_method ?? current.explanationMethod;
  const learningModes = normalizeModes(user.learning_modes?.length ? user.learning_modes : current.learningModes);
  const studentInterests = (user.student_interests?.filter((interest) => interest !== 'none') ?? current.studentInterests) as StudentInterest[];

  return {
    ...current,
    grade: user.grade || current.grade,
    subject: user.subject || current.subject,
    language: user.language === 'en' ? 'en' : 'ar',
    teachingLevel,
    explanationMethod,
    learningModes,
    studentInterests,
    interests: studentInterests,
    teachingStyle: legacyTeachingStyle(teachingLevel, explanationMethod),
    answerFormat: primaryAnswerFormat(learningModes),
  };
};

const ProtectedRoute = ({ user, booting }: { user: UserProfile | null; booting: boolean }) => {
  const location = useLocation();
  if (booting) {
    return <main className="route-loading"><LoadingSkeleton rows={5} /></main>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return null;
};

const GuestOnly = ({ user, children }: { user: UserProfile | null; children: ReactElement }) => {
  if (user) return <Navigate to="/" replace />;
  return children;
};

const LoginPage = ({ onLogin }: { onLogin: () => Promise<void> }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as { from?: string; sessionExpired?: boolean } | null;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(locationState?.sessionExpired ? AUTH_EXPIRED_MESSAGE : '');

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.includes('@') || password.length < 6) {
      setError('أدخل بريداً إلكترونياً صحيحاً وكلمة مرور من 6 أحرف على الأقل.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authApi.login(email, password);
      await onLogin();
      const nextPath = locationState?.from && locationState.from !== '/login' ? locationState.from : '/';
      navigate(nextPath, { replace: true });
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر تسجيل الدخول. تحقق من البريد وكلمة المرور.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="مرحباً بعودتك" subtitle="سجل الدخول لمتابعة رحلة الكيمياء.">
      <form className="auth-form" onSubmit={submit}>
        {error && <ErrorBanner message={error} />}
        <label>
          البريد الإلكتروني
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" required />
        </label>
        <label>
          كلمة المرور
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required minLength={6} />
        </label>
        <Button type="submit" disabled={loading}>{loading ? 'جار الاتصال...' : 'دخول'}</Button>
        <p className="auth-switch">جديد في EduMind؟ <Link to="/register">أنشئ حساباً</Link></p>
      </form>
    </AuthLayout>
  );
};

const RegisterPage = ({ onRegistered }: { onRegistered: () => Promise<void> }) => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    grade: 'grade_9',
    subject: 'chemistry',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (field: keyof typeof form, value: string) => setForm((current) => ({ ...current, [field]: value }));

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (form.password !== form.confirmPassword) {
      setError('كلمتا المرور غير متطابقتين.');
      return;
    }
    if (form.password.length < 6) {
      setError('كلمة المرور يجب أن تكون 6 أحرف على الأقل.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authApi.register(form);
      await authApi.login(form.email, form.password);
      await onRegistered();
      navigate('/onboarding/interests', { replace: true });
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر إنشاء الحساب.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="أنشئ ملفك التعليمي" subtitle="جهز مساحة تعلم الكيمياء للصف التاسع.">
      <form className="auth-form" onSubmit={submit}>
        {error && <ErrorBanner message={error} />}
        <div className="form-grid">
          <label>
            الاسم الأول
            <input value={form.firstName} onChange={(event) => update('firstName', event.target.value)} required />
          </label>
          <label>
            الاسم الأخير
            <input value={form.lastName} onChange={(event) => update('lastName', event.target.value)} />
          </label>
        </div>
        <label>
          البريد الإلكتروني
          <input value={form.email} onChange={(event) => update('email', event.target.value)} type="email" required />
        </label>
        <div className="form-grid">
          <label>
            كلمة المرور
            <input value={form.password} onChange={(event) => update('password', event.target.value)} type="password" required minLength={6} />
          </label>
          <label>
            تأكيد كلمة المرور
            <input value={form.confirmPassword} onChange={(event) => update('confirmPassword', event.target.value)} type="password" required minLength={6} />
          </label>
        </div>
        <div className="form-grid">
          <label>
            الصف
            <select value={form.grade} onChange={(event) => update('grade', event.target.value)}>
              <option value="grade_9">الصف التاسع</option>
              <option value="grade_8">الصف الثامن</option>
            </select>
          </label>
          <label>
            المادة
            <select value={form.subject} onChange={(event) => update('subject', event.target.value)}>
              <option value="chemistry">الكيمياء</option>
            </select>
          </label>
        </div>
        <Button type="submit" disabled={loading}>{loading ? 'جار الإنشاء...' : 'تسجيل'}</Button>
        <p className="auth-switch">لديك حساب؟ <Link to="/login">سجل الدخول</Link></p>
      </form>
    </AuthLayout>
  );
};

const OnboardingPage = ({
  preferences,
  onSave,
}: {
  preferences: UserPreferences;
  onSave: (preferences: UserPreferences) => void;
}) => {
  const navigate = useNavigate();
  const [backendInterests, setBackendInterests] = useState<InterestCategory[]>([]);
  const [selected, setSelected] = useState<StudentInterest[]>(preferences.studentInterests);
  const [teachingLevel, setTeachingLevel] = useState<TeachingLevel>(preferences.teachingLevel);
  const [explanationMethod, setExplanationMethod] = useState<ExplanationMethod>(preferences.explanationMethod);
  const [learningModes, setLearningModes] = useState<LearningMode[]>(preferences.learningModes);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    authApi.interests().then(setBackendInterests);
  }, []);

  const toggle = (key: StudentInterest) => {
    setSelected((current) => (current.includes(key) ? current.filter((item) => item !== key) : [...current, key]));
  };

  const save = async () => {
    const normalizedLearningModes = normalizeModes(learningModes);
    const next: UserPreferences = {
      ...preferences,
      interests: selected,
      studentInterests: selected,
      teachingLevel,
      explanationMethod,
      learningModes: normalizedLearningModes,
      teachingStyle: legacyTeachingStyle(teachingLevel, explanationMethod),
      answerFormat: primaryAnswerFormat(normalizedLearningModes),
    };
    setLoading(true);
    setError('');
    try {
      const ids = backendInterests.filter((interest) => selected.includes(interest.key as StudentInterest)).map((interest) => interest.id);
      await authApi.completeOnboarding(next, ids);
    } catch (err) {
      setError(toErrorMessage(err, 'تم الحفظ محلياً. تعذر الوصول إلى نقطة إعداد التفضيلات في الخلفية.'));
    } finally {
      onSave(next);
      setLoading(false);
      navigate('/', { replace: true });
    }
  };

  return (
    <main className="onboarding-page">
      <Card className="onboarding-card">
        <PageHeader
          eyebrow="التخصيص"
          title="اختر كيف تريد أن يشرح EduMind"
          subtitle="هذه التفضيلات تضبط الأمثلة وصيغة الإجابة واقتراحات المراجعة."
        />
        {error && <ErrorBanner message={error} />}
        <div className="interest-grid">
          {studentInterestOptions.map((interest) => (
            <button
              key={interest.value}
              type="button"
              className={selected.includes(interest.value) ? 'interest active' : 'interest'}
              onClick={() => toggle(interest.value)}
            >
              <span>{interest.icon}</span>
              <strong>{interest.label}</strong>
            </button>
          ))}
        </div>
        <div className="preference-row">
          <label>
            مستوى الشرح
            <select value={teachingLevel} onChange={(event) => setTeachingLevel(event.target.value as TeachingLevel)}>
              {teachingLevelLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label>
            طريقة الشرح
            <select value={explanationMethod} onChange={(event) => setExplanationMethod(event.target.value as ExplanationMethod)}>
              {explanationMethodLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
        </div>
        <div className="preference-stack">
          <span>أنماط التعلم</span>
          <LearningModeSelector value={learningModes} onChange={(modes) => setLearningModes(normalizeModes(modes))} />
        </div>
        <Button onClick={save} disabled={loading}>{loading ? 'جار الحفظ...' : 'المتابعة إلى الرئيسية'}</Button>
      </Card>
    </main>
  );
};

const DashboardPage = ({ user, preferences }: { user: UserProfile; preferences: UserPreferences }) => {
  const [dashboard, setDashboard] = useState<Awaited<ReturnType<typeof dashboardApi.getDashboard>> | null>(null);
  const [dashboardError, setDashboardError] = useState('');

  useEffect(() => {
    let cancelled = false;
    dashboardApi.getDashboard()
      .then((data) => {
        if (!cancelled) {
          setDashboard(data);
          setDashboardError('');
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setDashboardError(toErrorMessage(error, 'تعذر تحميل بيانات لوحة التعلم، لذلك نعرض قيماً تجريبية مؤقتاً.'));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const continueLesson = {
    title: dashboard?.continue_lesson?.title_ar || 'الحموض والأسس في المحاليل المائية',
    progress: dashboard?.continue_lesson?.progress ?? 62,
    duration: dashboard?.continue_lesson?.duration_min ?? 18,
  };
  const weakTopics = dashboard?.weak_topics.length
    ? dashboard.weak_topics.map((topic) => topic.title_ar)
    : ['الحموض الضعيفة', 'تحويل mL إلى L', 'موازنة المعادلات'];
  const dueFlashcards = dashboard?.due_flashcards.due_count ?? 14;
  const nextQuiz = dashboard?.next_quiz?.title ?? 'اختبار قصير: التركيز المولي';
  const examDaysLeft = dashboard?.study_plan?.days_to_exam ?? 9;
  const unreadCount = dashboard?.notifications.unread_count ?? 0;
  const mission = dashboard?.today_mission || 'أكمل درساً قصيراً، حل مسألة تركيز خطوة بخطوة، ثم راجع البطاقات المستحقة.';
  const quickActions = [
    { to: '/ask-ai', label: 'اسأل الذكاء', icon: 'ذك', tone: 'blue' },
    { to: '/guided-lab', label: 'حل موجه', icon: 'حل', tone: 'purple' },
    { to: '/quiz', label: 'اختبار', icon: 'اخ', tone: 'gold' },
    { to: '/flashcards', label: 'بطاقات', icon: 'بط', tone: 'teal' },
    { to: '/homework', label: 'حل واجب', icon: 'وا', tone: 'coral' },
  ];

  return (
    <div className="dashboard-grid">
      <section className="hero-card">
        <p className="eyebrow">مركز تعلم اليوم</p>
        <h1>أهلاً {dashboard?.student_name || user.first_name || user.name || 'كيميائي'}</h1>
        <p className="dashboard-hero-copy">
          هدف اليوم: {mission}
        </p>
        <div className="badge-row">
          <StatusPill tone="gold">{dashboard?.streak_days ?? user.streak_days ?? 5} أيام متتالية</StatusPill>
          <StatusPill tone="blue">{dashboard?.xp ?? user.xp ?? 1240} XP</StatusPill>
          <StatusPill tone="teal">المستوى {dashboard?.level ?? user.level ?? 4}</StatusPill>
          {dashboardError && <StatusPill tone="purple">بيانات تجريبية عند غياب API</StatusPill>}
        </div>
        {dashboardError && <ErrorBanner message={dashboardError} />}
      </section>

      <StudyMissionCard
        title="احسب تركيز HCl خطوة بخطوة"
        meta={`${continueLesson.duration} دقيقة · ${preferenceLabel(preferences.teachingLevel)} · ${preferenceLabel(preferences.explanationMethod)}`}
        to="/guided-lab"
      />

      <div className="stats-row">
        <Card><strong>{continueLesson.progress}%</strong><span>درس مستمر</span></Card>
        <Card><strong>{dueFlashcards}</strong><span>بطاقة مستحقة</span></Card>
        <Card><strong>{examDaysLeft}</strong><span>أيام حتى الاختبار</span></Card>
      </div>

      <Card className="dashboard-command-card">
        <div className="section-title">
          <h2>متابعة الدرس</h2>
          <Link to="/lessons">عرض الدروس</Link>
        </div>
        <div className="continue-lesson-card">
          <div>
            <StatusPill tone="blue">الدرس الحالي</StatusPill>
            <h3>{continueLesson.title}</h3>
            <p>ابدأ من مصدر الدرس، ثم انتقل إلى اختبار قصير أو حل موجه حسب حاجتك.</p>
          </div>
          <ProgressBar value={continueLesson.progress} tone="teal" />
          <div className="guided-card-actions">
            <Link className="ed-btn ed-btn-primary" to="/lessons">تابع الدرس</Link>
            <Link className="ed-btn ed-btn-secondary" to="/ask-ai?question=اشرح درس الحموض والأسس من الكتاب">اسأل عن الدرس</Link>
          </div>
        </div>
      </Card>

      <Card className="dashboard-command-card">
        <div className="section-title">
          <h2>نقاط ضعف تحتاج تدريباً</h2>
          <Link to="/study-plan">عرض الخطة</Link>
        </div>
        <div className="recommendation-grid">
          {weakTopics.map((topic, index) => (
            <RecommendationCard
              key={topic}
              tone={index === 0 ? 'coral' : index === 1 ? 'gold' : 'purple'}
              label="موضوع ضعيف"
              title={topic}
              description="حوّله إلى اختبار قصير أو بطاقات مراجعة."
            />
          ))}
        </div>
      </Card>

      <Card className="dashboard-command-card">
        <div className="section-title"><h2>المراجعة والتنبيهات</h2><Link to="/notifications">الإشعارات</Link></div>
        <div className="dashboard-mini-grid">
          <article>
            <StatusPill tone="teal">بطاقات</StatusPill>
            <strong>{dueFlashcards} بطاقة للمراجعة اليوم</strong>
            <Link to="/flashcards">راجع الآن</Link>
          </article>
          <article>
            <StatusPill tone="gold">اختبار</StatusPill>
            <strong>{nextQuiz}</strong>
            <Link to="/quiz">ابدأ الاختبار</Link>
          </article>
          <article>
            <StatusPill tone={unreadCount ? 'coral' : 'blue'}>إشعارات</StatusPill>
            <strong>{unreadCount ? `${unreadCount} تنبيهات غير مقروءة` : 'لا توجد تنبيهات عاجلة'}</strong>
            <Link to="/notifications">افتح المركز</Link>
          </article>
        </div>
      </Card>

      <Card className="wide-card">
        <div className="section-title"><h2>أدوات سريعة</h2><span>انتقل مباشرة إلى طريقة التعلم المناسبة.</span></div>
        <div className="quick-grid">
          {quickActions.map((action) => (
            <Link key={action.label} to={action.to} className={`quick-action tone-${action.tone}`}>
              <span>{action.icon}</span>
              {action.label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
};

// Refactored StudyPlanPage imported from src/pages/StudyPlanPage

const EquationBalancerPage = () => {
  const [input, setInput] = useState('H2 + O2 -> H2O');
  const [result, setResult] = useState<BalanceResult | null>(null);
  const [loading, setLoading] = useState(false);

  const balance = async () => {
    setLoading(true);
    const next = await labApi.balanceEquation(input);
    setResult(next);
    setLoading(false);
  };

  const flaskColor = loading
    ? 'violet'
    : result
      ? (result.explanation.some((step) => step.toLowerCase().includes('balanced') || step.toLowerCase().includes('count') || step.toLowerCase().includes('neutralization')) ? 'green' : 'coral')
      : 'green';
  const flaskLevel = loading ? 45 : result ? 75 : 60;
  const flaskBubbling = loading || !!result;

  return (
    <div className="page-stack">
      <PageHeader eyebrow="المختبر" title="موازن المعادلات" subtitle="تدرب على موازنة معادلات كيمياء الصف التاسع." />
      <div className="lab-split-container">
        <Card className="lab-tool">
          <label>
            المعادلة
            <input value={input} onChange={(event) => setInput(event.target.value)} dir="ltr" aria-label="إدخال معادلة كيميائية" />
          </label>
          <div className="button-row">
            <Button onClick={balance} disabled={loading}>{loading ? 'جار الموازنة...' : 'وازن'}</Button>
            <Link className="ed-btn ed-btn-secondary" to={`/ask-ai?question=${encodeURIComponent(`اشرح كيف نوازن المعادلة ${input}`)}`}>اشرح بالذكاء</Link>
          </div>
          {result && (
            <div className="equation-result">
              <p>المعادلة الموزونة</p>
              <strong dir="ltr">{result.balanced}</strong>
              <ol>
                {result.explanation.map((step) => <li key={step}>{step}</li>)}
              </ol>
            </div>
          )}
        </Card>
        
        <Card className="reaction-chamber-card">
          <h3>حجرة التفاعل</h3>
          <ChemistryFlask color={flaskColor} level={flaskLevel} bubbling={flaskBubbling} size={150} />
          <p>
            {loading ? 'التفاعل قيد المعالجة...' : result ? 'اكتمل التفاعل' : 'بانتظار صيغة كيميائية'}
          </p>
        </Card>
      </div>
    </div>
  );
};

const ProfilePage = ({
  user,
  preferences,
  setPreferences,
}: {
  user: UserProfile;
  preferences: UserPreferences;
  setPreferences: (preferences: UserPreferences) => void;
}) => {
  const [status, setStatus] = useState('');
  const [notifPrefs, setNotifPrefs] = useState({
    exam_reminders_enabled: true,
    lesson_reminders_enabled: true,
    reminder_time_local: '08:00',
  });

  useEffect(() => {
    notificationsApi.getPreferences().then(setNotifPrefs).catch(() => {});
  }, []);

  const saveNotifPref = async (updates: Partial<typeof notifPrefs>) => {
    try {
      const updated = await notificationsApi.updatePreferences(updates);
      setNotifPrefs(updated);
      setStatus('تم تحديث إعدادات الإشعارات.');
      setTimeout(() => setStatus(''), 3000);
      
      // Auto-rebuild user reminders on preference change so they use the new time/switches
      await notificationsApi.rebuildReminders();
    } catch {
      setStatus('فشل في مزامنة إعدادات الإشعارات مع الخادم.');
      setTimeout(() => setStatus(''), 3000);
    }
  };

  const updatePreferences = async (next: UserPreferences) => {
    setPreferences(next);
    savePreferences(next);
    try {
      await userApi.updatePreferences(next);
      setStatus('تم حفظ التفضيلات.');
    } catch {
      setStatus('تم حفظ التفضيلات محلياً. تعذر الوصول إلى الخلفية.');
    }
  };

  const updatePreference = async <K extends keyof UserPreferences>(field: K, value: UserPreferences[K]) => {
    const next = { ...preferences, [field]: value } as UserPreferences;
    await updatePreferences(next);
  };

  const updateTeachingLevel = async (value: TeachingLevel) => {
    await updatePreferences({
      ...preferences,
      teachingLevel: value,
      teachingStyle: legacyTeachingStyle(value, preferences.explanationMethod),
    });
  };

  const updateExplanationMethod = async (value: ExplanationMethod) => {
    await updatePreferences({
      ...preferences,
      explanationMethod: value,
      teachingStyle: legacyTeachingStyle(preferences.teachingLevel, value),
    });
  };

  const updateLearningModes = async (value: LearningMode[]) => {
    const normalizedLearningModes = normalizeModes(value);
    await updatePreferences({
      ...preferences,
      learningModes: normalizedLearningModes,
      answerFormat: primaryAnswerFormat(normalizedLearningModes),
    });
  };

  const toggleInterest = async (value: StudentInterest) => {
    const nextInterests = preferences.studentInterests.includes(value)
      ? preferences.studentInterests.filter((item) => item !== value)
      : [...preferences.studentInterests, value];
    await updatePreferences({
      ...preferences,
      studentInterests: nextInterests,
      interests: nextInterests,
    });
  };

  return (
    <div className="profile-grid">
      <Card className="profile-card">
        <div className="avatar">{(user.first_name || user.name || 'E').slice(0, 1)}</div>
        <h1>{user.first_name || user.name}</h1>
        <p>كيمياء الصف التاسع · المستوى {user.level || 4}</p>
        <ProgressBar value={65} tone="blue" />
      </Card>
      <Card>
        <div className="section-title"><h2>التفضيلات</h2></div>
        {status && <StatusPill tone="teal">{status}</StatusPill>}
        <div className="settings-list">
          <label>
            مستوى الشرح
            <select value={preferences.teachingLevel} onChange={(event) => void updateTeachingLevel(event.target.value as TeachingLevel)}>
              {teachingLevelLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label>
            طريقة الشرح
            <select value={preferences.explanationMethod} onChange={(event) => void updateExplanationMethod(event.target.value as ExplanationMethod)}>
              {explanationMethodLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <div className="preference-stack">
            <span>أنماط التعلم</span>
            <LearningModeSelector value={preferences.learningModes} onChange={(modes) => void updateLearningModes(modes)} />
          </div>
          <div className="preference-stack">
            <span>اهتمامات الطالب</span>
            <div className="interest-grid compact">
              {studentInterestOptions.map((interest) => (
                <button
                  key={interest.value}
                  type="button"
                  className={preferences.studentInterests.includes(interest.value) ? 'interest active' : 'interest'}
                  onClick={() => void toggleInterest(interest.value)}
                >
                  <span>{interest.icon}</span>
                  <strong>{interest.label}</strong>
                </button>
              ))}
            </div>
          </div>
          <label>
            اللغة
            <select value={preferences.language} onChange={(event) => void updatePreference('language', event.target.value as UserPreferences['language'])}>
              <option value="ar">العربية</option>
              <option value="en">English</option>
            </select>
          </label>

          {/* User notifications preferences */}
          <div className="preference-stack" style={{ marginTop: '20px', borderTop: '1px solid var(--bg4)', paddingTop: '20px' }}>
            <span style={{ fontWeight: 'bold', fontSize: '0.9rem', marginBottom: '12px', display: 'block' }}>تفضيلات التنبيهات وإشعارات المذاكرة</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontSize: '0.85rem' }}>
                <input
                  type="checkbox"
                  checked={notifPrefs.exam_reminders_enabled}
                  onChange={(e) => void saveNotifPref({ exam_reminders_enabled: e.target.checked })}
                  style={{ width: '16px', height: '16px' }}
                />
                تنبيهات مواعيد الامتحانات (7 أيام، 3 أيام، يوم، ساعتان قبل الامتحان)
              </label>
              
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontSize: '0.85rem' }}>
                <input
                  type="checkbox"
                  checked={notifPrefs.lesson_reminders_enabled}
                  onChange={(e) => void saveNotifPref({ lesson_reminders_enabled: e.target.checked })}
                  style={{ width: '16px', height: '16px' }}
                />
                تنبيهات خطة الدروس والواجبات اليومية (يوم قبل الدرس، 30 دقيقة قبل المذاكرة)
              </label>

              <label style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem', marginTop: '6px' }}>
                وقت التنبيه اليومي المفضل
                <select
                  value={notifPrefs.reminder_time_local}
                  onChange={(e) => void saveNotifPref({ reminder_time_local: e.target.value })}
                  style={{ width: '130px', padding: '6px', borderRadius: '6px', background: 'var(--bg3)', border: '1px solid var(--bg5)', color: 'var(--t1)' }}
                >
                  {Array.from({ length: 24 }).map((_, h) => {
                    const timeStr = `${String(h).padStart(2, '0')}:00`;
                    return (
                      <option key={timeStr} value={timeStr}>
                        {timeStr}
                      </option>
                    );
                  })}
                </select>
              </label>
            </div>
          </div>
        </div>
      </Card>
      <Card className="wide-card">
        <div className="section-title"><h2>التقدم</h2></div>
        <div className="stats-row inline">
          <article className="stat-tile"><strong>{user.streak_days || 5}</strong><span>استمرارية</span></article>
          <article className="stat-tile"><strong>{user.xp || 1240}</strong><span>XP</span></article>
          <article className="stat-tile"><strong>8</strong><span>شارات</span></article>
        </div>
      </Card>
    </div>
  );
};

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [auth, setAuth] = useState<AuthState>({
    user: null,
    preferences: loadPreferences(),
    booting: Boolean(getToken()),
  });

  const refreshUser = async () => {
    if (!getToken()) {
      setAuth((current) => ({ ...current, booting: false }));
      return;
    }
    try {
      const user = await authApi.me();
      setAuth((current) => {
        const preferences = preferencesFromUser(user, current.preferences);
        savePreferences(preferences);
        return { ...current, user, preferences, booting: false };
      });
    } catch {
      clearToken();
      setAuth((current) => ({ ...current, user: null, booting: false }));
    }
  };

  useEffect(() => {
    if (!getToken()) return;
    let cancelled = false;
    const loadUser = async () => {
      try {
        const user = await authApi.me();
        if (!cancelled) {
          setAuth((current) => {
            const preferences = preferencesFromUser(user, current.preferences);
            savePreferences(preferences);
            return { ...current, user, preferences, booting: false };
          });
        }
      } catch {
        clearToken();
        if (!cancelled) {
          setAuth((current) => ({ ...current, user: null, booting: false }));
        }
      }
    };
    void loadUser();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handleAuthExpired = () => {
      clearToken();
      setAuth((current) => ({ ...current, user: null, booting: false }));

      const currentPath = `${location.pathname}${location.search}`;
      if (location.pathname !== '/login') {
        navigate('/login', {
          replace: true,
          state: { from: currentPath, sessionExpired: true },
        });
      }
    };

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, [location.pathname, location.search, navigate]);

  const updatePreferences = (preferences: UserPreferences) => {
    savePreferences(preferences);
    setAuth((current) => ({ ...current, preferences }));
  };

  const logout = () => {
    clearToken();
    setAuth((current) => ({ ...current, user: null }));
  };

  const userName = auth.user?.first_name || auth.user?.name || 'طالب';

  return (
    <div dir="rtl" lang="ar">
      <MoleculeBackground />
      <Suspense fallback={<main className="route-loading"><LoadingSkeleton rows={5} /></main>}>
        <Routes>
          <Route path="/login" element={<GuestOnly user={auth.user}><LoginPage onLogin={refreshUser} /></GuestOnly>} />
          <Route path="/register" element={<GuestOnly user={auth.user}><RegisterPage onRegistered={refreshUser} /></GuestOnly>} />
          <Route
            path="/onboarding/interests"
            element={
              auth.user ? (
                <OnboardingPage preferences={auth.preferences} onSave={updatePreferences} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route path="/" element={auth.user ? <AppShell userName={userName} onLogout={logout} /> : <ProtectedRoute user={auth.user} booting={auth.booting} />}>
            <Route index element={auth.user && <DashboardPage user={auth.user} preferences={auth.preferences} />} />
            <Route path="dashboard" element={<Navigate to="/" replace />} />
            <Route path="lessons" element={<LessonsPage />} />
            <Route path="lessons/:lessonId" element={<LessonDetailPage />} />
            <Route path="study-session/:lessonId" element={<StudySessionPage preferences={auth.preferences} />} />
            <Route path="book-search" element={<RagSearchPage />} />
            <Route path="rag-search" element={<RagSearchPage />} />
            <Route path="quiz" element={<QuizzesPage />} />
            <Route path="quizzes" element={<QuizzesPage />} />
            <Route path="study-plan" element={<StudyPlanPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="notifications/settings" element={<NotificationSettingsPage />} />
            <Route path="flashcards" element={<FlashcardsPage />} />
            <Route path="lab" element={<LabPage />} />
            <Route path="homework" element={<HomeworkPage />} />
            <Route path="guided-lab" element={<GuidedLabPage />} />
            <Route path="guided-lab/session/:sessionId" element={<SolverSessionPage />} />
            <Route path="lab/equation-balancer" element={<EquationBalancerPage />} />
            <Route path="admin/rag" element={<RagAdminPage />} />
            <Route path="admin/rag/reembed" element={<RagReembedPage />} />
            <Route path="admin/rag/evaluation" element={<RagEvaluationPage />} />
            <Route path="admin/rag/query-logs" element={<RagQueryLogsPage />} />
            <Route path="admin/sources" element={<SourcesPage />} />
            <Route path="ask-ai" element={<AskAiPage preferences={auth.preferences} setPreferences={updatePreferences} />} />
            <Route path="profile" element={auth.user && <ProfilePage user={auth.user} preferences={auth.preferences} setPreferences={updatePreferences} />} />
          </Route>
          <Route path="*" element={<Navigate to={auth.user ? '/' : '/login'} replace />} />
        </Routes>
      </Suspense>
    </div>
  );
}

export default App;
