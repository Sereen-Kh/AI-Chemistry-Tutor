import type { AiAskRequest, AiAskResponse, BalanceResult, FlashcardDeck, InterestCategory, StudyPlan } from '../types';

export const mockInterests: InterestCategory[] = [
  { id: 1, key: 'football', name_ar: 'كرة القدم', name_en: 'Football', icon: '⚽' },
  { id: 2, key: 'food', name_ar: 'الطعام', name_en: 'Food', icon: '🍱' },
  { id: 3, key: 'real_life', name_ar: 'أمثلة من الحياة', name_en: 'Real-life examples', icon: '🌍' },
  { id: 4, key: 'experiments', name_ar: 'التجارب', name_en: 'Experiments', icon: '⚗️' },
  { id: 5, key: 'visual', name_ar: 'تعلم بصري', name_en: 'Visual learning', icon: '🧭' },
  { id: 6, key: 'short_videos', name_ar: 'فيديوهات قصيرة', name_en: 'Short videos', icon: '🎬' },
  { id: 7, key: 'exam_prep', name_ar: 'تحضير امتحان', name_en: 'Exam preparation', icon: '📝' },
];

export const mockStudyPlan: StudyPlan = {
  weakTopics: ['الحموض الضعيفة', 'موازنة المعادلات', 'المركبات العضوية'],
  currentLesson: {
    id: 102,
    title: 'الحموض والأسس في المحاليل المائية',
    duration: 18,
    status: 'current',
  },
  chapters: [
    {
      id: 1,
      title: 'المحاليل والحموض',
      subtitle: '7 lessons · current unit',
      progress: 62,
      color: 'blue',
      lessons: [
        { id: 101, title: 'المحاليل المائية', duration: 12, status: 'completed' },
        { id: 102, title: 'الحموض والأسس', duration: 18, status: 'current' },
        { id: 103, title: 'قوة الحمض والأساس', duration: 15, status: 'weak' },
      ],
    },
    {
      id: 2,
      title: 'التفاعلات الكيميائية',
      subtitle: '6 lessons · equation practice',
      progress: 38,
      color: 'teal',
      lessons: [
        { id: 201, title: 'موازنة المعادلات', duration: 20, status: 'weak' },
        { id: 202, title: 'تفاعلات المعادن مع الحموض', duration: 16, status: 'locked' },
      ],
    },
    {
      id: 3,
      title: 'الكيمياء العضوية',
      subtitle: '5 lessons · upcoming',
      progress: 14,
      color: 'purple',
      lessons: [
        { id: 301, title: 'المركبات العضوية', duration: 13, status: 'locked' },
        { id: 302, title: 'الألكانات والألكينات', duration: 19, status: 'locked' },
      ],
    },
  ],
};

export const mockFlashcardDecks: FlashcardDeck[] = [
  {
    id: 1,
    title: 'الحموض والأسس',
    topic: 'Chapter 1',
    count: 6,
    mastered: 3,
    cards: [
      {
        id: 1,
        front: 'ما تعريف الحمض حسب الكتاب؟',
        back: 'الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+.',
        hint: 'ابحث عن الأيون الذي تعطيه الحموض.',
      },
      {
        id: 2,
        front: 'ماذا يحدث لورقة عباد الشمس في المحلول الحمضي؟',
        back: 'تتلون ورقة عباد الشمس باللون الأحمر في المحاليل الحمضية.',
      },
      {
        id: 3,
        front: 'ما معنى عدد الوظائف الحمضية؟',
        back: 'هو عدد أيونات الهدروجين في الصيغة الأيونية للحمض.',
      },
    ],
  },
  {
    id: 2,
    title: 'المعادلات الكيميائية',
    topic: 'Equation tools',
    count: 4,
    mastered: 1,
    cards: [
      {
        id: 4,
        front: 'وازن المعادلة: H2 + O2 -> H2O',
        back: '2H2 + O2 -> 2H2O',
      },
    ],
  },
];

export const mockAiAnswer = (request: AiAskRequest): AiAskResponse => {
  const source = {
    title: 'كتاب الكيمياء - الصف التاسع',
    page: 11,
    chunk_id: 'mock-acids-11',
    quote: 'الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين.',
    score: 0.78,
  };
  const baseAnswer =
    request.language === 'en'
      ? 'According to the available textbook context, acids are substances that release hydrogen ions (H+) when dissolved in water.'
      : 'بحسب مقاطع الكتاب المتاحة، الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+. لذلك نميّزها في المحاليل المائية من خلال خواص مثل تغيير لون ورقة عباد الشمس إلى الأحمر.';

  if (request.answer_format === 'audio') {
    return {
      answer: baseAnswer,
      sources: [source],
      confidence: 0.78,
      format: 'audio',
    };
  }
  if (request.answer_format === 'image') {
    return {
      answer: baseAnswer,
      sources: [source],
      confidence: 0.78,
      format: 'image',
      source_page_image_url: '/media/books/syria_grade_9_chemistry/page_images/page_011.png',
    };
  }
  if (request.answer_format === 'video') {
    return {
      answer: baseAnswer,
      sources: [source],
      confidence: 0.78,
      format: 'video',
      video_title: 'No suitable video found yet. Try text or image explanation.',
      video_source: 'internal',
    };
  }
  return {
    answer: baseAnswer,
    sources: [source],
    confidence: 0.78,
    format: 'text',
  };
};

export const mockBalanceEquation = (input: string): BalanceResult => {
  const normalized = input.replace(/\s+/g, '').toLowerCase();
  if (normalized === 'h2+o2->h2o' || normalized === 'h2+o2=h2o') {
    return {
      input,
      balanced: '2H2 + O2 -> 2H2O',
      explanation: ['Count hydrogen and oxygen atoms on both sides.', 'Place 2 before H2O to balance oxygen.', 'Place 2 before H2 to balance hydrogen.'],
    };
  }
  if (normalized === 'hcl+naoh->nacl+h2o') {
    return {
      input,
      balanced: 'HCl + NaOH -> NaCl + H2O',
      explanation: ['This acid-base neutralization equation is already balanced.', 'Each side has H2, Cl1, Na1, and O1.'],
    };
  }
  return {
    input,
    balanced: input || 'H2 + O2 -> H2O',
    explanation: ['No backend equation balancer is available yet.', 'The local helper currently supports common Grade 9 examples and leaves unknown equations unchanged.'],
  };
};
