import { Link } from 'react-router-dom';
import { Card, PageHeader, StatusPill } from '../components/DesignSystem';
import { ChemistryFlask } from '../components/ChemistryFlask';

const labTools = [
  {
    to: '/guided-lab',
    title: 'حل المسائل الموجه',
    subtitle: 'حل مسائل التركيز خطوة بخطوة مع فحص الإجابة وتلميحات ذكية.',
    badge: 'الأداة الأساسية',
    tone: 'purple',
    icon: 'حل',
    cta: 'ابدأ الحل',
    level: 'متوسط',
    duration: '8-12 دقيقة',
    relation: 'يرتبط بالاختبارات والبطاقات',
    featured: true,
  },
  {
    to: '/lab/equation-balancer',
    title: 'موازن المعادلات',
    subtitle: 'وازن معادلات كيميائية وتعلّم خطوات الموازنة.',
    badge: 'أداة تفاعلية',
    tone: 'teal',
    icon: 'مع',
    cta: 'افتح الأداة',
    level: 'أساسي',
    duration: '5 دقائق',
    relation: 'اسأل الذكاء عن كل خطوة',
  },
  {
    to: '/ask-ai?question=اشرح لي تجربة كيميائية آمنة للصف التاسع',
    title: 'مساعد التجارب',
    subtitle: 'اسأل عن خطوات تجربة آمنة مرتبطة بالدرس.',
    badge: 'ذكاء تعليمي',
    tone: 'blue',
    icon: 'ذك',
    cta: 'اسأل الذكاء',
    level: 'أساسي',
    duration: '3 دقائق',
    relation: 'ينتج شرحاً مع مصادر عند توفرها',
  },
  {
    to: '/ask-ai?question=اشرح لي مقياس pH والحموض والأسس بطريقة مبسطة',
    title: 'محاكي pH',
    subtitle: 'افهم الفرق بين الحمضي والأساسي والمتعادل من خلال سيناريوهات بسيطة.',
    badge: 'قادم كتفاعل',
    tone: 'gold',
    icon: 'PH',
    cta: 'اطلب شرحاً الآن',
    level: 'أساسي',
    duration: '4 دقائق',
    relation: 'يمهّد لاختبار الحموض والأسس',
  },
  {
    to: '/ask-ai?question=اشرح لي بناء الذرة والعناصر للصف التاسع',
    title: 'باني الذرة',
    subtitle: 'راجع البروتونات والإلكترونات والعدد الذري قبل الانتقال للجدول الدوري.',
    badge: 'تصور بصري',
    tone: 'coral',
    icon: 'ذر',
    cta: 'راجع المفهوم',
    level: 'أساسي',
    duration: '6 دقائق',
    relation: 'يدعم دروس العناصر',
  },
  {
    to: '/ask-ai?question=أعطني قوانين التركيز الغرامي والمولي والتمديد مع مثال',
    title: 'مساعد القوانين',
    subtitle: 'قوانين التركيز، عدد المولات، والتمديد مع أمثلة جاهزة للتطبيق.',
    badge: 'مراجعة سريعة',
    tone: 'purple',
    icon: 'قو',
    cta: 'اعرض القوانين',
    level: 'امتحاني',
    duration: '5 دقائق',
    relation: 'حوّل القانون إلى بطاقة أو اختبار',
  },
] as const;

export const LabPage = () => (
  <div className="page-stack">
    <PageHeader
      eyebrow="المختبر"
      title="مختبر EduMind"
      subtitle="أدوات تفاعلية للتدريب على الكيمياء بدل الاكتفاء بقراءة الجواب."
    />
    <section className="lab-home-hero">
      <Card className="lab-home-card">
        <StatusPill tone="gold">مهمة مختبرية</StatusPill>
        <h2>ابدأ بمسألة تركيز وحلّها خطوة خطوة.</h2>
        <p>المختبر الموجه يساعدك على اختيار القانون، تحويل الوحدات، التعويض، ثم كتابة الجواب النهائي.</p>
        <Link className="ed-btn ed-btn-primary" to="/guided-lab">ابدأ الحل الموجه</Link>
      </Card>
      <Card className="lab-home-flask" aria-label="تفاعل مختبري">
        <ChemistryFlask color="violet" level={68} bubbling size={150} />
        <span>مختبر كيمياء تفاعلي</span>
      </Card>
    </section>
    <section className="lab-tool-grid" aria-label="أدوات المختبر">
      {labTools.map((tool) => (
        <Link key={tool.to} to={tool.to} className={`lab-tool-card tone-${tool.tone} ${'featured' in tool && tool.featured ? 'featured' : ''}`}>
          <span className="lab-tool-icon" aria-hidden="true">{tool.icon}</span>
          <div>
            <StatusPill tone={tool.tone}>{tool.badge}</StatusPill>
            <h2>{tool.title}</h2>
            <p>{tool.subtitle}</p>
          </div>
          <div className="lab-tool-meta">
            <span>{tool.level}</span>
            <span>{tool.duration}</span>
          </div>
          <small>{tool.relation}</small>
          <strong>{tool.cta}</strong>
        </Link>
      ))}
    </section>
  </div>
);
