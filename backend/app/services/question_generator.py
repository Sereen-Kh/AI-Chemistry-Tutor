import uuid
import json

from app.core.config import settings
from app.services.gemini_service import GeminiService
from app.services.retriever_service import RetrieverService


QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string"
                    },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "answer": {
                        "type": "string"
                    },
                    "explanation": {
                        "type": "string"
                    },
                    "difficulty": {
                        "type": "string"
                    },
                },
                "required": [
                    "question",
                    "answer",
                    "explanation",
                    "difficulty",
                ],
            },
        }
    },
    "required": [
        "questions"
    ],
}


REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "is_valid": {
                        "type": "boolean"
                    },
                    "issue": {
                        "type": "string"
                    },
                },
                "required": [
                    "id",
                    "is_valid",
                    "issue",
                ],
            },
        }
    },
    "required": [
        "questions"
    ],
}


class QuestionGenerator:

    @staticmethod
    def generate(
        lesson: str,
        count: int,
        difficulty: str,
        question_type: str,
    ) -> list[dict]:

        print("Retrieving lesson content...")
        context = RetrieverService.retrieve_lesson_content(lesson)
        prompt = f"""
You are an expert educational question generator.

Lesson:
{lesson}

Lesson Content:
{context}

Generate exactly {count} questions.

Rules:
- Use ONLY information from the lesson content.
- Do NOT use external knowledge.
- Every question must be directly related to the lesson.
- Every answer must be supported by the lesson content.
- Do not generate generic example questions.
- Difficulty level must be: {difficulty}.
- Question type must be: {question_type}.
- If the lesson content does not contain enough information, generate fewer questions instead of inventing information.

For MCQ:
- Provide exactly 4 options.
- Exactly one option must be correct.
- The answer must match one of the options.

Return JSON only.
"""

        print("Calling Gemini Generator...")
        try:
            result = GeminiService.generate_json(
                model=settings.QUESTION_GEN_MODEL,
                prompt=prompt,
                schema=QUESTIONS_SCHEMA,
                temperature=0.3,
            )
        except Exception as e:
            print(f"Gemini generation failed: {e}")
            return []

        questions = result["questions"]
        for q in questions:
            q["id"] = str(uuid.uuid4())
            q["lesson"] = lesson
            q["question_type"] = question_type
        
        return questions

    @staticmethod
    def review(
        questions: list[dict],
        lesson: str,
    ) -> list[dict]:
        context = RetrieverService.retrieve_lesson_content(lesson)

        prompt = f"""
You are an expert reviewer of educational questions.

Lesson content:
{context}


Questions to review:

{json.dumps(
    questions,
    ensure_ascii=False,
    indent=2
)}


Instructions:
- Return the exact same id received in the input.
- Set is_valid to true or false.
- Always provide the field "issue".
- If is_valid is false, explain why the question was rejected.
- If is_valid is true, issue should be "OK".
- Never omit any question.
- Never change any question id.
- Reject questions unrelated to the lesson.
- Reject questions whose answer is not supported by the lesson content.

Return JSON only.
"""


        result = GeminiService.generate_json(
            model=settings.QUESTION_REVIEW_MODEL,
            prompt=prompt,
            schema=REVIEW_SCHEMA,
            temperature=0,
        )
        return result["questions"]



    @staticmethod
    def generate_and_review(
        lesson: str,
        count: int,
        difficulty: str,
        question_type: str,
    ) -> list[dict]:

        print("Generating questions...")
        questions = QuestionGenerator.generate(
            lesson=lesson,
            count=count,
            difficulty=difficulty,
            question_type=question_type,
        )
        print("Reviewing questions...")
        reviews = QuestionGenerator.review(questions,lesson,)

        review_map = {r["id"]: r for r in reviews}
        valid_questions = []

        for q in questions:
            review = review_map.get(q["id"])
            if review and review["is_valid"]:
                valid_questions.append(q)

        return valid_questions