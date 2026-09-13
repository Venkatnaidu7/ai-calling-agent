import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
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
from app.api.intelligence import router as intelligence_router
from app.api.handoff import router as handoff_router
from app.api.security import router as security_router

@asynccontextmanager
async def lifespan(app):
    yield
    await engine.dispose()

s = get_settings()
app = FastAPI(title='AI Voice Employee Platform', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in s.cors_origins.split(',') if x.strip()], allow_credentials=True, allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'], allow_headers=['Authorization','Content-Type','Accept','X-Request-ID','Stripe-Signature'])
trusted_hosts = [x.strip() for x in s.trusted_hosts.split(',') if x.strip()]
if trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

@app.middleware('http')
async def request_security(request: Request, call_next):
    rid = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    request.state.request_id = rid
    start = time.perf_counter()
    content_length = request.headers.get('content-length')
    if content_length:
        try:
            if int(content_length) > s.request_max_bytes and request.url.path not in {'/api/v1/voice/twilio/stream','/api/v1/voice/plivo/stream'}:
                return JSONResponse(status_code=413, content={'error': {'code':'PAYLOAD_TOO_LARGE','message':'Request payload exceeds the configured limit.','request_id':rid}}, headers={'X-Request-ID':rid})
        except ValueError:
            return JSONResponse(status_code=400, content={'error': {'code':'INVALID_CONTENT_LENGTH','message':'Invalid Content-Length header.','request_id':rid}}, headers={'X-Request-ID':rid})
    try:
        response = await call_next(request)
        response.headers['X-Request-ID'] = rid
        response.headers['X-Response-Time-ms'] = f'{(time.perf_counter()-start)*1000:.1f}'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if s.app_env.lower() in {'production','prod'}:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    except Exception:
        return JSONResponse(status_code=500, content={'error': {'code':'INTERNAL_ERROR','message':'Internal server error.','request_id':rid}}, headers={'X-Request-ID':rid})

for r in [auth_router,agents_router,phone_numbers_router,contacts_router,contact_consent_router,contact_import_router,voice_router,product_router,calls_router,analytics_router,billing_router,campaigns_router,intelligence_router,handoff_router,security_router]:
    app.include_router(r, prefix='/api/v1')

@app.get('/health')
async def health(): return {'status':'ok','service':s.app_name}
@app.get('/liveness')
async def liveness(): return {'status':'alive'}
async def _readiness_check():
    async with engine.connect() as c: await c.execute(text('SELECT 1'))
    return {'status':'ready'}
@app.get('/readiness')
async def readiness(): return await _readiness_check()
@app.get('/ready')
async def ready(): return await _readiness_check()
