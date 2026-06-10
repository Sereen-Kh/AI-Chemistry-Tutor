# EduMind Frontend React Implementation Prompt

You are a senior full-stack engineer and frontend architect working on EduMind, an AI-powered Grade 9 Chemistry Tutor.

Your task is to implement the EduMind web frontend in the existing React/Vite app using the static design reference in:

- `docs/edumind_web.html`

Do not create a separate static HTML app. Translate the design into production React + TypeScript components inside the existing `frontend-web` app.

## Project Context

The frontend already exists:

- App directory: `frontend-web/`
- Stack: React 19, TypeScript, Vite, React Router, Axios
- Framer Motion is already installed and must be used for polished route/page/component motion
- Current app files:
  - `frontend-web/src/App.tsx`
  - `frontend-web/src/App.css`
  - `frontend-web/src/index.css`
  - `frontend-web/src/components/DesignSystem.tsx`
  - `frontend-web/src/components/AvatarGuide.tsx`
  - `frontend-web/src/components/ChemistryFlask.tsx`
  - `frontend-web/src/components/MoleculeBackground.tsx`
  - `frontend-web/src/api/*`
  - `frontend-web/src/types.ts`

The backend is FastAPI and uses `/api/v1` by default. Keep the existing API clients and improve them only when needed:

- `authApi`
- `userApi`
- `aiApi`
- `studyPlanApi`
- `flashcardsApi`
- `labApi`

The AI chat endpoint is already wired through `aiApi.ask()` to:

- `POST /api/v1/chat/ask`

Do not replace real API integration with mock-only code. Mock data may be used only as graceful fallback when the backend is unavailable.

## Design Source

Use `docs/edumind_web.html` as the visual and UX source of truth. It includes:

- RTL Arabic-first UI
- Dark chemistry-learning theme
- Landing page
- Login and register pages
- Full app shell
- Sidebar navigation
- Dashboard
- Lessons
- Ask AI chat
- RAG/book search
- Study plan
- Quizzes
- Flashcards
- Profile
- Responsive behavior
- Chemistry/molecule visual motif

The HTML file is static and uses plain JavaScript functions like `showPage`, `showApp`, `showSection`, `flipCard`, etc. Replace those with React Router, React state, and typed components.

## Product Direction

EduMind is not a generic chatbot. It is an Arabic Grade 9 Chemistry learning platform.

Primary user experience:

- Arabic is the primary UI language
- The tutor answers from the Grade 9 chemistry book through RAG
- Students can ask questions, review sources, practice quizzes, use flashcards, and follow a study plan
- The app should feel like a learning workspace, not a marketing landing page once logged in
- A hybrid mascot/avatar guide should be visible in helpful places, but it must not distract from study tasks
- Video/Reel support is UI-only for now; show a placeholder state when selected

## Implementation Goals

### 1. Rebuild The App Shell

Create a polished RTL app shell inspired by `docs/edumind_web.html`:

- Fixed/right sidebar on desktop
- Bottom navigation on mobile
- Topbar with page title, search placeholder, badges/status
- User area with avatar, name, role/streak
- Main content region with route transitions
- Responsive layout for mobile, tablet, and desktop

Keep routes compatible with the existing app:

- `/login`
- `/register`
- `/onboarding/interests`
- `/dashboard`
- `/study-plan`
- `/flashcards`
- `/lab/equation-balancer`
- `/ask-ai`
- `/profile`

Add routes only if the UI needs them:

- `/lessons`
- `/rag-search`
- `/quizzes`

If added, make them real pages, not empty placeholders.

### 2. Convert Static Design Tokens

Move the design tokens from the HTML into CSS variables in `frontend-web/src/index.css` or `frontend-web/src/App.css`.

Use these core tokens as a base:

```css
:root {
  --bg: #0A1628;
  --bg2: #0F1F38;
  --bg3: #162444;
  --bg4: #1E3050;
  --bg5: #243858;
  --acc: #4E87F5;
  --teal: #00D4A8;
  --gold: #F5A623;
  --coral: #FF6B6B;
  --pur: #8B7FE8;
  --t1: #F0F4FF;
  --t2: #7A90B5;
  --t3: #4A607D;
  --r: 10px;
  --rs: 7px;
}
```

Adapt naming if needed, but keep a consistent token system. Avoid hardcoded one-off colors scattered across components.

### 3. Component Architecture

Refactor toward clear reusable components. Suggested structure:

