from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_claims, tenant_id, require_roles
from app.db.session import get_db
from app.models import ApiKey, AuditLog, CompliancePolicy

router = APIRouter(prefix='/security', tags=['security'])

DEFAULT_POLICY = {
    'ai_disclosure': 'ALWAYS',
    'recording': 'DISABLED',
    'retention_days': 30,
    'do_not_call_enforcement': True,
    'consent_required': True,
}

@router.get('/status')
async def security_status(t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    keys = (await db.scalars(select(ApiKey).where(ApiKey.tenant_id == t))).all()
    logs = (await db.scalars(select(AuditLog).where(AuditLog.tenant_id == t).order_by(AuditLog.created_at.desc()).limit(20))).all()
    policy = await db.scalar(select(CompliancePolicy).where(CompliancePolicy.tenant_id == t))
    return {
        'tenant_id': str(t),
        'api_keys': len(keys),
        'recent_audit_events': len(logs),
        'compliance_policy_configured': policy is not None,
        'security_controls': {
            'tenant_isolation': True,
            'bearer_authentication': True,
            'role_authorization': True,
            'audit_logging': True,
            'provider_webhook_validation': True,
            'stripe_webhook_signature_validation': True,
            'security_headers': True,
            'trusted_hosts': True,
            'request_size_limit': True,
        },
    }

@router.get('/compliance')
async def get_compliance(t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    row = await db.scalar(select(CompliancePolicy).where(CompliancePolicy.tenant_id == t))
    return {'policy': {**DEFAULT_POLICY, **(row.policy or {})} if row else DEFAULT_POLICY}

@router.put('/compliance')
async def update_compliance(data: dict, claims=Depends(require_roles('TENANT_OWNER', 'ADMIN')), db: AsyncSession = Depends(get_db)):
    allowed = set(DEFAULT_POLICY)
    unknown = set(data) - allowed
    if unknown:
        raise HTTPException(400, f'Unsupported compliance fields: {", ".join(sorted(unknown))}')
    if 'ai_disclosure' in data and data['ai_disclosure'] not in {'ALWAYS', 'ON_REQUEST', 'DISABLED'}:
        raise HTTPException(400, 'ai_disclosure must be ALWAYS, ON_REQUEST, or DISABLED')
    if 'recording' in data and data['recording'] not in {'DISABLED', 'ALWAYS', 'ON_CONSENT'}:
        raise HTTPException(400, 'recording must be DISABLED, ALWAYS, or ON_CONSENT')
    if 'retention_days' in data and (not isinstance(data['retention_days'], int) or not 1 <= data['retention_days'] <= 3650):
        raise HTTPException(400, 'retention_days must be an integer between 1 and 3650')
    for field in ('do_not_call_enforcement', 'consent_required'):
        if field in data and not isinstance(data[field], bool):
            raise HTTPException(400, f'{field} must be boolean')

    tid = claims['tenant_id']
    row = await db.scalar(select(CompliancePolicy).where(CompliancePolicy.tenant_id == tid))
    if not row:
        row = CompliancePolicy(tenant_id=tid, policy={})
        db.add(row)
    row.policy = {**DEFAULT_POLICY, **(row.policy or {}), **data}
    await db.commit()
    return {'policy': row.policy}

@router.get('/audit')
async def audit(limit: int = 50, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    limit = max(1, min(limit, 200))
    rows = (await db.scalars(select(AuditLog).where(AuditLog.tenant_id == t).order_by(AuditLog.created_at.desc()).limit(limit))).all()
    return [{'id': str(x.id), 'action': x.action, 'resource_type': x.resource_type, 'resource_id': str(x.resource_id) if x.resource_id else None, 'created_at': x.created_at.isoformat() if x.created_at else None} for x in rows]
