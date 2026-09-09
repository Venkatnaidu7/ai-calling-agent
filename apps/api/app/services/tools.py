import json
from sqlalchemy import select
from app.models import ToolDefinition,ToolPermission,Contact,Lead,Appointment,TransferDestination
from app.services.audit import audit
class ToolExecutor:
    async def execute(self,db,tenant_id,agent_version_id,call_id,name,args,user_id=None):
        tool=await db.scalar(select(ToolDefinition).where(ToolDefinition.tenant_id==tenant_id,ToolDefinition.name==name,ToolDefinition.enabled==True))
        if not tool:return {'success':False,'error_code':'TOOL_NOT_AUTHORIZED'}
        perm=await db.scalar(select(ToolPermission).where(ToolPermission.tenant_id==tenant_id,ToolPermission.agent_version_id==agent_version_id,ToolPermission.tool_id==tool.id,ToolPermission.enabled==True))
        if not perm:return {'success':False,'error_code':'TOOL_NOT_AUTHORIZED'}
        try:
            if name=='create_lead':
                x=Lead(tenant_id=tenant_id,contact_id=args.get('contact_id'),source=args.get('source','voice'),stage=args.get('stage','NEW'),notes=args.get('notes'));db.add(x);await db.flush();result={'success':True,'lead_id':str(x.id)}
            elif name=='get_customer':
                x=await db.scalar(select(Contact).where(Contact.tenant_id==tenant_id,Contact.id==args.get('contact_id')));result={'success':bool(x),'customer':({'id':str(x.id),'phone':x.phone,'email':x.email} if x else None)}
            elif name=='create_appointment':
                x=Appointment(tenant_id=tenant_id,contact_id=args.get('contact_id'),start_at=args['start_at'],end_at=args['end_at'],timezone=args.get('timezone','Asia/Kolkata'),notes=args.get('notes'));db.add(x);await db.flush();result={'success':True,'appointment_id':str(x.id)}
            elif name=='transfer_call':
                x=await db.scalar(select(TransferDestination).where(TransferDestination.tenant_id==tenant_id,TransferDestination.id==args.get('destination_id')));result={'success':bool(x),'phone':x.phone if x else None}
            elif name=='end_call':result={'success':True,'action':'end_call'}
            else:result={'success':False,'error_code':'UNSUPPORTED_TOOL'}
        except Exception:result={'success':False,'error_code':'TOOL_EXECUTION_FAILED'}
        await audit(db,tenant_id,'tool.executed',user_id,'call',call_id,{'tool':name,'success':result.get('success')});await db.commit();return result
