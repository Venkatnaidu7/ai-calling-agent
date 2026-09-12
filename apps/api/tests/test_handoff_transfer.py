from types import SimpleNamespace
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio

from app.providers.openai_realtime import HANDOFF_TOOL
from app.services.handoff import ACTIVE_STATES, HANDOFF_STATES, is_business_hours, sync_handoff_state


def test_handoff_active_states_are_supported():
    assert ACTIVE_STATES == {'AVAILABLE', 'ONLINE', 'READY'}


def test_transfer_provider_contract_is_restricted():
    from app.services.handoff import VOICE_PROVIDERS
    assert VOICE_PROVIDERS == {'twilio', 'plivo'}


def test_transfer_states_are_explicit():
    assert HANDOFF_STATES == {'REQUESTED', 'TRANSFERRING', 'CONNECTED', 'FAILED'}


def test_realtime_handoff_tool_has_safe_required_reason():
    assert HANDOFF_TOOL['type'] == 'function'
    assert HANDOFF_TOOL['name'] == 'transfer_to_human'
    params = HANDOFF_TOOL['parameters']
    assert params['required'] == ['reason']
    assert params['additionalProperties'] is False
    assert 'phone' not in params['properties']


def _db_with_hours(hours):
    bh = SimpleNamespace(timezone='Asia/Kolkata', hours=hours)
    class DB:
        async def scalar(self, query): return bh
    return DB()


def test_business_hours_supports_list_windows():
    db = _db_with_hours({'sat': [['09:00', '17:00']]})
    assert asyncio.run(is_business_hours(db, object(), datetime(2026, 9, 12, 12, 0, tzinfo=ZoneInfo('Asia/Kolkata')))) is True
    assert asyncio.run(is_business_hours(db, object(), datetime(2026, 9, 12, 18, 0, tzinfo=ZoneInfo('Asia/Kolkata')))) is False


def test_business_hours_supports_overnight_window_across_midnight():
    db = _db_with_hours({'sat': [['22:00', '06:00']]})
    assert asyncio.run(is_business_hours(db, object(), datetime(2026, 9, 12, 23, 0, tzinfo=ZoneInfo('Asia/Kolkata')))) is True
    assert asyncio.run(is_business_hours(db, object(), datetime(2026, 9, 13, 2, 0, tzinfo=ZoneInfo('Asia/Kolkata')))) is True
    assert asyncio.run(is_business_hours(db, object(), datetime(2026, 9, 13, 7, 0, tzinfo=ZoneInfo('Asia/Kolkata')))) is False


def _handoff_db(handoff):
    class DB:
        async def scalar(self, query): return handoff
    return DB()


def test_handoff_state_moves_to_connected_on_provider_answer():
    handoff = SimpleNamespace(status='TRANSFERRING', failure_reason=None)
    call = SimpleNamespace(id='call-1', tenant_id='tenant-1')
    result = asyncio.run(sync_handoff_state(_handoff_db(handoff), call, 'in-progress'))
    assert result is handoff
    assert handoff.status == 'CONNECTED'
    assert handoff.failure_reason is None


def test_handoff_state_is_idempotent_after_connected():
    handoff = SimpleNamespace(status='CONNECTED', failure_reason=None)
    call = SimpleNamespace(id='call-1', tenant_id='tenant-1')
    asyncio.run(sync_handoff_state(_handoff_db(handoff), call, 'completed'))
    assert handoff.status == 'CONNECTED'


def test_handoff_state_marks_unanswered_transfer_failed():
    handoff = SimpleNamespace(status='TRANSFERRING', failure_reason=None)
    call = SimpleNamespace(id='call-1', tenant_id='tenant-1')
    asyncio.run(sync_handoff_state(_handoff_db(handoff), call, 'no-answer'))
    assert handoff.status == 'FAILED'
    assert handoff.failure_reason == 'NO-ANSWER'
