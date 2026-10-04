from src.schemas import Exchange, Role, Transcript, Turn

MAX_TURNS_PER_EXCHANGE = 4      # hard cap so one exchange never grows into a whole meeting
MAX_GAP_SECONDS = 30.0          # a silence longer than this starts a new exchange
MAX_EXCHANGE_SECONDS = 120.0    # an exchange never spans more than two minutes
MIN_EXCHANGE_WORDS = 6          # tiny exchanges ("Okay.", "Right.") are joined to the previous one


def _word_count(turns: list[Turn]) -> int:
    return sum(len(turn.text.split()) for turn in turns)


def _should_break(current: list[Turn], turn: Turn) -> bool:
    """True if the next turn is too far away (in time) to belong to the current exchange."""
    if not current:
        return False
    if turn.start - current[-1].end > MAX_GAP_SECONDS:
        return True
    return turn.end - current[0].start > MAX_EXCHANGE_SECONDS


def _closes_exchange(current: list[Turn], use_roles: bool, max_turns: int) -> bool:
    """An exchange ends when the client reacts to something said, or the turn cap is hit."""
    if len(current) >= max_turns:
        return True
    if not use_roles:
        return False
    last = current[-1]
    spoke_before = any(turn.role != Role.CLIENT for turn in current[:-1])
    return last.role == Role.CLIENT and spoke_before


def _absorb_small_groups(groups: list[list[Turn]]) -> list[list[Turn]]:
    """Join very short exchanges onto the previous one so every exchange carries some meaning."""
    merged: list[list[Turn]] = []
    for group in groups:
        close_enough = bool(merged) and group[0].start - merged[-1][-1].end <= MAX_GAP_SECONDS
        if close_enough and _word_count(group) < MIN_EXCHANGE_WORDS:
            merged[-1].extend(group)
        else:
            merged.append(group)
    return merged


def segment_exchanges(
    transcript: Transcript,
    max_turns: int = MAX_TURNS_PER_EXCHANGE,
) -> list[Exchange]:
    """Cut a transcript into exchanges: something is said, and the client reacts to it."""
    turns = [turn for turn in transcript.turns if turn.text.strip()]
    if not turns:
        return []

    use_roles = (
        any(turn.role == Role.CLIENT for turn in turns)
        and any(turn.role == Role.REP for turn in turns)
    )

    groups: list[list[Turn]] = []
    current: list[Turn] = []
    for turn in turns:
        if _should_break(current, turn):
            groups.append(current)
            current = []
        current.append(turn)
        if _closes_exchange(current, use_roles, max_turns):
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    groups = _absorb_small_groups(groups)
    return [Exchange(index=i, turns=group) for i, group in enumerate(groups)]


def describe_exchanges(exchanges: list[Exchange]) -> str:
    """A readable dump of the exchanges, for debugging and demos."""
    from src.schemas import format_timestamp

    blocks = []
    for exchange in exchanges:
        header = (
            f"--- Exchange {exchange.index} "
            f"({len(exchange.turns)} turns, "
            f"{format_timestamp(exchange.start)}-{format_timestamp(exchange.end)})"
        )
        blocks.append(f"{header}\n{exchange.text}")
    return "\n".join(blocks)
