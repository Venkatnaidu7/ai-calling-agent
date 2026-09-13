from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_claims, tenant_id
from app.db.session import get_db
from app.models import ApiKey, AuditLog

router = APIRouter(prefix='/security', tags=['security'])

@router.get('/status')
async def security_status(t=Depends(tenant_id), db: AsyncSession=Depends(get_db)):
    tid=t
    keys=(await db.scalars(select(ApiKey).where(ApiKey.tenant_id==tid))).all()
    logs=(await db.scalars(select(AuditLog).where(AuditLog.tenant_id==tid).order_by(AuditLog.created_at.desc()).limit(20))).all()
    return {'tenant_id':str(tid),'api_keys':len(keys),'recent_audit_events':len(logs),'security_controls':{'tenant_isolation':True,'bearer_authentication':True,'role_authorization':True,'audit_logging':True,'provider_webhook_validation':True,'stripe_webhook_signature_validation':True}}

@router.get('/audit')
async def audit(limit:int=50,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    limit=max(1,min(limit,200))
    rows=(await db.scalars(select(AuditLog).where(AuditLog.tenant_id==t).order_by(AuditLog.created_at.desc()).limit(limit))).all()
    return [{'id':str(x.id),'action':x.action,'resource_type':x.resource_type,'resource_id':str(x.resource_id) if x.resource_id else None,'created_at':x.created_at.isoformat() if x.created_at else None} for x in rows]
