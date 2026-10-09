from src.schemas import Role, Transcript, Turn
from src.nlp.segmenter import segment_exchanges


def _t(role, start, text):
    return Turn(speaker="S1" if role == Role.REP else "S0", role=role, start=start, end=start+4, text=text)


def test_basic_segmentation():
    turns = [
        _t(Role.REP, 0, "Our platform plugs into your tools."),
        _t(Role.CLIENT, 5, "Your pricing seems high."),
        _t(Role.REP, 10, "We can offer a pilot."),
        _t(Role.CLIENT, 15, "That could work."),
    ]
    exchanges = segment_exchanges(Transcript(turns=turns, duration=20))
    assert len(exchanges) == 2
    assert all(e.turns[-1].role == Role.CLIENT for e in exchanges)


def test_long_silence_splits():
    turns = [
        _t(Role.REP, 0, "Let me walk you through the platform."),
        _t(Role.CLIENT, 5, "Sounds good."),
        _t(Role.REP, 120, "Following up from earlier."),
        _t(Role.CLIENT, 125, "Yes, still interested."),
    ]
    exchanges = segment_exchanges(Transcript(turns=turns, duration=130))
    assert len(exchanges) == 2


def test_empty_transcript():
    assert segment_exchanges(Transcript(turns=[], duration=0)) == []


def test_no_roles_fallback():
    from src.schemas import Role
    turns = [Turn(speaker="S0", role=Role.UNKNOWN, start=i*5, end=i*5+4, text=f"line {i}") for i in range(6)]
    exchanges = segment_exchanges(Transcript(turns=turns, duration=30))
    assert len(exchanges) >= 1
