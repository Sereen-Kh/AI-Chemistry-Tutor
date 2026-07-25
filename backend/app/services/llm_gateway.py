import asyncio

from fastapi import HTTPException
import httpx

from app.core.config import settings
from app.core.constants import AnswerScope, SourceType, TeachingStyle

class LLMGateway:

    BASE_URL = (settings.MODEL_API_URL)
    API_TIMEOUT = 45.0
    AI_SEMAPHORE = (asyncio.Semaphore(10))


    @staticmethod
    async def ask(
                question: str,
                teaching_style: TeachingStyle,
                history: list = None,
                lesson_id=None,
                topic_id=None
                ) -> dict:

        if history is None:
            history = []

        payload = {
            "question":question,
            "lesson_id":lesson_id,
            "topic_id":topic_id,
            "source_types":[SourceType.TEXTBOOK.value],
            "preferred_answer_type": teaching_style.value, 
            "history":history,
            "answer_scope":AnswerScope.BOOK_ONLY.value
        }

        try:
            async with LLMGateway.AI_SEMAPHORE:
                async with (httpx.AsyncClient(timeout=
                                                httpx.Timeout(connect=10.0,read=45.0,write=10.0,pool=10.0)
                                                #LLMGateway.API_TIMEOUT
                                                )
                    ) as client:

                    response = (
                        await client.post(f"{LLMGateway.BASE_URL}/chat/ask",
                                        json=payload,
                                        headers={"Authorization":(f"Bearer "f"{settings.MODEL_API_TOKEN}")}
                                    ))
                if (response.status_code!= 200):
                    raise HTTPException(status_code=502, detail=("AI service temporarily unavailable"))

                data = (response.json())

                return {
                    "answer":data.get("answer",""),
                    "sources":data.get("sources",[]),
                    "page_numbers":data.get("page_numbers",[]),
                    "confidence":data.get("confidence",0.0),
                    "suggested_next_action":data.get("suggested_next_action",None)
                }

        except (httpx.ReadTimeout):
            raise HTTPException(
                status_code=504,
                detail=("AI response timed out")
            )

        except (httpx.ConnectError):
            raise HTTPException(
                status_code=503,
                detail=("AI service unreachable")
            )

        except Exception:

            raise HTTPException(
                status_code=500,
                detail=("Unexpected AI service error")
            )
