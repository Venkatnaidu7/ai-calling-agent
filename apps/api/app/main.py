import uuid,time
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.db.session import engine
from app.core.config import get_settings
from app.api.auth import router as auth_router
from app.api.agents import router as agents_router
from app.api.phone_numbers import router as phone_numbers_router
from app.api.contacts import router as contacts_router
from app.api.contact_consent import router as contact_consent_router
from app.api.contact_import import router as contact_import_router
from app.api.voice import router as voice_router
from app.api.product import router as product_router
from app.api.calls import router as calls_router
from app.api.analytics import router as analytics_router
from app.api.billing import router as billing_router
from app.api.campaigns import router as campaigns_router
@asynccontextmanager
async def lifespan(app): yield; await engine.dispose()
s=get_settings(); app=FastAPI(title='AI Voice Employee Platform',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in s.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.middleware('http')
async def request_context(request:Request,call_next):
    rid=request.headers.get('X-Request-ID',str(uuid.uuid4())); request.state.request_id=rid; start=time.perf_counter()
    try:
        response=await call_next(request); response.headers['X-Request-ID']=rid; response.headers['X-Response-Time-ms']=f'{(time.perf_counter()-start)*1000:.1f}'; return response
    except Exception:
        return JSONResponse(status_code=500,content={'error':{'code':'INTERNAL_ERROR','message':'Internal server error.','request_id':rid}},headers={'X-Request-ID':rid})
for r in [auth_router,agents_router,phone_numbers_router,contacts_router,contact_consent_router,contact_import_router,voice_router,product_router,calls_router,analytics_router,billing_router,campaigns_router]: app.include_router(r,prefix='/api/v1')
@app.get('/health')
async def health(): return {'status':'ok','service':s.app_name}
@app.get('/liveness')
async def liveness(): return {'status':'alive'}
@app.get('/readiness')
async def readiness():
    async with engine.connect() as c: await c.execute(text('SELECT 1'))
    return {'status':'ready'}
