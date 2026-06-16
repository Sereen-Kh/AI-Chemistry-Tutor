import { useState, useEffect, useMemo } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { curriculumApi, fallbackCurriculumUnits, studyPlanApi, notificationsApi } from '../api';
import { Button, Card, ErrorBanner, LoadingSkeleton, PageHeader, ProgressBar, StatusPill } from '../components/DesignSystem';
import type { StudyPlan, UnitCatalogItem } from '../types';

export interface LessonMetadata {
  lesson_id: number;
  chapter_id: number;
  unit_id: number;
  unit_number: number;
  semester: number;
  title_ar: string;
  duration_minutes: number;
  difficulty: 'easy' | 'medium' | 'hard';
  completion_status: 'completed' | 'current' | 'weak' | 'locked';
  weak_score: number;
  pageStart: number;
  pageEnd: number;
}

const chapterColorCycle: Array<'blue' | 'teal' | 'gold' | 'coral' | 'purple'> = ['blue', 'teal', 'purple', 'gold', 'coral'];

const allLessonIds = (units: UnitCatalogItem[]) =>
  units.flatMap((unit) => unit.chapters.flatMap((chapter) => chapter.lessons.map((lesson) => lesson.id)));

const semesterLessonIds = (units: UnitCatalogItem[], semester: number) =>
  units
    .filter((unit) => unit.semester === semester)
    .flatMap((unit) => unit.chapters.flatMap((chapter) => chapter.lessons.map((lesson) => lesson.id)));

const dateInputValueFromToday = (daysFromNow: number): string => {
  const date = new Date();
  date.setDate(date.getDate() + daysFromNow);
  return date.toISOString().slice(0, 10);
};

const daysUntilDate = (dateValue: string): number => {
  const target = new Date(dateValue);
  const today = new Date();
  target.setHours(23, 59, 59, 999);
  today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.ceil((target.getTime() - today.getTime()) / 86_400_000));
};

const dailyStudyMinutes = (value: string): number => {
  if (value === 'ساعة واحدة') return 60;
  if (value === 'ساعتان') return 120;
  if (value === '3 ساعات') return 180;
  if (value === '4 ساعات أو أكثر') return 240;
  return 0;
};

type LearningRailSection = 'today' | 'continue' | 'weak' | 'ai' | 'timeline' | 'review' | 'exam' | 'achievement';

const railSectionLabels: Record<LearningRailSection, string> = {
  today: 'اليوم',
  continue: 'الدرس الحالي',
  weak: 'نقاط الضعف',
  ai: 'توصيات الذكاء',
  timeline: 'المسار',
  review: 'المراجعة',
  exam: 'الاختبار',
  achievement: 'الإنجاز',
};

const railSectionMessages: Record<LearningRailSection, string> = {
  today: 'ابدأ من هنا',
  continue: 'تابع مسارك الحالي بثبات.',
  weak: 'هذا موضوع ضعيف يحتاج مراجعة.',
  ai: 'هذه اقتراحات مبنية على تقدمك.',
  timeline: 'راقب الخطة وهي تتقدم معك.',
  review: 'حوّل المعرفة إلى ممارسة سريعة.',
  exam: 'اقترب موعدك النهائي، ركز هنا.',
  achievement: 'اقتربت من هدف اليوم.',
};

const railSectionAccents: Record<LearningRailSection, 'teal' | 'blue' | 'coral' | 'purple' | 'gold'> = {
  today: 'blue',
  continue: 'teal',
  weak: 'coral',
  ai: 'purple',
  timeline: 'blue',
  review: 'teal',
  exam: 'gold',
  achievement: 'purple',
};

const StudyScrollSection = ({
  section,
  children,
  className = '',
}: {
  section: LearningRailSection;
  children: ReactNode;
  className?: string;
}) => (
  <section
    id={`study-section-${section}`}
    data-rail-section={section}
    data-accent={railSectionAccents[section]}
    className={`study-scroll-section reveal-card ${className}`.trim()}
  >
    {children}
  </section>
);

const LearningPathRail = ({
  sections,
  activeSection,
}: {
  sections: LearningRailSection[];
  activeSection: LearningRailSection;
}) => (
  <aside className="study-path-rail" aria-label="مراحل الصفحة">
    <span className="study-path-caption">مسار التعلم</span>
    <div className="study-path-list">
      {sections.map((section) => (
        <button
          key={section}
          type="button"
          data-accent={railSectionAccents[section]}
          className={`study-path-item ${activeSection === section ? 'active' : ''}`}
          onClick={() => {
            const node = document.getElementById(`study-section-${section}`);
            node?.scrollIntoView({
              behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
              block: 'start',
            });
          }}
        >
          <span className="study-path-dot" aria-hidden="true" />
          <span>{railSectionLabels[section]}</span>
        </button>
      ))}
    </div>
  </aside>
);

const ContextualStudyAssistant = ({ activeSection }: { activeSection: LearningRailSection }) => (
  <aside className="study-context-assistant" aria-live="polite">
    <div className="study-assistant-core" aria-hidden="true">
      <span className="study-assistant-orbit orbit-a" />
      <span className="study-assistant-orbit orbit-b" />
      <span className="study-assistant-nucleus" />
    </div>
    <div className="study-assistant-copy">
      <strong>مرشد EduMind</strong>
      <p>{railSectionMessages[activeSection]}</p>
    </div>
  </aside>
);

