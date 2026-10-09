"""
Train the deal scorer on real or synthetic won/lost data.
Run:  python -m training.train_scorer
      python -m training.train_scorer --data data/synthetic/synthetic_calls.jsonl
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

from config.settings import settings
from src.nlp.segmenter import segment_exchanges
from src.nlp.sentiment_intent import analyze_exchanges
from src.schemas import Transcript, Turn, Role
from src.scoring.features import extract_features, features_table
from src.scoring.scorer import save_scorer

DEFAULT_DATA = settings.processed_dir / "scorer_train.jsonl"


def _transcript_from_text(text: str) -> Transcript:
    turns = []
    for i, line in enumerate(text.strip().splitlines()):
        if ":" not in line:
            continue
        speaker, _, utt = line.partition(":")
        role = Role.REP if speaker.strip().upper() == "REP" else Role.CLIENT
        turns.append(Turn(speaker=speaker.strip(), role=role,
                          start=float(i * 8), end=float(i * 8 + 6), text=utt.strip()))
    return Transcript(turns=turns, duration=float(len(turns) * 8))


def train(data_path: Path) -> None:
    rows = [json.loads(l) for l in data_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"Loaded {len(rows)} rows from {data_path}")

    feature_dicts, labels = [], []
    for i, row in enumerate(rows):
        try:
            transcript = _transcript_from_text(row["text"])
            exchanges = segment_exchanges(transcript)
            analyses = analyze_exchanges(exchanges)
            feature_dicts.append(extract_features(analyses, transcript))
            labels.append(int(row["label"]))
        except Exception as exc:
            print(f"  skipped row {i}: {exc}")
        if (i + 1) % 50 == 0:
            print(f"  processed {i + 1}/{len(rows)}")

    X = features_table(feature_dicts).values
    y = np.array(labels)
    print(f"Features: {X.shape}, won: {y.sum()}, lost: {len(y)-y.sum()}")

    model = GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
    print(f"CV AUC: {scores.mean():.3f} ± {scores.std():.3f}")

    model.fit(X, y)
    path = save_scorer(model, metadata={"data": str(data_path), "n": len(y), "cv_auc": float(scores.mean())})
    print(f"Scorer saved to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    train(args.data)
