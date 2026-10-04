import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from config.settings import settings

SEARCH_WINDOW_SECONDS = 15.0   # look this far back from the size limit for a quiet spot
FRAME_SECONDS = 0.1            # loudness is measured in 0.1 s slices
HEADER_MARGIN_BYTES = 4096     # safety room for the WAV header


@dataclass
class Chunk:
    """One piece of a long recording."""

    index: int
    path: Path
    start: float       # where this chunk begins in the ORIGINAL audio (seconds)
    end: float
    size_bytes: int

    @property
    def duration(self) -> float:
        return self.end - self.start


def _max_chunk_seconds(sample_rate: int, max_bytes: int) -> float:
    """How many seconds of 16-bit mono audio fit inside max_bytes."""
    bytes_per_second = sample_rate * 2
    return (max_bytes - HEADER_MARGIN_BYTES) / bytes_per_second


def _quietest_point(samples: np.ndarray, lo: int, hi: int, sample_rate: int) -> int:
    """Return the sample index of the quietest 0.1 s slice between lo and hi."""
    frame = int(FRAME_SECONDS * sample_rate)
    usable = (hi - lo) // frame
    if usable < 2:
        return hi
    block = samples[lo : lo + usable * frame].astype(np.float32).reshape(usable, frame)
    energy = np.abs(block).mean(axis=1)
    quietest = int(np.argmin(energy))
    return lo + quietest * frame + frame // 2


def split_audio(wav_path: Path, max_bytes: Optional[int] = None) -> list[Chunk]:
    """Split a WAV file into chunks that each stay under max_bytes.

    Cuts are placed at the quietest moment near the size limit, so words
    are not sliced in half. Short files come back as a single chunk.
    """
    wav_path = Path(wav_path)
    if max_bytes is None:
        max_bytes = settings.max_chunk_bytes

    file_size = wav_path.stat().st_size
    total_seconds = float(sf.info(str(wav_path)).duration)

    if file_size <= max_bytes:
        return [Chunk(0, wav_path, 0.0, total_seconds, file_size)]

    samples, sample_rate = sf.read(str(wav_path), dtype="int16")
    if samples.ndim > 1:
        samples = samples[:, 0]
    total = len(samples)

    max_samples = int(_max_chunk_seconds(sample_rate, max_bytes) * sample_rate)
    window = int(SEARCH_WINDOW_SECONDS * sample_rate)

    out_dir = settings.processed_dir / "chunks" / wav_path.stem
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    chunks: list[Chunk] = []
    start, index = 0, 0
    while start < total:
        end = min(start + max_samples, total)
        if end < total:
            lo = max(start + max_samples // 2, end - window)
            end = _quietest_point(samples, lo, end, sample_rate)

        chunk_path = out_dir / f"{wav_path.stem}_part{index:03d}.wav"
        sf.write(str(chunk_path), samples[start:end], sample_rate, subtype="PCM_16")

        size = chunk_path.stat().st_size
        if size > max_bytes:
            raise RuntimeError(f"Chunk {index} is {size} bytes, over the {max_bytes} limit.")

        chunks.append(Chunk(index, chunk_path, start / sample_rate, end / sample_rate, size))
        start = end
        index += 1

    return chunks


def cleanup_chunks(chunks: list[Chunk]) -> None:
    """Delete the temporary chunk files (never the original recording)."""
    chunks_root = settings.processed_dir / "chunks"
    for chunk in chunks:
        if chunks_root in chunk.path.parents:
            chunk.path.unlink(missing_ok=True)
