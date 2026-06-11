import { useEffect, useMemo, useState, lazy, Suspense } from 'react';
import type { FormEvent, ReactElement } from 'react';
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import {
  aiApi,
  authApi,
  labApi,
  studyPlanApi,
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
  ChatMessage,
  ErrorBanner,
  LearningModeSelector,
  LessonCard,
  LoadingSkeleton,
  PageHeader,
  ProgressBar,
  RecommendationCard,
  StatusPill,
  StudyMissionCard,
} from './components/DesignSystem';
import { clearToken, getToken, loadPreferences, savePreferences } from './lib/storage';
import { LessonsPage, RagSearchPage } from './pages/LearningPages';

const QuizzesPage = lazy(() => import('./pages/QuizzesPage').then(module => ({ default: module.QuizzesPage })));
const FlashcardsPage = lazy(() => import('./pages/FlashcardsPage').then(module => ({ default: module.FlashcardsPage })));
const LessonDetailPage = lazy(() => import('./pages/LessonDetailPage').then(module => ({ default: module.LessonDetailPage })));
import type {
  AiAskResponse,
  AiAskRequest,
  AnswerFormat,
  BalanceResult,
  ExplanationMethod,
  InterestCategory,
  LearningMode,
  StudentInterest,
  StudyPlan,
  TeachingLevel,
  UserPreferences,
  UserProfile,
} from './types';

type AnswerScope = NonNullable<AiAskRequest['answer_scope']>;

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
    video: 'Reel',
    reel: 'Reel',
    interactive: 'تفاعلي',
    quiz: 'اختبار',
    flashcards: 'بطاقات',
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

const answerScopeLabels: Array<{ value: AnswerScope; label: string }> = [
  { value: 'auto', label: 'تلقائي' },
  { value: 'book_only', label: 'من الكتاب فقط' },
  { value: 'tutor_general', label: 'شرح عام عند الحاجة' },
];

const suggestedChemistryQuestions = [
  'ما هو الماء؟',
  'ما هي الحموض؟',
  'لماذا نضيف الحمض إلى الماء وليس العكس؟',
  'ما هو التركيز المولي؟',
  'محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي؟',
];

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
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
};

