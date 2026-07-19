"""Explicit, citation-required web grounding for Ask AI."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

from app.core.config import settings
from app.services.gemini_client import get_gemini_client, tutor_generation_http_options


class WebGroundingError(RuntimeError):
    code = "WEB_SEARCH_UNAVAILABLE"


class WebSearchDisabledError(WebGroundingError):
    code = "WEB_SEARCH_DISABLED"


class WebSearchUnavailableError(WebGroundingError):
    code = "WEB_SEARCH_UNAVAILABLE"


class WebSearchNoVerifiableSourcesError(WebGroundingError):
    code = "WEB_SEARCH_NO_VERIFIABLE_SOURCES"


@dataclass(frozen=True)
class ExternalSource:
    title: str
    url: str
    domain: str
    cited_text: str
    start_index: int | None = None
    end_index: int | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WebGroundingResult:
    answer: str
    sources: list[ExternalSource]


class WebSearchProvider(Protocol):
    async def search(self, question: str, *, subject: str, grade: str) -> WebGroundingResult: ...


def _value(value: object, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _safe_web_url(value: object) -> tuple[str, str] | None:
    raw = str(value or "").strip()
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return raw, parsed.netloc.lower()


def sanitize_web_question(question: str, *, max_chars: int = 1000) -> str:
    return " ".join((question or "").split())[:max_chars]


def _extract_sources(response: object) -> list[ExternalSource]:
    candidates = _value(response, "candidates", []) or []
    if not candidates:
        return []
    metadata = _value(candidates[0], "grounding_metadata")
    chunks = _value(metadata, "grounding_chunks", []) or []
    supports = _value(metadata, "grounding_supports", []) or []
    cited_segments: dict[int, list[tuple[str, int | None, int | None]]] = {}

    for support in supports:
        segment = _value(support, "segment")
        text = str(_value(segment, "text", "") or "").strip()
        start = _value(segment, "start_index")
        end = _value(segment, "end_index")
        for index in _value(support, "grounding_chunk_indices", []) or []:
            if isinstance(index, int):
                cited_segments.setdefault(index, []).append((text, start, end))

    results: list[ExternalSource] = []
    seen_urls: set[str] = set()
    for index, chunk in enumerate(chunks):
        web = _value(chunk, "web")
        safe = _safe_web_url(_value(web, "uri"))
        if safe is None:
            continue
        url, domain = safe
        if url in seen_urls:
            continue
        segments = cited_segments.get(index, [])
        cited_text = " ".join(text for text, _start, _end in segments if text).strip()
        if not cited_text:
            continue
        seen_urls.add(url)
        start_values = [start for _text, start, _end in segments if isinstance(start, int)]
        end_values = [end for _text, _start, end in segments if isinstance(end, int)]
        results.append(
            ExternalSource(
                title=str(_value(web, "title", domain) or domain).strip()[:240],
                url=url,
                domain=domain,
                cited_text=cited_text[:800],
                start_index=min(start_values) if start_values else None,
                end_index=max(end_values) if end_values else None,
            )
        )
    return results


class GeminiGoogleSearchProvider:
    async def search(self, question: str, *, subject: str, grade: str) -> WebGroundingResult:
        if not settings.ask_ai_web_search_enabled:
            raise WebSearchDisabledError("Web grounding is disabled.")
        if not settings.effective_gemini_api_key:
            raise WebSearchUnavailableError("Web grounding provider is not configured.")

        clean_question = sanitize_web_question(question)
        if not clean_question:
            raise WebSearchNoVerifiableSourcesError("A chemistry question is required.")

        def _generate():
            from google.genai import types

            client = get_gemini_client()
            return client.models.generate_content(
                model=settings.model_name,
                contents=clean_question,
                config=types.GenerateContentConfig(
                    http_options=tutor_generation_http_options(),
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    system_instruction=(
                        f"أجب بالعربية عن سؤال {subject} للصف {grade}. "
                        "استخدم نتائج بحث موثوقة فقط، ولا تدّعِ أنها من كتاب EduMind."
                    ),
                    temperature=0.2,
                    max_output_tokens=1024,
                ),
            )

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(_generate),
                timeout=settings.ask_ai_web_search_timeout_seconds,
            )
        except WebGroundingError:
            raise
        except Exception as exc:
            raise WebSearchUnavailableError("Web grounding is temporarily unavailable.") from exc

        answer = str(_value(response, "text", "") or "").strip()
        sources = _extract_sources(response)
        if not answer or not sources:
            raise WebSearchNoVerifiableSourcesError("No verifiable web citations were returned.")
        return WebGroundingResult(answer=answer, sources=sources)


async def search_web_for_chemistry(
    question: str,
    *,
    subject: str = "chemistry",
    grade: str = "9",
    provider: WebSearchProvider | None = None,
) -> WebGroundingResult:
    provider = provider or GeminiGoogleSearchProvider()
    return await provider.search(question, subject=subject, grade=grade)