```text
frontend-web/src/
  components/
    shell/
      AppShell.tsx
      Sidebar.tsx
      Topbar.tsx
      BottomNav.tsx
    ui/
      Button.tsx
      Card.tsx
      StatusPill.tsx
      ProgressBar.tsx
      PageHeader.tsx
      SourceCard.tsx
      EmptyState.tsx
      LoadingState.tsx
    ai/
      ChatPanel.tsx
      ChatMessage.tsx
      AnswerFormatSelector.tsx
      SourceCitationGrid.tsx
      SuggestedQuestions.tsx
    mascot/
      HybridMascot.tsx
  pages/
    LandingPage.tsx
    LoginPage.tsx
    RegisterPage.tsx
    OnboardingPage.tsx
    DashboardPage.tsx
    LessonsPage.tsx
    AskAiPage.tsx
    RagSearchPage.tsx
    StudyPlanPage.tsx
    QuizzesPage.tsx
    FlashcardsPage.tsx
    EquationBalancerPage.tsx
    ProfilePage.tsx
```

You do not have to use this exact structure if the existing codebase suggests a better local pattern, but do not leave all UI in one huge `App.tsx`.

### 4. Dashboard

Implement a dashboard inspired by the HTML design:

- Welcome/mission card
- Daily mission
- Weekly progress strip
- AI recommendations
- Progress/stat cards:
  - XP
  - streak
  - completed lessons
  - weak topics
- Recent lessons or next lesson
- Quick actions:
  - Ask AI
  - Practice quiz
  - Flashcards
  - Study plan

Use existing `studyPlanApi.getStudyPlan()` where possible. Use fallback data only if the API fails.

### 5. Ask AI Chat

The Ask AI page is the core feature. It must be production-quality.

Implement:

- RTL chat layout
- User and assistant bubbles
- Answer format selector:
  - نص
  - صوت
  - صورة
  - Reel
- Teaching style selector:
  - مبسط
  - من الحياة
  - بصري
  - امتحاني
- Answer scope selector:
  - تلقائي
  - من الكتاب فقط
  - شرح عام عند الحاجة
- Input textarea with submit
- Loading state
- Error state
- Retry action
- Suggested questions
- “I did not understand” / rephrase action
- Source cards with page number, chunk type, and quality label
- Confidence display that is subtle and student-friendly
- Diagnostics should not be shown to normal students by default

Use existing request type:

```ts
AiAskRequest {
  question: string;
  subject: string;
  grade: string;
  answer_format: 'text' | 'audio' | 'image' | 'video';
  teaching_style: 'simple' | 'real_life' | 'visual' | 'exam';
  interests: string[];
  language: 'ar' | 'en';
  answer_scope?: 'auto' | 'book_only' | 'tutor_general';
  source_types?: string[];
  action?: 'rephrase_previous' | 'try_differently' | 'simplify_previous';
  previous_question?: string;
  previous_answer?: string;
  previous_sources?: SourceCitation[];
  previous_selected_chunks?: Record<string, unknown>[];
}
```

Render response fields:

```ts
AiAskResponse {
  answer: string;
  sources: SourceCitation[];
  confidence: number;
  format: AnswerFormat;
  answer_type?: string;
  route?: string;
  diagnostics?: Record<string, unknown>;
  audio_url?: string;
  image_url?: string;
  source_page_image_url?: string;
  video_url?: string;
  video_title?: string;
  video_source?: 'internal' | 'youtube' | 'instagram';
}
```

Important chat behavior:

- For video/Reel mode, show UI-only placeholder if backend returns no video
- For image mode, show textbook page image if available
- For audio mode, show audio player if available, otherwise show “الصوت قيد المعالجة” or “الصوت غير متاح حالياً”
- Do not show raw Gemini quota/backend errors to students
- Do show a useful friendly message if the backend is unreachable

### 6. RAG Source UX

Improve source display:

- Each answer can show source cards
- Source card should include:
  - book/source title
  - page number
  - chunk id or source id in small muted text only if useful
  - content type
  - quality label:
    - `مطابقة عالية`
    - `مطابقة جيدة`
    - `مطابقة متوسطة`
- Avoid misleading “high match” labels if score is missing or low
- Make source cards compact and scannable

Do not expose raw diagnostics to students unless there is a developer/debug toggle.

### 7. Lessons Page

Implement a lessons/chapter page matching the static design style:

- Chapter cards
- Lesson rows
- Status states:
  - completed
  - current
  - locked
  - weak
- Progress per chapter
- Actions:
  - Start lesson
  - Ask AI
  - Quiz
  - Flashcards

If backend lesson endpoints are unavailable, use current study plan data or fallback static Grade 9 chemistry topics.

### 8. Study Plan

Improve the existing study plan page:

