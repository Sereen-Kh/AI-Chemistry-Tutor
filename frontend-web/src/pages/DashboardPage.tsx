import { useEffect, useState } from 'react';
import {
  Bell,
  BookOpen,
  BrainCircuit,
  CalendarDays,
  ClipboardCheck,
  FlaskConical,
  Layers3,
  MessageCircleQuestion,
  RefreshCw,
  Sparkles,
  Target,
  Timer,
  Trophy,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';

import { dashboardApi, toErrorMessage } from '../api';
import type { DashboardResponse } from '../api/dashboardApi';
import {
  Card,
  ErrorBanner,
  LoadingSkeleton,
  PageHeader,
  ProgressBar,
  StatusPill,
} from '../components/DesignSystem';

const lessonStatusLabels: Record<string, string> = {
  not_started: 'لم يبدأ',
  in_progress: 'قيد الدراسة',
  completed: 'مكتمل',
};

const evidenceLabels: Record<string, string> = {
  limited: 'دليل أولي',
  established: 'دليل كافٍ',
};

const missionIcons: Record<DashboardResponse['primary_mission']['kind'], LucideIcon> = {
  overdue_lesson: Timer,
  today_lesson: Target,
  due_flashcards: Layers3,
  next_lesson: BookOpen,
  create_plan: CalendarDays,
};

const quickToolIcons: Record<string, LucideIcon> = {
  '/ask-ai': MessageCircleQuestion,
  '/guided-lab': FlaskConical,
  '/quiz': ClipboardCheck,
  '/quizzes': ClipboardCheck,
  '/flashcards': Layers3,
  '/homework': BookOpen,
};

const ProgressCard = ({
  label,
  completed,
  total,
  percent,
  emptyMessage,
  icon: Icon,
}: {
  label: string;
  completed: number;
  total: number;
  percent: number | null;
  emptyMessage: string;
  icon: LucideIcon;
}) => (
  <Card className="dashboard-progress-card">
    <div className="dashboard-card-heading">
      <span className="dashboard-icon"><Icon aria-hidden="true" size={21} /></span>
      <h2>{label}</h2>
    </div>
    {percent === null ? (
      <p className="dashboard-empty-copy">{emptyMessage}</p>
    ) : (
      <>
        <div className="dashboard-progress-value">
          <strong>{percent}%</strong>
          <span>{completed} من {total} دروس مكتملة</span>
        </div>
        <ProgressBar value={percent} tone="teal" />
      </>
    )}
  </Card>
);

const DashboardSkeleton = () => (
  <div className="dashboard-v1" aria-label="جار تحميل لوحة التعلم">
    <Card className="dashboard-v1-hero"><LoadingSkeleton rows={3} /></Card>
    <div className="dashboard-progress-grid">
      <Card><LoadingSkeleton rows={3} /></Card>
      <Card><LoadingSkeleton rows={3} /></Card>
    </div>
    <Card><LoadingSkeleton rows={4} /></Card>
  </div>
);

export const DashboardPage = () => {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState('');
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    let active = true;
    dashboardApi.getDashboard()
      .then((response) => {
        if (!active) return;
        setDashboard(response);
        setError('');
      })
      .catch((requestError) => {
        if (!active) return;
        setDashboard(null);
        setError(toErrorMessage(requestError, 'تعذر تحميل لوحة التعلم. تحقق من الاتصال ثم أعد المحاولة.'));
      });
    return () => {
      active = false;
    };
  }, [requestVersion]);

  const retry = () => {
    setDashboard(null);
    setError('');
    setRequestVersion((value) => value + 1);
  };

  if (!dashboard && !error) return <DashboardSkeleton />;

  if (!dashboard) {
    return (
      <div className="page-stack dashboard-v1">
        <PageHeader
          eyebrow="لوحة التعلم"
          title="تعذر تحميل تقدمك"
          subtitle="لن نعرض قيماً تجريبية بدلاً من بياناتك الحقيقية."
        />
        <Card className="dashboard-error-card">
          <ErrorBanner message={error} onRetry={retry} />
        </Card>
      </div>
    );
  }

  const mission = dashboard.primary_mission;
  const MissionIcon = missionIcons[mission.kind];
  const continueLesson = dashboard.continue_lesson;
  const activePlan = dashboard.active_plan_progress;
  const examDays = dashboard.study_plan?.days_to_exam;

  return (
    <div className="dashboard-v1">
      <section className="dashboard-v1-hero">
        <div>
          <p className="eyebrow">مركز تعلم اليوم</p>
          <h1>أهلاً {dashboard.student_name}</h1>
          <p>بيانات التقدم هنا مبنية على دروسك المجدولة ونتائج اختباراتك الفعلية.</p>
        </div>
        <div className="dashboard-identity-stats" aria-label="ملخص حساب الطالب">
          <span><Trophy aria-hidden="true" size={18} /> {dashboard.xp} XP إجمالي</span>
          <span><Sparkles aria-hidden="true" size={18} /> المستوى {dashboard.level}</span>
          <span><RefreshCw aria-hidden="true" size={18} /> {dashboard.streak_days} أيام متتالية</span>
        </div>
      </section>

      <section className="dashboard-progress-grid" aria-label="ملخص التقدم">
        <ProgressCard
          label="تقدم المنهج"
          completed={dashboard.curriculum_progress.completed_lessons}
          total={dashboard.curriculum_progress.total_lessons}
          percent={dashboard.curriculum_progress.percent}
          emptyMessage="لا توجد دروس منهج متاحة لحساب التقدم."
          icon={BookOpen}
        />
        <ProgressCard
          label="تقدم الخطة"
          completed={activePlan?.completed_lessons ?? 0}
          total={activePlan?.total_scheduled_lessons ?? 0}
          percent={activePlan?.percent ?? null}
          emptyMessage="لم تُنشئ خطة تحتوي على دروس مجدولة بعد."
          icon={CalendarDays}
        />
      </section>

      <Card className={`dashboard-mission-v1 mission-${mission.kind}`}>
        <span className="dashboard-mission-icon"><MissionIcon aria-hidden="true" size={26} /></span>
        <div>
          <p className="eyebrow">المهمة الأساسية</p>
          <h2>{mission.title_ar}</h2>
          <p>{mission.description_ar}</p>
        </div>
        <Link className="ed-btn ed-btn-primary" to={mission.action_url}>{mission.action_label_ar}</Link>
      </Card>

      <section className="dashboard-content-grid">
        <Card className="dashboard-command-card">
          <div className="section-title">
            <h2>متابعة التعلم</h2>
            <Link to="/lessons">كل الدروس</Link>
          </div>
          {continueLesson ? (
            <div className="dashboard-continue-v1">
              <StatusPill tone={continueLesson.status === 'in_progress' ? 'teal' : 'blue'}>
                {lessonStatusLabels[continueLesson.status] ?? continueLesson.status}
              </StatusPill>
              <h3>{continueLesson.title_ar}</h3>
              {continueLesson.chapter_title_ar && <p>{continueLesson.chapter_title_ar}</p>}
              <span><Timer aria-hidden="true" size={17} /> {continueLesson.duration_min} دقيقة تقريباً</span>
              <div className="guided-card-actions">
                <Link className="ed-btn ed-btn-primary" to={`/study-session/${continueLesson.id}`}>ابدأ الدرس</Link>
                <Link className="ed-btn ed-btn-secondary" to={`/ask-ai?lessonId=${continueLesson.id}`}>اسأل عن الدرس</Link>
              </div>
            </div>
          ) : (
            <div className="dashboard-neutral-state">
              <BookOpen aria-hidden="true" size={24} />
              <strong>لا يوجد درس متاح للمتابعة حالياً.</strong>
            </div>
          )}
        </Card>

        <Card className="dashboard-command-card">
          <div className="section-title">
            <h2>نقاط الضعف</h2>
            <Link to="/quiz">الاختبارات</Link>
          </div>
          {dashboard.weak_topics_state === 'insufficient_evidence' ? (
            <div className="dashboard-neutral-state">
              <BrainCircuit aria-hidden="true" size={24} />
              <strong>أكمل اختباراً قصيراً لنحدد نقاط الضعف بدقة.</strong>
              <span>نحتاج إلى خمسة إجابات على الأقل في الموضوع الواحد.</span>
            </div>
          ) : dashboard.weak_topics.length === 0 ? (
            <div className="dashboard-neutral-state">
              <BrainCircuit aria-hidden="true" size={24} />
              <strong>لا تظهر نقطة ضعف وفق نتائج الاختبارات الحالية.</strong>
            </div>
          ) : (
            <div className="dashboard-weak-list">
              {dashboard.weak_topics.map((topic) => (
                <article key={topic.topic_id}>
                  <div>
                    <StatusPill tone={topic.accuracy_percent < 50 ? 'coral' : 'gold'}>
                      دقة {Math.round(topic.accuracy_percent)}%
                    </StatusPill>
                    <StatusPill tone="blue">{evidenceLabels[topic.evidence_level]}</StatusPill>
                  </div>
                  <h3>{topic.title_ar}</h3>
                  <p>{topic.answered_questions} إجابات عبر {topic.attempt_count} محاولات</p>
                  <Link to={topic.action_url}>تدرّب الآن</Link>
                </article>
              ))}
            </div>
          )}
        </Card>
      </section>

      <Card className="dashboard-review-card">
        <div className="section-title">
          <h2>المراجعة والتنبيهات</h2>
          <Link to="/notifications">مركز الإشعارات</Link>
        </div>
        <div className="dashboard-mini-grid">
          <article>
            <Layers3 aria-hidden="true" size={21} />
            <strong>{dashboard.due_flashcards.due_count} بطاقة مستحقة</strong>
            <span>{dashboard.due_flashcards.due_count ? 'جاهزة للمراجعة اليوم' : 'لا توجد بطاقات مستحقة اليوم'}</span>
            <Link to="/flashcards">فتح البطاقات</Link>
          </article>
          <article>
            <ClipboardCheck aria-hidden="true" size={21} />
            <strong>{dashboard.next_quiz?.title ?? 'لا توجد محاولة اختبار سابقة'}</strong>
            <span>{dashboard.next_quiz ? 'راجع نتيجتك الأخيرة أو ابدأ محاولة جديدة' : 'ابدأ اختباراً لبناء دليل على مستوى إتقانك'}</span>
            <Link to="/quiz">فتح الاختبارات</Link>
          </article>
          <article>
            <Bell aria-hidden="true" size={21} />
            <strong>{dashboard.notifications.unread_count} إشعار غير مقروء</strong>
            <span>{dashboard.notifications.unread_count ? 'لديك تحديثات تحتاج الانتباه' : 'لا توجد تنبيهات عاجلة'}</span>
            <Link to="/notifications">فتح المركز</Link>
          </article>
          {typeof examDays === 'number' && (
            <article>
              <CalendarDays aria-hidden="true" size={21} />
              <strong>{examDays >= 0 ? `${examDays} أيام حتى الاختبار` : 'انتهى موعد الاختبار'}</strong>
              <span>الموعد مرتبط بخطة الدراسة النشطة</span>
              <Link to="/study-plan">عرض الخطة</Link>
            </article>
          )}
        </div>
      </Card>

      <Card className="dashboard-tools-card">
        <div className="section-title">
          <h2>أدوات سريعة</h2>
          <span>اختر إجراءً مرتبطاً بتعلمك.</span>
        </div>
        <div className="quick-grid dashboard-quick-grid">
          {dashboard.quick_tools.map((tool) => {
            const Icon = quickToolIcons[tool.route] ?? Target;
            return (
              <Link key={`${tool.route}-${tool.label}`} to={tool.route} className="quick-action tone-blue">
                <span><Icon aria-hidden="true" size={20} /></span>
                {tool.label}
              </Link>
            );
          })}
        </div>
      </Card>

      <small className="dashboard-semantics-note">تعريفات التقدم: {dashboard.semantics_version}</small>
    </div>
  );
};

export default DashboardPage;
