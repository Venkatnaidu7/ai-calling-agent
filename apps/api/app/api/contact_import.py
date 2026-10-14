import csv, io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import tenant_id
from app.db.session import get_db
from app.models import Contact

router = APIRouter(prefix="/contacts", tags=["contacts-import"])

@router.post("/import")
async def import_contacts(file: UploadFile = File(...), tenant: str = Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "CSV file exceeds 10 MB limit")
    try:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must be UTF-8 encoded")
    tid = __import__('uuid').UUID(tenant); created = 0; skipped = 0
    existing = {x for x in (await db.scalars(select(Contact.phone).where(Contact.tenant_id == tid, Contact.phone.is_not(None)))).all()}
    for row in rows:
        phone = (row.get("phone") or "").strip() or None; email = (row.get("email") or "").strip().lower() or None
        if not phone and not email: skipped += 1; continue
        if phone and phone in existing: skipped += 1; continue
        contact = Contact(tenant_id=tid, first_name=(row.get("first_name") or "").strip() or None, last_name=(row.get("last_name") or "").strip() or None, phone=phone, email=email, tags=[x.strip() for x in (row.get("tags") or "").split(",") if x.strip()], custom_fields={}, status=(row.get("status") or "ACTIVE").strip().upper())
        db.add(contact); created += 1
        if phone: existing.add(phone)
    await db.commit()
    return {"created": created, "skipped": skipped, "total_rows": len(rows)}

@router.get("/export")
async def export_contacts(tenant: str = Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Contact).where(Contact.tenant_id == __import__('uuid').UUID(tenant)).order_by(Contact.created_at.desc()))).all()
    buf = io.StringIO(); writer = csv.writer(buf); writer.writerow(["id","first_name","last_name","phone","email","tags","status"])
    for c in rows: writer.writerow([c.id,c.first_name or "",c.last_name or "",c.phone or "",c.email or "",";".join(c.tags or []),c.status])
    return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=contacts.csv"})
