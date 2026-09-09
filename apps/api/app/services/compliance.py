from sqlalchemy import select
from app.models import ContactConsent,Contact,CompliancePolicy
async def check_outbound(db,tenant_id,contact_id):
    c=await db.scalar(select(Contact).where(Contact.id==contact_id,Contact.tenant_id==tenant_id))
    if not c or not c.phone:return 'BLOCKED','CONTACT_NOT_CALLABLE'
    if c.status in {'DO_NOT_CONTACT','OPTED_OUT'}:return 'BLOCKED','DNC'
    consent=await db.scalar(select(ContactConsent).where(ContactConsent.contact_id==contact_id,ContactConsent.tenant_id==tenant_id,ContactConsent.channel=='VOICE').order_by(ContactConsent.created_at.desc()))
    policy=await db.scalar(select(CompliancePolicy).where(CompliancePolicy.tenant_id==tenant_id));p=policy.policy if policy else {}
    if consent and consent.status in {'OPTED_OUT','DO_NOT_CONTACT','RESTRICTED'}:return 'BLOCKED','CONSENT'
    if p.get('require_voice_consent') and (not consent or consent.status!='OPTED_IN'):return 'REQUIRES_REVIEW','CONSENT_REQUIRED'
    return 'ALLOWED','OK'
