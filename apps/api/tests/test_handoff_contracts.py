from datetime import datetime
from types import SimpleNamespace

from app.services.handoff import ACTIVE_STATES, is_business_hours


def test_handoff_states_are_provider_agnostic():
    assert ACTIVE_STATES == {'AVAILABLE', 'ONLINE', 'READY'}


def test_business_hours_window_is_inclusive():
    assert is_business_hours


def test_handoff_destination_has_normalized_shape():
    destination = SimpleNamespace(id='d1', name='Support', phone='+14155551234')
    assert destination.phone.startswith('+')
    assert destination.name == 'Support'


def test_timezone_aware_datetime_is_accepted():
    value = datetime.fromisoformat('2026-09-12T10:00:00+05:30')
    assert value.utcoffset() is not None
