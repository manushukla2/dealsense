import pytest
from pathlib import Path
from src.pipeline import run


def test_pipeline_fallback(tmp_path):
    """Full pipeline on dialogue.wav, LLM off."""
    sample = Path("data/samples/dialogue.wav")
    if not sample.exists():
        pytest.skip("dialogue.wav not found in data/samples")
    result = run(sample, use_llm=False)
    assert result.meeting_id
    assert len(result.transcript.turns) >= 2
    assert result.prediction is not None
    assert 0.0 <= result.prediction.probability <= 1.0


def test_pipeline_missing_file():
    with pytest.raises(FileNotFoundError):
        run(Path("data/samples/nonexistent.wav"), use_llm=False)
