from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import tenant_id
from app.db.session import get_db
from app.models import Contact
from app.schemas.contact import ContactCreate, ContactOut, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])


def out(contact: Contact) -> ContactOut:
    return ContactOut.model_validate(contact)


@router.get("", response_model=list[ContactOut])
async def list_contacts(
    q: str | None = Query(default=None, max_length=100),
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant: str = Depends(tenant_id),
    db: AsyncSession = Depends(get_db),
):
    tid = UUID(tenant)
    stmt = select(Contact).where(Contact.tenant_id == tid).order_by(Contact.created_at.desc()).offset(offset).limit(limit)
    if status_filter:
        stmt = stmt.where(Contact.status == status_filter.upper())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Contact.first_name.ilike(like), Contact.last_name.ilike(like), Contact.phone.ilike(like), Contact.email.ilike(like)))
    return [out(c) for c in (await db.scalars(stmt)).all()]


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    tenant: str = Depends(tenant_id),
    db: AsyncSession = Depends(get_db),
):
    tid = UUID(tenant)
    if not data.phone and not data.email:
        raise HTTPException(400, "A phone number or email address is required")
    contact = Contact(tenant_id=tid, **data.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return out(contact)


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(contact_id: UUID, tenant: str = Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    contact = await db.scalar(select(Contact).where(Contact.id == contact_id, Contact.tenant_id == UUID(tenant)))
    if not contact:
        raise HTTPException(404, "Contact not found")
    return out(contact)


@router.patch("/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: UUID,
    data: ContactUpdate,
    tenant: str = Depends(tenant_id),
    db: AsyncSession = Depends(get_db),
):
    contact = await db.scalar(select(Contact).where(Contact.id == contact_id, Contact.tenant_id == UUID(tenant)))
    if not contact:
        raise HTTPException(404, "Contact not found")
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(contact, key, value)
    if not contact.phone and not contact.email:
        raise HTTPException(400, "A phone number or email address is required")
    await db.commit()
    await db.refresh(contact)
    return out(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: UUID, tenant: str = Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    contact = await db.scalar(select(Contact).where(Contact.id == contact_id, Contact.tenant_id == UUID(tenant)))
    if not contact:
        raise HTTPException(404, "Contact not found")
    contact.status = "DELETED"
    await db.commit()
