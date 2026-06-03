# Answer Blocks Architecture & Equation/Reaction Retrieval Fixes

## Problem

The tutor returns generic acid definitions for reaction/equation questions like "ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟". The response format is a flat text string with no structured blocks, and there's no answer-type selection.

## User Review Required

> [!IMPORTANT]
> **Breaking API Change**: The `/chat/ask` endpoint response schema changes from `{answer: string}` to `{answer_type, blocks[], sources[], diagnostics}`. The old `answer` field is preserved for backward compatibility but `blocks[]` is the primary structured response. The frontend must be updated simultaneously.

> [!WARNING]
> **Activity series rule engine**: I'm adding a deterministic chemistry rule fallback for metal + dilute acid reactions. This covers Cu, Ag, Au, Pt (below H) and Zn, Fe, Mg, Al, Na, K, Ca (above H). This is Grade 9 textbook-level and only applies to dilute acids. Concentrated acid reactions are noted but not predicted.

## Proposed Changes

### 1. New Response Schema

#### [MODIFY] [chat.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/schemas/chat.py) (schemas)

Add `preferred_answer_type` to request, and structured blocks to response:

```python
class ChatAskRequest:
    question: str
    lesson_id: int | None
    topic_id: int | None
    source_types: list[str] | None
    preferred_answer_type: str = "auto"  # NEW: auto|text|image|video|mixed

class AnswerBlock:                        # NEW
    type: str       # text|equation|table|source_page|image|video_script|clarification
    content: str
    page: int | None
    image_url: str | None
    metadata: dict

class AnswerSourceBlock:                  # NEW
    book_id: str | None
    page: int | None
    chunk_id: int
    chunk_type: str
    score: float

class ChatAnswerResponse:
    answer: str                           # KEPT for backward compat (plain text concat)
    answer_type: str                      # NEW: text|image|video|mixed|clarification|not_found
    blocks: list[AnswerBlock]             # NEW: structured answer
    sources: list[ChatSourceResponse]     # KEPT
    page_numbers: list[int]               # KEPT
    confidence: float                     # KEPT
    diagnostics: dict                     # NEW: intent, query_rewrite, etc.
    suggested_next_action: str | None     # KEPT
```

---

### 2. Answer Type Auto-Selection & Intent Expansion

#### [MODIFY] [chat_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py)

Expand `_classify_intent()` with new intents and add `_select_answer_type()`:

| Intent              | Triggers                                | Answer Type               |
| ------------------- | --------------------------------------- | ------------------------- |
| `definition_lookup` | "ما هي", "عرف", "تعريف"                 | `text`                    |
| `formula_lookup`    | "صيغة", "رمز"                           | `text` (already routed)   |
| `equation_lookup`   | "معادلة" + reactants                    | `mixed` (text + equation) |
| `reaction_query`    | "تفاعل", "يتفاعل", "مع حمض", "مع الماء" | `mixed`                   |
| `table_lookup`      | "جدول", "سلسلة"                         | `text` or `source_page`   |
| `book_grounded`     | "من الكتاب"                             | inherits from sub-intent  |
| `general`           | default                                 | `text`                    |

New function `_build_answer_blocks()` converts the flat answer text + chunks into structured `AnswerBlock` objects:

- Split on equation patterns (→, ⇌, `+`) to extract equation blocks
- Attach `source_page` blocks when page images exist
- Mark `video_script` blocks only when `preferred_answer_type = "video"` and no real video URL

---

### 3. Activity Series Chemistry Rule Engine

#### [NEW] [chemistry_rules.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chemistry_rules.py)

Deterministic rule engine for metal + dilute acid reactions:

```python
ACTIVITY_SERIES = [
    "K", "Ca", "Na", "Mg", "Al", "Zn", "Fe", "Ni", "Sn", "Pb",
    "H",  # ← hydrogen reference line
    "Cu", "Hg", "Ag", "Pt", "Au",
]

# Arabic name → symbol mapping
METAL_NAMES_AR = {
    "نحاس": "Cu", "حديد": "Fe", "زنك": "Zn", "خارصين": "Zn",
    "مغنزيوم": "Mg", "المنيوم": "Al", "صوديوم": "Na", "بوتاسيوم": "K",
    "كالسيوم": "Ca", "فضه": "Ag", "ذهب": "Au", "رصاص": "Pb", "قصدير": "Sn",
}

DILUTE_ACID_NAMES_AR = {
    "حمض الكبريت الممدد": "H₂SO₄(dilute)",
    "حمض كلور الماء": "HCl",
    "حمض الازوت الممدد": "HNO₃(dilute)",
}
```

`check_metal_acid_reaction(metal_ar, acid_ar)` returns:

- If metal is above H: the reaction equation + products
- If metal is below H: "لا يحدث تفاعل" + explanation why
- Note about concentrated acid if applicable

This is called **before** RAG retrieval when the intent is `reaction_query` or `equation_lookup` and both reactants are identified.

