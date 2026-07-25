import json
import time
import logging
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    @staticmethod
    def generate_json(
        *,
        model: str,
        prompt: str,
        schema: dict,
        temperature: float = 0.3,
        max_retries: int = 4,
    ) -> dict:
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling Gemini model={model}, attempt={attempt + 1}")
                response = GeminiService.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )

                if not response.text:
                    raise ValueError("Gemini returned empty response")
                
                return json.loads(response.text)

            except Exception as e:
                logger.warning(f"Gemini failed attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise
                sleep_time = (2 ** attempt) * 3
                time.sleep(sleep_time)