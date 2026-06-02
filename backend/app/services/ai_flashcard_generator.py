import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.assessment import Flashcard
from app.services import ai_service
from app.services.rag import retrieve_context, format_context

async def generate_flashcards_for_topic(db: AsyncSession, topic_id: int, user_id: int, num_flashcards: int = 5) -> list[Flashcard]:
    chunks = await retrieve_context(db, "", user_id=user_id, topic_id=topic_id, top_k=10)
    context = format_context(chunks)
    
    if not chunks:
        context = "قم بتوليد بطاقات تعليمية عامة حول هذا الموضوع."

    prompt = f"""
    قم بتوليد {num_flashcards} بطاقات تعليمية (Flashcards) في الكيمياء بناءً على السياق التالي.
    يجب أن يكون الرد بتنسيق JSON فقط، يحتوي على مصفوفة من الكائنات بالشكل التالي:
    [
      {{
        "front": "السؤال أو المفهوم (الوجه الأمامي)",
        "back": "الإجابة أو الشرح (الوجه الخلفي)",
        "hint": "تلميح اختياري"
      }}
    ]
    
    السياق:
    {context}
    """
    
    response = await ai_service.get_ai_response([{"role": "user", "content": prompt}])
    
    try:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
            
        flashcards_data = json.loads(response)
    except json.JSONDecodeError:
        return []

    flashcards = []
    for f_data in flashcards_data:
        flashcard = Flashcard(
            topic_id=topic_id,
            front=f_data.get("front", ""),
            back=f_data.get("back", ""),
            hint=f_data.get("hint")
        )
        db.add(flashcard)
        flashcards.append(flashcard)
        
    if flashcards:
        await db.commit()
        for f in flashcards:
            await db.refresh(f)
            
    return flashcards
