from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignContactAdd

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
