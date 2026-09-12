import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.billing import current_period, enforce_call_limit


def test_current_period_is_utc_calendar_month():
    start, end = current_period()
    now = datetime.now(timezone.utc)
    assert start.tzinfo is not None and end.tzinfo is not None
    assert start.day == 1
    assert start.hour == 0 and start.minute == 0
    assert end.month == now.month and end.year == now.year
    assert end.day >= 28


def test_unconfigured_subscription_does_not_block_calls():
    class DB:
        async def scalar(self, query):
            return None
    asyncio.run(enforce_call_limit(DB(), uuid4()))


def test_plan_limit_blocks_when_usage_reaches_limit():
    tenant = uuid4()
    plan = SimpleNamespace(id=uuid4(), limits={'minutes': 10})
    sub = SimpleNamespace(tenant_id=tenant, plan_id=plan.id, status='ACTIVE')

    class DB:
        async def scalar(self, query):
            text = str(query)
            if 'subscriptions' in text:
                return sub
            if 'plans' in text:
                return plan
            return 10

    try:
        asyncio.run(enforce_call_limit(DB(), tenant))
    except Exception as exc:
        assert getattr(exc, 'status_code', None) == 402
        assert 'Monthly voice-minute limit' in str(getattr(exc, 'detail', ''))
    else:
        raise AssertionError('Expected monthly voice-minute limit to block the call')