---

### 4. Enhanced Query Rewriting for Reactions

#### [MODIFY] [rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py)

Add reaction-specific term expansions and query rewriting:

```python
# When intent is equation_lookup or reaction_query:
# Extract reactants: النحاس, حمض الكبريت الممدد
# Rewrite: "النحاس حمض الكبريت الممدد تفاعلات الإزاحة سلسلة النشاط لا يحدث تفاعل"
```

Add to `_TERM_EXPANSIONS`:

```python
"نحاس": {"نحاس", "النحاس", "cu", "سلسله النشاط", ...},
"تفاعل": {"تفاعل", "تفاعلات", "معادله", "ازاحه", "احلال", ...},
```

When intent is `equation_lookup`, boost chunks with `content_type` in `("equation", "activity", "result", "exercise")` and penalize generic definition chunks.

---

### 5. Source Page Image Serving

#### [MODIFY] [main.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/main.py)

Mount static file serving for page images:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/media/books", StaticFiles(directory=str(PROJECT_DIR / "data" / "textbooks")), name="book_media")
```

Images accessible at: `/media/books/syria_grade_9_chemistry/page_images/page_033.png`

#### [MODIFY] [chat_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py)

When building answer blocks, check if page images exist and attach `source_page` blocks:

```python
{"type": "source_page", "page": 33, "image_url": "/media/books/syria_grade_9_chemistry/page_images/page_033.png"}
```

---

### 6. Chat API Route Updates

#### [MODIFY] [routes.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py)

Pass `preferred_answer_type` from request to `ask_question()`, map the new response dict to the updated `ChatAnswerResponse` schema with blocks.

---

### 7. Frontend Updates

#### [MODIFY] [api.ts](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/frontend-web/src/api.ts)

Update TypeScript types for the new response schema:

```typescript
interface AnswerBlock { type: string; content: string; page?: number; image_url?: string; metadata?: any; }
interface ChatAnswer { answer: string; answer_type: string; blocks: AnswerBlock[]; ... }
```

Add `preferred_answer_type` to `askChemistry()`.

#### [MODIFY] [App.tsx](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/frontend-web/src/App.tsx)

- Add answer type selector dropdown near chat input (تلقائي, نص, صورة, فيديو, مختلط)
- Replace flat `<p>{message.content}</p>` with block renderer:
  - `text` → paragraph
  - `equation` → styled equation box (monospace, centered, bordered)
  - `table` → HTML table
  - `source_page` → clickable image thumbnail with page number
  - `video_script` → "شرح فيديو مقترح" styled card
  - `clarification` → clarification question card

#### [MODIFY] [index.css](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/frontend-web/src/index.css)

Add styles for:

- `.equation-block` — centered, monospace, gradient border box
- `.source-page-thumb` — clickable page image thumbnail with overlay
- `.video-script-card` — styled card for video script suggestions
- `.answer-type-selector` — styled dropdown/pill selector
- `.clarification-card` — question card style

---

## File Change Summary

| File                                                                                                                    | Action     | Description                                            |
| ----------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------ |
| [chemistry_rules.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chemistry_rules.py) | **NEW**    | Activity series rule engine                            |
| [chat.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/schemas/chat.py)                        | **MODIFY** | New request/response schemas with blocks               |
| [chat_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py)       | **MODIFY** | Intent expansion, answer type selection, block builder |
| [query_router.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/query_router.py)       | **MODIFY** | Activity series reaction routing                       |
| [rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py)                         | **MODIFY** | Reaction term expansions, equation chunk boosting      |
| [routes.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py)                   | **MODIFY** | Pass answer type, map blocks response                  |
| [main.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/main.py)                                | **MODIFY** | Mount static files for page images                     |
| [api.ts](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/frontend-web/src/api.ts)                             | **MODIFY** | Updated types + answer type param                      |
| [App.tsx](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/frontend-web/src/App.tsx)                           | **MODIFY** | Block renderer + answer type selector                  |
| [index.css](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/frontend-web/src/index.css)                       | **MODIFY** | New block styles                                       |

## Verification Plan

### Automated Tests

1. Restart backend, run debug script:
   ```bash
   .venv/bin/python -m scripts.debug_rag_pipeline "ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟"
   ```
2. Curl the API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/ask \
     -H "Authorization: Bearer TOKEN" \
     -d '{"question":"ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟"}'
   ```
3. **Expected results:**
   - `answer_type = "mixed"`
   - `blocks` contains text + equation blocks
   - Answer contains "لا يحدث تفاعل" and "النحاس أقل نشاطاً من الهيدروجين"
   - Answer does NOT contain generic acid definition
   - confidence > 0.65

### Manual Verification

- Open frontend at localhost:5173, ask the copper + sulfuric acid question
- Verify equation box renders correctly
- Test answer type selector (تلقائي, نص, صورة, etc.)
- Test acids definition question still works: "اشرح لي ما هي الحموض من الكتاب؟"
