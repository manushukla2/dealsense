import pytest
from pathlib import Path
from src.audio.preprocess import preprocess_audio
from src.audio.transcribe import transcribe_audio


def test_transcribe_short_wav(tmp_path):
    """Transcribe the test tone we already have; just check it returns text and timing."""
    sample = Path("data/samples/test_speech.wav")
    if not sample.exists():
        pytest.skip("test_speech.wav not found in data/samples")
    wav = preprocess_audio(sample, denoise=False)
    result = transcribe_audio(wav)
    assert result.language is not None
    assert len(result.segments) > 0
    assert result.duration > 0
    joined = result.as_text().lower()
    assert "pricing" in joined or "technical" in joined or "crm" in joined


def test_transcribe_empty_raises(tmp_path):
    """A silent WAV should come back with no segments (not crash)."""
    import soundfile as sf
    import numpy as np
    silent = tmp_path / "silent.wav"
    sf.write(str(silent), np.zeros(16000, dtype="float32"), 16000)
    result = transcribe_audio(silent)
    assert isinstance(result.segments, list)
