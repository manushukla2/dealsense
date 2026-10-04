import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import soundfile as sf
import torch

from config.settings import settings

logger = logging.getLogger(__name__)

PIPELINE_NAME = "pyannote-community/speaker-diarization-community-1"  # public mirror, no token needed
MERGE_GAP_SECONDS = 0.6      # same speaker, pause shorter than this -> join into one segment
MIN_SEGMENT_SECONDS = 0.2    # drop blips shorter than this


@dataclass
class SpeakerSegment:
    """One stretch of speech by one speaker."""

    speaker: str     # e.g. "SPEAKER_00"
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@lru_cache(maxsize=1)
def _load_pipeline():
    """Download (first time) and load the diarization model once per run."""
    from pyannote.audio import Pipeline

    help_text = (
        f"Could not load {PIPELINE_NAME}. Check your internet connection and that "
        f"https://huggingface.co/{PIPELINE_NAME} is still reachable."
    )
    try:
        pipeline = Pipeline.from_pretrained(PIPELINE_NAME, token=settings.hf_token or None)
    except Exception as error:
        raise RuntimeError(help_text) from error
    if pipeline is None:
        raise RuntimeError(help_text)

    if torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))
    return pipeline


def _extract_annotation(output):
    """Get the speaker timeline out of the pipeline result (works across pyannote versions)."""
    for name in ("exclusive_speaker_diarization", "speaker_diarization"):
        annotation = getattr(output, name, None)
        if annotation is not None:
            return annotation
    return output


def _merge_adjacent(segments: list[SpeakerSegment]) -> list[SpeakerSegment]:
    """Join consecutive segments of the same speaker separated by a short pause."""
    merged: list[SpeakerSegment] = []
    for seg in segments:
        if merged and merged[-1].speaker == seg.speaker and seg.start - merged[-1].end <= MERGE_GAP_SECONDS:
            merged[-1].end = max(merged[-1].end, seg.end)
        else:
            merged.append(SpeakerSegment(seg.speaker, seg.start, seg.end))
    return merged


def diarize_audio(
    wav_path: Path,
    num_speakers: Optional[int] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
) -> list[SpeakerSegment]:
    """Work out who spoke when in a cleaned 16 kHz WAV file."""
    wav_path = Path(wav_path)
    if not wav_path.exists():
        raise FileNotFoundError(f"Audio file not found: {wav_path}")

    pipeline = _load_pipeline()

    # Load the audio ourselves so pyannote does not need to decode the file.
    audio, sample_rate = sf.read(str(wav_path), dtype="float32", always_2d=True)
    waveform = torch.from_numpy(audio.mean(axis=1))[None, :]   # shape: (1, samples)

    options = {}
    if num_speakers is not None:
        options["num_speakers"] = num_speakers
    if min_speakers is not None:
        options["min_speakers"] = min_speakers
    if max_speakers is not None:
        options["max_speakers"] = max_speakers

    logger.info("Running speaker diarization on %s", wav_path.name)
    output = pipeline({"waveform": waveform, "sample_rate": sample_rate}, **options)
    annotation = _extract_annotation(output)

    segments = [
        SpeakerSegment(speaker=str(label), start=float(turn.start), end=float(turn.end))
        for turn, _track, label in annotation.itertracks(yield_label=True)
    ]
    segments.sort(key=lambda s: s.start)
    segments = _merge_adjacent(segments)
    return [s for s in segments if s.duration >= MIN_SEGMENT_SECONDS]


def speaking_time(segments: list[SpeakerSegment]) -> dict[str, float]:
    """Total seconds each speaker talked, longest first."""
    totals: dict[str, float] = {}
    for seg in segments:
        totals[seg.speaker] = totals.get(seg.speaker, 0.0) + seg.duration
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))
