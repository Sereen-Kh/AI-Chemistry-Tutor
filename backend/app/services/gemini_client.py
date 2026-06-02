"""Centralized Google GenAI client and config helpers."""

from __future__ import annotations

from app.core.config import settings


def get_gemini_client():
    """Create a Google GenAI client from configured API credentials."""
    if not settings.effective_gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required to use Gemini.")
    from google import genai

    return genai.Client(api_key=settings.effective_gemini_api_key)


def generation_http_options():
    """Return shared generation timeout/retry options."""
    from google.genai import types

    return types.HttpOptions(
        timeout=settings.ai_request_timeout_seconds * 1000,
        retry_options=types.HttpRetryOptions(attempts=1),
    )


def document_generation_config(response_schema):
    """Return structured-output config for document extraction."""
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        http_options=generation_http_options(),
        temperature=0.0,
        max_output_tokens=8192,
    )


def tutor_generation_config(system_prompt: str, *, temperature: float = 0.4, max_output_tokens: int = 1024):
    """Return config for normal tutor answer generation."""
    from google.genai import types

    return types.GenerateContentConfig(
        http_options=generation_http_options(),
        system_instruction=system_prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def embedding_config(task_type: str):
    """Return Gemini embedding config for document/query vectors."""
    from google.genai import types

    return types.EmbedContentConfig(task_type=task_type, output_dimensionality=768)
