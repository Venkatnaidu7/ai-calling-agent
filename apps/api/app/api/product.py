from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import tenant_id,current_claims
from app.models import PhoneNumber,Contact,ContactConsent,KnowledgeSource,KnowledgeDocument,Appointment,Campaign,HumanAgent,ToolDefinition,ToolPermission,ApiKey
from app.schemas.product import *
from app.core.security import new_api_key,hash_secret
from app.services.audit import audit
router=APIRouter(tags=['product'])
def tid(x):return UUID(x)
@router.get('/phone-numbers')
async def phones(t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):return (await db.scalars(select(PhoneNumber).where(PhoneNumber.tenant_id==tid(t)))).all()
@router.post('/phone-numbers')
async def add_phone(d:PhoneCreate,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    x=PhoneNumber(tenant_id=tid(t),e164=d.e164,agent_id=UUID(d.agent_id) if d.agent_id else None,country=d.country,capabilities=d.capabilities);db.add(x);await db.commit();await db.refresh(x);return x
@router.get('/contacts')
async def contacts(t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):return (await db.scalars(select(Contact).where(Contact.tenant_id==tid(t)).order_by(Contact.created_at.desc()))).all()
@router.post('/contacts')
async def add_contact(d:ContactCreate,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):x=Contact(tenant_id=tid(t),**d.model_dump());db.add(x);await db.commit();await db.refresh(x);return x
@router.post('/contacts/{contact_id}/consent')
async def consent(contact_id:UUID,status:str,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    c=ContactConsent(tenant_id=tid(t),contact_id=contact_id,channel='VOICE',type='CALLING',status=status);db.add(c);await db.commit();return {'status':status}
@router.post('/knowledge')
async def knowledge(d:KnowledgeCreate,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    s=KnowledgeSource(tenant_id=tid(t),name=d.name,source_type=d.source_type);db.add(s);await db.flush();doc=KnowledgeDocument(tenant_id=tid(t),source_id=s.id,title=d.title,content=d.content);db.add(doc);await db.commit();return {'document_id':str(doc.id)}
@router.get('/knowledge/search')
async def knowledge_search(q:str,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    docs=(await db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.tenant_id==tid(t),KnowledgeDocument.content.ilike(f'%{q}%')).limit(20))).all();return [{'id':str(x.id),'title':x.title,'content':x.content} for x in docs]
@router.post('/appointments')
async def appointment(d:AppointmentCreate,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    overlap=await db.scalar(select(Appointment.id).where(Appointment.tenant_id==tid(t),Appointment.status=='BOOKED',Appointment.start_at<d.end_at,Appointment.end_at>d.start_at).limit(1))
    if overlap:raise HTTPException(409,'Appointment time is unavailable')
    x=Appointment(tenant_id=tid(t),**d.model_dump());db.add(x);await db.commit();await db.refresh(x);return x
@router.get('/appointments')
async def appointments(t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):return (await db.scalars(select(Appointment).where(Appointment.tenant_id==tid(t)).order_by(Appointment.start_at))).all()
@router.post('/campaigns')
async def campaign(d:CampaignCreate,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):x=Campaign(tenant_id=tid(t),**d.model_dump());db.add(x);await db.commit();await db.refresh(x);return x
@router.get('/campaigns')
async def campaigns(t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):return (await db.scalars(select(Campaign).where(Campaign.tenant_id==tid(t)))).all()
@router.post('/human-agents')
async def human(d:HumanAgentCreate,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):x=HumanAgent(tenant_id=tid(t),**d.model_dump());db.add(x);await db.commit();return x
@router.post('/tools')
async def tool(d:ToolCreate,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):x=ToolDefinition(tenant_id=tid(t),**d.model_dump());db.add(x);await db.commit();await db.refresh(x);return x
@router.post('/api-keys')
async def api_key(d:ApiKeyCreate,t=Depends(tenant_id),db:AsyncSession=Depends(get_db)):
    raw=new_api_key();x=ApiKey(tenant_id=tid(t),name=d.name,secret_hash=hash_secret(raw),scopes=d.scopes,expires_at=d.expires_at);db.add(x);await db.commit();return {'id':str(x.id),'api_key':raw}
