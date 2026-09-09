async def audit(db,tenant_id,action,user_id=None,resource_type=None,resource_id=None,metadata=None):
    from app.models import AuditLog
    db.add(AuditLog(tenant_id=tenant_id,user_id=user_id,action=action,resource_type=resource_type,resource_id=str(resource_id) if resource_id else None,metadata_=metadata or {}))
