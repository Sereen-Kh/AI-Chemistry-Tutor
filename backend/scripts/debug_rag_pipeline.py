#!/usr/bin/env python3
"""Debug script: traces a query through the entire RAG pipeline.

Run from the backend directory:
    .venv/bin/python -m scripts.debug_rag_pipeline "اشرح لي ما هي الحموض من الكتاب؟"

Traces:
  1. retrieval diagnostics
  2. query rewrite
  3. hybrid search
  4. confidence scoring
  5. answer prompt
"""

import asyncio
import logging
import sys

# Enable all rag.diagnostics logging to stderr
logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s | %(levelname)s | %(message)s",
    stream=sys.stderr,
)

async def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "اشرح لي ما هي الحموض من الكتاب؟"

    # -- Step 0: Imports (after logging is set up) --
    from app.services.rag import clean_query, rewrite_query, _query_terms, lexical_relevance_score
    from app.services.chat_service import _classify_intent, _compute_confidence

    print("=" * 70)
    print("🔍 RAG PIPELINE DEBUG")
    print("=" * 70)

    # ── Step 1: Query Cleanup ──
    cleaned = clean_query(query)
    print("\n📝 STEP 1 — QUERY CLEANUP")
    print(f"   Original : {query}")
    print(f"   Cleaned  : {cleaned}")

    # ── Step 2: Intent Classification ──
    intent = _classify_intent(query)
    print("\n🎯 STEP 2 — INTENT CLASSIFICATION")
    print(f"   Intent   : {intent}")

    # ── Step 3: Query Rewriting ──
    rewritten = rewrite_query(cleaned)
    terms = sorted(_query_terms(cleaned))
    print("\n🔄 STEP 3 — QUERY REWRITING")
    print(f"   Rewritten: {rewritten}")
    print(f"   Terms ({len(terms)}): {', '.join(terms)}")

    # ── Step 4: Hybrid Search + Diagnostics ──
    print("\n🔎 STEP 4 — HYBRID SEARCH (with DB)")

    from app.database import AsyncSessionLocal
    from app.services.rag import retrieve_context

    async with AsyncSessionLocal() as db:
        chunks = await retrieve_context(
            db, query, user_id=1, top_k=6, min_similarity=0.0, intent=intent,
        )

    print(f"   Retrieved {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        snippet = chunk.content[:100].replace("\n", " ")
        print(f"   [{i+1}] page={chunk.page_number} score={chunk.similarity_score:.4f} "
              f"type={chunk.content_type} | {snippet}...")

    # ── Step 5: Confidence Scoring ──
    confidence = _compute_confidence(query, chunks)
    raw_max = max((c.similarity_score for c in chunks), default=0.0)
    print("\n📊 STEP 5 — CONFIDENCE SCORING")
    print(f"   Raw max hybrid score : {raw_max:.4f}")
    print(f"   Computed confidence  : {confidence:.4f}")
    print("   Threshold (min)      : 0.25")
    print(f"   Would pass?          : {'✅ YES' if confidence >= 0.25 else '❌ NO'}")

    # ── Step 6: Lexical Breakdown ──
    print("\n📋 STEP 6 — LEXICAL SCORES PER CHUNK")
    for i, chunk in enumerate(chunks):
        lex = lexical_relevance_score(cleaned, chunk.content)
        print(f"   [{i+1}] lexical={lex:.4f} hybrid={chunk.similarity_score:.4f} page={chunk.page_number}")

    # ── Step 7: Answer Prompt Preview ──
    from app.services.rag import format_context
    context = format_context(chunks)
    print("\n💬 STEP 7 — SYSTEM PROMPT (first 500 chars)")
    prompt_template = (
        "أنت مدرس كيمياء للصف التاسع. أجب بالاعتماد حصرياً على المقاطع التالية من الكتاب.\n"
        "التعليمات:\n"
        "1. استخدم فقط المعلومات الموجودة في المقاطع أدناه.\n"
        "2. اذكر رقم الصفحة لكل معلومة تستخدمها بالشكل: (صفحة XX).\n"
        "3. إذا لم تجد الإجابة في المقاطع، قل ذلك بوضوح.\n"
        "4. لا تخترع معلومات أو مصادر غير موجودة في المقاطع.\n"
        "5. رتب إجابتك: التعريف أولاً، ثم التفاصيل، ثم الأمثلة.\n\n"
        f"المقاطع:\n{context}"
    )
    print(f"   {prompt_template[:500]}...")

    print(f"\n{'=' * 70}")
    print("✅ PIPELINE DEBUG COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
