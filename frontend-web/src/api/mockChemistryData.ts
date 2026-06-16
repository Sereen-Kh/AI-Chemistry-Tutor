import type {
  LessonKnowledgeUnit,
  LessonQualityReport,
  QuizGenerationConfig,
  GeneratedQuizQuestion,
  FlashcardGenerationConfig,
  GeneratedFlashcard,
} from '../types';

export const mockLessons: LessonKnowledgeUnit[] = [
  {
    lessonId: 'lesson_1_1',
    chapterId: 'chapter_1',
    titleAr: 'مفهوم المحلول',
    pageStart: 8,
    pageEnd: 11,
    objectives: [
      'تعريف المحلول المائي ومكوناته الأساسية.',
      'التمييز بين المخاليط المتجانسة وغير المتجانسة.',
      'فهم آلية الانحلال والتعبير عنها كيميائياً.'
    ],
    keyTerms: [
      { term: 'المذيب', definition: 'المادة التي تقوم بإذابة المادة الأخرى وتكون نسبتها أكبر في المحلول (كالماء).', sourcePage: 8 },
      { term: 'المذاب', definition: 'المادة التي تتفكك جزيئاتها أو أيوناتها وتتوزع في المذيب وتكون نسبتها أقل (كالملح).', sourcePage: 8 }
    ],
    definitions: [
      { concept: 'المحلول المائي', explanation: 'مزيج متجانس ناتج عن ذوبان مادة (مذاب) أو أكثر في الماء (مذيب).', sourcePage: 9 },
      { concept: 'المخلوط المتجانس', explanation: 'مخلوط تمتزج فيه المواد تماماً ولا يمكن تمييز مكوناته بالعين المجردة.', sourcePage: 9 }
    ],
    equations: [
      { latex: 'NaCl (s) \\xrightarrow{H_2O} Na^+ (aq) + Cl^- (aq)', explanation: 'معادلة ذوبان ملح الطعام (كلوريد الصوديوم) وتأينه كلياً في الماء.', variables: [], sourcePage: 10 }
    ],
    examples: [
      { question: 'ماذا يحدث عند إضافة ملح الطعام إلى الماء مع التحريك؟', solution: 'يتفكك الملح الصلب ويذوب كلياً في الماء ليشكل محلولاً مائياً متجانساً من أيونات الصوديوم والكلور المتماهرة.', sourcePage: 10 }
    ],
    experiments: [
      {
        title: 'التمييز بين المخاليط المتجانسة وغير المتجانسة',
        materials: ['ماء', 'ملح الطعام', 'رمل', 'كأسا زجاج', 'قضيب تحريك'],
        steps: [
          'ضع كمية متساوية من الماء في الكأسين.',
          'أضف ملعقة ملح إلى الكأس الأول ورمل إلى الكأس الثاني.',
          'حرك محتويات كل كأس وراقب توزع المكونات.'
        ],
        conclusion: 'مزيج الملح والماء متجانس (محلول مائي)، بينما مزيج الرمل والماء غير متجانس ويمكن تمييز الرمل.',
        sourcePage: 9
      }
    ],
    exercises: [
      { question: 'لماذا يعد الماء مذيباً ممتازاً للمركبات الأيونية؟', answer: 'لأنه مركب قطبي يستطيع إضعاف قوى التجاذب بين أيونات المذاب وإحاطتها بجزيئاته (التميه).', sourcePage: 11 }
    ],
    ragChunkIds: ['chunk_1_1_1', 'chunk_1_1_2', 'chunk_1_1_3'],
    qualityScore: 88
  },
  {
    lessonId: 'lesson_1_2',
    chapterId: 'chapter_1',
    titleAr: 'التركيز الغرامي',
    pageStart: 12,
    pageEnd: 14,
    objectives: [
      'فهم قانون التركيز الغرامي وحساب كمياته.',
      'حل المسائل المتعلقة بالكتلة والحجم والتركيز الغرامي.'
    ],
    keyTerms: [
      { term: 'التركيز الغرامي', definition: 'كتلة المذاب بالغرام في ليتر واحد من المحلول.', sourcePage: 12 }
    ],
    definitions: [
      { concept: 'التركيز الغرامي C_m', explanation: 'النسبة بين كتلة المادة المذابة m وحجم المحلول V بالليتر: C_m = m / V.', sourcePage: 12 }
    ],
    equations: [
      { latex: 'C_m = \\frac{m}{V}', explanation: 'قانون حساب التركيز الغرامي حيث m الكتلة بالغرام و V الحجم بالليتر.', variables: ['C_m: التركيز الغرامي (g/L)', 'm: كتلة المذاب (g)', 'V: حجم المحلول (L)'], sourcePage: 12 }
    ],
    examples: [
      { question: 'نذيب 10 g من هيدروكسيد الصوديوم في الماء للحصول على محلول حجمه 250 mL. احسب تركيزه الغرامي.', solution: 'Cm = m / V = 10 / 0.25 = 40 g/L', sourcePage: 13 }
    ],
    experiments: [],
    exercises: [
      { question: 'احسب كتلة ملح النحاس اللازمة لتحضير محلول تركيزه 20 g/L وحجمه 500 mL.', answer: 'm = Cm × V = 20 × 0.5 = 10 g', sourcePage: 14 }
    ],
    ragChunkIds: ['chunk_1_2_1', 'chunk_1_2_2'],
    qualityScore: 92
  },
  {
    lessonId: 'lesson_1_3',
    chapterId: 'chapter_1',
    titleAr: 'التركيز المولي',
    pageStart: 15,
    pageEnd: 17,
    objectives: [
      'تعريف التركيز المولي وكيفية حسابه.',
      'ربط التركيز المولي بالتركيز الغرامي عبر الكتلة المولية.'
    ],
    keyTerms: [
      { term: 'التركيز المولي', definition: 'عدد مولات المذاب في ليتر واحد من المحلول.', sourcePage: 15 }
    ],
    definitions: [
      { concept: 'التركيز المولي C', explanation: 'النسبة بين عدد مولات المذاب n وحجم المحلول V بالليتر: C = n / V.', sourcePage: 15 }
    ],
    equations: [
      { latex: 'C = \\frac{n}{V}', explanation: 'قانون حساب التركيز المولي حيث n عدد المولات و V الحجم بالليتر.', variables: ['C: التركيز المولي (mol/L)', 'n: عدد المولات (mol)', 'V: حجم المحلول (L)'], sourcePage: 15 },
      { latex: 'C_m = C \\times M', explanation: 'العلاقة بين التركيز الغرامي والتركيز المولي حيث M هي الكتلة المولية للمذاب.', variables: ['M: الكتلة المولية (g/mol)'], sourcePage: 16 }
    ],
    examples: [
      { question: 'نذيب 0.2 mol من حمض كلور الماء HCl في الماء للحصول على محلول حجمه 200 mL. احسب التركيز المولي.', solution: 'C = n / V = 0.2 / 0.2 = 1 mol/L', sourcePage: 16 }
    ],
    experiments: [],
    exercises: [
      { question: 'احسب التركيز المولي لمحلول من ملح الطعام NaCl تركيزه الغرامي 58.5 g/L (الكتلة المولية لملح الطعام M = 58.5 g/mol).', answer: 'C = Cm / M = 58.5 / 58.5 = 1 mol/L', sourcePage: 17 }
    ],
    ragChunkIds: ['chunk_1_3_1', 'chunk_1_3_2'],
    qualityScore: 95
  },
  {
    lessonId: 'lesson_1_4',
    chapterId: 'chapter_1',
    titleAr: 'تمديد المحاليل',
    pageStart: 18,
    pageEnd: 20,
    objectives: [
      'شرح عملية تمديد المحلول وتأثيرها على التركيز وحجم المحلول.',
      'استخدام قانون التمديد لحل المسائل العملية.'
    ],
    keyTerms: [
      { term: 'التمديد', definition: 'إضافة كمية من المذيب (الماء) إلى المحلول لزيادة حجمه وتقليل تركيزه.', sourcePage: 18 }
    ],
    definitions: [
      { concept: 'التمديد الكيميائي', explanation: 'إضافة كمية من الماء المقطر إلى محلول مائي لتقليل تركيزه مع بقاء كمية المذاب ثابتة.', sourcePage: 18 }
    ],
    equations: [
      { latex: 'C_1 \\times V_1 = C_2 \\times V_2', explanation: 'قانون التمديد: عدد مولات المذاب قبل التمديد يساوي عدد مولاته بعد التمديد.', variables: ['C1: التركيز المولي للمحلول المركز', 'V1: حجم المحلول المركز', 'C2: التركيز المولي للمحلول الممدد', 'V2: حجم المحلول الممدد (V2 = V1 + V_water)'], sourcePage: 19 }
    ],
    examples: [
      { question: 'محلول حمض كلور الماء تركيزه 2 mol/L وحجمه 100 mL. نمدده بالماء للحصول على محلول تركيزه 0.5 mol/L. احسب حجم الماء المضاف.', solution: 'C1×V1 = C2×V2 => 2 × 0.1 = 0.5 × V2 => V2 = 0.4 L = 400 mL. حجم الماء المضاف = V2 - V1 = 400 - 100 = 300 mL.', sourcePage: 19 }
    ],
    experiments: [],
    exercises: [],
    ragChunkIds: ['chunk_1_4_1'],
    qualityScore: 78
  },
  {
    lessonId: 'lesson_2_1',
    chapterId: 'chapter_2',
    titleAr: 'تعريف الحمض',
    pageStart: 22,
    pageEnd: 24,
    objectives: [
      'تعريف الحمض وصيغته الأيونية.',
      'فهم عملية تأين الحموض في المحاليل المائية.'
    ],
    keyTerms: [
      { term: 'الحمض', definition: 'مركب كيميائي يطلق أيونات الهيدروجين الموجبة H+ عند انحلاله في الماء.', sourcePage: 22 }
    ],
    definitions: [
      { concept: 'الحموض', explanation: 'مواد تعطي عند انحلالها في الماء أيونات الهيدروجين H+ المسؤولة عن الخواص الحمضية.', sourcePage: 22 }
    ],
    equations: [
      { latex: 'HCl \\xrightarrow{H_2O} H^+ + Cl^-', explanation: 'معادلة تأين حمض كلور الماء كلياً في الماء.', variables: [], sourcePage: 23 },
      { latex: 'H_2SO_4 \\xrightarrow{H_2O} 2H^+ + SO_4^{2-}', explanation: 'معادلة تأين حمض الكبريت ثنائي الوظيفة كلياً في الماء.', variables: [], sourcePage: 23 }
    ],
    examples: [],
    experiments: [],
    exercises: [
      { question: 'اكتب المعادلة الأيونية لتأين حمض الآزوت HNO3.', answer: 'HNO3 -> H+ + NO3-', sourcePage: 24 }
    ],
    ragChunkIds: ['chunk_2_1_1', 'chunk_2_1_2'],
    qualityScore: 82
  },
  {
    lessonId: 'lesson_2_2',
    chapterId: 'chapter_2',
    titleAr: 'قوة الحمض',
    pageStart: 25,
    pageEnd: 27,
    objectives: [
      'التمييز بين الحموض القوية والضعيفة بناء على درجة التأين.',
      'كتابة معادلات التأين كلياً وجزئياً.'
    ],
    keyTerms: [
      { term: 'الحمض القوي', definition: 'حمض يتأين كلياً في الماء وتكون ناقليته للكهرباء عالية (مثل HCl).', sourcePage: 25 },
      { term: 'الحمض الضعيف', definition: 'حمض يتأين جزئياً في الماء وتكون ناقليته للكهرباء ضعيفة ونعبر عنه بسهمين متعاكسين (مثل CH3COOH).', sourcePage: 25 }
    ],
    definitions: [
      { concept: 'التأين الكلي', explanation: 'تفكك جميع جزيئات الحمض المذاب في الماء إلى أيونات موجبة وسالبة.', sourcePage: 25 },
      { concept: 'التأين الجزئي', explanation: 'تفكك جزء صغير من جزيئات الحمض في الماء مع بقاء معظم الجزيئات دون تفكك.', sourcePage: 26 }
    ],
    equations: [
      { latex: 'CH_3COOH \\rightleftharpoons CH_3COO^- + H^+', explanation: 'تأين حمض الخل الضعيف جزئياً في الماء ويشار إليه بسهمين متعاكسين.', variables: [], sourcePage: 26 }
    ],
    examples: [],
    experiments: [
      {
        title: 'مقارنة الناقلية الكهربائية بين حمض قوي وحمض ضعيف',
        materials: ['محلول حمض كلور الماء HCl', 'محلول حمض الخل CH3COOH', 'دارة كهربائية (مصباح، أسلاك، بطارية، مسريان)'],
        steps: [
          'اغمس المسريين في محلول حمض كلور الماء ولاحظ شدة توهج المصباح.',
          'نظف المسريين واغسهما في حمض الخل وراقب توهج المصباح.'
        ],
        conclusion: 'المصباح يتوهج بشدة في حمض كلور الماء (ناقل قوي / تأين كلي)، ويتوهج بضعف في حمض الخل (ناقل ضعيف / تأين جزئي).',
        sourcePage: 26
      }
    ],
    exercises: [
      { question: 'صنف الحموض التالية لقوية وضعيفة: حمض الكبريت، حمض الخل، حمض كلور الماء، حمض النمل.', answer: 'الحموض القوية: حمض الكبريت وحمض كلور الماء. الحموض الضعيفة: حمض الخل وحمض النمل (الكرونيك).', sourcePage: 27 }
    ],
    ragChunkIds: ['chunk_2_2_1', 'chunk_2_2_2'],
    qualityScore: 84
  },
  {
    lessonId: 'lesson_2_3',
    chapterId: 'chapter_2',
    titleAr: 'الكشف عن الحموض',
    pageStart: 28,
    pageEnd: 29,
    objectives: [
      'استخدام الكواشف المخبرية للكشف عن المحاليل الحمضية.'
    ],
    keyTerms: [],
    definitions: [],
    equations: [],
    examples: [],
    experiments: [],
    exercises: [],
    ragChunkIds: [],
    qualityScore: 50 // Blocked
  },
  {
    lessonId: 'lesson_3_1',
    chapterId: 'chapter_3',
    titleAr: 'تعريف الأساس',
    pageStart: 31,
    pageEnd: 33,
    objectives: [
      'تعريف الأساس ومعرفة الأيون المميز للمحاليل الأساسية.',
      'كتابة معادلات تأين الأسس.'
    ],
    keyTerms: [
      { term: 'الأساس (القاعدة)', definition: 'مركب كيميائي يعطي أيونات الهيدروكسيد السالبة OH- عند انحلاله في الماء.', sourcePage: 31 }
    ],
    definitions: [
      { concept: 'الأسس', explanation: 'مواد تعطي عند تأينها في الماء أيونات الهيدروكسيد المميزة للخواص الأساسية ولون عباد الشمس الأزرق.', sourcePage: 31 }
    ],
    equations: [
      { latex: 'NaOH \\xrightarrow{H_2O} Na^+ + OH^-', explanation: 'معادلة تأين هيدروكسيد الصوديوم كلياً في الماء.', variables: [], sourcePage: 32 }
    ],
    examples: [],
    experiments: [],
    exercises: [
      { question: 'اكتب معادلة تأين هيدروكسيد البوتاسيوم KOH.', answer: 'KOH -> K+ + OH-', sourcePage: 33 }
    ],
    ragChunkIds: ['chunk_3_1_1'],
    qualityScore: 81
  },
  {
    lessonId: 'lesson_3_2',
    chapterId: 'chapter_3',
    titleAr: 'قوة الأساس',
    pageStart: 34,
    pageEnd: 35,
    objectives: [
      'التمييز بين الأسس القوية والضعيفة بناء على ناقليتها الكهربائية.'
    ],
    keyTerms: [],
    definitions: [
      { concept: 'الأسس الضعيفة', explanation: 'أسس تتأين جزئياً في محاليلها المائية مثل هيدروكسيد الأمونيوم.', sourcePage: 34 }
    ],
    equations: [
      { latex: 'NH_3 + H_2O \\rightleftharpoons NH_4^+ + OH^-', explanation: 'معادلة تأين غاز النشادر (الأمونيا) جزئياً في الماء لتشكيل محلول أساسي ضعيف.', variables: [], sourcePage: 34 }
    ],
    examples: [],
    experiments: [],
    exercises: [],
    ragChunkIds: ['chunk_3_2_1'],
    qualityScore: 70 // Needs Review
  },
  {
    lessonId: 'lesson_4_1',
    chapterId: 'chapter_4',
    titleAr: 'تفاعلات الاتحاد',
    pageStart: 37,
    pageEnd: 39,
    objectives: [
      'شرح مفهوم تفاعلات الاتحاد وكتابة أمثلة عليها كيميائياً.'
    ],
    keyTerms: [
      { term: 'تفاعل الاتحاد', definition: 'تفاعل كيميائي تتحد فيه مادتان أو أكثر لتكوين مادة واحدة جديدة.', sourcePage: 37 }
    ],
    definitions: [
      { concept: 'تفاعلات الاتحاد', explanation: 'تفاعلات تتم بالصيغة العامة: A + B -> AB.', sourcePage: 37 }
    ],
    equations: [
      { latex: 'NH_3 (g) + HCl (g) \\rightarrow NH_4Cl (s)', explanation: 'تفاعل غاز النشادر مع غاز كلور الهيدروجين لإنتاج دخان أبيض من كلوريد الأمونيوم.', variables: [], sourcePage: 38 },
      { latex: 'CaO + H_2O \\rightarrow Ca(OH)_2', explanation: 'تفاعل أكسيد الكالسيوم مع الماء لإنتاج هيدروكسيد الكالسيوم (الجير المطفأ) وهو تفاعل ناشر للحرارة.', variables: [], sourcePage: 38 }
    ],
    examples: [],
    experiments: [],
    exercises: [
      { question: 'ما صيغة الغازات المتفاعلة لتشكيل سحب كلوريد الأمونيوم البيضاء؟', answer: 'غاز النشادر NH3 وغاز كلور الهيدروجين HCl.', sourcePage: 39 }
    ],
    ragChunkIds: ['chunk_4_1_1'],
    qualityScore: 85
  },
  {
    lessonId: 'lesson_4_2',
    chapterId: 'chapter_4',
    titleAr: 'تفاعلات التفكك',
    pageStart: 40,
    pageEnd: 42,
    objectives: [
      'شرح مفهوم تفاعلات التفكك بالحرارة وكتابة المعادلات الكيميائية.'
    ],
    keyTerms: [
      { term: 'تفاعل التفكك', definition: 'تفاعل يتفكك فيه مركب كيميائي واحد بالحرارة أو الكهرباء لإنتاج مادتين أو أكثر.', sourcePage: 40 }
    ],
    definitions: [
      { concept: 'تفاعلات التفكك', explanation: 'تفاعلات عكس تفاعلات الاتحاد وتتم بالصيغة العامة: AB -> A + B.', sourcePage: 40 }
    ],
    equations: [
      { latex: 'CaCO_3 \\xrightarrow{\\Delta} CaO + CO_2 \\uparrow', explanation: 'تفكك كربونات الكالسيوم بالحرارة إلى أكسيد الكالسيوم وغاز ثنائي أكسيد الكربون.', variables: [], sourcePage: 41 },
      { latex: '2H_2O \\xrightarrow{electrolysis} 2H_2 \\uparrow + O_2 \\uparrow', explanation: 'معادلة تفكك الماء كهربائياً في وعاء فولتا لإنتاج غازي الهيدروجين والأكسجين بنسبة 2:1.', variables: [], sourcePage: 41 }
    ],
    examples: [],
    experiments: [],
    exercises: [
      { question: 'كيف نكشف عن غاز ثنائي أكسيد الكربون المنطلق من تفكك الكربونات؟', answer: 'نمرره في رائق الكلس (ماء الجير) فيتعكر نتيجة تشكل كربونات الكالسيوم غير الذوابة.', sourcePage: 42 }
    ],
    ragChunkIds: ['chunk_4_2_1'],
    qualityScore: 86
  },
  {
    lessonId: 'lesson_4_3',
    chapterId: 'chapter_4',
    titleAr: 'تفاعلات الإزاحة',
    pageStart: 43,
    pageEnd: 45,
    objectives: [
      'فهم سلسلة النشاط الكيميائي وتطبيقها في تفاعلات إزاحة المعادن.'
    ],
    keyTerms: [
      { term: 'سلسلة النشاط الكيميائي', definition: 'ترتيب المعادن تنازلياً حسب نشاطها الكيميائي وميلها لفقدان الإلكترونات وتشكل الشوارد.', sourcePage: 43 }
    ],
    definitions: [
      { concept: 'تفاعل الإزاحة (الاستبدال الأحادي)', explanation: 'تفاعل يحل فيه معدن أكثر نشاطاً محل معدن أقل نشاطاً (أو محل الهيدروجين) في محاليل مركباته.', sourcePage: 43 }
    ],
    equations: [
      { latex: 'Zn + 2HCl \\rightarrow ZnCl_2 + H_2 \\uparrow', explanation: 'الزنك يزيح الهيدروجين من حمض كلور الماء الممدد لأنه يسبقه في سلسلة النشاط.', variables: [], sourcePage: 44 },
      { latex: 'Fe + CuSO_4 \\rightarrow FeSO_4 + Cu', explanation: 'الحديد يزيح النحاس من محلول كبريتات النحاس الزرقاء ليتشكل كبريتات الحديد ويترسب النحاس الأحمر.', variables: [], sourcePage: 44 }
    ],
    examples: [
      { question: 'هل يتفاعل النحاس مع حمض الكبريت الممدد؟ علل.', solution: 'لا يحدث تفاعل (No reaction) لأن النحاس Cu يقع بعد الهيدروجين في سلسلة النشاط الكيميائي فهو أقل نشاطاً منه ولا يستطيع إزاحته.', sourcePage: 44 }
    ],
    experiments: [],
    exercises: [],
    ragChunkIds: ['chunk_4_3_1'],
    qualityScore: 80
  },
  {
    lessonId: 'lesson_4_4',
    chapterId: 'chapter_4',
    titleAr: 'تفاعلات التبادل الثنائي',
    pageStart: 46,
    pageEnd: 47,
    objectives: [
      'فهم تفاعلات التبادل الثنائي والترسيب.'
    ],
    keyTerms: [],
    definitions: [
      { concept: 'التبادل الثنائي', explanation: 'تفاعل يتم فيه تبادل الأيونات بين مركبين لتشكيل مركبين جديدين أحدهما راسب أو غاز أو ماء.', sourcePage: 46 }
    ],
    equations: [
      { latex: 'AgNO_3 + NaCl \\rightarrow AgCl \\downarrow + NaNO_3', explanation: 'تفاعل نترات الفضة مع كلوريد الصوديوم لترسيب كلوريد الفضة ذو اللون الأبيض الذي يسود بالضوء.', variables: [], sourcePage: 46 }
    ],
    examples: [],
    experiments: [],
    exercises: [],
    ragChunkIds: ['chunk_4_4_1'],
    qualityScore: 68 // Needs Review
  },
  {
    lessonId: 'lesson_5_1',
    chapterId: 'chapter_5',
    titleAr: 'تركيب الملح',
    pageStart: 49,
    pageEnd: 51,
    objectives: [
      'شرح تركيب الأملاح الكيميائي وتسميتها وصيغتها.'
    ],
    keyTerms: [
      { term: 'الملح', definition: 'مركب أيوني يتكون من شق أساسي موجب (معدن أو أمونيوم) وشق حمضي سالب.', sourcePage: 49 }
    ],
    definitions: [
      { concept: 'الأملاح', explanation: 'مركبات كيميائية تنتج عادة من تفاعل التعديل بين حمض وأساس مع انطلاق جزيء ماء.', sourcePage: 49 }
    ],
    equations: [
      { latex: 'HCl + NaOH \\rightarrow NaCl + H_2O', explanation: 'معادلة التعديل المباشرة لإنتاج ملح الطعام والماء.', variables: [], sourcePage: 50 }
    ],
    examples: [],
    experiments: [],
    exercises: [
      { question: 'اكتب تفاعل التعديل بين حمض الكبريت وهيدروكسيد الصوديوم.', answer: 'H2SO4 + 2NaOH -> Na2SO4 + 2H2O', sourcePage: 51 }
    ],
    ragChunkIds: ['chunk_5_1_1'],
    qualityScore: 83
  },
  {
    lessonId: 'lesson_5_2',
    chapterId: 'chapter_5',
    titleAr: 'ذوبان الأملاح في الماء',
    pageStart: 52,
    pageEnd: 54,
    objectives: [
      'معرفة تصنيف الأملاح حسب قابليتها للذوبان في الماء.'
    ],
    keyTerms: [],
    definitions: [],
    equations: [],
    examples: [],
    experiments: [],
    exercises: [],
    ragChunkIds: [],
    qualityScore: 40 // Blocked
  }
];

