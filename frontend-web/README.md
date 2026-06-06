# EduMind Frontend Web

Vite + React + TypeScript implementation of the EduMind Grade 9 Chemistry learning platform.

## Routes

- `/login` - email/password login.
- `/register` - student registration.
- `/onboarding/interests` - interests, teaching style, answer format.
- `/dashboard` - personalized home, mission, recommendations, quick actions.
- `/study-plan` - chapters, lessons, progress, weak topics.
- `/flashcards` - decks, flip cards, known/unknown flow.
- `/lab/equation-balancer` - equation input, balancing, AI explanation link.
- `/ask-ai` - RAG chat with text/audio/image/video answer modes and source cards.
- `/profile` - progress and preference settings.

Protected routes require a backend JWT token in `localStorage`.

## API Modules

API code lives in `src/api/`:

- `authApi.ts` - `/auth/register`, `/auth/login`, `/auth/me`, `/auth/interests`, `/auth/onboarding`.
- `userApi.ts` - `/users/me` preference updates.
- `aiApi.ts` - uses the current backend RAG endpoint `/chat/ask`.
- `studyPlanApi.ts` - `/chapters` and `/lessons`, with fallback plan data.
- `flashcardsApi.ts` - `/flashcards`, with fallback decks.
- `labApi.ts` - local equation balancing adapter until a backend lab endpoint exists.
- `mockData.ts` - isolated mock/fallback data only.

Set the backend URL with:

```bash
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

## Design Tokens

Design tokens and visual system styles are in `src/index.css`. The uploaded reference file is
`/Users/sereenkh/Desktop/edumind_design_system_complete.html`.

The implementation follows `edumind_design_system_complete.html`:

- Dark blue background: `#0A1628`
- Secondary panels: `#0F1F38`, `#162444`, `#1E3050`
- Primary accent: `#4E87F5`
- Status colors: teal, gold, coral, purple
- Compact rounded cards, progress bars, pills, mobile bottom navigation

Reusable UI components live in `src/components/DesignSystem.tsx`.

## Real Backend vs Mock Fallback

The frontend prefers real backend APIs. If an endpoint is missing or unavailable, only these modules fall back:

- `studyPlanApi.ts`
- `flashcardsApi.ts`
- `aiApi.ts`
- `labApi.ts`
- `authApi.interests()`

React pages do not hardcode mock business logic. Replace a mock by updating the adapter module only.

The student-facing preference values are `real_life | visual | exam | simple` and
`text | audio | image | video`. The current backend stores older enum values, so
`authApi.ts` and `userApi.ts` map those values at the API boundary. Ask AI still
sends the selected answer format directly to `/chat/ask`.

## Run

```bash
npm install
npm run dev
```

Build check:

```bash
npm run build
```
