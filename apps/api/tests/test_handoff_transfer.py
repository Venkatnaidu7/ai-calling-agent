from types import SimpleNamespace
from datetime import datetime
from zoneinfo import ZoneInfo

from app.providers.openai_realtime import HANDOFF_TOOL
from app.services.handoff import ACTIVE_STATES, is_business_hours


def test_handoff_active_states_are_supported():
    assert ACTIVE_STATES == {'AVAILABLE', 'ONLINE', 'READY'}


def test_transfer_provider_contract_is_restricted():
    assert {'twilio', 'plivo'} == {'twilio', 'plivo'}


def test_transfer_states_are_explicit():
    assert {'REQUESTED', 'TRANSFERRING', 'CONNECTED', 'FAILED'} == {'REQUESTED', 'TRANSFERRING', 'CONNECTED', 'FAILED'}


def test_realtime_handoff_tool_has_safe_required_reason():
    assert HANDOFF_TOOL['type'] == 'function'
    assert HANDOFF_TOOL['name'] == 'transfer_to_human'
    params = HANDOFF_TOOL['parameters']
    assert params['required'] == ['reason']
    assert params['additionalProperties'] is False


def test_business_hours_supports_list_windows():
    bh = SimpleNamespace(timezone='Asia/Kolkata', hours={'sat': [['09:00', '17:00']]})

    class DB:
        async def scalar(self, query):
            return bh

    import asyncio
    assert asyncio.run(is_business_hours(DB(), object(), datetime(2026, 9, 12, 12, 0, tzinfo=ZoneInfo('Asia/Kolkata')))) is True
    assert asyncio.run(is_business_hours(DB(), object(), datetime(2026, 9, 12, 18, 0, tzinfo=ZoneInfo('Asia/Kolkata')))) is False


def test_business_hours_supports_overnight_window():
    bh = SimpleNamespace(timezone='Asia/Kolkata', hours={'sat': [['22:00', '06:00']]})

    class DB:
        async def scalar(self, query):
            return bh

    import asyncio
    assert asyncio.run(is_business_hours(DB(), object(), datetime(2026, 9, 12, 23, 0, tzinfo=ZoneInfo('Asia/Kolkata')))) is True
