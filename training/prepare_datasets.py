"""
Download and format the public datasets for fine-tuning.
Outputs two JSONL files:
  data/processed/sentiment_intent_train.jsonl  -- for train_sentiment_intent.py
  data/processed/scorer_train.jsonl            -- for train_scorer.py
"""
import json
from pathlib import Path

from datasets import load_dataset

from config.settings import settings

OUT = settings.processed_dir
OUT.mkdir(parents=True, exist_ok=True)

INTENT_MAP = {
    "neutral": "small_talk",
    "joy": "interested",
    "surprise": "interested",
    "anger": "price_concern",
    "disgust": "rejecting",
    "sadness": "stalling",
    "fear": "concern_raised",
}

SENTIMENT_MAP = {
    "neutral": "neutral",
    "joy": "positive",
    "surprise": "positive",
    "anger": "negative",
    "disgust": "negative",
    "sadness": "negative",
    "fear": "negative",
}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(rows)} rows -> {path}")


def prepare_sentiment_intent() -> None:
    """MELD: map emotions to our intent/sentiment labels."""
    ds = load_dataset("declare-lab/MELD", split="train", trust_remote_code=True)
    rows = []
    for item in ds:
        emotion = item.get("emotion", "neutral").lower()
        text = item.get("utterance", "").strip()
        if not text:
            continue
        rows.append({
            "text": text,
            "sentiment": SENTIMENT_MAP.get(emotion, "neutral"),
            "intent": INTENT_MAP.get(emotion, "small_talk"),
        })
    _write_jsonl(OUT / "sentiment_intent_train.jsonl", rows)


def prepare_scorer() -> None:
    """CraigslistBargains: map deal/no-deal to won=1/lost=0."""
    ds = load_dataset("stanfordnlp/craigslist_bargains", split="train", trust_remote_code=True)
    rows = []
    for item in ds:
        history = item.get("dialogue_history") or item.get("history") or []
        outcome = item.get("output", {})
        if not history:
            continue
        agreed = outcome.get("agree", None)
        if agreed is None:
            continue
        text = " ".join(
            f"{t.get('role','?')}: {t.get('text','')}" for t in history
        ).strip()
        rows.append({"text": text, "label": int(bool(agreed))})
    _write_jsonl(OUT / "scorer_train.jsonl", rows)


if __name__ == "__main__":
    print("Preparing sentiment/intent data...")
    prepare_sentiment_intent()
    print("Preparing scorer data...")
    prepare_scorer()
    print("Done.")
