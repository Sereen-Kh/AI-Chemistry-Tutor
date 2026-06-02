import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.textbook import ExtractedQuestion
from app.services import ai_service
from app.services.rag import format_context, retrieve_context

async def generate_questions_for_topic(db: AsyncSession, topic_id: int, user_id: int, num_questions: int = 5) -> list[ExtractedQuestion]:
    # 1. Get context for the topic
    chunks = await retrieve_context(db, "", user_id=user_id, topic_id=topic_id, top_k=10)
    context = format_context(chunks)
    
    if not chunks:
        # Fallback if no specific chunks found for topic
        context = "قم بتوليد أسئلة عامة حول هذا الموضوع."

    prompt = f"""
    قم بتوليد {num_questions} أسئلة اختيار من متعدد في الكيمياء بناءً على السياق التالي.
    يجب أن يكون الرد بتنسيق JSON فقط، يحتوي على مصفوفة من الكائنات بالشكل التالي:
    [
      {{
        "question_text": "نص السؤال",
        "options": ["خيار 1", "خيار 2", "خيار 3", "خيار 4"],
        "correct_answer": "الخيار الصحيح",
        "explanation": "شرح الإجابة",
        "difficulty": 1,
        "page_number": 10
      }}
    ]
    
    السياق:
    {context}
    """
    
    response = await ai_service.get_ai_response([{"role": "user", "content": prompt}])
    
    try:
        # Strip markdown code blocks if any
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
            
        questions_data = json.loads(response)
    except json.JSONDecodeError:
        return []

    # Save to db
    extracted_questions = []
    # Using the first chunk's source_id as fallback
    source_id = chunks[0].source_id if chunks else 1 
    
    for q_data in questions_data:
        question = ExtractedQuestion(
            source_id=source_id,
            topic_id=topic_id,
            question_text=q_data.get("question_text", ""),
            question_type="multiple_choice",
            options=q_data.get("options", []),
            correct_answer=q_data.get("correct_answer", ""),
            explanation=q_data.get("explanation", ""),
            difficulty=q_data.get("difficulty", 1),
            page_number=q_data.get("page_number", None),
            needs_review=True
        )
        db.add(question)
        extracted_questions.append(question)
        
    if extracted_questions:
        await db.commit()
        for q in extracted_questions:
            await db.refresh(q)
            
    return extracted_questions
