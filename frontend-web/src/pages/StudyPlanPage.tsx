import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { curriculumApi, fallbackCurriculumUnits, studyPlanApi } from '../api';
import { Button, Card, ErrorBanner, LoadingSkeleton, PageHeader, ProgressBar, StatusPill } from '../components/DesignSystem';
import { useStudyPlanProgress } from '../hooks/useStudyPlanProgress';
import type {
  CurriculumEntityId,
  ExamPlanConfig,
  SemesterPlanConfig,
  StudyDayCode,
  StudyPlan,
  StudyPlanProgress,
  StudyPlanProgressStatus,
  StudyPlanScheduledLessonProgress,
  StudyScheduleEntry,
  StudyScheduleSession,
  UnitCatalogItem,
} from '../types';

type StudyPlanViewState = 'loading' | 'empty' | 'setup' | 'generating' | 'active' | 'error';
type PlanType = 'semester' | 'exam' | 'custom';
type FocusPriority = 'balanced' | 'weak_topics_first' | 'fast_coverage';
type ActiveTab = 'today' | 'weakness' | 'path' | 'review' | 'achievement';
type UnitFilter = number | 'all';

interface SetupFormState {
  planType: PlanType;
  selectedLessonIds: CurriculumEntityId[];
  startDate: string;
  endDate: string;
  examDate: string;
  dailyStudyMinutes: number;
  studyDays: StudyDayCode[];
  focusPriority: FocusPriority;
  unitFilter: UnitFilter;
}

interface TimelineSession {
  date: string;
  weekday: string;
  session: StudyScheduleSession;
  status: StudyPlanProgressStatus | 'today' | 'upcoming';
}

const STUDY_DAY_OPTIONS: Array<{ code: StudyDayCode; short: string; label: string }> = [
  { code: 'sun', short: 'ح', label: 'الأحد' },
  { code: 'mon', short: 'ن', label: 'الاثنين' },
  { code: 'tue', short: 'ث', label: 'الثلاثاء' },
  { code: 'wed', short: 'ر', label: 'الأربعاء' },
  { code: 'thu', short: 'خ', label: 'الخميس' },
  { code: 'fri', short: 'ج', label: 'الجمعة' },
  { code: 'sat', short: 'س', label: 'السبت' },
];

const ACTIVE_TABS: Array<{ id: ActiveTab; label: string }> = [
  { id: 'today', label: 'اليوم' },
  { id: 'weakness', label: 'الضعف' },
  { id: 'path', label: 'المسار' },
  { id: 'review', label: 'المراجعة' },
  { id: 'achievement', label: 'الإنجاز' },
];

const PLAN_TYPE_LABELS: Record<PlanType, { title: string; description: string }> = {
  semester: {
    title: 'خطة فصل دراسي',
    description: 'توزيع متوازن للدروس على فترة أطول مع متابعة أسبوعية.',
  },
  exam: {
    title: 'خطة امتحان',
    description: 'تركيز مكثف قبل موعد الاختبار مع مراجعة الدروس المحددة.',
  },
  custom: {
    title: 'خطة مخصصة',
    description: 'اختر الدروس والأيام والوقت حسب إيقاعك الدراسي.',
  },
};

const FOCUS_LABELS: Record<FocusPriority, string> = {
  balanced: 'توازن بين التغطية والمراجعة',
  weak_topics_first: 'نقاط الضعف أولاً',
  fast_coverage: 'تغطية سريعة للمنهج',
};

const STATUS_LABELS: Record<StudyPlanProgressStatus, string> = {
  completed: 'مكتمل',
  in_progress: 'قيد الدراسة',
  not_started: 'لم يبدأ',
  skipped: 'متجاوز',
  overdue: 'متأخر',
};

const STATUS_TONES: Record<StudyPlanProgressStatus, string> = {
  completed: 'teal',
  in_progress: 'blue',
  not_started: 'ghost',
  skipped: 'gold',
  overdue: 'coral',
};

const dateInputValue = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const todayInputValue = () => dateInputValue(new Date());

const dateInputValueFromToday = (days: number): string => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return dateInputValue(date);
};

const formatPlanDate = (value?: string | null): string => {
  if (!value) return 'غير محدد';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('ar', { day: 'numeric', month: 'long' }).format(date);
};

const daysUntilDate = (value?: string | null): number | null => {
  if (!value) return null;
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) return null;
  const today = new Date();
  target.setHours(23, 59, 59, 999);
  today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.ceil((target.getTime() - today.getTime()) / 86_400_000));
};

const isSameDateKey = (a: string, b: string): boolean => a.slice(0, 10) === b.slice(0, 10);

const countAvailableLessons = (units: UnitCatalogItem[]) =>
  units.reduce((total, unit) => total + unit.chapters.reduce((chapterTotal, chapter) => chapterTotal + chapter.lessons.length, 0), 0);

const getScheduledLessonSessionCount = (plan: StudyPlan | null): number =>
  (plan?.schedule ?? []).reduce((total, entry) => (
    total + entry.sessions.filter((session) => session.type === 'lesson' && Boolean(session.lesson_id)).length
  ), 0);

const hasGeneratedSchedule = (plan: StudyPlan | null, progress?: StudyPlanProgress | null): boolean => {
  if (!plan) return false;
  if (getScheduledLessonSessionCount(plan) > 0) return true;
  return Boolean(progress && progress.total_scheduled_lessons > 0);
};

const getScheduledLessons = (progress: StudyPlanProgress | null, plan: StudyPlan | null): StudyPlanScheduledLessonProgress[] => {
  if (progress?.scheduled_lessons?.length) return progress.scheduled_lessons;

  const lessonLookup = new Map<number, { title: string; chapterTitle: string }>();
  plan?.chapters.forEach((chapter) => {
    chapter.lessons.forEach((lesson) => {
      lessonLookup.set(lesson.id, { title: lesson.title, chapterTitle: chapter.title });
    });
  });

  return (plan?.schedule ?? [])
    .flatMap((entry, index) => (
      entry.sessions
        .filter((session) => session.type === 'lesson' && Boolean(session.lesson_id))
        .map((session) => {
          const lessonInfo = session.lesson_id ? lessonLookup.get(session.lesson_id) : undefined;
          return {
            study_plan_item_id: index + 1,
            lesson_id: session.lesson_id ?? index + 1,
            lesson_title_ar: lessonInfo?.title ?? session.title,
            unit_title_ar: session.unit_number ? `الوحدة ${session.unit_number}` : null,
            chapter_title_ar: lessonInfo?.chapterTitle ?? null,
            scheduled_date: entry.date,
            status: session.completed || session.status === 'completed' ? 'completed' : 'not_started',
            completion_percent: session.completed || session.status === 'completed' ? 100 : 0,
            estimated_minutes: session.minutes,
          } satisfies StudyPlanScheduledLessonProgress;
        })
    ));
};