const LoginPage = ({ onLogin }: { onLogin: () => Promise<void> }) => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
      navigate('/dashboard', { replace: true });
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
      navigate('/dashboard', { replace: true });
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
  const quickActions = [
    { to: '/ask-ai', label: 'اسأل', tone: 'blue' },
    { to: '/quizzes', label: 'اختبار', tone: 'gold' },
    { to: '/ask-ai', label: 'Reel', tone: 'purple' },
    { to: '/flashcards', label: 'بطاقات', tone: 'teal' },
    { to: '/lab/equation-balancer', label: 'موازنة', tone: 'coral' },
  ];

  return (
    <div className="dashboard-grid">
      <section className="hero-card">
        <p className="eyebrow">مختبر اليوم</p>
        <h1>{user.first_name || user.name || 'كيميائي'}</h1>
        <div className="badge-row">
          <StatusPill tone="gold">{user.streak_days || 5} أيام متتالية</StatusPill>
          <StatusPill tone="blue">{user.xp || 1240} XP</StatusPill>
          <StatusPill tone="teal">المستوى {user.level || 4}</StatusPill>
        </div>
      </section>

      <StudyMissionCard
        title="اشرح الحموض من مصادر الكتاب"
        meta={`18 دقيقة · ${preferenceLabel(preferences.teachingLevel)} · ${preferenceLabel(preferences.explanationMethod)}`}
        to="/ask-ai"
      />

      <div className="stats-row">
        <Card><strong>62%</strong><span>خطة الدراسة</span></Card>
        <Card><strong>14</strong><span>بطاقة للمراجعة</span></Card>
        <Card><strong>9 أيام</strong><span>حتى الاختبار</span></Card>
      </div>

      <Card className="wide-card">
        <div className="section-title">
          <h2>توصيات الذكاء</h2>
          <Link to="/study-plan">عرض الخطة</Link>
        </div>
        <div className="recommendation-grid">
          <RecommendationCard tone="coral" label="نقطة ضعف" title="راجع الحموض الضعيفة" description="اطلب جدول مقارنة بسيطاً." />
          <RecommendationCard tone="teal" label="تدريب" title="وازن 3 معادلات" description="استخدم المختبر قبل الاختبار." />
          <RecommendationCard tone="purple" label="مراجعة" title="اقلب بطاقات الحموض والأسس" description="جلسة تكرار قصيرة." />
        </div>
      </Card>

      <Card className="wide-card">
        <div className="section-title"><h2>إجراءات سريعة</h2></div>
        <div className="quick-grid">
          {quickActions.map((action) => (
            <Link key={action.label} to={action.to} className={`quick-action tone-${action.tone}`}>
              <span>{action.label.slice(0, 2)}</span>
              {action.label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
};

const StudyPlanPage = () => {
  const [plan, setPlan] = useState<StudyPlan | null>(null);

  useEffect(() => {
    studyPlanApi.getStudyPlan().then(setPlan);
  }, []);

  if (!plan) {
    return <LoadingSkeleton rows={6} />;
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="خطة الدراسة"
        title="خارطة كيمياء الصف التاسع"
        subtitle={`الدرس الحالي: ${plan.currentLesson.title}`}
      />
      <Card>
        <div className="section-title"><h2>موضوعات تحتاج مراجعة</h2></div>
        <div className="badge-row">
          {plan.weakTopics.map((topic) => <StatusPill key={topic} tone="coral">{topic}</StatusPill>)}
        </div>
      </Card>
      <div className="chapter-list">
        {plan.chapters.map((chapter) => (
          <Card key={chapter.id} className="chapter-card">
            <div className="chapter-head">
              <div><h2>{chapter.title}</h2><p>{chapter.subtitle}</p></div>
              <StatusPill tone={chapter.color}>{chapter.progress}%</StatusPill>
            </div>
            <ProgressBar value={chapter.progress} tone={chapter.color} />
            <div className="lesson-list">
              {chapter.lessons.map((lesson) => <LessonCard key={lesson.id} lesson={lesson} />)}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

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
            <input value={input} onChange={(event) => setInput(event.target.value)} dir="ltr" aria-label="Equation input" />
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

interface ChatItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: AiAskResponse;
  question?: string;
}

const AskAiPage = ({ preferences, setPreferences }: { preferences: UserPreferences; setPreferences: (preferences: UserPreferences) => void }) => {
  const location = useLocation();
  const initialQuestion = useMemo(() => new URLSearchParams(location.search).get('question') || '', [location.search]);
  const [question, setQuestion] = useState(initialQuestion);
  const [teachingLevel, setTeachingLevel] = useState<TeachingLevel>(preferences.teachingLevel);
  const [explanationMethod, setExplanationMethod] = useState<ExplanationMethod>(preferences.explanationMethod);
  const [learningModes, setLearningModes] = useState<LearningMode[]>(preferences.learningModes);
  const [answerScope, setAnswerScope] = useState<AnswerScope>('auto');
  const [conversationId] = useState(() => `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`);
  const [messages, setMessages] = useState<ChatItem[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'اسألني من كتاب الكيمياء للصف التاسع. سأعرض المصادر والصفحات عندما يجدها نظام RAG.',
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const ask = async (override?: string, action?: AiAskRequest['action']) => {
    const text = (override ?? question).trim();
    if (!text || loading) return;
    const previousAssistant = [...messages].reverse().find((item) => item.role === 'assistant' && item.response);
    const previousUser = [...messages].reverse().find((item) => item.role === 'user');
    const parentMessageId = action ? previousAssistant?.id : undefined;
    setQuestion('');
    setError('');
    setLoading(true);
    setMessages((current) => [...current, { id: `user-${Date.now()}`, role: 'user', content: text }]);
    try {
      const normalizedLearningModes = normalizeModes(learningModes);
      const response = await aiApi.ask({
        conversation_id: conversationId,
        parent_message_id: parentMessageId,
        question: text,
        subject: preferences.subject,
        grade: preferences.grade,
        answer_format: primaryAnswerFormat(normalizedLearningModes),
        teaching_style: legacyTeachingStyle(teachingLevel, explanationMethod),
        teaching_level: teachingLevel,
        explanation_method: explanationMethod,
        learning_modes: normalizedLearningModes,
        student_interests: preferences.studentInterests,
        interests: preferences.interests,
        language: preferences.language,
        answer_scope: answerScope,
        action,
        previous_question: previousAssistant?.question || previousUser?.content,
        previous_answer: previousAssistant?.response?.answer,
        previous_sources: previousAssistant?.response?.sources,
        previous_selected_chunks: previousAssistant?.response?.diagnostics?.selected_context as Record<string, unknown>[] | undefined,
      });
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.answer,
          response,
          question: text,
        },
      ]);
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر إرسال السؤال إلى خدمة الذكاء.'));
    } finally {
      setLoading(false);
    }
  };

  const saveLearningModes = (nextModes: LearningMode[]) => {
    const normalizedLearningModes = normalizeModes(nextModes);
    setLearningModes(normalizedLearningModes);
    const next = {
      ...preferences,
      learningModes: normalizedLearningModes,
      answerFormat: primaryAnswerFormat(normalizedLearningModes),
    };
    setPreferences(next);
    savePreferences(next);
  };

  const saveTeachingLevel = (nextLevel: TeachingLevel) => {
    setTeachingLevel(nextLevel);
    const next = {
      ...preferences,
      teachingLevel: nextLevel,
      teachingStyle: legacyTeachingStyle(nextLevel, explanationMethod),
    };
    setPreferences(next);
    savePreferences(next);
  };

  const saveExplanationMethod = (nextMethod: ExplanationMethod) => {
    setExplanationMethod(nextMethod);
    const next = {
      ...preferences,
      explanationMethod: nextMethod,
      teachingStyle: legacyTeachingStyle(teachingLevel, nextMethod),
    };
    setPreferences(next);
    savePreferences(next);
  };

  const compactPreferenceLabel = [
    preferenceLabel(teachingLevel),
    preferenceLabel(explanationMethod),
    learningModes.map(preferenceLabel).join(' + '),
  ].join(' · ');

  return (
    <div className="ask-layout">
      <PageHeader eyebrow="اسأل الذكاء" title="معلّم الكيمياء RAG" subtitle={`إجابات موثقة بصفحات من كتاب الكيمياء. ${compactPreferenceLabel}`} />
      <Card className="chat-panel">
        <div className="chat-toolbar">
          <label>
            مستوى الشرح
            <select value={teachingLevel} onChange={(event) => saveTeachingLevel(event.target.value as TeachingLevel)}>
              {teachingLevelLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label>
            طريقة الشرح
            <select value={explanationMethod} onChange={(event) => saveExplanationMethod(event.target.value as ExplanationMethod)}>
              {explanationMethodLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label>
            نطاق الإجابة
            <select value={answerScope} onChange={(event) => setAnswerScope(event.target.value as AnswerScope)}>
              {answerScopeLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <LearningModeSelector value={learningModes} onChange={saveLearningModes} />
        </div>
        <div className="chat-feed">
          {messages.map((message) => (
            <ChatMessage key={message.id} role={message.role} content={message.content} response={message.response} />
          ))}
          {loading && <div className="typing-dots" aria-label="AI is typing"><span /><span /><span /></div>}
        </div>
        <div className="suggestion-row chat-suggestions" aria-label="أسئلة مقترحة">
          {suggestedChemistryQuestions.map((item) => (
            <button key={item} type="button" onClick={() => void ask(item)} disabled={loading}>
              {item}
            </button>
          ))}
        </div>
        {error && <ErrorBanner message={error} onRetry={() => ask(messages.findLast((item) => item.role === 'user')?.content)} />}
        <div className="chat-actions">
          <Button
            variant="secondary"
            onClick={() => ask('اشرح هذا بطريقة أبسط مع مثال واضح.', 'rephrase_previous')}
            disabled={loading}
          >
            أعد الشرح
          </Button>
          <Button variant="ghost" onClick={() => setError('تم تسجيل أنك فهمت هذه الإجابة في الجلسة الحالية.')}>فهمت</Button>
        </div>
        <form className="ask-input-row" onSubmit={(event) => { event.preventDefault(); void ask(); }}>
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="اسأل من كتاب الكيمياء..." aria-label="سؤال للذكاء الاصطناعي" />
          <Button type="submit" disabled={loading || !question.trim()}>{loading ? '...' : 'إرسال'}</Button>
        </form>
      </Card>
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
          <Route element={auth.user ? <AppShell userName={userName} onLogout={logout} /> : <ProtectedRoute user={auth.user} booting={auth.booting} />}>
            <Route path="/dashboard" element={auth.user && <DashboardPage user={auth.user} preferences={auth.preferences} />} />
            <Route path="/lessons" element={<LessonsPage />} />
            <Route path="/lessons/:lessonId" element={<LessonDetailPage />} />
            <Route path="/rag-search" element={<RagSearchPage />} />
            <Route path="/quizzes" element={<QuizzesPage />} />
            <Route path="/study-plan" element={<StudyPlanPage />} />
            <Route path="/flashcards" element={<FlashcardsPage />} />
            <Route path="/lab/equation-balancer" element={<EquationBalancerPage />} />
            <Route path="/ask-ai" element={<AskAiPage preferences={auth.preferences} setPreferences={updatePreferences} />} />
            <Route path="/profile" element={auth.user && <ProfilePage user={auth.user} preferences={auth.preferences} setPreferences={updatePreferences} />} />
          </Route>
          <Route path="/" element={<Navigate to={auth.user ? '/dashboard' : '/login'} replace />} />
          <Route path="*" element={<Navigate to={auth.user ? '/dashboard' : '/login'} replace />} />
        </Routes>
      </Suspense>
    </div>
  );
}

export default App;
