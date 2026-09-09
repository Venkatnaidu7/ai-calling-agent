import hmac,hashlib
from fastapi import APIRouter,Request,HTTPException
from app.core.config import get_settings
router=APIRouter(prefix='/billing',tags=['billing'])
@router.get('/plans')
async def plans():return [{'name':'Starter','minutes':100,'agents':3,'users':5}]
@router.post('/stripe/webhook')
async def stripe_webhook(request:Request):
    body=await request.body();secret=get_settings().stripe_webhook_secret
    if secret:
        sig=request.headers.get('Stripe-Signature','');expected=hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,sig.split('=')[-1]):raise HTTPException(400,'Invalid signature')
    return {'received':True}
