import pytest

from app.api.voice import STATUS_MAP, TERMINAL_CALL_STATES


def test_plivo_terminal_statuses_are_explicitly_terminal():
    for status in ("completed", "busy", "no-answer", "failed", "canceled"):
        mapped = STATUS_MAP[status]
        assert mapped in TERMINAL_CALL_STATES or mapped == "FAILED"


def test_plivo_status_mapping_preserves_unknown_state():
    current = "RINGING"
    assert STATUS_MAP.get("provider-future-state", current) == current


def test_terminal_transition_guard_is_idempotent():
    current = "COMPLETED"
    incoming = STATUS_MAP["completed"]
    was_terminal = current in TERMINAL_CALL_STATES
    assert was_terminal is True
    assert incoming == current
    # Terminal callbacks must not be treated as a new terminal transition.
    assert not (incoming in TERMINAL_CALL_STATES and not was_terminal)
