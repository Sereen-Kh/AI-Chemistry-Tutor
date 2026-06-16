import type { InteractiveSession, InteractiveStep, SourceReference } from './types';

export const hclConcentrationProblem =
  'محلول HCl حجمه 100 mL ويحتوي 3.65 g من الحمض. احسب التركيز الغرامي والمولي.';

export const exampleProblems = [
  {
    title: 'حساب التركيز',
    label: 'حساب تركيز HCl',
    problem: hclConcentrationProblem,
  },
  {
    title: 'مسألة تمديد',
    label: 'مسألة تمديد',
    problem: 'محلول تركيزه 2 mol/L حجمه 50 mL أضيف إليه ماء مقطر حتى أصبح حجمه 200 mL. احسب التركيز الجديد.',
  },
  {
    title: 'سلامة الحموض والأسس',
    label: 'حموض وأسس',
    problem: 'لماذا نضيف الحمض إلى الماء وليس الماء إلى الحمض؟',
  },
  {
    title: 'موازنة معادلة',
    label: 'موازنة معادلة',
    problem: 'وازن المعادلة الكيميائية: H2 + O2 -> H2O',
  },
] as const;

export const mockGuidedSources: SourceReference[] = [
  {
    chunk_id: 11001,
    page_number: 110,
    source_type: 'textbook',
    content_type: 'formula',
    preview: 'قانون التركيز الغرامي: Cg = m / V، حيث m الكتلة بالغرام و V الحجم باللتر.',
    score: 0.88,
  },
  {
    chunk_id: 11102,
    page_number: 111,
    source_type: 'textbook',
    content_type: 'calculation',
    preview: 'قانون التركيز المولي: C = n / V، وعدد المولات: n = m / M.',
    score: 0.84,
  },
];

export const mockGuidedSteps: InteractiveStep[] = [
  {
    step_id: 1,
    step_index: 0,
    step_type: 'formula',
    prompt: 'ما القانون المناسب لحساب التركيز الغرامي Cg؟',
    hint: 'نحتاج علاقة تربط الكتلة m بحجم المحلول V.',
    status: 'pending',
    expected_answer: 'Cg = m / V',
    explanation: 'التركيز الغرامي يساوي كتلة المادة المنحلة مقسومة على حجم المحلول باللتر.',
  },
  {
    step_id: 2,
    step_index: 1,
    step_type: 'unit_conversion',
    prompt: 'حوّل حجم المحلول من mL إلى L.',
    hint: 'كل 1000 mL تساوي 1 L.',
    status: 'pending',
    expected_answer: '100 mL = 0.1 L',
    explanation: 'نقسم 100 على 1000، فيصبح الحجم 0.1 L.',
  },
  {
    step_id: 3,
    step_index: 2,
    step_type: 'calculation',
    prompt: 'احسب التركيز الغرامي Cg باستخدام الكتلة والحجم بعد التحويل.',
    hint: 'استعمل Cg = m / V، حيث m = 3.65 g و V = 0.1 L.',
    status: 'pending',
    expected_answer: '36.5 g/L',
    explanation: 'Cg = 3.65 / 0.1 = 36.5 g/L.',
  },
  {
    step_id: 4,
    step_index: 3,
    step_type: 'molar_mass',
    prompt: 'ما الكتلة المولية للمركب HCl؟',
    hint: 'اجمع الكتلة الذرية للهيدروجين 1 مع الكلور 35.5.',
    status: 'pending',
    expected_answer: '36.5 g/mol',
    explanation: 'M(HCl) = 1 + 35.5 = 36.5 g/mol.',
  },
  {
    step_id: 5,
    step_index: 4,
    step_type: 'calculation',
    prompt: 'احسب عدد المولات n في 3.65 g من HCl.',
    hint: 'استعمل n = m / M.',
    status: 'pending',
    expected_answer: '0.1 mol',
    explanation: 'n = 3.65 / 36.5 = 0.1 mol.',
  },
  {
    step_id: 6,
    step_index: 5,
    step_type: 'calculation',
    prompt: 'احسب التركيز المولي C للمحلول.',
    hint: 'استعمل C = n / V، حيث n = 0.1 mol و V = 0.1 L.',
    status: 'pending',
    expected_answer: '1 mol/L',
    explanation: 'C = 0.1 / 0.1 = 1 mol/L.',
  },
  {
    step_id: 7,
    step_index: 6,
    step_type: 'final_answer',
    prompt: 'اكتب الجواب النهائي مع الوحدات.',
    hint: 'اجمع قيمة التركيز الغرامي وقيمة التركيز المولي.',
    status: 'pending',
    expected_answer: 'Cg = 36.5 g/L, C = 1 mol/L',
    explanation: 'النتيجة النهائية هي Cg = 36.5 g/L و C = 1 mol/L.',
  },
];

export const mockAcceptedAnswers: Record<number, string[]> = {
  1: ['cg=m/v', 'c=m/v', 'cg = m / v', 'التركيز=الكتلة/الحجم', 'الكتلة/الحجم'],
  2: ['0.1l', '0.1 l', '0,1l', '0,1 l', '100ml=0.1l', '100 ml = 0.1 l'],
  3: ['36.5g/l', '36.5 g/l', '36.5g.l-1', '36.5', '36,5'],
  4: ['36.5g/mol', '36.5 g/mol', '36.5', '36,5'],
  5: ['0.1mol', '0.1 mol', '0,1 mol', '0.1', '0,1'],
  6: ['1mol/l', '1 mol/l', '1 mol/litre', '1', '1m'],
  7: ['36.5g/l1mol/l', 'cg=36.5g/l,c=1mol/l', '36.5 و 1', '36.5g/l و 1mol/l'],
};

export const buildMockGuidedSession = (problemText: string, sessionId: number): InteractiveSession => {
  const steps: InteractiveStep[] = mockGuidedSteps.map((step) => ({
    ...step,
    status: 'pending',
  }));

  return {
    session_id: sessionId,
    problem_text: problemText || hclConcentrationProblem,
    problem_type: 'concentration_calculation',
    status: 'active',
    current_step_index: 0,
    current_step: steps[0],
    steps,
    sources: mockGuidedSources,
    confidence_score: 0.86,
    mock_mode: true,
  };
};
