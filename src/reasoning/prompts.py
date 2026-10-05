from src.schemas import Exchange, ExchangeAnalysis, format_timestamp
from src.scoring.scorer import DealScore

EXPECTED_KEYS = ["verdict", "summary", "moments", "positives", "risks", "next_step"]
MOMENT_KEYS = ["exchange", "timestamp", "what_happened", "why_it_matters", "effect"]
VALID_EFFECTS = {"positive", "negative", "neutral"}

SYSTEM_PROMPT = """You are a sales-conversation analyst. You explain, in clear plain English, why a recorded meeting looks likely or unlikely to end in a positive result.

You are given:
- the meeting split into numbered exchanges (speaker, time, exact words),
- an automatic analysis of each exchange (score, tone, intent, evidence found),
- a FINAL ESTIMATE: the percentage chance of a positive result, already computed.

Rules:
1. The percentage is fixed. Never recalculate, adjust or contradict it. Refer to it as an estimate.
2. Use only what is in the transcript and the analysis. Do not invent facts, names, prices, dates or events.
3. Quote the speakers' exact words in quotation marks, copied character for character from the transcript. Keep each quote short.
4. Call the two sides "the client" and "the rep".
5. Write one moment for every exchange, in order. For each, say what was said and how the other side reacted ("the client said ..., the rep replied ..., the client responded ..."), then say what that suggests for the deal and whether the effect is positive, negative or neutral.
6. If an exchange has no client reply, say so and mark it neutral.
7. Keep the reasoning consistent with the analysis scores and the evidence lists. If you disagree with a score because the words clearly say otherwise, follow the words and note the doubt briefly.
8. Be honest about uncertainty. If told the estimate is not calibrated, or that there is little evidence, say so plainly in the summary.
9. Use simple, direct sentences. No jargon, no hype, no filler.

Reply with ONE JSON object and nothing else: no introduction, no markdown fences. Use exactly this shape:

{
  "verdict": "a short phrase, for example: Leaning positive, but the client is still comparing options",
  "summary": "2 or 3 sentences: the overall picture, the estimate, and the main reason for it",
  "moments": [
    {
      "exchange": 0,
      "timestamp": "04:12",
      "what_happened": "what was said and how the other side reacted, with short exact quotes",
      "why_it_matters": "what this suggests about the deal, in one or two sentences",
      "effect": "positive"
    }
  ],
  "positives": ["up to 4 short points that raise the chance of a deal"],
  "risks": ["up to 4 short points that lower it"],
  "next_step": "one practical recommendation for the rep"
}

"effect" must be exactly "positive", "negative" or "neutral". "exchange" is the exchange number you were given."""


def _readable(intent: str) -> str:
    return intent.replace("_", " ")


def _format_drivers(drivers) -> str:
    if not drivers:
        return "  - none"
    return "\n".join(f"  - {d.description} ({d.effect_points:+.1f} points)" for d in drivers)


def build_user_prompt(
    exchanges: list[Exchange],
    analyses: list[ExchangeAnalysis],
    percent: float,
    score: DealScore,
    calibration_note: str = "",
) -> str:
    """Assemble everything the LLM needs: the meeting, the evidence and the final estimate."""
    by_index = {a.exchange_index: a for a in analyses}

    blocks = []
    for exchange in exchanges:
        lines = [f"EXCHANGE {exchange.index} (starts {format_timestamp(exchange.start)})", exchange.text]
        analysis = by_index.get(exchange.index)
        if analysis is not None:
            lines.append(
                f"Machine analysis: score {analysis.score:+.2f} (-1 bad to +1 good), "
                f"tone {analysis.sentiment.value}, intent: {_readable(analysis.intent)}"
            )
            if analysis.signals:
                lines.append("Evidence found:")
                lines.extend(f"  - {signal}" for signal in analysis.signals)
            else:
                lines.append("Evidence found: none")
        blocks.append("\n".join(lines))

    notes = []
    if calibration_note:
        notes.append(f"Calibration: {calibration_note}.")
    notes.append(f"The estimate came from the {score.source} scoring method.")
    if score.low_data:
        notes.append("There are very few exchanges, so say clearly that the estimate rests on little evidence.")

    return "\n\n".join([
        "MEETING",
        "\n\n".join(blocks),
        f"FINAL ESTIMATE: {percent:.0f}% chance of a positive result",
        "Factors that raised the estimate (effect in percentage points):\n" + _format_drivers(score.positives),
        "Factors that lowered the estimate:\n" + _format_drivers(score.risks),
        "NOTES\n" + "\n".join(notes),
        "Now write the JSON object.",
    ])


def build_repair_prompt(bad_output: str, error: str) -> str:
    """Sent when the first reply could not be read as the required JSON."""
    keys = ", ".join(EXPECTED_KEYS)
    return (
        f"Your previous reply could not be used: {error}\n"
        f"Reply again with ONLY one valid JSON object containing exactly these keys: {keys}. "
        "Do not add any text before or after it and do not use markdown fences.\n\n"
        f"Previous reply:\n{bad_output[:3000]}"
    )
