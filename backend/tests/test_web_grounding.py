"""Deterministic tests for explicit web grounding; no provider calls."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services.web_grounding import (
    ExternalSource,
    WebGroundingResult,
    _extract_sources,
    sanitize_web_question,
    search_web_for_chemistry,
)


def test_web_question_is_sanitized_and_bounded():
    question = "  ما   هو الماء؟  " + ("س" * 1200)
    sanitized = sanitize_web_question(question)
    assert sanitized.startswith("ما هو الماء؟")
    assert len(sanitized) == 1000


def test_invalid_urls_and_uncited_chunks_are_rejected():
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[
                        SimpleNamespace(web=SimpleNamespace(uri="javascript:alert(1)", title="bad")),
                        SimpleNamespace(web=SimpleNamespace(uri="https://example.org/good", title="good")),
                        SimpleNamespace(web=SimpleNamespace(uri="https://example.org/uncited", title="uncited")),
                    ],
                    grounding_supports=[
                        SimpleNamespace(
                            segment=SimpleNamespace(text="موضع موثق", start_index=0, end_index=10),
                            grounding_chunk_indices=[0, 1],
                        )
                    ],
                )
            )
        ]
    )

    sources = _extract_sources(response)

    assert [source.url for source in sources] == ["https://example.org/good"]
    assert sources[0].cited_text == "موضع موثق"


def test_provider_abstraction_can_be_fully_mocked():
    class FakeProvider:
        async def search(self, question: str, *, subject: str, grade: str) -> WebGroundingResult:
            assert (question, subject, grade) == ("ما هو الماء؟", "chemistry", "9")
            return WebGroundingResult(
                answer="الماء مركب كيميائي.",
                sources=[
                    ExternalSource(
                        title="Example",
                        url="https://example.org/water",
                        domain="example.org",
                        cited_text="Water is a compound.",
                    )
                ],
            )

    result = asyncio.run(
        search_web_for_chemistry(
            "ما هو الماء؟",
            subject="chemistry",
            grade="9",
            provider=FakeProvider(),
        )
    )
    assert result.sources[0].domain == "example.org"
