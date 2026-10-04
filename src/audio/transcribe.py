import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

from config.settings import settings
from src.audio.chunker import Chunk, cleanup_chunks, split_audio

logger = logging.getLogger(__name__)

MAX_RETRIES = 4
BACKOFF_SECONDS = 5
NO_SPEECH_THRESHOLD = 0.8   # segments Whisper thinks are silence/noise above this are dropped


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Segment:
    text: str
    start: float
    end: float


@dataclass
class TranscriptionResult:
    """Speech-to-text output for a whole recording, on the ORIGINAL timeline."""

    segments: list[Segment] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    language: Optional[str] = None
    duration: float = 0.0

    def as_text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field whether the API gave us a dict or an object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _call_api(client: Groq, chunk: Chunk, language: Optional[str], prompt: Optional[str]) -> Any:
    """Send one chunk to Groq Whisper, retrying on rate limits and network errors."""
    audio_bytes = chunk.path.read_bytes()
    options: dict[str, Any] = {
        "model": settings.whisper_model,
        "response_format": "verbose_json",
        "timestamp_granularities": ["word", "segment"],
        "temperature": 0.0,
    }
    if language:
        options["language"] = language
    if prompt:
        options["prompt"] = prompt

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.audio.transcriptions.create(
                file=(chunk.path.name, audio_bytes), **options
            )
        except (RateLimitError, APIConnectionError) as error:
            reason = type(error).__name__
        except APIStatusError as error:
            if error.status_code < 500:
                raise          # bad key, bad file, etc. Retrying will not help.
            reason = f"server error {error.status_code}"

        if attempt == MAX_RETRIES:
            raise RuntimeError(f"Chunk {chunk.index} failed after {MAX_RETRIES} attempts ({reason}).")
        wait = BACKOFF_SECONDS * 2 ** (attempt - 1)
        logger.warning("Chunk %s: %s. Retrying in %ss (attempt %s/%s).",
                       chunk.index, reason, wait, attempt, MAX_RETRIES)
        time.sleep(wait)


def _parse_response(response: Any, offset: float) -> tuple[list[Segment], list[Word]]:
    """Turn one API response into Segment/Word objects shifted by the chunk offset."""
    segments: list[Segment] = []
    for seg in _get(response, "segments", []) or []:
        text = (_get(seg, "text", "") or "").strip()
        no_speech = _get(seg, "no_speech_prob", 0.0) or 0.0
        if not text or no_speech > NO_SPEECH_THRESHOLD:
            continue
        segments.append(Segment(text, float(_get(seg, "start", 0.0)) + offset,
                                float(_get(seg, "end", 0.0)) + offset))

    words: list[Word] = []
    for w in _get(response, "words", []) or []:
        start = float(_get(w, "start", 0.0)) + offset
        end = float(_get(w, "end", 0.0)) + offset
        middle = (start + end) / 2
        if any(s.start <= middle <= s.end for s in segments):
            words.append(Word((_get(w, "word", "") or "").strip(), start, end))
    return segments, words


def transcribe_audio(
    wav_path: Path,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    keep_chunks: bool = False,
) -> TranscriptionResult:
    """Transcribe a cleaned WAV file of any length with Groq Whisper."""
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is empty. Add it to .env first.")

    client = Groq(api_key=settings.groq_api_key, max_retries=0)  # we do our own retries
    chunks = split_audio(Path(wav_path))
    result = TranscriptionResult(duration=chunks[-1].end)

    try:
        for chunk in chunks:
            logger.info("Transcribing chunk %s/%s", chunk.index + 1, len(chunks))
            response = _call_api(client, chunk, language, prompt)
            segments, words = _parse_response(response, offset=chunk.start)
            result.segments.extend(segments)
            result.words.extend(words)
            if result.language is None:
                result.language = _get(response, "language", None)
    finally:
        if not keep_chunks:
            cleanup_chunks(chunks)

    return result