- Weekly plan
- Today’s mission
- Weak topics
- Recommended review sequence
- Progress bars
- CTA buttons into Ask AI, quizzes, flashcards

### 9. Quizzes Page

Create a UI for quiz/exam trainer even if backend support is partial:

- Quiz setup:
  - topic
  - difficulty
  - number of questions
  - source: textbook/exam/mixed
- Question card
- Choices
- Submit answer
- Explanation panel
- Score summary
- Weak topic recommendations

Use fallback local demo questions if the endpoint is missing, but structure the page so it can later connect to `/quizzes/generate`, `/quizzes/submit`, `/quizzes/history`, etc.

### 10. Flashcards

Use existing `flashcardsApi` and existing flashcard types.

UI requirements:

- Deck list
- Active deck
- Flip animation with Framer Motion
- Review actions:
  - أعرفها
  - أحتاج مراجعة
  - تخطي
- Progress count
- Link to Ask AI for the card topic

### 11. Profile And Preferences

Profile should support:

- Student name/email
- Grade/subject
- XP/level/streak
- Interests
- Teaching style
- Default answer format
- Language preference
- Save preferences locally and through API if available

### 12. Hybrid Mascot

The avatar should be a hybrid mascot, not a generic robot only.

Design direction:

- Friendly chemistry tutor mascot
- Blend of lab assistant + AI guide
- Can be represented with CSS/SVG/React component
- Use subtle states:
  - welcome
  - thinking
  - success
  - warning
  - idle
- Should appear in:
  - auth pages
  - dashboard mission area
  - Ask AI empty state or loading state

Do not make the mascot too large or distracting in task-heavy screens.

### 13. Motion

Use Framer Motion intentionally:

- Route transitions
- Sidebar/bottom nav entrance
- Chat message entrance
- Flashcard flip
- Loading/thinking state
- Source card reveal

Avoid excessive animation. Keep motion fast and useful.

### 14. Responsive Requirements

Support:

- Mobile: 360px wide and up
- Tablet
- Desktop

Rules:

- Sidebar becomes bottom navigation on mobile
- Chat input remains reachable on mobile
- Source cards stack on mobile
- No horizontal overflow
- Arabic text must not overlap buttons/cards
- Use stable dimensions for repeated UI elements

### 15. Accessibility

Implement:

- Semantic buttons and forms
- Proper labels
- `aria-live` for chat loading/error updates
- Keyboard-accessible flashcards and selectors
- Focus states
- Sufficient contrast
- Respect RTL direction

### 16. API And Error Handling

Preserve the existing auth/token flow:

- Token stored through `lib/storage`
- Axios interceptor adds `Authorization: Bearer <token>`
- `VITE_API_URL` controls backend URL

Handle API failures gracefully:

- Auth failures should redirect/login cleanly
- Chat failures should show a friendly Arabic message
- If backend is unavailable, do not crash the page
- Do not hide errors in console only

### 17. Build And Verification

After implementation, run:

```bash
cd frontend-web
npm run build
npm run lint
```

Then run the frontend locally:

```bash
npm run dev -- --host 127.0.0.1
```

Verify:

- `/login`
- `/register`
- `/dashboard`
- `/ask-ai`
- `/study-plan`
- `/flashcards`
- `/lab/equation-balancer`
- `/profile`

If new routes were added, verify those too:

- `/lessons`
- `/rag-search`
- `/quizzes`

### 18. Backend Smoke Test For Chat

When backend is running, test these questions from the frontend:

```text
ما هو الماء؟
ما هي الحموض؟
لماذا نضيف الحمض إلى الماء وليس العكس؟
ما هو التركيز المولي؟
محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي؟
```

Expected UI behavior:

- Water question should answer about H₂O, not acids
- Safety question should answer the acid-to-water safety reason, not acid definition
- HCl calculation should show the step-by-step calculation
- Source cards should appear when backend returns sources
- No raw Gemini quota errors should be shown to students

### 19. Constraints

- Do not delete existing API clients unless replacing them with equivalent typed clients
- Do not hardcode everything as static cards
- Do not create a separate HTML page outside React
- Do not make the logged-in experience a landing page
- Do not expose raw backend diagnostics by default
- Do not use one giant component for the whole app
- Keep Arabic as primary UI language
- Keep code typed and production-readable
- Keep design consistent with `docs/edumind_web.html`

## Final Response Required

After implementation, report:

1. Files changed
2. Routes/pages implemented
3. API integrations preserved or added
4. Build/lint results
5. Local dev URL
6. Any backend endpoints still missing or mocked