const getProgressStats = (progress: StudyPlanProgress | null, plan: StudyPlan | null) => {
  const scheduledLessons = getScheduledLessons(progress, plan);
  const total = progress?.total_scheduled_lessons ?? scheduledLessons.length;
  if (total === 0) return null;

  const completed = progress?.completed_lessons ?? scheduledLessons.filter((lesson) => lesson.status === 'completed').length;
  const inProgress = progress?.in_progress_lessons ?? scheduledLessons.filter((lesson) => lesson.status === 'in_progress').length;
  const overdue = progress?.overdue_lessons ?? scheduledLessons.filter((lesson) => lesson.status === 'overdue').length;
  const notStarted = progress?.not_started_lessons ?? scheduledLessons.filter((lesson) => lesson.status === 'not_started').length;
  const percent = progress?.completion_percent ?? Math.round((completed / total) * 100);

  return { total, completed, inProgress, overdue, notStarted, percent };
};

const getTodayEntries = (plan: StudyPlan | null): StudyScheduleEntry[] => {
  const today = todayInputValue();
  return (plan?.schedule ?? []).filter((entry) => isSameDateKey(entry.date, today));
};

const getNextLesson = (progress: StudyPlanProgress | null, plan: StudyPlan | null): StudyPlanScheduledLessonProgress | null => {
  const scheduledLessons = getScheduledLessons(progress, plan);
  if (!scheduledLessons.length) return null;
  return scheduledLessons
    .filter((lesson) => lesson.status !== 'completed' && lesson.status !== 'skipped')
    .sort((a, b) => (a.scheduled_date ?? '9999-12-31').localeCompare(b.scheduled_date ?? '9999-12-31'))[0] ?? null;
};

const getTimelineSessions = (plan: StudyPlan | null, progress: StudyPlanProgress | null): TimelineSession[] => {
  const today = todayInputValue();
  const statusByLesson = new Map(
    (progress?.scheduled_lessons ?? []).map((lesson) => [String(lesson.lesson_id), lesson.status] as const),
  );

  return (plan?.schedule ?? [])
    .flatMap((entry) => (
      entry.sessions
        .filter((session) => session.type === 'lesson' && Boolean(session.lesson_id))
        .map((session) => {
          const progressStatus = session.lesson_id ? statusByLesson.get(String(session.lesson_id)) : undefined;
          const status: TimelineSession['status'] = progressStatus
            ?? (session.completed || session.status === 'completed'
              ? 'completed'
              : isSameDateKey(entry.date, today)
                ? 'today'
                : entry.date.slice(0, 10) < today
                  ? 'overdue'
                  : 'upcoming');
          return {
            date: entry.date,
            weekday: entry.weekday_ar,
            session,
            status,
          };
        })
    ));
};

const getDefaultSetupForm = (): SetupFormState => ({
  planType: 'semester',
  selectedLessonIds: [],
  startDate: todayInputValue(),
  endDate: dateInputValueFromToday(120),
  examDate: dateInputValueFromToday(30),
  dailyStudyMinutes: 60,
  studyDays: ['sun', 'mon', 'wed', 'fri'],
  focusPriority: 'balanced',
  unitFilter: 'all',
});

const validateSetup = (form: SetupFormState): Record<string, string> => {
  const errors: Record<string, string> = {};
  const today = todayInputValue();

  if (!form.selectedLessonIds.length) {
    errors.lessons = 'اختر درساً واحداً على الأقل لإنشاء الخطة.';
  }
  if (!form.startDate) {
    errors.startDate = 'تاريخ البداية مطلوب.';
  } else if (form.startDate < today) {
    errors.startDate = 'تاريخ البداية يجب أن يكون اليوم أو بعده.';
  }
  if (form.planType === 'exam') {
    if (!form.examDate) {
      errors.examDate = 'تاريخ الامتحان مطلوب.';
    } else if (form.examDate <= form.startDate) {
      errors.examDate = 'تاريخ الامتحان يجب أن يكون بعد تاريخ البداية.';
    }
  } else if (!form.endDate) {
    errors.endDate = 'تاريخ النهاية مطلوب.';
  } else if (form.endDate <= form.startDate) {
    errors.endDate = 'تاريخ النهاية يجب أن يكون بعد تاريخ البداية.';
  }
  if (!Number.isFinite(form.dailyStudyMinutes) || form.dailyStudyMinutes < 20) {
    errors.dailyStudyMinutes = 'وقت الدراسة اليومي يجب أن يكون 20 دقيقة على الأقل.';
  }
  if (!form.studyDays.length) {
    errors.studyDays = 'اختر يوماً واحداً على الأقل للدراسة.';
  }

  return errors;
};

const buildGenerationPayload = (form: SetupFormState): SemesterPlanConfig | ExamPlanConfig => {
  const hours = Math.max(0.5, Math.round((form.dailyStudyMinutes / 60) * 10) / 10);
  const studyHoursByDay = form.studyDays.reduce<Partial<Record<StudyDayCode, number>>>((acc, day) => {
    acc[day] = hours;
    return acc;
  }, {});

  if (form.planType === 'exam') {
    const payload: ExamPlanConfig & Record<string, unknown> = {
      title: 'خطة امتحان الكيمياء',
      examDate: form.examDate,
      dailyStudyHours: String(hours),
      studyDays: form.studyDays,
      studyHoursByDay,
      priority: form.focusPriority,
      lessonIds: form.selectedLessonIds,
      startDate: form.startDate,
      endDate: form.examDate,
      mode: 'exam',
      plan_type: form.planType,
      focus_priority: form.focusPriority,
    };
    return payload;
  }

  const payload: SemesterPlanConfig & Record<string, unknown> = {
    startDate: form.startDate,
    endDate: form.endDate,
    studyDays: form.studyDays,
    studyHoursByDay,
    lessonDuration: String(form.dailyStudyMinutes),
    weeklyRest: 'none',
    lessonIds: form.selectedLessonIds,
    title: form.planType === 'custom' ? 'خطة كيمياء مخصصة' : 'خطة الفصل الدراسي',
    mode: form.planType,
    plan_type: form.planType,
    focus_priority: form.focusPriority,
  };
  return payload;
};

