import uuid
from types import SimpleNamespace
import pytest
from app.services.handoff import ACTIVE_STATES

def test_handoff_active_states_are_explicit():
    assert ACTIVE_STATES == {'AVAILABLE','ONLINE','READY'}

def test_handoff_requires_valid_destination_shape():
    destination=SimpleNamespace(id=uuid.uuid4(),phone='+14155551234',name='Support')
    assert destination.phone.startswith('+')
    assert destination.name
