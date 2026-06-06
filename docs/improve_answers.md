You are a senior full-stack engineer and frontend architect working on the EduMind project.

EduMind is an AI-powered Chemistry learning platform for Grade 9 students. The backend is expected to support authentication, user profile, interests, study plan, flashcards, equation tools, and RAG-based AI answers from the chemistry knowledge base.

Your task is to inspect the existing codebase and implement the frontend web platform based on the uploaded design system file:

- edumind_design_system_complete.html

This design file contains the visual language, dark-blue color palette, typography, components, mobile-style prototype, and existing screens:

- Home
- Lessons
- Ask AI
- The Lab
- Profile

You must preserve the design system as much as possible:

- dark blue background
- primary blue accent
- teal/gold/coral/purple status colors
- rounded card style
- bottom/mobile navigation style if applicable
- clean dashboard layout
- study progress cards
- AI answer format buttons
- lesson cards
- lab/equation tools
- profile/progress components

Do not create a generic UI. Build EduMind specifically.

==================================================
MAIN PRODUCT GOAL
==================================================

Create a frontend web platform where a student can:

1. Register
2. Log in
3. Choose their learning interests
4. Choose preferred teaching style / answer format
5. See a personalized home page
6. View study plan
7. Use equation tools
8. Read/review flashcards
9. Ask the AI tutor questions from the RAG system
10. Receive AI answers as:

- Text
- Audio
- Image
- Video / Reel suggestion

==================================================
REQUIRED USER FLOW
==================================================

Implement these pages/routes:

1. /login
   - Email/password login form
   - Validation
   - Loading state
   - Error state
   - Redirect to /dashboard after login

2. /register
   - Name
   - Email
   - Password
   - Confirm password
   - Grade selection
   - Subject selection, default Chemistry
   - Redirect to onboarding after successful registration

3. /onboarding/interests
   - User chooses learning interests
   - Examples:
     - Football
     - Food
     - Real-life examples
     - Experiments
     - Visual learning
     - Short videos
     - Exam preparation
   - Save interests to profile
   - Redirect to dashboard

4. /dashboard
   The home page must be based on the EduMind design system.
   Include:
   - Greeting
   - Streak / XP / progress badges
   - Today's study mission
   - Study plan progress
   - Exam countdown placeholder
   - AI recommendations
   - Quick actions:
     - Ask AI
     - Quiz
     - Reels
     - Flashcards
     - Equation Balancer

5. /study-plan
   - List chapters and lessons
   - Show progress per chapter
   - Show current lesson
   - Show weak topics
   - Lesson cards should follow the existing design system

6. /flashcards
   - List flashcard decks
   - Open deck
   - Flip card interaction
   - Mark as known / unknown
   - Track progress locally or through API
   - Use chemistry-focused placeholder data if backend endpoint is missing

7. /lab/equation-balancer
   - Equation input field
   - Example: H2 + O2 -> H2O
   - Button: Balance
   - Button: Explain with AI
   - Show balanced equation result
   - Show step-by-step placeholder if backend is unavailable

8. /ask-ai
   The AI tutor page must support:
   - Chat interface
   - User question input
   - Teaching style selector
   - Answer format selector:
     - Text
     - Audio
     - Image
     - Video
   - Source/citation display from RAG result
   - Loading/typing state
   - Error/retry state
   - “Try differently” button
   - “I understand” button

==================================================
ASK AI FUNCTIONAL REQUIREMENTS
==================================================

The Ask AI page must call the backend RAG API if available.

First inspect the backend/API client code and identify existing endpoints.

Expected API behavior:

POST /api/ai/ask

Request body:
{
"question": "Why does salt dissolve in water?",
"subject": "chemistry",
"grade": "9",
"answer_format": "text | audio | image | video",
"teaching_style": "real_life | visual | exam | simple",
"interests": ["football", "food", "experiments"],
"language": "en"
}

Expected response for text:
{
"answer": "....",
"sources": [
{
"title": "Chemistry.pdf",
"page": 45,
"chunk_id": "...",
"quote": "..."
}
],
"confidence": 0.0,
"format": "text"
}

Expected response for audio:
{
"answer": "....",
"audio_url": "...",
"sources": [...],
"format": "audio"
}

Expected response for image:
{
"answer": "....",
"image_url": "...",
"source_page_image_url": "...",
"sources": [...],
"format": "image"
}

Expected response for video:
{
"answer": "....",
"video_url": "...",
"video_title": "...",
"video_source": "internal | youtube | instagram",
"sources": [...],
"format": "video"
}

If the backend endpoint does not exist yet:

- Create a typed frontend API client with the expected contract.
- Add mock fallback data behind a clearly named mock adapter.
- Do not hardcode business logic inside React components.

==================================================
IMPORTANT RAG BEHAVIOR
==================================================

