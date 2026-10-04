import shutil
import subprocess
from pathlib import Path
from typing import Optional

import noisereduce as nr
import soundfile as sf

from config.settings import settings

SUPPORTED_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".wma",
    ".mp4", ".mkv", ".webm", ".mov",
}


def _check_ffmpeg() -> None:
    """Stop early with a clear message if ffmpeg is not installed / not on PATH."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg was not found on PATH. Install it (winget install Gyan.FFmpeg) "
            "and open a new terminal."
        )


def convert_to_wav(input_path: Path, output_path: Optional[Path] = None) -> Path:
    """Convert any audio/video file to 16 kHz, mono, 16-bit WAV (what Whisper expects)."""
    _check_ffmpeg()
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{input_path.suffix}'. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    if output_path is None:
        settings.processed_dir.mkdir(parents=True, exist_ok=True)
        output_path = settings.processed_dir / f"{input_path.stem}_16k.wav"
    output_path = Path(output_path)

    command = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",                                   # drop any video track
        "-ac", "1",                              # mono
        "-ar", str(settings.target_sample_rate), # 16 kHz
        "-c:a", "pcm_s16le",                     # 16-bit WAV
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-800:]}")
    return output_path


def reduce_noise(wav_path: Path, output_path: Optional[Path] = None) -> Path:
    """Reduce steady background noise (fans, hum, hiss) in a WAV file."""
    wav_path = Path(wav_path)
    audio, sample_rate = sf.read(str(wav_path))

    cleaned = nr.reduce_noise(y=audio, sr=sample_rate, stationary=True, prop_decrease=0.8)

    if output_path is None:
        output_path = wav_path.with_name(f"{wav_path.stem}_clean.wav")
    sf.write(str(output_path), cleaned, sample_rate)
    return Path(output_path)


def get_duration(wav_path: Path) -> float:
    """Length of an audio file in seconds."""
    return float(sf.info(str(wav_path)).duration)


def preprocess_audio(input_path: Path, denoise: bool = False) -> Path:
    """Full Stage-1 cleanup: convert to 16 kHz mono WAV, optionally reduce noise."""
    wav_path = convert_to_wav(input_path)
    if denoise:
        wav_path = reduce_noise(wav_path)
    return wav_path
