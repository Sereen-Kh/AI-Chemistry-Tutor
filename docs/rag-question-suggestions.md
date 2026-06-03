# RAG Question Suggestions

Use this file to test the EduMind RAG chatbot from the frontend chat UI or from Swagger `/docs`.
The questions are written in Arabic because the textbook and tutor answers are Arabic.

## How To Use

Start with the smoke-test questions, then test each category. For every answer, check:

- The answer uses textbook context when available.
- Page/source citations appear when relevant.
- Reaction/equation questions do not fall back to generic definitions.
- `answer_type` matches the question shape: `text`, `mixed`, `image`, `video`, or `not_found`.
- `blocks[]` contains useful structured blocks such as `text`, `equation`, and `source_page`.

## Smoke Tests

| Question | Expected Signal |
| --- | --- |
| اشرح لي ما هي الحموض من الكتاب؟ | Definition from acid pages with source pages. |
| ما هي الصيغة الكيميائية للماء؟ | Direct formula answer: H2O. |
| ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟ | No reaction; equation block; activity-series explanation. |
| اكتب تفاعل الزنك مع حمض الكبريت الممدد | Reaction happens; hydrogen gas appears in the equation. |
| ما معادلة تفكك الماء؟ | Direct water decomposition equation. |

## Definitions And Concepts

- ما هي الحموض من الكتاب؟
- عرف الحموض كما وردت في الكتاب.
- ما المقصود بعدد الوظائف الحمضية؟
- ما الفرق بين الحمض القوي والحمض الضعيف؟
- ما هي الأسس؟
- ما المقصود بالتأين؟
- ما هي الأملاح؟
- ما المقصود بتفاعلات الإزاحة؟
- ما المقصود بتفاعلات التبادل الثنائي؟
- اشرح مفهوم المحلول المائي.

## Formula Lookup

- ما هي الصيغة الكيميائية للماء؟
- ما رمز حمض كلور الماء؟
- ما صيغة حمض الكبريت؟
- ما صيغة هيدروكسيد الصوديوم؟
- ما صيغة حمض الخل؟
- ما هي الصيغة الأيونية لحمض النمل؟
- اكتب صيغة الملح الناتج من أيونات الأمونيوم والكبريتات.

## Equations And Reactions

- ما معادلة تفكك الماء في وعاء فولتا؟
- اكتب تفاعل الحديد مع كبريتات النحاس.
- لماذا لا يتفاعل النحاس مع كبريتات الحديد؟
- ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟
- اكتب تفاعل الزنك مع حمض الكبريت الممدد.
- اكتب تفاعل الحديد مع حمض كلور الماء.
- اكتب تفاعل الألمنيوم مع حمض كلور الماء.
- هل يتفاعل الذهب مع حمض كلور الماء؟ ولماذا؟
- هل يتفاعل المغنزيوم مع حمض الكبريت الممدد؟
- اكتب معادلة تفاعل حمض الخل مع هيدروكسيد البوتاسيوم.
- اكتب معادلة تفاعل حمض الكبريت الممدد مع كلوريد الباريوم.
- اكتب المعادلة الأيونية لتفاعل نترات الفضة مع كلوريد الصوديوم.

## Activity Series And Reasoning

- اعتماداً على سلسلة النشاط الكيميائي، هل يتفاعل النحاس مع حمض الكبريت الممدد؟
- لماذا يستطيع الحديد إزاحة النحاس من كبريتات النحاس؟
- لماذا لا يستطيع النحاس إزاحة الحديد من كبريتات الحديد؟
- أيهما أنشط كيميائياً: الحديد أم النحاس؟ اشرح من الكتاب.
- ما المعدن الذي يمكن أن يتفاعل مع كبريتات الحديد؟
- رتب المعادن التالية حسب النشاط: الزنك، الحديد، النحاس.

## Exercises And Exam Practice

- اعطني سؤال اختيار من متعدد عن الحموض.
- اعطني تمريناً قصيراً عن عدد الوظائف الحمضية.
- اعطني سؤالاً تدريبياً عن تفاعلات الإزاحة.
- اعطني مسألة عن تركيز حمض الكبريت.
- اعطني سؤالاً من نمط صح أو غلط عن المحاليل الحمضية.
- حول هذا السؤال إلى تدريب: ما الفرق بين الحمض القوي والضعيف؟
- اعطني اختباراً صغيراً من 5 أسئلة عن الحموض.

## Source/Page Citation Tests

- اشرح لي الحموض مع ذكر أرقام الصفحات.
- ما الصفحات التي تتحدث عن الحموض القوية والضعيفة؟
- اعرض لي مصدر تعريف الحموض من الكتاب.
- أين يظهر تفاعل النحاس في الكتاب؟
- اعرض صفحة المصدر لتفاعلات الإزاحة.

## Visual Or Source-Page Tests

Use `preferred_answer_type = "image"` or select `صورة` in the frontend.

- اعرض لي صفحة الكتاب التي تشرح تفاعلات الإزاحة.
- أريد صورة الصفحة التي فيها النحاس وحمض الكبريت الممدد.
- اعرض مصدر صفحة الحموض.
- اعرض صفحة النشاط عن سلسلة النشاط الكيميائي.

## Video Script Tests

Use `preferred_answer_type = "video"` or select `فيديو` in the frontend.

- اشرح تفاعل النحاس مع حمض الكبريت الممدد كفيديو قصير.
- اعمل لي سيناريو فيديو يشرح الحموض القوية والضعيفة.
- اشرح تفكك الماء بفيديو قصير للصف التاسع.

## Clarification And Not-Found Tests

- ما معادلة الماء؟
- اشرح لي هذا الشيء من الكتاب.
- ما علاقة هذا الدرس بالفيزياء النووية؟
- اشرح لي كيمياء الصف الجامعي من هذا الكتاب.
- ما هو تفاعل النحاس مع حمض الآزوت الممدد؟

## Personalization Prompts

- اشرح لي الحموض بطريقة سهلة وكأنني مبتدئ.
- اشرح تفاعلات الإزاحة بخطوات قصيرة.
- اشرح تفاعل النحاس مع حمض الكبريت الممدد مع مثال مشابه.
- اعطني تلميحاً فقط بدون الحل الكامل.
- اختبرني بسؤال واحد بعد الشرح.

## API Payload Examples

Text answer:

```json
{
  "question": "اشرح لي ما هي الحموض من الكتاب؟",
  "source_types": ["textbook"],
  "preferred_answer_type": "text"
}
```

Mixed answer with equation/source blocks:

```json
{
  "question": "ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟",
  "source_types": ["textbook"],
  "preferred_answer_type": "auto"
}
```

Source-page answer:

```json
{
  "question": "اعرض صفحة النشاط عن سلسلة النشاط الكيميائي.",
  "source_types": ["textbook"],
  "preferred_answer_type": "image"
}
```
