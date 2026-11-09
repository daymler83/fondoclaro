from enum import StrEnum

from ..config import Blocked


class State(StrEnum):
    PENDING = "PENDING"
    DATA_COLLECTED = "DATA_COLLECTED"
    DATA_VALIDATED = "DATA_VALIDATED"
    CALCULATED = "CALCULATED"
    NUMERICALLY_VERIFIED = "NUMERICALLY_VERIFIED"
    CONTENT_GENERATED = "CONTENT_GENERATED"
    VISUAL_GENERATED = "VISUAL_GENERATED"
    VISUALLY_VERIFIED = "VISUALLY_VERIFIED"
    HUMAN_REVIEW_PENDING = "HUMAN_REVIEW_PENDING"
    APPROVED_FOR_PUBLICATION = "APPROVED_FOR_PUBLICATION"
    MARKED_PUBLISHED = "MARKED_PUBLISHED"
    BLOCKED = "BLOCKED"
    SUPERSEDED = "SUPERSEDED"


FLOW = list(State)[:-2]
AUDIT_STATES = ("NOT_REQUESTED", "PACKAGE_EXPORTED", "RESULT_IMPORTED_PASS", "RESULT_IMPORTED_FINDINGS", "RESULT_INVALID")


def check_transition(old, new):
    old, new = State(old), State(new)
    if old in (State.BLOCKED, State.SUPERSEDED):
        raise Blocked("Terminal state")
    if new in (State.BLOCKED, State.SUPERSEDED):
        return
    if FLOW.index(old)+1 >= len(FLOW) or FLOW[FLOW.index(old)+1] != new:
        raise Blocked(f"INVALID_TRANSITION: {old} -> {new}")
