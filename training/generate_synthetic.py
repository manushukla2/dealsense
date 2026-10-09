"""
Generate synthetic sales calls labelled won=1 / lost=0 using the Anthropic API.
Writes data/synthetic/synthetic_calls.jsonl.
Run:  python -m training.generate_synthetic --n 200
"""
import argparse
import json
import random
from pathlib import Path

import anthropic

from config.settings import settings

OUT = settings.synthetic_dir / "synthetic_calls.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)

WON_CUES = [
    "the client asks to move forward",
    "the client confirms budget is approved",
    "the client sets a start date",
    "the client says the pilot worked well",
    "the client asks to loop in legal for the contract",
]
LOST_CUES = [
    "the client says they went with a competitor",
    "the client says the price is too high and they are stopping the process",
    "the client says they no longer have budget this year",
    "the client says the product is not a fit",
    "the client stops responding after the rep follows up twice",
]

SYSTEM = (
    "You write short fictional B2B sales call transcripts. "
    "Each transcript has 4 to 6 exchanges. "
    "Format each line as SPEAKER: text. "
    "Use only REP and CLIENT as speaker labels. "
    "Write nothing except the transcript."
)


def _prompt(label: int) -> str:
    cue = random.choice(WON_CUES if label == 1 else LOST_CUES)
    return (
        f"Write a short B2B sales call transcript where {cue}. "
        "Include natural objections, questions and replies. "
        "End the call clearly."
    )


def generate(n: int = 100, append: bool = False) -> None:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    mode = "a" if append else "w"
    written = 0
    with open(OUT, mode, encoding="utf-8") as f:
        for i in range(n):
            label = i % 2          # alternate won/lost so the set stays balanced
            try:
                response = client.messages.create(
                    model=settings.llm_model,
                    max_tokens=600,
                    system=SYSTEM,
                    messages=[{"role": "user", "content": _prompt(label)}],
                )
                text = "".join(
                    block.text for block in response.content
                    if getattr(block, "type", "") == "text"
                ).strip()
                if text:
                    f.write(json.dumps({"text": text, "label": label}) + "\n")
                    written += 1
                    if written % 10 == 0:
                        print(f"  {written}/{n}")
            except Exception as exc:
                print(f"  skipped {i}: {exc}")
    print(f"Done. {written} calls written to {OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()
    generate(args.n, args.append)