export function getLessonQualityReport(lesson: LessonKnowledgeUnit): LessonQualityReport {
  const score = lesson.qualityScore;
  const status = score >= 80 ? 'ready' : score >= 60 ? 'needs_review' : 'blocked';
  
  const checks = {
    hasTitle: !!lesson.titleAr,
    hasSourcePages: lesson.pageStart > 0 && lesson.pageEnd > 0,
    hasEnoughText: lesson.objectives.length > 0 || lesson.definitions.length > 0,
    hasObjectives: lesson.objectives.length > 0,
    hasKeyTerms: lesson.keyTerms.length > 0,
    hasDefinitions: lesson.definitions.length > 0,
    hasEquations: lesson.equations.length > 0,
    hasExamples: lesson.examples.length > 0,
    hasExercises: lesson.exercises.length > 0,
    hasValidRagChunks: lesson.ragChunkIds.length > 0,
    hasNoOcrGaps: score > 50,
  };
  
  const issues: string[] = [];
  if (!checks.hasTitle) issues.push('اسم الدرس مفقود في قاعدة البيانات');
  if (!checks.hasSourcePages) issues.push('صفحات الكتاب المدرسي غير محددة');
  if (!checks.hasObjectives) issues.push('أهداف الدرس التعليمية غير محددة');
  if (!checks.hasKeyTerms) issues.push('المصطلحات الكيميائية المهمة غير مستخرجة');
  if (!checks.hasDefinitions) issues.push('التعاريف الكيميائية الرسمية مفقودة');
  if (!checks.hasEquations) issues.push('لم يتم العثور على معادلات كيميائية مرتبطة');
  if (!checks.hasExamples) issues.push('الدرس يفتقر إلى مسائل أو أمثلة محلولة');
  if (!checks.hasExercises) issues.push('التمارين والمسائل التدريبية غير متوفرة');
  if (!checks.hasValidRagChunks) issues.push('لم يتم العثور على مقاطع RAG مرتبطة بالدرس');
  if (!checks.hasNoOcrGaps) issues.push('توجد فجوات قراءة أو أخطاء ناتجة عن عدم توفر OCR');
  
  return {
    lessonId: lesson.lessonId,
    status,
    score,
    checks,
    issues,
  };
}

