import asyncio,sys
sys.path.insert(0,'apps/api')
from app.db.session import SessionLocal
from app.models import Tenant,User,Agent,AgentVersion,KnowledgeSource,KnowledgeDocument,Contact,Plan
from app.core.security import hash_password
async def main():
    password='CHANGE_ME_LOCAL_ONLY'
    async with SessionLocal() as db:
        t=Tenant(name='Demo Business');db.add(t);await db.flush()
        db.add(User(tenant_id=t.id,email='demo@example.com',password_hash=hash_password(password),email_verified=True))
        a=Agent(tenant_id=t.id,name='Demo AI Employee',description='Local development agent');db.add(a);await db.flush()
        v=AgentVersion(tenant_id=t.id,agent_id=a.id,version=1,status='PUBLISHED',system_instructions='You are a helpful AI employee. Never invent facts.');db.add(v);await db.flush();a.active_version_id=v.id
        s=KnowledgeSource(tenant_id=t.id,name='Demo FAQ',source_type='manual');db.add(s);await db.flush();db.add(KnowledgeDocument(tenant_id=t.id,source_id=s.id,title='Demo FAQ',content='Our business is open Monday to Saturday.'))
        db.add(Contact(tenant_id=t.id,first_name='Demo',last_name='Customer',phone='+15550000000'));db.add(Plan(name='Starter',limits={'minutes':100,'agents':3,'users':5}));await db.commit()
        print('Seed complete. Set the local demo password in scripts/seed.py before running.')
asyncio.run(main())