const StudyPlanSkeleton = () => (
  <div className="sp-page" dir="rtl">
    <StudyPlanHeader />
    <Card className="sp-skeleton-card">
      <LoadingSkeleton rows={5} />
    </Card>
  </div>
);

const StudyPlanHeader = ({ action }: { action?: React.ReactNode }) => (
  <PageHeader
    eyebrow="تنظيم المذاكرة"
    title="خطة الدراسة"
    subtitle="خطة يومية متصلة بالدروس، المراجعة، الاختبارات، والبطاقات."
    action={action}
  />
);

const StudyPlanEmptyState = ({
  units,
  onStart,
}: {
  units: UnitCatalogItem[];
  onStart: () => void;
}) => {
  const lessonCount = countAvailableLessons(units);
  const unitCount = units.length;

  return (
    <div className="sp-page" dir="rtl">
      <StudyPlanHeader />
      <section className="sp-empty-hero" aria-labelledby="study-empty-title">
        <div className="sp-empty-copy">
          <span className="sp-kicker">ابدأ من خطة واضحة</span>
          <h2 id="study-empty-title">لم تُنشئ خطتك الدراسية بعد</h2>
          <p>
            أنشئ خطة ذكية تعتمد على الذكاء الاصطناعي — تُوزّع دروسك يومياً، تُركّز على نقاط ضعفك،
            وتضمن استعدادك للامتحان.
          </p>
          <div className="sp-benefits" aria-label="فوائد خطة الدراسة">
            <span>جدول يومي ذكي</span>
            <span>يركز على الضعف</span>
            <span>تتبع التقدم</span>
            <span>إنجازات وتحفيز</span>
          </div>
          <Button onClick={onStart} className="sp-primary-cta">ابدأ إنشاء الخطة</Button>
        </div>
        <div className="sp-empty-preview" aria-label="معاينة الخطة">
          <div>
            <strong>{lessonCount}</strong>
            <span>درساً متاحاً</span>
          </div>
          <div>
            <strong>{unitCount}</strong>
            <span>وحدات في المنهج</span>
          </div>
          <div>
            <strong>4</strong>
            <span>خطوات للإنشاء</span>
          </div>
        </div>
      </section>

      <div className="sp-preview-strip">
        <Card className="sp-preview-card">
          <strong>الدروس المتاحة</strong>
          <span>اختر من بنية المنهج: وحدة ← فصل ← درس ← موضوع.</span>
        </Card>
        <Card className="sp-preview-card">
          <strong>الفصل الدراسي</strong>
          <span>وزّع الدروس حسب الأيام والوقت المتاح لك.</span>
        </Card>
        <Card className="sp-preview-card">
          <strong>طريقة إنشاء الخطة</strong>
          <span>نراجع الاختيارات قبل إرسالها للخادم لتوليد جدول حقيقي.</span>
        </Card>
      </div>
    </div>
  );
};

const StudyPlanError = ({
  message,
  onRetry,
  onSetup,
}: {
  message: string;
  onRetry: () => void;
  onSetup: () => void;
}) => (
  <div className="sp-page" dir="rtl">
    <StudyPlanHeader action={<Button variant="secondary" onClick={onSetup}>إعداد خطة جديدة</Button>} />
    <ErrorBanner message={message} onRetry={onRetry} />
  </div>
);

const PlanGenerationOverlay = () => (
  <div className="sp-generation-overlay" role="status" aria-live="polite">
    <Card className="sp-generation-card">
      <span className="sp-spinner" aria-hidden="true" />
      <h2>نولّد خطتك الدراسية</h2>
      <p>نرتّب الدروس على الأيام المختارة ونراجع السعة اليومية قبل عرض الجدول.</p>
      <div className="sp-generation-steps">
        <span>قراءة الدروس المحددة</span>
        <span>حساب الوقت اليومي</span>
        <span>إنشاء الجدول</span>
      </div>
    </Card>
  </div>
);