export const StudyPlanPage = () => {

  // Core view and plan states
  const [activeView, setActiveView] = useState<'home' | 'semester-create' | 'exam-create' | 'generating' | 'semester-view' | 'exam-view'>('home');
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [catalogWarning, setCatalogWarning] = useState<string | null>(null);
  const [curriculumUnits, setCurriculumUnits] = useState<UnitCatalogItem[]>(fallbackCurriculumUnits);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  
  // Simulated offline mode (banner always available for demonstration)
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [activeSection, setActiveSection] = useState<LearningRailSection>('today');

  // Active view tabs for active plan view
  const [activePlanTab, setActivePlanTab] = useState<'timeline' | 'weekly' | 'chapters'>('timeline');

  // Semester Creator Form State
  const [semStep, setSemStep] = useState(1);
  const [semStartDate, setSemStartDate] = useState('2024-09-01');
  const [semEndDate, setSemEndDate] = useState('2025-06-15');
  const [semStudyDays, setSemStudyDays] = useState<string[]>(['ن', 'ث', 'ر', 'خ', 'ج']);
  const [semLessonDuration, setSemLessonDuration] = useState('45 دقيقة');
  const [semWeeklyRest, setSemWeeklyRest] = useState('يوم راحة كل 5 دروس');
  const [semSelectedLessons, setSemSelectedLessons] = useState<number[]>(() => allLessonIds(fallbackCurriculumUnits));
  const [semValidationError, setSemValidationError] = useState<string | null>(null);

  // Exam Creator Form State
  const [examStep, setExamStep] = useState(1);
  const [examTitle, setExamTitle] = useState('امتحان الكيمياء — الفصل الثاني');
  const [examDate, setExamDate] = useState(() => dateInputValueFromToday(13));
  const [examDailyStudyHours, setExamDailyStudyHours] = useState('ساعتان');
  const [examPriority, setExamPriority] = useState('balanced');
  const [examSelectedLessons, setExamSelectedLessons] = useState<number[]>(() => semesterLessonIds(fallbackCurriculumUnits, 1));
  const [examValidationError, setExamValidationError] = useState<string | null>(null);

  // AI generating spinner logs
  const [genTitle, setGenTitle] = useState('');
  const [genSteps, setGenSteps] = useState<{ text: string; status: 'wait' | 'active' | 'done' }[]>([]);

  // Accordion collapsed state for chapters in selectors
  const [collapsedChapters, setCollapsedChapters] = useState<Record<string, boolean>>({});

  // Monitor network status
  useEffect(() => {
    const goOnline = () => setIsOffline(false);
    const goOffline = () => setIsOffline(true);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    curriculumApi.getUnits()
      .then((units) => {
        if (cancelled || units.length === 0) return;
        setCurriculumUnits(units);
        setCatalogWarning(null);
      })
      .catch(() => {
        if (!cancelled) {
          setCurriculumUnits(fallbackCurriculumUnits);
          setCatalogWarning('تعذر تحميل فهرس الدروس من الخادم. تُستخدم بنية الكتاب المحلية للتجربة.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const ids = allLessonIds(curriculumUnits);
    if (ids.length === 0) return;
    queueMicrotask(() => {
      setSemSelectedLessons((current) => {
        const kept = current.filter((id) => ids.includes(id));
        return kept.length > 0 ? kept : ids;
      });
      setExamSelectedLessons((current) => {
        const kept = current.filter((id) => ids.includes(id));
        return kept.length > 0 ? kept : semesterLessonIds(curriculumUnits, 1);
      });
    });
  }, [curriculumUnits]);

  // Map the real curriculum catalog into study-plan lesson metadata.
  const curriculumLessons = useMemo<LessonMetadata[]>(() => {
    const catalogLessons = curriculumUnits.flatMap((unit) =>
      unit.chapters.flatMap((chapter) => chapter.lessons.map((lesson) => ({ unit, chapter, lesson }))),
    );
    return catalogLessons.map(({ unit, chapter, lesson }, index) => {
          const displayIndex = index + 1;
          const status: LessonMetadata['completion_status'] =
            displayIndex <= 3 ? 'completed' : displayIndex === 4 ? 'current' : lesson.difficulty >= 3 ? 'weak' : 'locked';
          return {
            lesson_id: lesson.id,
            chapter_id: chapter.id,
            unit_id: unit.id,
            unit_number: unit.unit_number,
            semester: unit.semester,
            title_ar: lesson.title_ar,
            duration_minutes: lesson.duration_min || 45,
            difficulty: lesson.difficulty <= 1 ? 'easy' : lesson.difficulty === 2 ? 'medium' : 'hard',
            completion_status: status,
            weak_score: status === 'weak' ? 60 + Math.min(lesson.difficulty * 8, 30) : Math.max(0, lesson.difficulty * 10 - displayIndex),
            pageStart: lesson.page_start ?? 0,
            pageEnd: lesson.page_end ?? lesson.page_start ?? 0,
          };
        });
  }, [curriculumUnits]);

  const completedLessonCount = useMemo(
    () => curriculumLessons.filter((lesson) => lesson.completion_status === 'completed').length,
    [curriculumLessons],
  );

  const currentLesson = useMemo(
    () => curriculumLessons.find((lesson) => lesson.completion_status === 'current') ?? curriculumLessons[0],
    [curriculumLessons],
  );

  const weakLessons = useMemo(
    () =>
      [...curriculumLessons]
        .filter((lesson) => lesson.weak_score >= 35 || lesson.completion_status === 'weak')
        .sort((left, right) => right.weak_score - left.weak_score)
        .slice(0, 3),
    [curriculumLessons],
  );

  const visibleRailSections = useMemo<LearningRailSection[]>(() => {
    if (activeView === 'home') return ['today', 'continue', 'weak', 'ai', 'review', 'exam'];
    if (activeView === 'semester-view') return ['today', 'weak', 'timeline', 'review', 'achievement'];
    if (activeView === 'exam-view') return ['today', 'weak', 'review', 'timeline', 'exam', 'achievement'];
    return [];
  }, [activeView]);

  // Fetch active study plan on load
  const loadPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const active = await studyPlanApi.getStudyPlan();
      setPlan(active);
      
      // Determine if there is an active plan type configured
      if (active && active.chapters.length > 0) {
        // If plan has a custom config, check if it's an exam plan or semester plan
        const hasExamConfig = active.config?.examDate;
        setActiveView(hasExamConfig ? 'exam-view' : 'semester-view');
      } else {
        setActiveView('home');
      }
    } catch {
      setError('تعذر تحميل خطة الدراسة. الرجاء التحقق من اتصال الخادم.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadPlan();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return undefined;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const cards = Array.from(document.querySelectorAll<HTMLElement>('.study-plan-page .reveal-card'));

    if (prefersReducedMotion) {
      cards.forEach((card) => card.classList.add('is-visible'));
      return undefined;
    }

    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.16, rootMargin: '0px 0px -8% 0px' },
    );

    cards.forEach((card) => revealObserver.observe(card));
    return () => revealObserver.disconnect();
  }, [activeView, activePlanTab, plan]);

  useEffect(() => {
    if (visibleRailSections.length === 0 || typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      return undefined;
    }

    const sections = Array.from(document.querySelectorAll<HTMLElement>('.study-plan-page [data-rail-section]'));
    if (!sections.length) return undefined;

    const sectionObserver = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio);

        if (!visible[0]) return;
        const next = visible[0].target.getAttribute('data-rail-section') as LearningRailSection | null;
        if (next) setActiveSection(next);
      },
      { threshold: [0.2, 0.45, 0.72], rootMargin: '-18% 0px -48% 0px' },
    );

    sections.forEach((section) => sectionObserver.observe(section));
    return () => sectionObserver.disconnect();
  }, [activeView, activePlanTab, visibleRailSections, plan]);

  // Calculation Logic: sum selected lesson durations dynamically
  const semTotalDuration = useMemo(() => {
    return curriculumLessons
      .filter(l => semSelectedLessons.includes(l.lesson_id))
      .reduce((sum, l) => sum + l.duration_minutes, 0);
  }, [semSelectedLessons, curriculumLessons]);

  const examTotalDuration = useMemo(() => {
    return curriculumLessons
      .filter(l => examSelectedLessons.includes(l.lesson_id))
      .reduce((sum, l) => sum + l.duration_minutes, 0);
  }, [examSelectedLessons, curriculumLessons]);

  const draftExamDaysRemaining = useMemo(() => daysUntilDate(examDate), [examDate]);

  // Handle Chapter Accordion Toggle
  const toggleChapterCollapse = (chId: number) => {
    setCollapsedChapters(prev => ({ ...prev, [chId]: !prev[chId] }));
  };

  // Chapter Checkbox Selection logic
  const handleChapterCheckbox = (chId: number, isSem: boolean) => {
    const targetLessons = curriculumLessons.filter(l => l.chapter_id === chId).map(l => l.lesson_id);
    const selected = isSem ? semSelectedLessons : examSelectedLessons;
    const setSelected = isSem ? setSemSelectedLessons : setExamSelectedLessons;

    const allSelected = targetLessons.every(id => selected.includes(id));
    if (allSelected) {
      // Deselect all in this chapter
      setSelected(prev => prev.filter(id => !targetLessons.includes(id)));
    } else {
      // Select all in this chapter
      setSelected(prev => Array.from(new Set([...prev, ...targetLessons])));
    }
  };

  const handleLessonCheckbox = (lessonId: number, isSem: boolean) => {
    const selected = isSem ? semSelectedLessons : examSelectedLessons;
    const setSelected = isSem ? setSemSelectedLessons : setExamSelectedLessons;

    if (selected.includes(lessonId)) {
      setSelected(prev => prev.filter(id => id !== lessonId));
    } else {
      setSelected(prev => [...prev, lessonId]);
    }
  };

  // Select all or clear all
  const selectAll = (isSem: boolean) => {
    const ids = curriculumLessons.map(l => l.lesson_id);
    if (isSem) setSemSelectedLessons(ids);
    else setExamSelectedLessons(ids);
  };

  const clearAll = (isSem: boolean) => {
    if (isSem) setSemSelectedLessons([]);
    else setExamSelectedLessons([]);
  };

  // Form step navigation & validations
  const handleSemesterNext = () => {
    setSemValidationError(null);
    if (semStep === 1) {
      // Validation 1: Start Date must be before End Date
      if (new Date(semStartDate) >= new Date(semEndDate)) {
        setSemValidationError('تاريخ بداية الفصل الدراسي يجب أن يكون قبل تاريخ نهايته.');
        return;
      }
      // Validation 2: At least one study day must be selected
      if (semStudyDays.length === 0) {
        setSemValidationError('الرجاء اختيار يوم دراسي واحد على الأقل في الأسبوع.');
        return;
      }
      setSemStep(2);
    } else if (semStep === 2) {
      // Validation 3: At least one lesson must be selected
      if (semSelectedLessons.length === 0) {
        setSemValidationError('الرجاء اختيار درساً واحداً على الأقل للمذاكرة.');
        return;
      }
      setSemStep(3);
    }
  };

  const handleExamNext = () => {
    setExamValidationError(null);
    if (examStep === 1) {
      // Validation 1: Exam Date must be in the future
      if (new Date(examDate) <= new Date()) {
        setExamValidationError('تاريخ الامتحان يجب أن يكون في المستقبل.');
        return;
      }
      if (dailyStudyMinutes(examDailyStudyHours) <= 0) {
        setExamValidationError('الرجاء تحديد عدد ساعات دراسة يومية صحيح.');
        return;
      }
      setExamStep(2);
    } else if (examStep === 2) {
      // Validation 2: At least one lesson must be selected
      if (examSelectedLessons.length === 0) {
        setExamValidationError('الرجاء تحديد بعض الدروس لإدراجها في خطة المراجعة.');
        return;
      }
      setExamStep(3);
    }
  };

  // AI Plan Generation simulation
  const startGeneratingPlan = (type: 'semester' | 'exam') => {
    setActiveView('generating');
    setGenTitle(type === 'semester' ? 'الذكاء الاصطناعي يبني خطة الفصل...' : 'الذكاء الاصطناعي يبني خطة الامتحان...');
    
    const semSteps = [
      'حساب الأيام الدراسية وتوزيع الحصص...',
      'توزيع الدروس الذكي على الأسابيع...',
      'تحديد الفصول الصعبة ومضاعفة حيزها الدراسي...',
      'إدراج فترات الراحة وأيام المراجعة التراكمية...',
      'جاهزة! تم إعداد 36 يوماً دراسياً مجدولاً بنجاح'
    ];
    const examSteps = [
      'حساب الأيام المتبقية حتى الامتحان...',
      'تحليل وتقييم نقاط الضعف المسجلة للطالب...',
      'تخصيص يومين إضافيين للمفاهيم الصعبة (موازنة المعادلات)...',
      'توزيع الدروس التسعة على الأيام الـ 13 المتاحة...',
      'جاهزة! تم إعداد خطة المراجعة المكثفة للامتحان'
    ];
    const stepsList = type === 'semester' ? semSteps : examSteps;

    setGenSteps(stepsList.map(stepText => ({ text: stepText, status: 'wait' })));

    let currentIndex = 0;
    const interval = setInterval(() => {
      setGenSteps(prev => 
        prev.map((step, idx) => {
          if (idx < currentIndex) return { ...step, status: 'done' };
          if (idx === currentIndex) return { ...step, status: 'active' };
          return step;
        })
      );

      if (currentIndex === stepsList.length) {
        clearInterval(interval);
        
        // Execute API save
        const savePlan = async () => {
          const config = type === 'semester' ? {
            startDate: semStartDate,
            endDate: semEndDate,
            studyDays: semStudyDays,
            lessonDuration: semLessonDuration,
            weeklyRest: semWeeklyRest,
            lessonIds: semSelectedLessons
          } : {
            title: examTitle,
            examDate: examDate,
            dailyStudyHours: examDailyStudyHours,
            priority: examPriority,
            lessonIds: examSelectedLessons
          };

          try {
            const nextPlan = await studyPlanApi.generatePlan(config);
            setPlan(nextPlan);
            
            // Add a welcome system notification
              await notificationsApi.getNotifications();
              dispatchNotificationCreated();

            setSuccessToast(type === 'semester' ? 'تم إنشاء خطة الفصل الدراسي بنجاح! 🎉' : 'تم إنشاء خطة الامتحان بنجاح! 🎯');
            setActiveView(type === 'semester' ? 'semester-view' : 'exam-view');
            setTimeout(() => setSuccessToast(null), 4000);
          } catch {
            setError('فشل في حفظ الخطة بالذكاء الاصطناعي.');
            setActiveView('home');
          }
        };
        void savePlan();
      }
      currentIndex++;
    }, 700);
  };

  const dispatchNotificationCreated = () => {
    window.dispatchEvent(new Event('notifications-updated'));
  };

  // Interactive Action: Complete Lesson
  const markLessonComplete = async (lessonId: number | string) => {
    if (!plan) return;
    try {
      const updated = await studyPlanApi.completeLesson('active-plan', lessonId);
      setPlan(updated);
      setSuccessToast('أحسنت! تم إكمال الدرس بنجاح ومزامنة تقدمك. 🌟');
      setTimeout(() => setSuccessToast(null), 3000);
    } catch (e) {
      console.error(e);
    }
  };

  // Group selection curriculum for semester/exam lesson pickers
  const groupedCurriculum = useMemo(() => {
    return curriculumUnits.flatMap((unit) =>
      unit.chapters.map((chapter, index) => ({
        id: chapter.id,
        title: chapter.title_ar,
        subtitle: `الوحدة ${unit.unit_number} · الفصل ${chapter.order} · ${unit.semester === 1 ? 'الفصل الدراسي الأول' : 'الفصل الدراسي الثاني'}`,
        color: chapterColorCycle[index % chapterColorCycle.length],
        lessons: curriculumLessons.filter(l => l.chapter_id === chapter.id),
      })),
    );
  }, [curriculumLessons, curriculumUnits]);

  // Exam Countdown calculation
  const examDaysRemaining = useMemo(() => {
    if (activeView !== 'exam-view') return 13;
    const targetDate = plan?.config?.examDate
      ? plan.config.examDate
      : examDate;
    return daysUntilDate(targetDate);
  }, [activeView, plan, examDate]);

  // Final Revision Mode detection (last 2 days before exam)
  const isFinalRevisionMode = examDaysRemaining > 0 && examDaysRemaining <= 2;
  const showMotionLayout = visibleRailSections.length > 0;
  const displayedActiveSection = visibleRailSections.includes(activeSection) ? activeSection : visibleRailSections[0] ?? 'today';
  const timelinePrimaryLesson = currentLesson ?? curriculumLessons[0];
  const timelineReviewLesson = weakLessons[0] ?? timelinePrimaryLesson;
  const timelineNextLesson =
    curriculumLessons.find((lesson) => lesson.lesson_id !== timelinePrimaryLesson?.lesson_id && lesson.completion_status !== 'completed')
    ?? timelinePrimaryLesson;

  if (loading) {
    return (
      <div className="page-stack">
        <PageHeader eyebrow="خطة الدراسة" title="خارطة المذاكرة الذكية" subtitle="جار استرداد خطتك الحالية..." />
        <LoadingSkeleton rows={6} />
      </div>
    );
  }

  return (
    <div className="page-stack study-plan-page" dir="rtl">
      <div className="study-plan-atmosphere" aria-hidden="true">
        <span className="study-atmosphere-particle particle-a" />
        <span className="study-atmosphere-particle particle-b" />
        <span className="study-atmosphere-particle particle-c" />
      </div>
      
      {/* Offline Cached Banner */}
      {isOffline && (
        <div className="offline-banner" role="status">
          <span>⚠️</span>
          <span>أنت تعمل في وضع عدم الاتصال. يتم حفظ التحديثات والتقدم محلياً وسيجري مزامنتها بمجرد عودة الاتصال.</span>
        </div>
      )}

      {/* Success Toast */}
      {successToast && (
        <div className="toast-success" role="alert" aria-live="assertive">
          <span>✨</span>
          <span>{successToast}</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div style={{ marginBottom: '20px' }}>
          <ErrorBanner message={error} onRetry={loadPlan} />
        </div>
      )}

      {catalogWarning && (
        <div style={{ marginBottom: '20px' }}>
          <ErrorBanner message={catalogWarning} />
        </div>
      )}

      <div className={`study-plan-shell ${showMotionLayout ? 'has-rail' : 'no-rail'}`}>
        {showMotionLayout && <LearningPathRail sections={visibleRailSections} activeSection={displayedActiveSection} />}
        <div className="study-plan-stage">

      {/* ── HOME VIEW ── */}
      {activeView === 'home' && (
        <div className="study-view-transition">
          <StudyScrollSection section="today" className="study-hero-section">
            <PageHeader
              eyebrow="منظم الجدول الدراسي"
              title="خطة الدراسة المخصصة بالذكاء الاصطناعي"
              subtitle="جدول يومي يربط بين التعلّم، المراجعة، والامتحان من دون أن تفقد إحساس التقدم."
            />

            <Card className="study-note-card" style={{ background: 'rgba(78,135,245,.06)', borderColor: 'rgba(78,135,245,.25)' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                <span style={{ fontSize: '24px' }}>💡</span>
                <p style={{ color: 'var(--t2)', fontSize: '0.9rem', lineHeight: '1.7' }}>
                  لديك منهج كيمياء كامل يحتوي على 5 وحدات و15 درساً. المسار هنا يقسم يومك إلى تعلّم جديد، مراجعة سريعة،
                  وإنذار مبكر قبل الامتحان حتى تبقى الخطة واضحة وممتعة للعودة إليها كل يوم.
                </p>
              </div>
            </Card>
          </StudyScrollSection>

          <StudyScrollSection section="continue">
            <div className="study-plan-home-grid">
              {plan && plan.chapters.length > 0 ? (
                <Card className="study-home-highlight-card" style={{ borderColor: 'rgba(0,212,168,.3)', background: 'rgba(0,212,168,.03)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', marginBottom: '14px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '20px' }}>📘</span>
                      <div>
                        <strong style={{ fontSize: '1rem', display: 'block' }}>خطة الدراسة النشطة</strong>
                        <StatusPill tone="teal">قيد التنفيذ</StatusPill>
                      </div>
                    </div>
                    <Button variant="secondary" onClick={() => setActiveView(plan.config?.examDate ? 'exam-view' : 'semester-view')}>
                      عرض الخطة ←
                    </Button>
                  </div>
                  <p style={{ color: 'var(--t2)', fontSize: '0.85rem', lineHeight: '1.7', marginBottom: '16px' }}>
                    تتضمن كافة فصول المنهج مع تقدم {plan.chapters[0]?.progress ?? 62}% في الوحدة الأولى وخط مراجعة جاهز لبقية الأسابيع.
                  </p>
                  <ProgressBar value={Math.round((completedLessonCount / curriculumLessons.length) * 100)} tone="teal" />
                </Card>
              ) : (
                <Card className="study-home-highlight-card">
                  <strong style={{ fontSize: '1rem' }}>لا توجد خطة مفعلة بعد</strong>
                  <p style={{ color: 'var(--t2)', lineHeight: '1.7' }}>
                    ابدأ بخطة فصل دراسي إذا أردت مساراً هادئاً ومستداماً، أو بخطة امتحان إذا كان الوقت ضيقاً وتحتاج مراجعة مكثفة.
                  </p>
                </Card>
              )}

              <Card className="study-home-highlight-card study-current-lesson-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <strong style={{ fontSize: '1rem', display: 'block' }}>تابع من الدرس الحالي</strong>
                    <span style={{ color: 'var(--t2)', fontSize: '0.8rem' }}>جلسة مركزة من {currentLesson?.duration_minutes ?? 20} دقيقة</span>
                  </div>
                  <StatusPill tone="blue">الآن</StatusPill>
                </div>
                <h3 style={{ fontSize: '1.08rem', marginBottom: '8px' }}>{currentLesson?.title_ar ?? 'المحاليل المائية'}</h3>
                <p style={{ color: 'var(--t2)', fontSize: '0.85rem', lineHeight: '1.7', marginBottom: '14px' }}>
                  صفحات {currentLesson?.pageStart ?? 2}–{currentLesson?.pageEnd ?? 4} · مستوى
                  {' '}{currentLesson?.difficulty === 'easy' ? 'سهل' : currentLesson?.difficulty === 'medium' ? 'متوسط' : 'صعب'}
                </p>
                <div className="study-mini-action-row">
                  <Link to={`/lessons/${currentLesson?.lesson_id ?? 401}`} className="ed-btn ed-btn-primary ed-btn-xs">ابدأ الدرس</Link>
                  <Link to={`/ask-ai?question=${encodeURIComponent(`ساعدني في فهم ${currentLesson?.title_ar ?? 'الدرس الحالي'}`)}`} className="ed-btn ed-btn-ghost ed-btn-xs">اسأل الذكاء</Link>
                </div>
              </Card>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="weak">
            <div className="study-plan-home-grid">
              <Card className="study-home-highlight-card">
                <div className="study-section-head">
                  <strong>نقاط الضعف</strong>
                  <StatusPill tone="coral">تحتاج مراجعة</StatusPill>
                </div>
                <div className="study-insight-list">
                  {weakLessons.map((lesson) => (
                    <article key={lesson.lesson_id}>
                      <strong>{lesson.title_ar}</strong>
                      <span>{lesson.weak_score}% مستوى إتقان · {lesson.duration_minutes} دقيقة مراجعة</span>
                    </article>
                  ))}
                </div>
              </Card>

              <Card className="study-home-highlight-card">
                <div className="study-section-head">
                  <strong>بطاقات واختبار قريب</strong>
                  <StatusPill tone="gold">جاهز للمراجعة</StatusPill>
                </div>
                <div className="study-insight-list">
                  <article>
                    <strong>4 بطاقات مستحقة اليوم</strong>
                    <span>تركز على الروابط والتراكيز والحموض القوية.</span>
                  </article>
                  <article>
                    <strong>اختبار قصير مقترح</strong>
                    <span>7 أسئلة على نقاط الضعف قبل الانتقال للدرس التالي.</span>
                  </article>
                </div>
              </Card>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="ai">
            <Card className="study-recommendation-band">
              <div className="study-section-head">
                <strong>توصيات الذكاء لمسارك</strong>
                <StatusPill tone="purple">مبنية على التقدم</StatusPill>
              </div>
              <div className="study-recommendation-grid">
                <article>
                  <strong>ابدأ بالمحاليل المائية اليوم</strong>
                  <span>لأنها تمهد مباشرة لمسائل التراكيز وتمديد المحاليل.</span>
                </article>
                <article>
                  <strong>راجع الروابط قبل الاختبار القصير</strong>
                  <span>هناك ضعف متكرر في تمييز الرابطة الأيونية عن التساهمية.</span>
                </article>
                <article>
                  <strong>أبق جلسة قصيرة للمراجعة النهائية</strong>
                  <span>15 دقيقة كافية لتثبيت ما أنجزته قبل الانتقال للوحدة التالية.</span>
                </article>
              </div>
            </Card>

            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '16px' }}>ابدأ إنشاء خطتك الدراسية</h2>
              <div className="type-picker" style={{ marginBottom: '0' }}>
            <button
              type="button"
              className="tp-card on"
              onClick={() => setActiveView('semester-create')}
              style={{ textAlign: 'right', background: 'transparent' }}
              aria-label="إنشاء خطة الفصل الدراسي"
            >
              <div className="tp-check">✓</div>
              <div className="tp-icon">📘</div>
              <h3 className="tp-title">خطة الفصل الدراسي</h3>
              <p className="tp-desc">تغطية كاملة للمنهج على مدار الفصل. توزيع متوازن أسبوعي يناسب دوامك اليومي مع فترات راحة تراكمية.</p>
              <div style={{ marginTop: '14px', display: 'flex', gap: '6px' }}>
                <StatusPill tone="teal">منهج كامل</StatusPill>
                <StatusPill tone="blue">توزيع أسبوعي</StatusPill>
                <StatusPill tone="ghost">مرن</StatusPill>
              </div>
            </button>

            <button
              type="button"
              className="tp-card"
              onClick={() => setActiveView('exam-create')}
              style={{ textAlign: 'right', background: 'transparent' }}
              aria-label="إنشاء خطة الامتحان"
            >
              <div className="tp-check">✓</div>
              <div className="tp-icon">🎯</div>
              <h3 className="tp-title">خطة الامتحان</h3>
              <p className="tp-desc">خطة مكثفة وسريعة للمراجعة قبل الامتحان. تحدد الدروس التي تريدها والذكاء الاصطناعي يركز على نقاط الضعف.</p>
              <div style={{ marginTop: '14px', display: 'flex', gap: '6px' }}>
                <StatusPill tone="gold">مكثفة</StatusPill>
                <StatusPill tone="coral">نقاط الضعف</StatusPill>
                <StatusPill tone="purple">عد تنازلي</StatusPill>
              </div>
            </button>
              </div>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="review">
            <div className="study-tools-strip">
              <Link to="/ask-ai" className="study-tool-tile">
                <strong>اسأل الذكاء</strong>
                <span>شرح سريع مدعوم بالمصادر</span>
              </Link>
              <Link to="/guided-lab" className="study-tool-tile">
                <strong>حل موجّه</strong>
                <span>مسألة بخطوات وتغذية راجعة</span>
              </Link>
              <Link to="/quizzes" className="study-tool-tile">
                <strong>اختبار قصير</strong>
                <span>تحقق من الفهم خلال دقائق</span>
              </Link>
              <Link to="/flashcards" className="study-tool-tile">
                <strong>بطاقات مراجعة</strong>
                <span>استرجاع سريع للمفاهيم</span>
              </Link>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="exam">
            <div className="study-plan-home-grid">
              <Card className="study-home-highlight-card study-exam-focus-card">
                <div className="study-section-head">
                  <strong>عدّاد الامتحان</strong>
                  <StatusPill tone="gold">13 يوماً</StatusPill>
                </div>
                <p style={{ color: 'var(--t2)', lineHeight: '1.8', margin: 0 }}>
                  إذا واصلت على وتيرة الدرس الحالي مع جلسة مراجعة يومية قصيرة، ستصل إلى آخر يومين مع مساحة مريحة للمراجعة النهائية فقط.
                </p>
              </Card>
              <Card className="study-home-highlight-card">
                <div className="study-section-head">
                  <strong>ملخص التنبيهات</strong>
                  <StatusPill tone="blue">متابعة يومية</StatusPill>
                </div>
                <div className="study-insight-list">
                  <article>
                    <strong>درس الغد</strong>
                    <span>تذكير صباحي بمراجعة الروابط الفلزية قبل الحصة التالية.</span>
                  </article>
                  <article>
                    <strong>اختبار الأسبوع</strong>
                    <span>موصى به بعد إكمال بطاقات التركيز المولي.</span>
                  </article>
                </div>
              </Card>
            </div>
          </StudyScrollSection>
        </div>
      )}

      {/* ── SEMESTER CREATE VIEW ── */}
      {activeView === 'semester-create' && (
        <div className="study-view-transition">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <Button variant="ghost" onClick={() => setActiveView('home')}>← رجوع</Button>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '700' }}>إعداد خطة الفصل الدراسي 📘</h2>
          </div>

          {/* Steps Indicator */}
          <div className="steps" style={{ maxWidth: '420px', margin: '0 auto 24px' }}>
            <div className="step-item" style={{ flexDirection: 'column', alignItems: 'center' }}>
              <div className={`step-dot ${semStep === 1 ? 'active' : semStep > 1 ? 'done' : ''}`}>
                {semStep > 1 ? '✓' : '1'}
              </div>
              <span className="step-label">الإعدادات</span>
            </div>
            <div className={`step-line ${semStep > 1 ? 'done' : ''}`} />
            <div className="step-item" style={{ flexDirection: 'column', alignItems: 'center' }}>
              <div className={`step-dot ${semStep === 2 ? 'active' : semStep > 2 ? 'done' : ''}`}>
                {semStep > 2 ? '✓' : '2'}
              </div>
              <span className="step-label">الدروس</span>
            </div>
            <div className={`step-line ${semStep > 2 ? 'done' : ''}`} />
            <div className="step-item" style={{ flexDirection: 'column', alignItems: 'center' }}>
              <div className={`step-dot ${semStep === 3 ? 'active' : ''}`}>3</div>
              <span className="step-label">المراجعة</span>
            </div>
          </div>

          {/* Inline Validation Alert */}
          {semValidationError && (
            <div className="error-banner" role="alert" style={{ marginBottom: '20px' }}>
              <span>⚠️ {semValidationError}</span>
            </div>
          )}

          {/* STEP 1: Settings */}
          {semStep === 1 && (
            <div className="grid2" style={{ alignItems: 'start' }}>
              <Card>
                <h3 style={{ fontSize: '1.05rem', marginBottom: '16px', fontWeight: 'bold' }}>إعدادات التوقيت والراحة</h3>
                
                <div className="form-group">
                  <label className="form-label" htmlFor="sem-start">تاريخ بداية الفصل الدراسي</label>
                  <input
                    id="sem-start"
                    type="date"
                    value={semStartDate}
                    onChange={e => setSemStartDate(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="sem-end">تاريخ نهاية الفصل الدراسي</label>
                  <input
                    id="sem-end"
                    type="date"
                    value={semEndDate}
                    onChange={e => setSemEndDate(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <span className="form-label">أيام الدراسة الأسبوعية</span>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                    {['ح', 'ن', 'ث', 'ر', 'خ', 'ج', 'س'].map(day => {
                      const isSelected = semStudyDays.includes(day);
                      return (
                        <button
                          key={day}
                          type="button"
                          className="ed-btn ed-btn-ghost"
                          onClick={() => {
                            if (isSelected) {
                              setSemStudyDays(prev => prev.filter(d => d !== day));
                            } else {
                              setSemStudyDays(prev => [...prev, day]);
                            }
                          }}
                          style={{
                            minWidth: '40px',
                            minHeight: '40px',
                            padding: '0',
                            borderRadius: '50%',
                            background: isSelected ? 'var(--acc)' : 'transparent',
                            color: isSelected ? '#fff' : 'var(--t2)',
                            borderColor: isSelected ? 'var(--acc)' : 'var(--bg5)'
                          }}
                          aria-pressed={isSelected}
                        >
                          {day}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="sem-duration">مدة جلسة المذاكرة للدرس الواحد</label>
                  <select
                    id="sem-duration"
                    value={semLessonDuration}
                    onChange={e => setSemLessonDuration(e.target.value)}
                  >
                    <option value="30 دقيقة">30 دقيقة</option>
                    <option value="45 دقيقة">45 دقيقة (موصى به)</option>
                    <option value="60 دقيقة">60 دقيقة</option>
                    <option value="90 دقيقة">90 دقيقة</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="sem-rest">جدولة فترات الراحة</label>
                  <select
                    id="sem-rest"
                    value={semWeeklyRest}
                    onChange={e => setSemWeeklyRest(e.target.value)}
                  >
                    <option value="بدون راحة مجدولة">بدون راحة مجدولة</option>
                    <option value="يوم راحة كل 5 دروس">يوم راحة كل 5 دروس</option>
                    <option value="يوم راحة كل أسبوع">يوم راحة كل أسبوع</option>
                  </select>
                </div>
              </Card>

              <Card>
                <h3 style={{ fontSize: '1.05rem', marginBottom: '16px', fontWeight: 'bold' }}>معاينة المدة الزمنية</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', textAlign: 'center', marginBottom: '16px' }}>
                  <div className="card-sm">
                    <strong style={{ fontSize: '1.5rem', color: 'var(--acc)', display: 'block' }}>9</strong>
                    <span style={{ fontSize: '0.75rem', color: 'var(--t2)' }}>أشهر فصلية</span>
                  </div>
                  <div className="card-sm">
                    <strong style={{ fontSize: '1.5rem', color: 'var(--teal)', display: 'block' }}>36</strong>
                    <span style={{ fontSize: '0.75rem', color: 'var(--t2)' }}>أسبوعاً</span>
                  </div>
                  <div className="card-sm">
                    <strong style={{ fontSize: '1.5rem', color: 'var(--gold)', display: 'block' }}>180</strong>
                    <span style={{ fontSize: '0.75rem', color: 'var(--t2)' }}>يوم دراسي</span>
                  </div>
                </div>
                <div className="info-banner" style={{ background: 'rgba(0, 212, 168, 0.08)', borderColor: 'rgba(0, 212, 168, 0.25)', marginBottom: '16px' }}>
                  <span>✅</span>
                  <p style={{ color: 'var(--t2)', fontSize: '0.85rem' }}>عدد الأيام الدراسية كافٍ جداً لتغطية الـ 15 درساً بشكل مريح مع المراجعة.</p>
                </div>
                <div className="card-sm">
                  <h4 style={{ fontSize: '0.85rem', fontWeight: '700', marginBottom: '8px' }}>توزيع الخطة للفصول</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>المحاليل والحموض</span><span style={{ color: 'var(--teal)' }}>أيلول - تشرين</span></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>التفاعلات الكيميائية</span><span style={{ color: 'var(--acc)' }}>كانون الأول</span></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>الأملاح والعضوية</span><span style={{ color: 'var(--pur)' }}>نيسان - أيار</span></div>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* STEP 2: Lesson Selector */}
          {semStep === 2 && (
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 'bold' }}>اختر الدروس المطلوبة</h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--t2)' }}>
                    الدروس المحددة: <strong>{semSelectedLessons.length} من {curriculumLessons.length}</strong>
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <Button variant="secondary" onClick={() => selectAll(true)} className="ed-btn-xs">تحديد الكل</Button>
                  <Button variant="ghost" onClick={() => clearAll(true)} className="ed-btn-xs">إلغاء الكل</Button>
                  <span style={{ fontSize: '0.85rem', alignSelf: 'center', marginRight: '8px' }}>
                    إجمالي الوقت: <strong style={{ color: 'var(--teal)' }}>{semTotalDuration} دقيقة</strong>
                  </span>
                </div>
              </div>

              {/* Chapter Accordions */}
              <div style={{ display: 'grid', gap: '10px' }}>
                {groupedCurriculum.map(chapter => {
                  const isCollapsed = collapsedChapters[chapter.id] ?? false;
                  const chapterLessons = chapter.lessons.map(l => l.lesson_id);
                  const selectedCount = chapterLessons.filter(id => semSelectedLessons.includes(id)).length;
                  const isChecked = selectedCount === chapterLessons.length;
                  const isPartial = selectedCount > 0 && selectedCount < chapterLessons.length;

                  return (
                    <div key={chapter.id} className="chapter-section" style={{ border: '1px solid var(--bg4)', borderRadius: '10px' }}>
                      <div
                        className="ch-hd"
                        onClick={() => toggleChapterCollapse(chapter.id)}
                        role="button"
                        aria-expanded={!isCollapsed}
                        tabIndex={0}
                        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && toggleChapterCollapse(chapter.id)}
                        style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', cursor: 'pointer' }}
                      >
                        <button
                          type="button"
                          className={`check-box ${isChecked ? 'on' : isPartial ? 'partial' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleChapterCheckbox(chapter.id, true);
                          }}
                          role="checkbox"
                          aria-checked={isChecked ? true : isPartial ? 'mixed' : false}
                          aria-label={`تحديد كافة دروس ${chapter.title}`}
                          style={{ background: 'transparent' }}
                        >
                          {isChecked ? '✓' : isPartial ? '■' : ''}
                        </button>
                        <div className="ch-num" style={{ background: 'var(--bg3)', width: '32px', height: '32px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                          {chapter.id}
                        </div>
                        <div style={{ flex: 1 }}>
                          <h4 style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>{chapter.title}</h4>
                          <span style={{ fontSize: '0.75rem', color: 'var(--t2)' }}>{chapter.subtitle}</span>
                        </div>
                        <span className="bx b-gray">{selectedCount} / {chapterLessons.length}</span>
                        <span className={`ch-toggle ${!isCollapsed ? 'open' : ''}`}>▶</span>
                      </div>

                      {!isCollapsed && (
                        <div className="ch-body open" style={{ borderTop: '1px solid var(--bg4)', background: 'rgba(20, 24, 34, 0.3)' }}>
                          {chapter.lessons.map(lesson => {
                            const isLessonSelected = semSelectedLessons.includes(lesson.lesson_id);
                            return (
                              <div
                                key={lesson.lesson_id}
                                className="lesson-check-row"
                                onClick={() => handleLessonCheckbox(lesson.lesson_id, true)}
                                role="checkbox"
                                aria-checked={isLessonSelected}
                                tabIndex={0}
                                onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && handleLessonCheckbox(lesson.lesson_id, true)}
                                style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 16px', cursor: 'pointer', borderBottom: '1px solid var(--bg4)' }}
                              >
                                <div className={`check-box ${isLessonSelected ? 'on' : ''}`}>
                                  {isLessonSelected ? '✓' : ''}
                                </div>
                                <div style={{ flex: 1 }}>
                                  <span style={{ fontSize: '0.85rem', fontWeight: '500' }}>{lesson.title_ar}</span>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.7rem', color: 'var(--t2)', marginTop: '2px' }}>
                                    <span className="diff-dot" style={{ background: lesson.difficulty === 'easy' ? 'var(--teal)' : lesson.difficulty === 'medium' ? 'var(--gold)' : 'var(--coral)' }} />
                                    <span>صعوبة: {lesson.difficulty === 'easy' ? 'سهل' : lesson.difficulty === 'medium' ? 'متوسط' : 'صعب'}</span>
                                    <span>·</span>
                                    <span>مدة: {lesson.duration_minutes} د</span>
                                    {lesson.completion_status === 'completed' && <span className="status-pill tone-teal">مكتمل</span>}
                                    {lesson.completion_status === 'weak' && <span className="status-pill tone-coral">نقطة ضعف ({lesson.weak_score}%)</span>}
                                  </div>
                                </div>
                                <div className="lesson-quick-actions selector-actions" onClick={(event) => event.stopPropagation()}>
                                  <Link to={`/lessons/${lesson.lesson_id}`} className="lesson-quick-btn" title="ابدأ الدرس" aria-label={`ابدأ درس ${lesson.title_ar}`}>▶</Link>
                                  <Link to={`/quizzes?lessonId=${lesson.lesson_id}`} className="lesson-quick-btn" title="توليد اختبار" aria-label={`توليد اختبار لدرس ${lesson.title_ar}`}>📝</Link>
                                  <Link to={`/flashcards?lessonId=${lesson.lesson_id}`} className="lesson-quick-btn" title="بطاقات مراجعة" aria-label={`توليد بطاقات لدرس ${lesson.title_ar}`}>🃏</Link>
                                  <Link to={`/ask-ai?question=${encodeURIComponent(`اشرح لي درس ${lesson.title_ar}`)}`} className="lesson-quick-btn" title="اسأل الذكاء" aria-label={`اسأل الذكاء عن درس ${lesson.title_ar}`}>✨</Link>
                                  <button
                                    type="button"
                                    className={`lesson-quick-btn ${lesson.completion_status === 'completed' ? 'done' : ''}`}
                                    onClick={() => void markLessonComplete(lesson.lesson_id)}
                                    aria-label={`تحديد درس ${lesson.title_ar} كمكتمل`}
                                  >
                                    ✓
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          )}

          {/* STEP 3: Review and Generate */}
          {semStep === 3 && (
            <div className="grid2" style={{ alignItems: 'start' }}>
              <Card>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 'bold', marginBottom: '16px' }}>ملخص إعدادات الخطة</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>نوع الخطة:</span><strong>خطة فصل كاملة</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>الفترة المجدولة:</span><strong>{semStartDate} ← {semEndDate}</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>أيام الدراسة:</span><strong>{semStudyDays.join('، ')}</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>مدة الحصة:</span><strong>{semLessonDuration}</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>راحة مجدولة:</span><strong>{semWeeklyRest}</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>عدد الدروس المختارة:</span><strong style={{ color: 'var(--teal)' }}>{semSelectedLessons.length} درساً</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>إجمالي وقت الدراسة:</span><strong>{semTotalDuration} دقيقة</strong></div>
                </div>
              </Card>

              <Card>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 'bold', marginBottom: '16px' }}>توزيع صعوبة المذاكرة</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                      <span>سهل ({curriculumLessons.filter(l => semSelectedLessons.includes(l.lesson_id) && l.difficulty === 'easy').length} دروس)</span>
                      <span>جلسة واحدة لكل درس</span>
                    </div>
                    <ProgressBar value={100} tone="teal" />
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                      <span>متوسط ({curriculumLessons.filter(l => semSelectedLessons.includes(l.lesson_id) && l.difficulty === 'medium').length} دروس)</span>
                      <span>جلسة ونصف لكل درس</span>
                    </div>
                    <ProgressBar value={75} tone="gold" />
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                      <span>صعب ({curriculumLessons.filter(l => semSelectedLessons.includes(l.lesson_id) && l.difficulty === 'hard').length} دروس)</span>
                      <span>جلستان لكل درس كحد أدنى</span>
                    </div>
                    <ProgressBar value={50} tone="coral" />
                  </div>
                </div>
                <div className="info-banner" style={{ background: 'rgba(139, 127, 232, 0.08)', borderColor: 'rgba(139, 127, 232, 0.25)', marginTop: '20px' }}>
                  <span>🔮</span>
                  <p style={{ color: 'var(--t2)', fontSize: '0.85rem' }}>سيقوم محرك الذكاء بتنظيم تتابع الدروس بحيث لا تقع المفاهيم الصعبة في أيام متتالية.</p>
                </div>
              </Card>
            </div>
          )}

          <div className="divider" />
          <div style={{ display: 'flex', gap: '10px' }}>
            {semStep > 1 && (
              <Button variant="ghost" onClick={() => setSemStep(prev => prev - 1)}>
                ← السابق
              </Button>
            )}
            <div style={{ marginRight: 'auto', display: 'flex', gap: '8px' }}>
              <Button variant="secondary" onClick={() => setActiveView('home')}>إلغاء</Button>
              {semStep < 3 ? (
                <Button variant="primary" onClick={handleSemesterNext}>
                  التالي: {semStep === 1 ? 'اختر الدروس' : 'مراجعة وتأكيد'} ←
                </Button>
              ) : (
                <Button variant="primary" onClick={() => startGeneratingPlan('semester')} style={{ background: 'var(--teal)', color: '#033A2E' }}>
                  ⚡ إنشاء الخطة بالذكاء الاصطناعي
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── EXAM CREATE VIEW ── */}
      {activeView === 'exam-create' && (
        <div className="study-view-transition">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <Button variant="ghost" onClick={() => setActiveView('home')}>← رجوع</Button>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '700' }}>إعداد خطة المراجعة للامتحان 🎯</h2>
          </div>

          {/* Steps Indicator */}
          <div className="steps" style={{ maxWidth: '420px', margin: '0 auto 24px' }}>
            <div className="step-item" style={{ flexDirection: 'column', alignItems: 'center' }}>
              <div className={`step-dot ${examStep === 1 ? 'active' : examStep > 1 ? 'done' : ''}`}>
                {examStep > 1 ? '✓' : '1'}
              </div>
              <span className="step-label">الامتحان</span>
            </div>
            <div className={`step-line ${examStep > 1 ? 'done' : ''}`} />
            <div className="step-item" style={{ flexDirection: 'column', alignItems: 'center' }}>
              <div className={`step-dot ${examStep === 2 ? 'active' : examStep > 2 ? 'done' : ''}`}>
                {examStep > 2 ? '✓' : '2'}
              </div>
              <span className="step-label">الدروس</span>
            </div>
            <div className={`step-line ${examStep > 2 ? 'done' : ''}`} />
            <div className="step-item" style={{ flexDirection: 'column', alignItems: 'center' }}>
              <div className={`step-dot ${examStep === 3 ? 'active' : ''}`}>3</div>
              <span className="step-label">الخطة</span>
            </div>
          </div>

          {/* Inline Validation Alert */}
          {examValidationError && (
            <div className="error-banner" role="alert" style={{ marginBottom: '20px' }}>
              <span>⚠️ {examValidationError}</span>
            </div>
          )}

          {/* STEP 1: Exam Settings */}
          {examStep === 1 && (
            <div className="grid2" style={{ alignItems: 'start' }}>
              <Card>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 'bold', marginBottom: '16px' }}>تفاصيل الامتحان القادم</h3>
                
                <div className="form-group">
                  <label className="form-label" htmlFor="exam-title">اسم الامتحان</label>
                  <input
                    id="exam-title"
                    type="text"
                    value={examTitle}
                    onChange={e => setExamTitle(e.target.value)}
                    placeholder="مثال: امتحان الكيمياء الشهري"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="exam-date">تاريخ الامتحان</label>
                  <input
                    id="exam-date"
                    type="date"
                    value={examDate}
                    onChange={e => setExamDate(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="exam-hours">ساعات المراجعة اليومية المتاحة</label>
                  <select
                    id="exam-hours"
                    value={examDailyStudyHours}
                    onChange={e => setExamDailyStudyHours(e.target.value)}
                  >
                    <option value="ساعة واحدة">ساعة واحدة</option>
                    <option value="ساعتان">ساعتان (موصى به)</option>
                    <option value="3 ساعات">3 ساعات</option>
                    <option value="4 ساعات أو أكثر">4 ساعات أو أكثر</option>
                  </select>
                </div>

                <div className="form-group">
                  <span className="form-label">أولوية وجدولة الذكاء</span>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                    {[
                      { key: 'balanced', label: 'متوازنة' },
                      { key: 'weak', label: 'نقاط الضعف أولاً' },
                      { key: 'quick', label: 'تغطية سريعة' }
                    ].map(opt => {
                      const isSelected = examPriority === opt.key;
                      return (
                        <button
                          key={opt.key}
                          type="button"
                          className={`ed-btn ${isSelected ? 'ed-btn-primary' : 'ed-btn-ghost'}`}
                          onClick={() => setExamPriority(opt.key)}
                          style={{ flex: 1, minHeight: '38px', fontSize: '0.8rem' }}
                          aria-pressed={isSelected}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </Card>

              <Card>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 'bold', marginBottom: '16px' }}>معلومات الاستعداد التلقائي</h3>
                
                <div className="card-sm" style={{ background: 'rgba(245, 166, 35, 0.05)', borderColor: 'rgba(245, 166, 35, 0.25)', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '20px' }}>📅</span>
                    <div>
                      <strong style={{ fontSize: '1.05rem', color: 'var(--gold)', display: 'block' }}>{draftExamDaysRemaining} يوماً متبقية</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--t2)' }}>الامتحان مجدول في {examDate}</span>
                    </div>
                  </div>
                </div>

                <div className="card-sm">
                  <h4 style={{ fontSize: '0.8rem', color: 'var(--t2)', marginBottom: '8px' }}>أبرز الثغرات ونقاط الضعف المكتشفة:</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                      <span>موازنة المعادلات الكيميائية</span>
                      <StatusPill tone="coral">40% درجة الفهم</StatusPill>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                      <span>قوة الحمض والأساس</span>
                      <StatusPill tone="gold">67% درجة الفهم</StatusPill>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* STEP 2: Exam Lesson Selector */}
          {examStep === 2 && (
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 'bold' }}>اختر دروس الامتحان</h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--t2)' }}>
                    الدروس المحددة: <strong>{examSelectedLessons.length} من {curriculumLessons.length}</strong>
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <Button variant="secondary" onClick={() => selectAll(false)} className="ed-btn-xs">تحديد الكل</Button>
                  <Button variant="ghost" onClick={() => clearAll(false)} className="ed-btn-xs">إلغاء الكل</Button>
                  <span style={{ fontSize: '0.85rem', alignSelf: 'center', marginRight: '8px' }}>
                    إجمالي وقت المراجعة: <strong style={{ color: 'var(--gold)' }}>{examTotalDuration} دقيقة</strong>
                  </span>
                </div>
              </div>

              {/* Chapter Accordions */}
              <div style={{ display: 'grid', gap: '10px' }}>
                {groupedCurriculum.map(chapter => {
                  const isCollapsed = collapsedChapters[chapter.id] ?? false;
                  const chapterLessons = chapter.lessons.map(l => l.lesson_id);
                  const selectedCount = chapterLessons.filter(id => examSelectedLessons.includes(id)).length;
                  const isChecked = selectedCount === chapterLessons.length;
                  const isPartial = selectedCount > 0 && selectedCount < chapterLessons.length;

                  return (
                    <div key={chapter.id} className="chapter-section" style={{ border: '1px solid var(--bg4)', borderRadius: '10px' }}>
                      <div
                        className="ch-hd"
                        onClick={() => toggleChapterCollapse(chapter.id)}
                        role="button"
                        aria-expanded={!isCollapsed}
                        tabIndex={0}
                        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && toggleChapterCollapse(chapter.id)}
                        style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', cursor: 'pointer' }}
                      >
                        <button
                          type="button"
                          className={`check-box ${isChecked ? 'on' : isPartial ? 'partial' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleChapterCheckbox(chapter.id, false);
                          }}
                          role="checkbox"
                          aria-checked={isChecked ? true : isPartial ? 'mixed' : false}
                          aria-label={`تحديد كافة دروس ${chapter.title}`}
                          style={{ background: 'transparent' }}
                        >
                          {isChecked ? '✓' : isPartial ? '■' : ''}
                        </button>
                        <div className="ch-num" style={{ background: 'var(--bg3)', width: '32px', height: '32px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                          {chapter.id}
                        </div>
                        <div style={{ flex: 1 }}>
                          <h4 style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>{chapter.title}</h4>
                          <span style={{ fontSize: '0.75rem', color: 'var(--t2)' }}>{chapter.subtitle}</span>
                        </div>
                        <span className="bx b-gray">{selectedCount} / {chapterLessons.length}</span>
                        <span className={`ch-toggle ${!isCollapsed ? 'open' : ''}`}>▶</span>
                      </div>

                      {!isCollapsed && (
                        <div className="ch-body open" style={{ borderTop: '1px solid var(--bg4)', background: 'rgba(20, 24, 34, 0.3)' }}>
                          {chapter.lessons.map(lesson => {
                            const isLessonSelected = examSelectedLessons.includes(lesson.lesson_id);
                            return (
                              <div
                                key={lesson.lesson_id}
                                className="lesson-check-row"
                                onClick={() => handleLessonCheckbox(lesson.lesson_id, false)}
                                role="checkbox"
                                aria-checked={isLessonSelected}
                                tabIndex={0}
                                onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && handleLessonCheckbox(lesson.lesson_id, false)}
                                style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 16px', cursor: 'pointer', borderBottom: '1px solid var(--bg4)' }}
                              >
                                <div className={`check-box ${isLessonSelected ? 'on' : ''}`}>
                                  {isLessonSelected ? '✓' : ''}
                                </div>
                                <div style={{ flex: 1 }}>
                                  <span style={{ fontSize: '0.85rem', fontWeight: '500' }}>{lesson.title_ar}</span>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.7rem', color: 'var(--t2)', marginTop: '2px' }}>
                                    <span className="diff-dot" style={{ background: lesson.difficulty === 'easy' ? 'var(--teal)' : lesson.difficulty === 'medium' ? 'var(--gold)' : 'var(--coral)' }} />
                                    <span>صعوبة: {lesson.difficulty === 'easy' ? 'سهل' : lesson.difficulty === 'medium' ? 'متوسط' : 'صعب'}</span>
                                    <span>·</span>
                                    <span>مدة: {lesson.duration_minutes} د</span>
                                    {lesson.completion_status === 'completed' && <span className="status-pill tone-teal">مكتمل</span>}
                                    {lesson.completion_status === 'weak' && <span className="status-pill tone-coral">نقطة ضعف ({lesson.weak_score}%)</span>}
                                  </div>
                                </div>
                                <div className="lesson-quick-actions selector-actions" onClick={(event) => event.stopPropagation()}>
                                  <Link to={`/lessons/${lesson.lesson_id}`} className="lesson-quick-btn" title="ابدأ الدرس" aria-label={`ابدأ درس ${lesson.title_ar}`}>▶</Link>
                                  <Link to={`/quizzes?lessonId=${lesson.lesson_id}`} className="lesson-quick-btn" title="توليد اختبار" aria-label={`توليد اختبار لدرس ${lesson.title_ar}`}>📝</Link>
                                  <Link to={`/flashcards?lessonId=${lesson.lesson_id}`} className="lesson-quick-btn" title="بطاقات مراجعة" aria-label={`توليد بطاقات لدرس ${lesson.title_ar}`}>🃏</Link>
                                  <Link to={`/ask-ai?question=${encodeURIComponent(`اشرح لي درس ${lesson.title_ar}`)}`} className="lesson-quick-btn" title="اسأل الذكاء" aria-label={`اسأل الذكاء عن درس ${lesson.title_ar}`}>✨</Link>
                                  <button
                                    type="button"
                                    className={`lesson-quick-btn ${lesson.completion_status === 'completed' ? 'done' : ''}`}
                                    onClick={() => void markLessonComplete(lesson.lesson_id)}
                                    aria-label={`تحديد درس ${lesson.title_ar} كمكتمل`}
                                  >
                                    ✓
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          )}

          {/* STEP 3: Review Exam Plan */}
          {examStep === 3 && (
            <div className="grid2" style={{ alignItems: 'start' }}>
              <Card>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 'bold', marginBottom: '16px' }}>ملخص خطة الامتحان</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>الهدف:</span><strong>{examTitle}</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>الموعد النهائي:</span><strong style={{ color: 'var(--gold)' }}>{examDate} (الامتحان بعد {draftExamDaysRemaining} يوم)</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>الجهد اليومي:</span><strong>{examDailyStudyHours} بمعدل ثابت</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>أولوية الجدول:</span><strong>{examPriority === 'weak' ? 'التركيز على الثغرات ونقاط الضعف' : examPriority === 'quick' ? 'مراجعة سريعة' : 'توزيع متوازن'}</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>الدروس المحددة:</span><strong>{examSelectedLessons.length} درساً</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>إجمالي وقت الدروس:</span><strong>{examTotalDuration} دقيقة</strong></div>
                </div>
              </Card>

              <Card>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 'bold', marginBottom: '16px' }}>جدولة المراجعة المقترحة</h3>
                <div className="card-sm" style={{ background: 'rgba(20,24,34,0.4)', fontSize: '0.8rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>الأيام 1-5</span><span>تغطية المفاهيم الأساسية والأيونية</span></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>الأيام 6-10</span><span>موازنة وحل مسائل كيمياء كمية</span></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>الأيام 11-12</span><strong style={{ color: 'var(--pur)' }}>مراجعة شاملة للامتحان (يومين أخريين)</strong></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--t2)' }}>اليوم 13</span><strong style={{ color: 'var(--gold)' }}>يوم الامتحان الكيميائي 🎯</strong></div>
                  </div>
                </div>
              </Card>
            </div>
          )}

          <div className="divider" />
          <div style={{ display: 'flex', gap: '10px' }}>
            {examStep > 1 && (
              <Button variant="ghost" onClick={() => setExamStep(prev => prev - 1)}>
                ← السابق
              </Button>
            )}
            <div style={{ marginRight: 'auto', display: 'flex', gap: '8px' }}>
              <Button variant="secondary" onClick={() => setActiveView('home')}>إلغاء</Button>
              {examStep < 3 ? (
                <Button variant="primary" onClick={handleExamNext}>
                  التالي: {examStep === 1 ? 'اختر الدروس' : 'جدولة المراجعة'} ←
                </Button>
              ) : (
                <Button variant="primary" onClick={() => startGeneratingPlan('exam')} style={{ background: 'var(--gold)', color: '#033A2E' }}>
                  ⚡ إنشاء خطة الامتحان بالذكاء الاصطناعي
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── AI GENERATING LOADING VIEW ── */}
      {activeView === 'generating' && (
        <Card className="gen-overlay study-view-transition" style={{ maxWidth: '520px', margin: '48px auto 0', padding: '40px' }}>
          <div className="gen-spinner" />
          <h2 style={{ fontSize: '1.25rem', fontWeight: '700', marginBottom: '8px' }}>{genTitle}</h2>
          <p style={{ color: 'var(--t2)', fontSize: '0.85rem', marginBottom: '24px' }}>يتم الآن تقييم التواريخ والدروس وتحسين جدول المراجعة الخاص بك...</p>
          
          <div className="gen-steps">
            {genSteps.map((step, idx) => (
              <div key={idx} className={`gen-step ${step.status === 'done' ? 'done' : ''}`} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', padding: '8px 12px', background: 'var(--bg3)', borderRadius: '6px', marginBottom: '6px' }}>
                <span className={`gs-dot ${step.status === 'done' ? 'gs-done-dot' : step.status === 'active' ? 'gs-active-dot' : 'gs-wait-dot'}`} />
                <span style={{ color: step.status === 'done' ? 'var(--teal)' : step.status === 'active' ? 'var(--acc)' : 'var(--t3)' }}>
                  {step.text}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── SEMESTER PLAN VIEW ── */}
      {activeView === 'semester-view' && plan && (
        <div className="study-view-transition">
          <StudyScrollSection section="today">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
              <Button variant="ghost" onClick={() => setActiveView('home')}>← لوحة التحكم</Button>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 'bold' }}>خطة الفصل الدراسي 📘</h2>
              <StatusPill tone="teal">نشط</StatusPill>
              <div style={{ marginRight: 'auto', display: 'flex', gap: '8px' }}>
                <Button variant="ghost" onClick={() => setActiveView('semester-create')} className="ed-btn-xs">تعديل ✏️</Button>
              </div>
            </div>

            <div className="summary-grid study-summary-grid">
              <div className="sum-card">
                <strong className="sum-val" style={{ color: 'var(--acc)' }}>36%</strong>
                <span className="sum-lbl">نسبة الإكمال</span>
              </div>
              <div className="sum-card">
                <strong className="sum-val" style={{ color: 'var(--teal)' }}>15</strong>
                <span className="sum-lbl">إجمالي الدروس</span>
              </div>
              <div className="sum-card">
                <strong className="sum-val" style={{ color: 'var(--gold)' }}>{completedLessonCount}/15</strong>
                <span className="sum-lbl">الدروس المنجزة</span>
              </div>
              <div className="sum-card">
                <strong className="sum-val" style={{ color: 'var(--pur)' }}>{semTotalDuration} د</strong>
                <span className="sum-lbl">وقت الدراسة الكلي</span>
              </div>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="weak">
            <div className="study-plan-home-grid">
              <Card className="study-home-highlight-card">
                <div className="study-section-head">
                  <strong>بؤر تحتاج مراجعة قبل التقدم</strong>
                  <StatusPill tone="coral">تنبيه مبكر</StatusPill>
                </div>
                <div className="study-insight-list">
                  {weakLessons.map((lesson) => (
                    <article key={lesson.lesson_id}>
                      <strong>{lesson.title_ar}</strong>
                      <span>{lesson.weak_score}% مستوى إتقان · راجعها قبل نهاية الأسبوع.</span>
                    </article>
                  ))}
                </div>
              </Card>
              <Card className="study-home-highlight-card">
                <div className="study-section-head">
                  <strong>توصية التوزيع الأسبوعي</strong>
                  <StatusPill tone="blue">هادئ ومستمر</StatusPill>
                </div>
                <p style={{ color: 'var(--t2)', lineHeight: '1.8', margin: 0 }}>
                  حافظ على جلسة تعلّم واحدة وجلسة مراجعة خفيفة في نفس اليوم. هذا يمنع تراكم الدروس الصعبة في نهاية الأسبوع.
                </p>
              </Card>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="timeline">
            <div className="tabs" style={{ marginBottom: '20px' }}>
              <button type="button" className={`tab ${activePlanTab === 'timeline' ? 'on' : ''}`} onClick={() => setActivePlanTab('timeline')}>الجدول الزمني</button>
              <button type="button" className={`tab ${activePlanTab === 'weekly' ? 'on' : ''}`} onClick={() => setActivePlanTab('weekly')}>التوزيع الأسبوعي</button>
              <button type="button" className={`tab ${activePlanTab === 'chapters' ? 'on' : ''}`} onClick={() => setActivePlanTab('chapters')}>تقدم الفصول</button>
            </div>

            {activePlanTab === 'timeline' && (
              <div className="plan-view">
                <div className="pv-row">
                  <div className="pv-date" style={{ color: 'var(--acc)', fontWeight: 'bold' }}>
                    اليوم<br />14 يونيو
                  </div>
                  <div className="pv-spine">
                    <div className="pv-dot" style={{ background: 'var(--acc)' }} />
                    <div className="pv-line" style={{ background: 'var(--bg4)' }} />
                  </div>
                  <div className="pv-content">
                    <div className="pv-card today">
                      <span className="pvc-icon">📖</span>
                      <div style={{ flex: 1 }}>
                        <strong className="pvc-lesson" style={{ color: 'var(--acc)' }}>{timelinePrimaryLesson?.title_ar ?? 'الدرس الحالي'}</strong>
                        <div className="pvc-meta" style={{ marginTop: '4px' }}>
                          <StatusPill tone="blue">تعلم جديد</StatusPill>
                          <span>{timelinePrimaryLesson?.duration_minutes ?? 45} دقيقة</span>
                          <span>الوحدة {timelinePrimaryLesson?.unit_number ?? 4}</span>
                        </div>
                      </div>
                      <div className="lesson-quick-actions">
                        <Link to={`/lessons/${timelinePrimaryLesson?.lesson_id ?? 401}`} className="ed-btn ed-btn-primary ed-btn-xs" style={{ minHeight: '32px' }}>
                          ابدأ الدرس ←
                        </Link>
                        <button
                          type="button"
                          className="lesson-quick-btn"
                          onClick={() => void markLessonComplete(timelinePrimaryLesson?.lesson_id ?? 401)}
                          aria-label="تحديد كمكتمل"
                          title="تحديد كمكتمل"
                        >
                          ✓
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {plan.chapters.map((chapter) => (
                  <div key={chapter.id}>
                    {chapter.lessons.map((lesson) => {
                      const isCompleted = lesson.status === 'completed';
                      const isCurrent = lesson.status === 'current';
                      const isWeak = lesson.status === 'weak';

                      if (timelinePrimaryLesson && lesson.id === timelinePrimaryLesson.lesson_id) return null;

                      return (
                        <div key={lesson.id} className="pv-row">
                          <div className="pv-date">
                            جدول دراسي<br />الوحدة {chapter.id}
                          </div>
                          <div className="pv-spine">
                            <div className="pv-dot" style={{ background: isCompleted ? 'var(--teal)' : isCurrent ? 'var(--acc)' : isWeak ? 'var(--coral)' : 'var(--bg5)' }} />
                            <div className="pv-line" style={{ background: 'var(--bg4)' }} />
                          </div>
                          <div className="pv-content">
                            <div className={`pv-card ${isCompleted ? 'rest' : ''}`}>
                              <span className="pvc-icon">{isCompleted ? '✅' : isWeak ? '⚠️' : '📚'}</span>
                              <div style={{ flex: 1 }}>
                                <strong className="pvc-lesson">{lesson.title}</strong>
                                <div className="pvc-meta" style={{ marginTop: '2px' }}>
                                  {isCompleted && <StatusPill tone="teal">مكتمل</StatusPill>}
                                  {isWeak && <StatusPill tone="coral">نقطة ضعف</StatusPill>}
                                  <span>{lesson.duration} دقيقة</span>
                                </div>
                              </div>
                              <div className="lesson-quick-actions">
                                {!isCompleted && (
                                  <>
                                    <Link to={`/quizzes?lessonId=${lesson.id}`} className="lesson-quick-btn" title="توليد اختبار" aria-label="توليد اختبار">📝</Link>
                                    <Link to={`/flashcards?lessonId=${lesson.id}`} className="lesson-quick-btn" title="بطاقات مراجعة" aria-label="بطاقات مراجعة">🃏</Link>
                                    <Link to={`/ask-ai?question=${encodeURIComponent(`اشرح لي درس ${lesson.title}`)}`} className="lesson-quick-btn" title="اسأل المعلم الذكي" aria-label="اسأل المعلم الذكي">✨</Link>
                                  </>
                                )}
                                <button
                                  type="button"
                                  className={`lesson-prog-check ${isCompleted ? 'done' : ''}`}
                                  onClick={() => void markLessonComplete(lesson.id)}
                                  aria-label={isCompleted ? 'غير مكتمل' : 'مكتمل'}
                                  style={{ background: 'transparent' }}
                                >
                                  {isCompleted ? '✓' : ''}
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}

            {activePlanTab === 'weekly' && (
              <Card>
                <h3 style={{ fontSize: '1rem', fontWeight: 'bold', marginBottom: '14px' }}>توزيع الأسبوع الحالي</h3>
                <div className="week-grid">
                  {['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'].map((day, idx) => {
                    const isToday = idx === 1;
                    const isRest = idx === 5 || idx === 6;
                    return (
                      <div
                        key={day}
                        className={`wday ${isToday ? 'today' : isRest ? 'rest' : 'has-lesson'}`}
                        role="gridcell"
                      >
                        <span className="wd-name">{day}</span>
                        <strong className="wd-num">{idx + 10}</strong>
                        <div className="wd-dots">
                          {!isRest && <span className="wd-dot" style={{ background: isToday ? '#fff' : 'var(--acc)' }} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}

            {activePlanTab === 'chapters' && (
              <div style={{ display: 'grid', gap: '12px' }}>
                {plan.chapters.map((chapter) => (
                  <Card key={chapter.id} className="card-sm" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div className="ch-num" style={{ background: 'var(--bg4)', color: 'var(--t1)', width: '36px', height: '36px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                      {chapter.id}
                    </div>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: '0.95rem' }}>{chapter.title}</strong>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--t2)' }}>نسبة التقدم:</span>
                        <ProgressBar value={chapter.progress} tone={chapter.color} />
                        <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>{chapter.progress}%</span>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </StudyScrollSection>

          <StudyScrollSection section="review">
            <div className="study-tools-strip">
              <Link to="/guided-lab" className="study-tool-tile">
                <strong>حل مسألة موجهة</strong>
                <span>انتقل من الدرس إلى تمرين تطبيقي بخطوات.</span>
              </Link>
              <Link to="/quizzes" className="study-tool-tile">
                <strong>اختبار نهاية الأسبوع</strong>
                <span>قياس سريع قبل الانتقال للفصل التالي.</span>
              </Link>
              <Link to="/flashcards" className="study-tool-tile">
                <strong>مراجعة فورية</strong>
                <span>حافظ على المفاهيم النشطة في الذاكرة.</span>
              </Link>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="achievement">
            <Card className="study-home-highlight-card">
              <div className="study-section-head">
                <strong>إحساس الإنجاز</strong>
                <StatusPill tone="purple">مسار ثابت</StatusPill>
              </div>
              <p style={{ color: 'var(--t2)', lineHeight: '1.8', margin: 0 }}>
                أنجزت {completedLessonCount} دروس حتى الآن. إذا أكملت درساً واحداً جديداً هذا الأسبوع فستنتقل مباشرة إلى مرحلة مراجعة أهدأ قبل الوحدة التالية.
              </p>
            </Card>
          </StudyScrollSection>
        </div>
      )}

      {/* ── EXAM PLAN VIEW ── */}
      {activeView === 'exam-view' && plan && (
        <div className="study-view-transition">
          <StudyScrollSection section="today">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
              <Button variant="ghost" onClick={() => setActiveView('home')}>← لوحة التحكم</Button>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 'bold' }}>خطة الامتحان 🎯</h2>
              <div style={{ marginRight: 'auto', display: 'flex', gap: '8px' }}>
                <Button variant="ghost" onClick={() => setActiveView('exam-create')} className="ed-btn-xs">تعديل الخطة ✏️</Button>
              </div>
            </div>

            <div className="study-exam-header-card">
              <div style={{ fontSize: '32px' }}>🎓</div>
              <div style={{ flex: 1 }}>
                <strong style={{ fontSize: '1.15rem', display: 'block', marginBottom: '4px' }}>{plan.config?.title || 'امتحان الكيمياء النهائي - الصف التاسع'}</strong>
                <span style={{ color: 'var(--t2)', fontSize: '0.85rem' }}>
                  الموعد: {plan.config?.examDate || examDate} · يتضمن {examSelectedLessons.length} دروس مراجعة
                </span>
              </div>
              <div className="study-exam-countdown">
                <strong>{examDaysRemaining}</strong>
                <span>يوم متبقٍ</span>
              </div>
            </div>

            <div className="summary-grid study-summary-grid study-summary-grid-compact">
              <div className="sum-card">
                <strong className="sum-val" style={{ color: 'var(--gold)' }}>{plan.chapters[0]?.lessons.filter((lesson) => lesson.status === 'completed').length ?? 3}/9</strong>
                <span className="sum-lbl">دروس مراجعة مقروءة</span>
              </div>
              <div className="sum-card">
                <strong className="sum-val" style={{ color: 'var(--coral)' }}>3</strong>
                <span className="sum-lbl">نقاط الضعف المتبقية</span>
              </div>
              <div className="sum-card">
                <strong className="sum-val" style={{ color: 'var(--teal)' }}>6</strong>
                <span className="sum-lbl">دروس بانتظار المراجعة</span>
              </div>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="weak">
            {plan.weakTopics && plan.weakTopics.length > 0 && (
              <Card style={{ background: 'rgba(255, 74, 96, 0.06)', borderColor: 'rgba(255, 74, 96, 0.25)' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 'bold', color: 'var(--coral)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>⚠️</span> بطاقة التركيز على نقاط الضعف
                </h3>
                <p style={{ color: 'var(--t2)', fontSize: '0.85rem', lineHeight: '1.7', marginBottom: '10px' }}>
                  موازنة المعادلات الكيميائية وقوى فان دير فالز تسجل معدلات فهم منخفضة. سيقوم محرك الجدولة تلقائياً بتخصيص فترتين إضافيتين وتزويدك بملخصات مبسطة.
                </p>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {plan.weakTopics.map((topic) => (
                    <StatusPill key={topic} tone="coral">{topic}</StatusPill>
                  ))}
                </div>
              </Card>
            )}
          </StudyScrollSection>

          <StudyScrollSection section="review">
            <Card style={{ background: 'rgba(20, 24, 34, 0.4)' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 'bold', marginBottom: '12px' }}>توصيات الذكاء لمراجعة الامتحان:</h3>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <Link to="/quizzes?mode=exam_review" className="ed-btn ed-btn-primary" style={{ minHeight: '38px', fontSize: '0.85rem' }}>
                  📝 إجراء اختبار الامتحان الموصى به
                </Link>
                <Link to="/flashcards?mode=weak_lessons" className="ed-btn ed-btn-secondary" style={{ minHeight: '38px', fontSize: '0.85rem' }}>
                  🃏 مراجعة بطاقات نقاط الضعف
                </Link>
              </div>
            </Card>

            {isFinalRevisionMode && (
              <div className="info-banner" style={{ background: 'rgba(139, 127, 232, 0.1)', borderColor: 'rgba(139, 127, 232, 0.3)', marginTop: '16px' }}>
                <span style={{ fontSize: '20px' }}>🔁</span>
                <div>
                  <strong style={{ color: 'var(--pur)', fontSize: '0.9rem', display: 'block', marginBottom: '2px' }}>وضع المراجعة النهائية النشط (آخر يومين)</strong>
                  <span style={{ color: 'var(--t2)', fontSize: '0.8rem' }}>
                    لقد أوقفت الخطة الدروس الجديدة. نركز الآن كلياً على مراجعة الملخصات الشاملة وحل اختبارات المحاكاة النهائية.
                  </span>
                </div>
              </div>
            )}
          </StudyScrollSection>

          <StudyScrollSection section="timeline">
            <div className="plan-view">
              <div className="pv-row">
                <div className="pv-date" style={{ color: 'var(--acc)', fontWeight: 'bold' }}>
                  اليوم<br />14 يونيو
                </div>
                <div className="pv-spine">
                  <div className="pv-dot" style={{ background: 'var(--acc)' }} />
                  <div className="pv-line" style={{ background: 'var(--bg4)' }} />
                </div>
                <div className="pv-content">
                  <div className="pv-card today">
                    <span className="pvc-icon">📖</span>
                    <div style={{ flex: 1 }}>
                      <strong className="pvc-lesson" style={{ color: 'var(--acc)' }}>{timelineReviewLesson?.title_ar ?? 'مراجعة مركزة'}</strong>
                      <div className="pvc-meta" style={{ marginTop: '2px' }}>
                        <StatusPill tone="blue">تعلّم جديد</StatusPill>
                        <span>{timelineReviewLesson?.duration_minutes ?? 45} دقيقة</span>
                      </div>
                    </div>
                    <div className="lesson-quick-actions">
                      <Link to={`/lessons/${timelineReviewLesson?.lesson_id ?? 401}`} className="ed-btn ed-btn-primary ed-btn-xs" style={{ minHeight: '32px' }}>ابدأ المراجعة ←</Link>
                      <button
                        type="button"
                        className="lesson-prog-check"
                        onClick={() => void markLessonComplete(timelineReviewLesson?.lesson_id ?? 401)}
                        aria-label="تحديد كمكتمل"
                        style={{ background: 'transparent' }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="pv-row">
                <div className="pv-date">الخميس<br />15 يونيو</div>
                <div className="pv-spine">
                  <div className="pv-dot" style={{ background: 'var(--bg5)' }} />
                  <div className="pv-line" style={{ background: 'var(--bg4)' }} />
                </div>
                <div className="pv-content">
                  <div className="pv-card">
                    <span className="pvc-icon">📚</span>
                    <div style={{ flex: 1 }}>
                      <strong className="pvc-lesson">{timelineNextLesson?.title_ar ?? 'درس قادم'}</strong>
                      <div className="pvc-meta" style={{ marginTop: '2px' }}>
                        <StatusPill tone="ghost">قادم</StatusPill>
                        <span>{timelineNextLesson?.duration_minutes ?? 45} دقيقة</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="lesson-prog-check"
                      onClick={() => void markLessonComplete(timelineNextLesson?.lesson_id ?? 401)}
                      aria-label="تحديد كمكتمل"
                      style={{ background: 'transparent' }}
                    />
                  </div>
                </div>
              </div>

              <div className="pv-row">
                <div className="pv-date" style={{ color: 'var(--pur)', fontWeight: 'bold' }}>25–26 يونيو</div>
                <div className="pv-spine">
                  <div className="pv-dot" style={{ background: 'var(--pur)' }} />
                  <div className="pv-line" style={{ background: 'var(--bg4)' }} />
                </div>
                <div className="pv-content">
                  <div className="pv-card" style={{ borderColor: 'rgba(139,127,232,.3)', background: 'rgba(139,127,232,.05)' }}>
                    <span className="pvc-icon">🔁</span>
                    <div>
                      <strong className="pvc-lesson" style={{ color: 'var(--pur)' }}>مراجعة شاملة وحل أسئلة دورات</strong>
                      <div className="pvc-meta" style={{ marginTop: '2px' }}>
                        <span style={{ color: 'var(--pur)' }}>مرحلة الاستعداد النهائي (آخر يومين)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pv-row">
                <div className="pv-date" style={{ color: 'var(--gold)', fontWeight: 'bold' }}>
                  {plan.config?.examDate || examDate}
                </div>
                <div className="pv-spine">
                  <div className="pv-dot" style={{ background: 'var(--gold)' }} />
                </div>
                <div className="pv-content">
                  <div className="pv-card exam" style={{ background: 'rgba(245,166,35,.05)' }}>
                    <span className="pvc-icon">🎓</span>
                    <div>
                      <strong className="pvc-lesson" style={{ color: 'var(--gold)', fontWeight: 'bold' }}>
                        موعد امتحان الكيمياء 🎯
                      </strong>
                      <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--t2)', marginTop: '2px' }}>تمنياتنا لك بالتوفيق والنجاح!</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </StudyScrollSection>

          <StudyScrollSection section="exam">
            <Card className="study-home-highlight-card study-exam-focus-card">
              <div className="study-section-head">
                <strong>نبض الامتحان</strong>
                <StatusPill tone="gold">المرحلة النهائية</StatusPill>
              </div>
              <p style={{ color: 'var(--t2)', lineHeight: '1.8', margin: 0 }}>
                تبقى {examDaysRemaining} أيام. كل جلسة الآن يجب أن تكون إما مراجعة لمفهوم ضعيف أو اختباراً قصيراً يثبت الفهم قبل يوم الامتحان.
              </p>
            </Card>
          </StudyScrollSection>

          <StudyScrollSection section="achievement">
            <Card className="study-home-highlight-card">
              <div className="study-section-head">
                <strong>جاهزية التقديم</strong>
                <StatusPill tone="teal">تقدّم مطمئن</StatusPill>
              </div>
              <p style={{ color: 'var(--t2)', lineHeight: '1.8', margin: 0 }}>
                إذا حافظت على هذه الوتيرة فستصل إلى يوم الامتحان مع مراجعة ختامية واضحة ووقت كاف لحل اختبار محاكاة أخير.
              </p>
            </Card>
          </StudyScrollSection>
        </div>
      )}

        </div>
      </div>

      {showMotionLayout && <ContextualStudyAssistant activeSection={displayedActiveSection} />}
    </div>
  );
};