const normalizeQuizDifficulty = (
  difficulty: QuizGenerationConfig['difficulty'],
  fallback: GeneratedQuizQuestion['difficulty'],
): GeneratedQuizQuestion['difficulty'] => (difficulty === 'mixed' ? fallback : difficulty);

const normalizeFlashcardDifficulty = (
  difficulty: FlashcardGenerationConfig['difficulty'],
  fallback: GeneratedFlashcard['difficulty'],
): GeneratedFlashcard['difficulty'] => (difficulty === 'mixed' ? fallback : difficulty);

export function mockGenerateQuiz(config: QuizGenerationConfig): GeneratedQuizQuestion[] {
  const questions: GeneratedQuizQuestion[] = [];
  const validLessons = mockLessons.filter(
    (l) => config.lessonIds.includes(l.lessonId) && l.qualityScore >= 60
  );

  if (!validLessons.length) return [];

  let qId = 1;
  const questionsPer = config.questionsPerLesson || 3;

  for (const lesson of validLessons) {
    let count = 0;

    // 1. Generate from definitions (MCQ)
    for (const def of lesson.definitions) {
      if (count >= questionsPer) break;
      if (config.questionTypes.includes('mcq')) {
        // Collect other definitions for distractors
        const otherExplanations = mockLessons
          .flatMap((l) => l.definitions.map((d) => d.explanation))
          .filter((e) => e !== def.explanation);
        
        const shuffledDistractors = otherExplanations.sort(() => 0.5 - Math.random()).slice(0, 3);
        const options = [def.explanation, ...shuffledDistractors].sort(() => 0.5 - Math.random());
        const correctIndex = options.indexOf(def.explanation);

        questions.push({
          id: `q-${qId++}`,
          lessonId: lesson.lessonId,
          chapterId: lesson.chapterId,
          questionType: 'mcq',
          question: `ما هو تعريف المفهوم العلمي: "${def.concept}"؟`,
          options,
          correctAnswer: def.explanation,
          correctOptionIndex: correctIndex,
          explanation: `بحسب كتاب الكيمياء، صفحة ${def.sourcePage}: ${def.concept} هو ${def.explanation}`,
          difficulty: normalizeQuizDifficulty(config.difficulty, 'medium'),
          sourcePage: def.sourcePage,
          sourceChunkId: lesson.ragChunkIds[0],
        });
        count++;
      }
    }

    // 2. Generate from equations (balancing or mcq)
    for (const eq of lesson.equations) {
      if (count >= questionsPer) break;
      
      if (config.questionTypes.includes('equation_balancing') || config.questionTypes.includes('mcq')) {
        const type: GeneratedQuizQuestion['questionType'] = config.questionTypes.includes('equation_balancing') ? 'equation_balancing' : 'mcq';
        
        questions.push({
          id: `q-${qId++}`,
          lessonId: lesson.lessonId,
          chapterId: lesson.chapterId,
          questionType: type,
          question: `أكمل أو وازن الصيغة الكيميائية التالية للتفاعل: "${eq.explanation}"`,
          options: type === 'mcq' ? [eq.latex, 'NaOH + HCl -> H2O', 'H2 + O2 -> H2O', 'None'].sort(() => 0.5 - Math.random()) : undefined,
          correctAnswer: eq.latex,
          correctOptionIndex: type === 'mcq' ? 0 : undefined, // simplify index
          explanation: `المعادلة الصحيحة بالرموز (صفحة ${eq.sourcePage}): ${eq.latex}`,
          difficulty: 'hard',
          sourcePage: eq.sourcePage,
          sourceChunkId: lesson.ragChunkIds[0],
        });
        count++;
      }
    }

    // 3. Generate from examples (calculations)
    for (const ex of lesson.examples) {
      if (count >= questionsPer) break;
      if (config.questionTypes.includes('calculation') || config.questionTypes.includes('short_answer')) {
        const type: GeneratedQuizQuestion['questionType'] = config.questionTypes.includes('calculation') ? 'calculation' : 'short_answer';
        questions.push({
          id: `q-${qId++}`,
          lessonId: lesson.lessonId,
          chapterId: lesson.chapterId,
          questionType: type,
          question: ex.question,
          correctAnswer: ex.solution,
          explanation: `طريقة الحل المفصلة في الصفحة ${ex.sourcePage}: ${ex.solution}`,
          difficulty: 'medium',
          sourcePage: ex.sourcePage,
          sourceChunkId: lesson.ragChunkIds[0],
        });
        count++;
      }
    }

    // 4. Generate from exercises (short answer)
    for (const exe of lesson.exercises) {
      if (count >= questionsPer) break;
      if (config.questionTypes.includes('short_answer') || config.questionTypes.includes('true_false')) {
        const type: GeneratedQuizQuestion['questionType'] = config.questionTypes.includes('true_false') && exe.question.includes('هل') ? 'true_false' : 'short_answer';
        
        questions.push({
          id: `q-${qId++}`,
          lessonId: lesson.lessonId,
          chapterId: lesson.chapterId,
          questionType: type,
          question: exe.question,
          options: type === 'true_false' ? ['صح', 'خطأ'] : undefined,
          correctAnswer: exe.answer || 'نعم',
          correctOptionIndex: type === 'true_false' ? 0 : undefined,
          explanation: `الإجابة الموثقة في صفحة ${exe.sourcePage}: ${exe.answer}`,
          difficulty: 'easy',
          sourcePage: exe.sourcePage,
          sourceChunkId: lesson.ragChunkIds[0],
        });
        count++;
      }
    }
  }

  return questions.slice(0, config.totalQuestions || 20);
}

