from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import tenant_id
from app.db.session import get_db
from app.models import Contact, ContactConsent
from app.schemas.contact import ConsentCreate, ConsentOut

router = APIRouter(prefix="/contacts", tags=["contact-consent"])

async def get_contact(contact_id: UUID, tenant: str, db: AsyncSession) -> Contact:
    contact = await db.scalar(select(Contact).where(Contact.id == contact_id, Contact.tenant_id == UUID(tenant)))
    if not contact:
        raise HTTPException(404, "Contact not found")
    return contact

@router.get("/{contact_id}/consents", response_model=list[ConsentOut])
async def list_consents(contact_id: UUID, tenant: str = Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    await get_contact(contact_id, tenant, db)
    rows = await db.scalars(select(ContactConsent).where(ContactConsent.contact_id == contact_id, ContactConsent.tenant_id == UUID(tenant)).order_by(ContactConsent.created_at.desc()))
    return rows.all()

@router.post("/{contact_id}/consents", response_model=ConsentOut, status_code=201)
async def create_consent(contact_id: UUID, data: ConsentCreate, tenant: str = Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    await get_contact(contact_id, tenant, db)
    consent = ContactConsent(tenant_id=UUID(tenant), contact_id=contact_id, channel=data.channel.lower(), type=data.type.upper(), source=data.source, status=data.status.upper())
    db.add(consent)
    await db.commit()
    await db.refresh(consent)
    return consent

@router.post("/{contact_id}/consents/{consent_id}/revoke", response_model=ConsentOut)
async def revoke_consent(contact_id: UUID, consent_id: UUID, tenant: str = Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    await get_contact(contact_id, tenant, db)
    consent = await db.scalar(select(ContactConsent).where(ContactConsent.id == consent_id, ContactConsent.contact_id == contact_id, ContactConsent.tenant_id == UUID(tenant)))
    if not consent:
        raise HTTPException(404, "Consent not found")
    consent.status = "REVOKED"
    consent.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(consent)
    return consent
