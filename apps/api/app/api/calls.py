from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import tenant_id
from app.models import Call,Contact,PhoneNumber,Agent
from app.services.compliance import check_outbound
from app.core.config import get_settings
from twilio.rest import Client
router=APIRouter(prefix='/calls',tags=['calls'])
@router.get('')
async def list_calls(t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):return (await db.scalars(select(Call).where(Call.tenant_id==UUID(t)).order_by(Call.created_at.desc()).limit(100))).all()
@router.get('/{call_id}')
async def get_call(call_id:UUID,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    x=await db.scalar(select(Call).where(Call.id==call_id,Call.tenant_id==UUID(t)))
    if not x:raise HTTPException(404,'Call not found')
    return x
@router.post('/outbound')
async def outbound(contact_id:UUID,phone_number_id:UUID,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    s=get_settings()
    if not s.outbound_enabled:raise HTTPException(403,'Outbound calling is disabled')
    c=await db.scalar(select(Contact).where(Contact.id==contact_id,Contact.tenant_id==UUID(t)));pn=await db.scalar(select(PhoneNumber).where(PhoneNumber.id==phone_number_id,PhoneNumber.tenant_id==UUID(t)))
    if not c or not pn:raise HTTPException(404,'Contact or phone number not found')
    gate,reason=await check_outbound(db,UUID(t),contact_id)
    if gate!='ALLOWED':raise HTTPException(403,reason)
    if not s.twilio_account_sid or not s.twilio_auth_token:raise HTTPException(503,'Twilio is not configured')
    call=Call(tenant_id=UUID(t),phone_number_id=pn.id,contact_id=c.id,direction='OUTBOUND',from_number=pn.e164,to_number=c.phone,status='QUEUED');db.add(call);await db.flush()
    client=Client(s.twilio_account_sid,s.twilio_auth_token);tw=client.calls.create(to=c.phone,from_=pn.e164,url=f'{s.public_base_url}/api/v1/voice/twilio/inbound');call.provider_call_id=tw.sid;call.status='RINGING';await db.commit();return {'call_id':str(call.id),'provider_call_id':tw.sid}