export function mockGenerateFlashcards(config: FlashcardGenerationConfig): GeneratedFlashcard[] {
  const cards: GeneratedFlashcard[] = [];
  const validLessons = mockLessons.filter(
    (l) => config.lessonIds.includes(l.lessonId) && l.qualityScore >= 60
  );

  if (!validLessons.length) return [];

  let cId = 1;
  const cardsPer = config.cardsPerLesson || 4;

  for (const lesson of validLessons) {
    let count = 0;

    // 1. keyTerms (term cards)
    for (const kt of lesson.keyTerms) {
      if (count >= cardsPer) break;
      if (config.cardTypes.includes('term')) {
        cards.push({
          id: `card-${cId++}`,
          lessonId: lesson.lessonId,
          chapterId: lesson.chapterId,
          front: `ما معنى المصطلح الكيميائي: "${kt.term}"؟`,
          back: kt.definition,
          cardType: 'term',
          difficulty: normalizeFlashcardDifficulty(config.difficulty, 'easy'),
          sourcePage: kt.sourcePage,
          reviewState: 'new',
        });
        count++;
      }
    }

    // 2. definitions (definition cards)
    for (const def of lesson.definitions) {
      if (count >= cardsPer) break;
      if (config.cardTypes.includes('definition')) {
        cards.push({
          id: `card-${cId++}`,
          lessonId: lesson.lessonId,
          chapterId: lesson.chapterId,
          front: `ما هو تعريف المفهوم: "${def.concept}"؟`,
          back: def.explanation,
          cardType: 'definition',
          difficulty: 'medium',
          sourcePage: def.sourcePage,
          reviewState: 'new',
        });
        count++;
      }
    }

    // 3. equations (formula/reaction cards)
    for (const eq of lesson.equations) {
      if (count >= cardsPer) break;
      const type: GeneratedFlashcard['cardType'] | null = config.cardTypes.includes('formula') ? 'formula' : config.cardTypes.includes('reaction') ? 'reaction' : null;
      if (type) {
        cards.push({
          id: `card-${cId++}`,
          lessonId: lesson.lessonId,
          chapterId: lesson.chapterId,
          front: `ما هي معادلة أو قانون: "${eq.explanation}"؟`,
          back: eq.latex,
          cardType: type,
          difficulty: 'hard',
          sourcePage: eq.sourcePage,
          reviewState: 'new',
        });
        count++;
      }
    }

    // 4. experiments (experiment cards)
    for (const exp of lesson.experiments) {
      if (count >= cardsPer) break;
      if (config.cardTypes.includes('experiment')) {
        cards.push({
          id: `card-${cId++}`,
          lessonId: lesson.lessonId,
          chapterId: lesson.chapterId,
          front: `صف التجربة المخبرية الخاصة بـ: "${exp.title}" واذكر خلاصتها.`,
          back: `المواد: ${exp.materials.join('، ')}\nالخطوات:\n${exp.steps.map((s, i) => `${i+1}. ${s}`).join('\n')}\nالخلاصة: ${exp.conclusion}`,
          cardType: 'experiment',
          difficulty: 'hard',
          sourcePage: exp.sourcePage,
          reviewState: 'new',
        });
        count++;
      }
    }
  }

  return cards;
}
