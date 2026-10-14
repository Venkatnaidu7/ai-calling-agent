from datetime import datetime, timezone

from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignContactAdd
from app.services.campaign_runner import scheduled_start


def test_campaign_schema_defaults():
    c=CampaignCreate(name='Outbound',phone_number_id='00000000-0000-0000-0000-000000000001')
    assert c.concurrency == 1
    assert c.retry_policy['max_attempts'] == 3


def test_campaign_update_validation():
    u=CampaignUpdate(concurrency=5)
    assert u.concurrency == 5


def test_campaign_contacts_require_ids():
    c=CampaignContactAdd(contact_ids=['00000000-0000-0000-0000-000000000001'])
    assert len(c.contact_ids) == 1


def test_campaign_schedule_start_parsing():
    dt = scheduled_start({'start_at': '2026-09-10T20:00:00+00:00'})
    assert dt == datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc)
    assert scheduled_start({}) is None
    assert scheduled_start({'start_at': 'not-a-date'}) is None
