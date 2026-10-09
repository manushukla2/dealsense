"""
Fine-tune the sentiment/intent model on the prepared JSONL data.
Run:  python -m training.train_sentiment_intent
"""
import json
from pathlib import Path

import torch
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from config.settings import settings

DATA = settings.processed_dir / "sentiment_intent_train.jsonl"
OUT  = settings.models_dir / "sentiment_intent"
BASE = "cardiffnlp/twitter-roberta-base-sentiment-latest"
MAX_LEN = 128
EPOCHS  = 3
BATCH   = 16


def _load(path: Path) -> Dataset:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    labels = sorted({r["sentiment"] for r in rows})
    label2id = {l: i for i, l in enumerate(labels)}
    return Dataset.from_list([
        {"text": r["text"], "label": label2id[r["sentiment"]]}
        for r in rows
    ]), label2id


def train() -> None:
    if not DATA.exists():
        raise FileNotFoundError(f"Run prepare_datasets.py first. Missing: {DATA}")

    ds, label2id = _load(DATA)
    id2label = {v: k for k, v in label2id.items()}
    ds = ds.train_test_split(test_size=0.1, seed=42)

    tokenizer = AutoTokenizer.from_pretrained(BASE)
    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=MAX_LEN, padding="max_length")
    ds = ds.map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, num_labels=len(label2id),
        id2label=id2label, label2id=label2id, ignore_mismatched_sizes=True,
    )

    args = TrainingArguments(
        output_dir=str(OUT / "checkpoints"),
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH,
        per_device_eval_batch_size=BATCH,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    Trainer(
        model=model,
        args=args,
        train_dataset=ds["train"],
        eval_dataset=ds["test"],
    ).train()

    model.save_pretrained(str(OUT))
    tokenizer.save_pretrained(str(OUT))
    print(f"Model saved to {OUT}")


if __name__ == "__main__":
    train()
