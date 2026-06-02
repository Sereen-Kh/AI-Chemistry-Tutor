import json
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.study_plan import StudyPlan
from app.services import ai_service

async def generate_study_plan(db: AsyncSession, user_id: int, target_date: date, topics: list[str]) -> StudyPlan:
    prompt = f"""
    قم بإنشاء خطة دراسية لطالب في الصف التاسع لمادة الكيمياء.
    تاريخ الامتحان المستهدف: {target_date.isoformat()}
    المواضيع المطلوبة: {', '.join(topics)}
    
    يجب أن يكون الرد بتنسيق JSON فقط، يحتوي على كائن بالشكل التالي:
    {{
      "overview": "نظرة عامة على الخطة",
      "weeks": [
        {{
          "week_number": 1,
          "focus": "التركيز الرئيسي للأسبوع",
          "tasks": ["مهمة 1", "مهمة 2"]
        }}
      ]
    }}
    """
    
    response = await ai_service.get_ai_response([{"role": "user", "content": prompt}])
    
    try:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
            
        plan_data = json.loads(response)
    except json.JSONDecodeError:
        plan_data = {"overview": "حدث خطأ في توليد الخطة.", "weeks": []}

    plan = StudyPlan(
        user_id=user_id,
        exam_date=target_date,
        plan_json=plan_data,
        status="active"
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    
    return plan
