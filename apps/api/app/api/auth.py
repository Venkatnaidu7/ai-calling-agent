from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Tenant,User,TenantSetting,BusinessHours,CompliancePolicy
from app.schemas.auth import *
from app.core.security import *
router=APIRouter(prefix='/auth',tags=['auth'])
@router.post('/register',response_model=TokenOut)
async def register(data:RegisterIn,db:AsyncSession=Depends(get_db)):
    if await db.scalar(select(User).where(User.email==data.email)): raise HTTPException(409,'Email already registered')
    t=Tenant(name=data.business_name); db.add(t); await db.flush()
    db.add(TenantSetting(tenant_id=t.id,settings={})); db.add(BusinessHours(tenant_id=t.id)); db.add(CompliancePolicy(tenant_id=t.id,policy={'ai_disclosure':'ALWAYS','recording':'DISABLED'}))
    u=User(tenant_id=t.id,email=data.email,password_hash=hash_password(data.password),email_verified=False); db.add(u); await db.commit()
    return TokenOut(access_token=create_token(u.id,t.id,u.role))
@router.post('/login',response_model=TokenOut)
async def login(data:LoginIn,db:AsyncSession=Depends(get_db)):
    u=await db.scalar(select(User).where(User.email==data.email))
    if not u or not u.active or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Invalid credentials')
    return TokenOut(access_token=create_token(u.id,u.tenant_id,u.role))
