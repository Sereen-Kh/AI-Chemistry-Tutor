"""Audio modality schemas and routing helpers for chat."""

from enum import StrEnum

from pydantic import BaseModel


class AudioInputType(StrEnum):
    TEXT = "text"
    AUDIO = "audio"


class RequestedReturnType(StrEnum):
    AUTO = "auto"
    TEXT = "text"
    AUDIO = "audio"
    TEXT_AUDIO = "text_audio"


class ResolvedReturnType(StrEnum):
    TEXT = "text"
    AUDIO = "audio"
    TEXT_AUDIO = "text_audio"


class AudioProcessingStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AudioChatRequestContext(BaseModel):
    input_type: AudioInputType
    requested_return_type: RequestedReturnType
    resolved_return_type: ResolvedReturnType


def resolve_return_type(
    input_type: AudioInputType | str,
    requested_return_type: RequestedReturnType | str,
) -> ResolvedReturnType:
    """Resolve response modality for the chat audio MVP decision matrix."""
    normalized_input = AudioInputType(input_type)
    requested = RequestedReturnType(requested_return_type)

    if requested == RequestedReturnType.TEXT:
        return ResolvedReturnType.TEXT
    if requested == RequestedReturnType.AUDIO:
        return ResolvedReturnType.AUDIO
    if requested == RequestedReturnType.TEXT_AUDIO:
        return ResolvedReturnType.TEXT_AUDIO
    if normalized_input == AudioInputType.AUDIO:
        return ResolvedReturnType.TEXT_AUDIO
    return ResolvedReturnType.TEXT


def should_generate_tts(resolved_return_type: ResolvedReturnType | str) -> bool:
    resolved = ResolvedReturnType(resolved_return_type)
    return resolved in {ResolvedReturnType.AUDIO, ResolvedReturnType.TEXT_AUDIO}