For text answers:

- Display grounded answer from RAG.
- Show source cards below answer.
- Show page number and source title.

For audio answers:

- Display the text answer.
- Display an audio player if audio_url exists.
- Otherwise show “Audio generation is still processing.”

For image answers:

- Prefer source image/page crop from the PDF if available.
- If backend returns generated image, show it clearly as “AI-generated explanation image.”
- Always keep source citation visible.

For video answers:

- First support internal/cached educational reels.
- Display video card with thumbnail/title/source.
- If no video is found, show:
  “No suitable video found yet. Try text or image explanation.”

Do not scrape Instagram or YouTube directly from the frontend.

==================================================
DESIGN REQUIREMENTS
==================================================

Extract reusable design tokens from edumind_design_system_complete.html.

Use constants/CSS variables for:

- colors
- border radius
- spacing
- typography
- card styles
- buttons
- pills
- progress bars
- input fields

Implement reusable components:

- AppShell
- AuthLayout
- Button
- Card
- ProgressBar
- StatusPill
- BottomNav or SidebarNav
- PageHeader
- StudyMissionCard
- RecommendationCard
- LessonCard
- Flashcard
- ChatMessage
- AnswerFormatSelector
- SourceCard
- LoadingSkeleton
- ErrorBanner

The UI must be responsive:

- Desktop web layout
- Tablet layout
- Mobile layout
- On mobile, preserve the bottom navigation feel from the design system.
- On desktop, use a sidebar or top navigation while keeping the same visual identity.

==================================================
AUTH REQUIREMENTS
==================================================

Implement authentication flow cleanly.

If backend auth exists:

- Use real auth endpoints.
- Store token securely according to the existing project pattern.
- Add route protection.

If backend auth does not exist:

- Implement frontend auth pages and a mock auth provider.
- Clearly isolate mock logic in a file such as:
  src/lib/mockAuth.ts
- Do not mix mock auth into UI components.

Expected endpoints if available:
POST /api/auth/register
POST /api/auth/login
GET /api/auth/me
POST /api/auth/logout
PATCH /api/users/me/preferences

==================================================
STATE MANAGEMENT
==================================================

Use the existing project stack if available.

If no clear stack exists, use:

- React + TypeScript
- React Router or Next.js routing depending on existing project
- TanStack Query for API calls
- Zod for schema validation
- React Hook Form for forms

Keep state clean:

- Auth state
- User profile/preferences
- Study progress
- Chat state
- Flashcard progress

==================================================
QUALITY REQUIREMENTS
==================================================

Before coding:

1. Inspect the repository structure.
2. Identify frontend framework.
3. Identify existing API client.
4. Identify existing auth system.
5. Identify styling approach.
6. Check whether the design system HTML is already imported or only uploaded as reference.
7. Create a short implementation plan.

Then implement.

Do not write pseudocode.
Do not leave TODO comments for core logic.
Do not create unused components.
Do not break existing backend or frontend behavior.
Use typed interfaces.
Use proper error handling.
Use loading states.
Use empty states.
Use accessible labels for forms and buttons.
Use responsive design.
Keep components small and maintainable.

==================================================
DELIVERABLES
==================================================

Implement the following:

1. Frontend routes:
   - /login
   - /register
   - /onboarding/interests
   - /dashboard
   - /study-plan
   - /flashcards
   - /lab/equation-balancer
   - /ask-ai
   - /profile

2. Reusable EduMind design system components.

3. API client modules:
   - authApi
   - userApi
   - aiApi
   - studyPlanApi
   - flashcardsApi
   - labApi

4. Mock fallback only where backend endpoint is missing.

5. Route protection:
   - logged-out users cannot access dashboard/study/AI/profile
   - logged-in users should not stay on login/register

6. User preferences:
   - interests
   - teaching style
   - preferred answer format
   - language

7. Ask AI multimodal UI:
   - text
   - audio
   - image
   - video

8. Source/citation cards for RAG responses.

9. A short README section explaining:
   - frontend routes
   - API contracts
   - where design tokens live
   - how to switch from mock API to real backend API

==================================================
ACCEPTANCE CRITERIA
==================================================

The implementation is accepted only if:

- The EduMind visual identity matches the uploaded design system.
- The user can register, log in, choose interests, and reach dashboard.
- Dashboard shows study plan, mission card, recommendations, and quick actions.
- Ask AI page supports selecting answer format: text/audio/image/video.
- RAG sources are shown under AI answers.
- Flashcards page works with mock or real data.
- Equation balancer page works with mock or real data.
- The app is responsive.
- TypeScript has no critical errors.
- No core feature is implemented only as a static screenshot.
- Code is clean, typed, and production-oriented.

Start by inspecting the repo and reporting the implementation plan, then apply the changes.
