import { api } from './http';
import type { LessonCatalogItem, TopicCatalogItem, UnitCatalogItem } from '../types';

const topic = (id: number, title_ar: string, title_en: string, order: number): TopicCatalogItem => ({
  id,
  title_ar,
  title_en,
  difficulty: 1,
  order,
});

export const fallbackCurriculumUnits: UnitCatalogItem[] = [
  {
    id: 4,
    unit_number: 4,
    semester: 1,
    title_ar: 'الكيمياء اللاعضوية',
    title_en: 'Inorganic Chemistry',
    description_ar: 'المحاليل المائية والحموض والأسس والتفاعلات الكيميائية والأملاح.',
    order: 4,
    icon: 'flask',
    chapters: [
      {
        id: 41,
        unit_id: 4,
        title_ar: 'المحاليل والتفاعلات اللاعضوية',
        title_en: 'Solutions and Inorganic Reactions',
        order: 1,
        difficulty: 2,
        lessons: [
          {
            id: 401,
            chapter_id: 41,
            title_ar: 'المحاليل المائية',
            title_en: 'Aqueous Solutions',
            content_ar: 'صفحات الكتاب: 108-115',
            order: 1,
            difficulty: 2,
            duration_min: 45,
            page_start: 108,
            page_end: 115,
            topics: [
              topic(4011, 'المحلول المائي', 'Aqueous solution', 1),
              topic(4012, 'التركيز الغرامي', 'Mass concentration', 2),
              topic(4013, 'التركيز المولي', 'Molar concentration', 3),
              topic(4014, 'تمديد المحاليل', 'Dilution', 4),
            ],
          },
          {
            id: 402,
            chapter_id: 41,
            title_ar: 'المحاليل الحمضية',
            title_en: 'Acidic Solutions',
            content_ar: 'صفحات الكتاب: 116-123',
            order: 2,
            difficulty: 2,
            duration_min: 45,
            page_start: 116,
            page_end: 123,
            topics: [
              topic(4021, 'الحموض', 'Acids', 10),
              topic(4022, 'أيون الهدروجين', 'Hydrogen ion', 11),
              topic(4023, 'حمض قوي', 'Strong acid', 12),
              topic(4024, 'حمض ضعيف', 'Weak acid', 13),
            ],
          },
          {
            id: 403,
            chapter_id: 41,
            title_ar: 'المحاليل الأساسية',
            title_en: 'Basic Solutions',
            content_ar: 'صفحات الكتاب: 124-131',
            order: 3,
            difficulty: 2,
            duration_min: 45,
            page_start: 124,
            page_end: 131,
            topics: [
              topic(4031, 'الأسس', 'Bases', 20),
              topic(4032, 'أيون الهدروكسيد', 'Hydroxide ion', 21),
              topic(4033, 'أساس قوي', 'Strong base', 22),
              topic(4034, 'أساس ضعيف', 'Weak base', 23),
            ],
          },
          {
            id: 404,
            chapter_id: 41,
            title_ar: 'أنواع التفاعلات الكيميائية',
            title_en: 'Types of Chemical Reactions',
            content_ar: 'صفحات الكتاب: 132-143',
            order: 4,
            difficulty: 3,
            duration_min: 55,
            page_start: 132,
            page_end: 143,
            topics: [
              topic(4041, 'تفاعل الاتحاد', 'Combination reaction', 30),
              topic(4042, 'تفاعل التفكك', 'Decomposition reaction', 31),
              topic(4043, 'تفاعل الإزاحة', 'Single displacement reaction', 32),
              topic(4044, 'تفاعل التبادل الثنائي', 'Double displacement reaction', 33),
            ],
          },
          {
            id: 405,
            chapter_id: 41,
            title_ar: 'الأملاح',
            title_en: 'Salts',
            content_ar: 'صفحات الكتاب: 146-155',
            order: 5,
            difficulty: 3,
            duration_min: 50,
            page_start: 146,
            page_end: 155,
            topics: [
              topic(4051, 'الملح', 'Salt', 40),
              topic(4052, 'تشكل الأملاح', 'Salt formation', 41),
              topic(4053, 'ذوبان الأملاح', 'Salt solubility', 42),
            ],
          },
        ],
      },
    ],
  },
  {
    id: 5,
    unit_number: 5,
    semester: 2,
    title_ar: 'الكيمياء العضوية',
    title_en: 'Organic Chemistry',
    description_ar: 'مدخل إلى مركبات الكربون والهيدروكربونات.',
    order: 5,
    icon: 'molecule',
    chapters: [
      {
        id: 51,
        unit_id: 5,
        title_ar: 'مدخل إلى الكيمياء العضوية',
        title_en: 'Introduction to Organic Chemistry',
        order: 1,
        difficulty: 2,
        lessons: [
          {
            id: 501,
            chapter_id: 51,
            title_ar: 'مركبات الكربون',
            title_en: 'Carbon Compounds',
            content_ar: '',
            order: 1,
            difficulty: 2,
            duration_min: 45,
            topics: [
              topic(5011, 'الكربون', 'Carbon', 50),
              topic(5012, 'الكيمياء العضوية', 'Organic chemistry', 51),
            ],
          },
          {
            id: 502,
            chapter_id: 51,
            title_ar: 'الهيدروكربونات',
            title_en: 'Hydrocarbons',
            content_ar: '',
            order: 2,
            difficulty: 3,
            duration_min: 45,
            topics: [
              topic(5021, 'الهيدروكربونات', 'Hydrocarbons', 53),
              topic(5022, 'الألكانات', 'Alkanes', 54),
              topic(5023, 'الميثان', 'Methane', 55),
            ],
          },
        ],
      },
    ],
  },
  {
    id: 6,
    unit_number: 6,
    semester: 2,
    title_ar: 'الكيمياء النووية',
    title_en: 'Nuclear Chemistry',
    description_ar: 'النشاط الإشعاعي والنظائر.',
    order: 6,
    icon: 'atom',
    chapters: [
      {
        id: 61,
        unit_id: 6,
        title_ar: 'النشاط الإشعاعي',
        title_en: 'Radioactivity',
        order: 1,
        difficulty: 3,
        lessons: [
          {
            id: 601,
            chapter_id: 61,
            title_ar: 'النشاط الإشعاعي والنظائر',
            title_en: 'Radioactivity and Isotopes',
            content_ar: '',
            order: 1,
            difficulty: 3,
            duration_min: 45,
            topics: [
              topic(6011, 'النشاط الإشعاعي', 'Radioactivity', 60),
              topic(6012, 'النظائر', 'Isotopes', 61),
              topic(6013, 'التفاعلات النووية', 'Nuclear reactions', 62),
            ],
          },
        ],
      },
    ],
  },
];

export const curriculumApi = {
  async getUnits(semester?: number): Promise<UnitCatalogItem[]> {
    const { data } = await api.get<UnitCatalogItem[]>('/units', {
      params: semester ? { semester } : undefined,
    });
    return data;
  },

  async getLesson(lessonId: number): Promise<LessonCatalogItem> {
    const { data } = await api.get<LessonCatalogItem>(`/lessons/${lessonId}`);
    return data;
  },
};