const StudyPlanSetupWizard = ({
  units,
  form,
  errors,
  isGenerating,
  onChange,
  onGenerate,
  onBackToEmpty,
}: {
  units: UnitCatalogItem[];
  form: SetupFormState;
  errors: Record<string, string>;
  isGenerating: boolean;
  onChange: (nextForm: SetupFormState) => void;
  onGenerate: () => void;
  onBackToEmpty: () => void;
}) => {
  const selectedCount = form.selectedLessonIds.length;
  const isValid = Object.keys(errors).length === 0;
  const hours = Math.round((form.dailyStudyMinutes / 60) * 10) / 10;
  const scheduleTarget = form.planType === 'exam' ? form.examDate : form.endDate;
  const daysRemaining = daysUntilDate(scheduleTarget);

  const updateField = <K extends keyof SetupFormState>(key: K, value: SetupFormState[K]) => {
    onChange({ ...form, [key]: value });
  };

  const toggleStudyDay = (day: StudyDayCode) => {
    updateField(
      'studyDays',
      form.studyDays.includes(day)
        ? form.studyDays.filter((code) => code !== day)
        : [...form.studyDays, day],
    );
  };

  return (
    <div className="sp-page sp-setup-page" dir="rtl">
      <StudyPlanHeader action={<Button variant="ghost" onClick={onBackToEmpty}>رجوع</Button>} />

      <Card className="sp-setup-card">
        <div className="sp-setup-intro">
          <span className="sp-kicker">إعداد الخطة</span>
          <h2>أنشئ خطة مرتبطة بالدروس المجدولة فعلياً</h2>
          <p>اختر نوع الخطة، الدروس، الأيام، والوقت. لن تظهر لوحة التقدم إلا بعد إنشاء جدول بدروس مجدولة.</p>
        </div>

        <div className="sp-setup-steps" aria-label="خطوات إنشاء خطة الدراسة">
          {['نوع الخطة', 'الدروس', 'التاريخ والأيام', 'مراجعة وإنشاء'].map((step, index) => (
            <span key={step}>
              <strong>{index + 1}</strong>
              {step}
            </span>
          ))}
        </div>

        <div className="sp-setup-grid">
          <section className="sp-form-section" aria-labelledby="plan-type-heading">
            <h3 id="plan-type-heading">نوع الخطة</h3>
            <div className="sp-plan-type-grid">
              {(Object.keys(PLAN_TYPE_LABELS) as PlanType[]).map((type) => (
                <button
                  key={type}
                  type="button"
                  className={`sp-option-card ${form.planType === type ? 'is-selected' : ''}`}
                  onClick={() => updateField('planType', type)}
                  aria-pressed={form.planType === type}
                >
                  <strong>{PLAN_TYPE_LABELS[type].title}</strong>
                  <span>{PLAN_TYPE_LABELS[type].description}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="sp-form-section" aria-labelledby="plan-dates-heading">
            <h3 id="plan-dates-heading">التاريخ والوقت</h3>
            <div className="sp-field-grid">
              <label className="sp-field" htmlFor="study-start-date">
                <span>تاريخ البداية</span>
                <input
                  id="study-start-date"
                  type="date"
                  min={todayInputValue()}
                  value={form.startDate}
                  onChange={(event) => updateField('startDate', event.target.value)}
                />
                {errors.startDate && <small role="alert">{errors.startDate}</small>}
              </label>

              {form.planType === 'exam' ? (
                <label className="sp-field" htmlFor="study-exam-date">
                  <span>تاريخ الامتحان</span>
                  <input
                    id="study-exam-date"
                    type="date"
                    min={todayInputValue()}
                    value={form.examDate}
                    onChange={(event) => updateField('examDate', event.target.value)}
                  />
                  {errors.examDate && <small role="alert">{errors.examDate}</small>}
                </label>
              ) : (
                <label className="sp-field" htmlFor="study-end-date">
                  <span>تاريخ النهاية</span>
                  <input
                    id="study-end-date"
                    type="date"
                    min={todayInputValue()}
                    value={form.endDate}
                    onChange={(event) => updateField('endDate', event.target.value)}
                  />
                  {errors.endDate && <small role="alert">{errors.endDate}</small>}
                </label>
              )}

              <label className="sp-field" htmlFor="study-daily-minutes">
                <span>وقت الدراسة اليومي</span>
                <input
                  id="study-daily-minutes"
                  type="number"
                  min={20}
                  step={10}
                  value={form.dailyStudyMinutes}
                  onChange={(event) => updateField('dailyStudyMinutes', Number(event.target.value))}
                />
                {errors.dailyStudyMinutes && <small role="alert">{errors.dailyStudyMinutes}</small>}
              </label>

              <label className="sp-field" htmlFor="study-focus">
                <span>أولوية التركيز</span>
                <select
                  id="study-focus"
                  value={form.focusPriority}
                  onChange={(event) => updateField('focusPriority', event.target.value as FocusPriority)}
                >
                  {(Object.keys(FOCUS_LABELS) as FocusPriority[]).map((priority) => (
                    <option key={priority} value={priority}>{FOCUS_LABELS[priority]}</option>
                  ))}
                </select>
              </label>
            </div>

            <fieldset className="sp-day-selector">
              <legend>أيام الدراسة</legend>
              <div>
                {STUDY_DAY_OPTIONS.map((day) => (
                  <button
                    key={day.code}
                    type="button"
                    className={form.studyDays.includes(day.code) ? 'is-selected' : ''}
                    onClick={() => toggleStudyDay(day.code)}
                    aria-pressed={form.studyDays.includes(day.code)}
                    title={day.label}
                  >
                    <span>{day.short}</span>
                    <small>{day.label}</small>
                  </button>
                ))}
              </div>
              {errors.studyDays && <small role="alert">{errors.studyDays}</small>}
            </fieldset>

            {form.studyDays.length > 0 && (
              <div className="sp-hours-summary" aria-label="ساعات الدراسة لكل يوم مختار">
                {form.studyDays.map((day) => (
                  <span key={day}>
                    {STUDY_DAY_OPTIONS.find((option) => option.code === day)?.label}: {hours} ساعة
                  </span>
                ))}
              </div>
            )}
          </section>

          <section className="sp-form-section sp-lessons-section" aria-labelledby="lesson-selector-heading">
            <div className="sp-section-heading">
              <div>
                <h3 id="lesson-selector-heading">الدروس</h3>
                <p>{selectedCount} درس محدد من المنهج</p>
              </div>
              <Button
                variant="ghost"
                onClick={() => updateField('selectedLessonIds', [])}
                disabled={!selectedCount}
                className="sp-compact-btn"
              >
                إلغاء التحديد
              </Button>
            </div>
            <LessonSelector units={units} form={form} onChange={onChange} />
            {errors.lessons && <p className="sp-inline-error" role="alert">{errors.lessons}</p>}
          </section>

          <aside className="sp-review-box" aria-label="مراجعة قبل الإنشاء">
            <span className="sp-kicker">مراجعة وإنشاء</span>
            <h3>ملخص الخطة</h3>
            <dl>
              <div>
                <dt>نوع الخطة</dt>
                <dd>{PLAN_TYPE_LABELS[form.planType].title}</dd>
              </div>
              <div>
                <dt>الدروس المحددة</dt>
                <dd>{selectedCount} درس</dd>
              </div>
              <div>
                <dt>الأيام المختارة</dt>
                <dd>{form.studyDays.length} أيام</dd>
              </div>
              <div>
                <dt>المدة المتوقعة</dt>
                <dd>{daysRemaining === null ? 'غير محددة' : `${daysRemaining} يوم`}</dd>
              </div>
            </dl>
            <Button onClick={onGenerate} disabled={!isValid || isGenerating}>
              {isGenerating ? 'جار الإنشاء...' : 'إنشاء الخطة'}
            </Button>
            {!isValid && <p className="sp-form-hint">أكمل الحقول المطلوبة لتفعيل زر الإنشاء.</p>}
          </aside>
        </div>
      </Card>

      {isGenerating && <PlanGenerationOverlay />}
    </div>
  );
};

const LessonSelector = ({
  units,
  form,
  onChange,
}: {
  units: UnitCatalogItem[];
  form: SetupFormState;
  onChange: (nextForm: SetupFormState) => void;
}) => {
  const visibleUnits = form.unitFilter === 'all'
    ? units
    : units.filter((unit) => unit.id === form.unitFilter);

  const setSelectedLessons = (selectedLessonIds: CurriculumEntityId[]) => {
    onChange({ ...form, selectedLessonIds });
  };

  const toggleLesson = (lessonId: CurriculumEntityId) => {
    const exists = form.selectedLessonIds.some((id) => String(id) === String(lessonId));
    setSelectedLessons(
      exists
        ? form.selectedLessonIds.filter((id) => String(id) !== String(lessonId))
        : [...form.selectedLessonIds, lessonId],
    );
  };

  const selectUnit = (unit: UnitCatalogItem) => {
    const unitLessonIds = unit.chapters.flatMap((chapter) => chapter.lessons.map((lesson) => lesson.id));
    const existing = new Set(form.selectedLessonIds.map(String));
    setSelectedLessons([...form.selectedLessonIds, ...unitLessonIds.filter((id) => !existing.has(String(id)))]);
  };

  return (
    <div className="sp-lesson-selector">
      <div className="sp-unit-filter" aria-label="تصفية الوحدات">
        <button
          type="button"
          className={form.unitFilter === 'all' ? 'is-selected' : ''}
          onClick={() => onChange({ ...form, unitFilter: 'all' })}
        >
          كل الوحدات
        </button>
        {units.map((unit) => (
          <button
            key={unit.id}
            type="button"
            className={form.unitFilter === unit.id ? 'is-selected' : ''}
            onClick={() => onChange({ ...form, unitFilter: unit.id })}
          >
            وحدة {unit.unit_number}
          </button>
        ))}
      </div>

      <div className="sp-curriculum-tree">
        {visibleUnits.map((unit) => (
          <article key={unit.id} className="sp-unit-block">
            <header>
              <div>
                <strong>{unit.title_ar}</strong>
                <span>الفصل {unit.semester} · {unit.chapters.length} فصول</span>
              </div>
              <Button variant="ghost" onClick={() => selectUnit(unit)} className="sp-compact-btn">تحديد الوحدة</Button>
            </header>
            {unit.chapters.map((chapter) => (
              <section key={chapter.id} className="sp-chapter-block">
                <h4>{chapter.title_ar}</h4>
                <div className="sp-lesson-list">
                  {chapter.lessons.map((lesson) => {
                    const checked = form.selectedLessonIds.some((id) => String(id) === String(lesson.id));
                    return (
                      <label key={lesson.id} className={`sp-lesson-row ${checked ? 'is-selected' : ''}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleLesson(lesson.id)}
                        />
                        <span>
                          <strong>{lesson.title_ar}</strong>
                          <small>
                            {lesson.duration_min || 45} دقيقة
                            {lesson.topics.length ? ` · ${lesson.topics.length} موضوع` : ''}
                          </small>
                          {lesson.topics.length > 0 && (
                            <em>{lesson.topics.slice(0, 3).map((topic) => topic.title_ar).join('، ')}</em>
                          )}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </section>
            ))}
          </article>
        ))}
      </div>
    </div>
  );
};

const StudyPlanActiveDashboard = ({
  plan,
  progress,
  progressLoading,
  activeTab,
  onTabChange,
  onSetupNew,
  onCompleteLesson,
}: {
  plan: StudyPlan;
  progress: StudyPlanProgress | null;
  progressLoading: boolean;
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  onSetupNew: () => void;
  onCompleteLesson: (lessonId: number | string) => Promise<void>;
}) => {
  const stats = getProgressStats(progress, plan);

  return (
    <div className="sp-page sp-active-page" dir="rtl">
      <StudyPlanHeader
        action={(
          <div className="sp-header-actions">
            <Button variant="secondary" onClick={onSetupNew}>تعديل الخطة</Button>
            <Link to="/lessons" className="ed-btn ed-btn-ghost">العودة للدروس</Link>
          </div>
        )}
      />

      <Card className="sp-active-hero">
        <div>
          <span className="sp-kicker">الخطة الحالية</span>
          <h2>{String(plan.config?.title ?? progress?.plan_title ?? 'خطة الكيمياء')}</h2>
          <StatusPill tone={progress?.track_status === 'behind' ? 'coral' : progress?.track_status === 'ahead' ? 'purple' : 'teal'}>
            {progress?.track_status === 'behind' ? 'تحتاج إلى تعويض' : progress?.track_status === 'ahead' ? 'متقدم على الخطة' : 'أنت على المسار'}
          </StatusPill>
        </div>
        {stats && <StudyPlanProgressStats stats={stats} progressLoading={progressLoading} />}
      </Card>

      <StudyPlanTabs activeTab={activeTab} onChange={onTabChange} />

      <section className="sp-tab-panel" role="tabpanel" id={`study-plan-panel-${activeTab}`} aria-labelledby={`study-plan-tab-${activeTab}`}>
        {activeTab === 'today' && <TodayPanel plan={plan} progress={progress} onCompleteLesson={onCompleteLesson} />}
        {activeTab === 'weakness' && <WeaknessPanel plan={plan} progress={progress} />}
        {activeTab === 'path' && <PathPanel plan={plan} progress={progress} onCompleteLesson={onCompleteLesson} />}
        {activeTab === 'review' && <ReviewPanel progress={progress} />}
        {activeTab === 'achievement' && <AchievementPanel progress={progress} />}
      </section>
    </div>
  );
};

const StudyPlanTabs = ({
  activeTab,
  onChange,
}: {
  activeTab: ActiveTab;
  onChange: (tab: ActiveTab) => void;
}) => (
  <nav className="sp-tabs" role="tablist" aria-label="أقسام خطة الدراسة">
    {ACTIVE_TABS.map((tab) => (
      <button
        key={tab.id}
        id={`study-plan-tab-${tab.id}`}
        type="button"
        role="tab"
        aria-selected={activeTab === tab.id}
        aria-controls={`study-plan-panel-${tab.id}`}
        className={activeTab === tab.id ? 'is-active' : ''}
        onClick={() => onChange(tab.id)}
      >
        {tab.label}
      </button>
    ))}
  </nav>
);

const StudyPlanProgressStats = ({
  stats,
  progressLoading,
}: {
  stats: NonNullable<ReturnType<typeof getProgressStats>>;
  progressLoading: boolean;
}) => (
  <div className="sp-progress-overview" aria-busy={progressLoading}>
    <div className="sp-progress-main">
      <strong>{Math.round(stats.percent)}%</strong>
      <span>{stats.completed} من {stats.total} دروس مكتملة</span>
      <ProgressBar value={stats.percent} tone="teal" />
    </div>
    <div className="sp-mini-stats">
      <span><strong>{stats.completed}</strong> مكتملة</span>
      <span><strong>{stats.inProgress}</strong> قيد الدراسة</span>
      <span><strong>{stats.notStarted}</strong> لم تبدأ</span>
      <span><strong>{stats.overdue}</strong> متأخرة</span>
    </div>
  </div>
);

const TodayPanel = ({
  plan,
  progress,
  onCompleteLesson,
}: {
  plan: StudyPlan;
  progress: StudyPlanProgress | null;
  onCompleteLesson: (lessonId: number | string) => Promise<void>;
}) => {
  const todayEntries = getTodayEntries(plan);
  const todayLessonSessions = todayEntries.flatMap((entry) => entry.sessions.filter((session) => session.type === 'lesson'));
  const nextLesson = getNextLesson(progress, plan);
  const examDays = daysUntilDate(plan.summary?.exam_date ?? plan.config?.examDate);
  const overdue = getScheduledLessons(progress, plan).find((lesson) => lesson.status === 'overdue');
  const studyPlanFlashcardsUrl = progress?.plan_id
    ? `/flashcards?scope=study_plan&plan_id=${progress.plan_id}`
    : '/flashcards';

  return (
    <div className="sp-panel-grid">
      <Card className="sp-panel-card sp-today-mission">
        <span className="sp-kicker">مهمة اليوم</span>
        {todayLessonSessions.length > 0 ? (
          <>
            <h2>{todayLessonSessions[0]?.title}</h2>
            <p>{todayLessonSessions.length} جلسة مجدولة اليوم ضمن خطة الكيمياء.</p>
            {todayLessonSessions[0]?.lesson_id && (
              <div className="sp-action-row">
                <Link className="ed-btn ed-btn-primary" to={`/study-session/${todayLessonSessions[0].lesson_id}`}>ابدأ جلسة اليوم</Link>
                <Button variant="secondary" onClick={() => onCompleteLesson(todayLessonSessions[0].lesson_id!)}>أكملت الدرس</Button>
              </div>
            )}
          </>
        ) : (
          <>
            <h2>لا توجد مهمة مجدولة اليوم</h2>
            <p>يمكنك مراجعة البطاقات أو بدء الدرس التالي حتى تبقى على المسار.</p>
            <div className="sp-action-row">
              <Link className="ed-btn ed-btn-primary" to={studyPlanFlashcardsUrl}>بطاقات اليوم</Link>
              {nextLesson && <Link className="ed-btn ed-btn-secondary" to={`/study-session/${nextLesson.lesson_id}`}>ابدأ الدرس التالي</Link>}
            </div>
          </>
        )}
      </Card>

      <Card className="sp-panel-card">
        <span className="sp-kicker">الدرس التالي</span>
        {nextLesson ? (
          <>
            <h3>{nextLesson.lesson_title_ar}</h3>
            <p>{nextLesson.scheduled_date ? `مجدول في ${formatPlanDate(nextLesson.scheduled_date)}` : 'مجدول ضمن الخطة'}</p>
            <StatusPill tone={STATUS_TONES[nextLesson.status]}>{STATUS_LABELS[nextLesson.status]}</StatusPill>
          </>
        ) : (
          <>
            <h3>أكملت كل دروس هذه الخطة.</h3>
            <p>انتقل إلى المراجعة أو اختبر نفسك للتأكد من تثبيت المعلومات.</p>
          </>
        )}
      </Card>

      <WeekStrip plan={plan} />

      <Card className="sp-panel-card sp-alert-card">
        <span className="sp-kicker">تنبيه الخطة</span>
        {overdue ? (
          <>
            <h3>لديك درس متأخر</h3>
            <p>{overdue.lesson_title_ar} لم يكتمل بعد.</p>
          </>
        ) : examDays !== null ? (
          <>
            <h3>{examDays} يوم للامتحان</h3>
            <p>استمر في جدول المراجعة حتى لا تتراكم الدروس قبل الموعد.</p>
          </>
        ) : (
          <>
            <h3>لا توجد تنبيهات حرجة</h3>
            <p>الخطة الحالية لا تحتوي على دروس متأخرة حسب البيانات المتاحة.</p>
          </>
        )}
      </Card>
    </div>
  );
};

const WeekStrip = ({ plan }: { plan: StudyPlan }) => {
  const scheduleByDay = new Map<string, StudyScheduleEntry[]>();
  (plan.schedule ?? []).forEach((entry) => {
    const key = entry.weekday;
    scheduleByDay.set(key, [...(scheduleByDay.get(key) ?? []), entry]);
  });

  return (
    <Card className="sp-week-strip">
      <span className="sp-kicker">الأسبوع</span>
      <div>
        {STUDY_DAY_OPTIONS.map((day) => {
          const entries = scheduleByDay.get(day.code) ?? [];
          const minutes = entries.reduce((total, entry) => total + entry.planned_minutes, 0);
          return (
            <span key={day.code} className={entries.length ? 'has-plan' : ''}>
              <strong>{day.short}</strong>
              <small>{minutes ? `${Math.round(minutes / 60)}س` : 'راحة'}</small>
            </span>
          );
        })}
      </div>
    </Card>
  );
};

const WeaknessPanel = ({
  plan,
  progress,
}: {
  plan: StudyPlan;
  progress: StudyPlanProgress | null;
}) => {
  const weakLessons = getScheduledLessons(progress, plan)
    .filter((lesson) => lesson.status === 'overdue' || lesson.completion_percent < 80)
    .slice(0, 8);

  return (
    <div className="sp-panel-grid">
      <Card className="sp-panel-card sp-wide-card">
        <span className="sp-kicker">نقاط تحتاج مراجعة</span>
        <h2>مؤشر الإتقان</h2>
        <p>نعرض الدروس التي يقل إتقانها عن 80% أو أصبحت متأخرة في الجدول.</p>
        {weakLessons.length ? (
          <div className="sp-weak-list">
            {weakLessons.map((lesson) => {
              const mastery = Math.max(0, Math.min(100, Math.round(lesson.completion_percent)));
              const severity = mastery < 50 || lesson.status === 'overdue' ? 'عالي' : mastery < 70 ? 'متوسط' : 'منخفض';
              return (
                <article key={`${lesson.lesson_id}-${lesson.scheduled_date}`} className="sp-weak-item">
                  <div>
                    <strong>{lesson.lesson_title_ar}</strong>
                    <span>{lesson.unit_title_ar ?? 'درس مجدول'} · إتقان {mastery}%</span>
                  </div>
                  <StatusPill tone={severity === 'عالي' ? 'coral' : severity === 'متوسط' ? 'gold' : 'blue'}>{severity}</StatusPill>
                  <Link className="ed-btn ed-btn-ghost ed-btn-xs" to={`/ask-ai?lessonId=${lesson.lesson_id}`}>راجع الآن</Link>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="sp-empty-panel">
            <h3>لا توجد نقاط ضعف واضحة الآن</h3>
            <p>عند ظهور درس بإتقان أقل من 80% سيظهر هنا مع إجراء مراجعة مباشر.</p>
          </div>
        )}
      </Card>
    </div>
  );
};

const PathPanel = ({
  plan,
  progress,
  onCompleteLesson,
}: {
  plan: StudyPlan;
  progress: StudyPlanProgress | null;
  onCompleteLesson: (lessonId: number | string) => Promise<void>;
}) => (
  <div className="sp-path-layout">
    <TimelineView plan={plan} progress={progress} onCompleteLesson={onCompleteLesson} />
    <Card className="sp-panel-card">
      <span className="sp-kicker">تقدم الوحدات</span>
      <h3>حسب الدروس المجدولة</h3>
      <div className="sp-unit-progress-list">
        {(progress?.unit_progress ?? []).length ? (
          progress!.unit_progress.map((unit) => (
            <article key={`${unit.unit_id ?? unit.unit_title_ar}`} className="sp-unit-progress">
              <div>
                <strong>{unit.unit_title_ar}</strong>
                <span>{unit.completed_lessons}/{unit.total_lessons} دروس</span>
              </div>
              <ProgressBar value={unit.completion_percent} tone="blue" />
            </article>
          ))
        ) : (
          <p>سيظهر تقدم الوحدات بعد تحميل بيانات التقدم من الخادم.</p>
        )}
      </div>
    </Card>
  </div>
);

const TimelineView = ({
  plan,
  progress,
  onCompleteLesson,
}: {
  plan: StudyPlan;
  progress: StudyPlanProgress | null;
  onCompleteLesson: (lessonId: number | string) => Promise<void>;
}) => {
  const timeline = getTimelineSessions(plan, progress);

  return (
    <Card className="sp-timeline-card">
      <span className="sp-kicker">المسار الزمني</span>
      <h2>جدول الدروس</h2>
      <div className="sp-timeline">
        {timeline.map((item, index) => (
          <article key={`${item.date}-${item.session.lesson_id}-${index}`} className={`sp-timeline-item status-${item.status}`}>
            <div className="sp-timeline-date">
              <strong>{formatPlanDate(item.date)}</strong>
              <span>{item.weekday}</span>
            </div>
            <div className="sp-timeline-dot" aria-hidden="true" />
            <div className="sp-timeline-content">
              <div>
                <strong>{item.session.title}</strong>
                <span>{item.session.minutes} دقيقة</span>
              </div>
              <div className="sp-action-row">
                <StatusPill tone={item.status === 'today' ? 'blue' : item.status === 'upcoming' ? 'ghost' : STATUS_TONES[item.status as StudyPlanProgressStatus]}>
                  {item.status === 'today' ? 'اليوم' : item.status === 'upcoming' ? 'قادم' : STATUS_LABELS[item.status as StudyPlanProgressStatus]}
                </StatusPill>
                {item.session.lesson_id && item.status !== 'completed' && (
                  <Button variant="ghost" onClick={() => onCompleteLesson(item.session.lesson_id!)} className="sp-compact-btn">أكملت</Button>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
};

const ReviewPanel = ({ progress }: { progress: StudyPlanProgress | null }) => {
  const nextLesson = progress?.next_lesson;
  const studyPlanFlashcardsUrl = progress?.plan_id
    ? `/flashcards?scope=study_plan&plan_id=${progress.plan_id}`
    : '/flashcards';
  const weakTopicsFlashcardsUrl = progress?.plan_id
    ? `/flashcards?scope=weak_topics&plan_id=${progress.plan_id}`
    : '/flashcards?scope=weak_topics';

  return (
    <div className="sp-review-grid">
      <Card className="sp-review-card">
        <span className="sp-kicker">مراجعة فورية</span>
        <h3>بطاقات ذكية</h3>
        <p>راجع أهم التعاريف والقوانين من الدرس التالي أو نقاط الضعف.</p>
        <div className="sp-action-row">
          <Link className="ed-btn ed-btn-primary" to={studyPlanFlashcardsUrl}>بطاقات اليوم</Link>
          {nextLesson && (
            <Link className="ed-btn ed-btn-secondary" to={`/flashcards?lessonId=${nextLesson.id}`}>
              بطاقات الدرس التالي
            </Link>
          )}
          <Link className="ed-btn ed-btn-ghost" to={weakTopicsFlashcardsUrl}>بطاقات نقاط الضعف</Link>
        </div>
      </Card>
      <Card className="sp-review-card">
        <span className="sp-kicker">اختبار نهاية الأسبوع</span>
        <h3>اختبار قصير</h3>
        <p>ولّد اختباراً من الدروس المجدولة فقط حتى تقيس تقدم الخطة.</p>
        <Link className="ed-btn ed-btn-secondary" to={nextLesson ? `/quiz?lessonId=${nextLesson.id}` : '/quiz'}>أنشئ اختباراً</Link>
      </Card>
      <Card className="sp-review-card">
        <span className="sp-kicker">حل موجّه</span>
        <h3>اسأل AI</h3>
        <p>اطلب شرح خطوة بخطوة للدرس التالي أو لأي نقطة غير واضحة.</p>
        <Link className="ed-btn ed-btn-ghost" to={nextLesson ? `/ask-ai?lessonId=${nextLesson.id}` : '/ask-ai'}>اسأل الآن</Link>
      </Card>
    </div>
  );
};

const AchievementPanel = ({ progress }: { progress: StudyPlanProgress | null }) => {
  const completedThisWeek = (progress?.scheduled_lessons ?? [])
    .filter((lesson) => lesson.status === 'completed')
    .slice(0, 7)
    .length;

  return (
    <div className="sp-achievement-grid">
      <Card className="sp-achievement-card">
        <span className="sp-kicker">إنجازات الخطة</span>
        <h3>{completedThisWeek}</h3>
        <p>دروس مكتملة في آخر مجموعة ظاهرة من الجدول.</p>
      </Card>
      <Card className="sp-achievement-card">
        <span className="sp-kicker">السلسلة</span>
        <h3>قريباً</h3>
        <p>سيظهر عدد أيام الالتزام عند ربط خدمة الإنجازات بالحساب.</p>
      </Card>
      <Card className="sp-achievement-card">
        <span className="sp-kicker">XP</span>
        <h3>قريباً</h3>
        <p>سيتم احتساب النقاط من الدروس المكتملة والاختبارات.</p>
      </Card>
      <Card className="sp-achievement-card">
        <span className="sp-kicker">الشارات</span>
        <h3>قريباً</h3>
        <p>الشارات ستظهر بعد اكتمال ربط نظام المكافآت.</p>
      </Card>
    </div>
  );
};

export const StudyPlanPage = () => {
  const [viewState, setViewState] = useState<StudyPlanViewState>('loading');
  const [units, setUnits] = useState<UnitCatalogItem[]>(fallbackCurriculumUnits);
  const [activePlan, setActivePlan] = useState<StudyPlan | null>(null);
  const [setupForm, setSetupForm] = useState<SetupFormState>(() => getDefaultSetupForm());
  const [activeTab, setActiveTab] = useState<ActiveTab>('today');
  const [errorMessage, setErrorMessage] = useState<string>('تعذر تحميل خطة الدراسة.');
  const { progress, loading: progressLoading, refetch: refetchProgress } = useStudyPlanProgress(activePlan);

  const setupErrors = useMemo(() => validateSetup(setupForm), [setupForm]);

  const loadInitialData = async () => {
    setViewState('loading');
    try {
      const [curriculumUnits, plan] = await Promise.all([
        curriculumApi.getUnits().catch(() => fallbackCurriculumUnits),
        studyPlanApi.getActiveStudyPlan(),
      ]);
      setUnits(curriculumUnits.length ? curriculumUnits : fallbackCurriculumUnits);
      setActivePlan(plan);
      setViewState(plan && hasGeneratedSchedule(plan) ? 'active' : plan ? 'setup' : 'empty');
    } catch {
      setErrorMessage('تعذر تحميل بيانات خطة الدراسة.');
      setViewState('error');
    }
  };

  useEffect(() => {
    void loadInitialData();
  }, []);

  useEffect(() => {
    if (activePlan && hasGeneratedSchedule(activePlan, progress) && viewState !== 'generating') {
      setViewState('active');
    }
  }, [activePlan, progress, viewState]);

  const startSetup = (planType: PlanType = 'semester') => {
    setSetupForm({ ...getDefaultSetupForm(), planType });
    setViewState('setup');
  };

  const generatePlan = async () => {
    const errors = validateSetup(setupForm);
    if (Object.keys(errors).length > 0) {
      setErrorMessage(Object.values(errors)[0] ?? 'تحقق من بيانات الخطة.');
      return;
    }

    setViewState('generating');
    try {
      const payload = buildGenerationPayload(setupForm);
      const generatedPlan = await studyPlanApi.generateStudyPlan(payload);
      setActivePlan(generatedPlan);
      if (getScheduledLessonSessionCount(generatedPlan) === 0) {
        setErrorMessage('تم حفظ الإعدادات، لكن الخطة لم تتضمن دروساً مجدولة بعد. تحقق من الخادم أو عدّل الإعدادات.');
        setViewState('setup');
        return;
      }
      setViewState('active');
      setActiveTab('today');
      await refetchProgress();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'تعذر إنشاء الخطة.');
      setViewState('setup');
    }
  };

  const completeLesson = async (lessonId: number | string) => {
    if (!activePlan?.id) return;
    try {
      const updatedPlan = await studyPlanApi.completeStudyPlanLesson(activePlan.id, lessonId);
      setActivePlan(updatedPlan);
      await refetchProgress();
    } catch {
      setErrorMessage('تعذر تحديث حالة الدرس.');
    }
  };

  if (viewState === 'loading') {
    return <StudyPlanSkeleton />;
  }

  if (viewState === 'error') {
    return (
      <StudyPlanError
        message={errorMessage}
        onRetry={() => void loadInitialData()}
        onSetup={() => startSetup()}
      />
    );
  }

  if (viewState === 'empty') {
    return <StudyPlanEmptyState units={units} onStart={() => startSetup()} />;
  }

  if (viewState === 'setup' || viewState === 'generating') {
    return (
      <StudyPlanSetupWizard
        units={units}
        form={setupForm}
        errors={setupErrors}
        isGenerating={viewState === 'generating'}
        onChange={setSetupForm}
        onGenerate={() => void generatePlan()}
        onBackToEmpty={() => setViewState(activePlan && hasGeneratedSchedule(activePlan, progress) ? 'active' : 'empty')}
      />
    );
  }

  if (activePlan && hasGeneratedSchedule(activePlan, progress)) {
    return (
      <StudyPlanActiveDashboard
        plan={activePlan}
        progress={progress}
        progressLoading={progressLoading}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onSetupNew={() => startSetup('custom')}
        onCompleteLesson={completeLesson}
      />
    );
  }

  return <StudyPlanEmptyState units={units} onStart={() => startSetup()} />;
};
