from fastapi import HTTPException
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse
from app.core.config import get_settings
def validate_twilio(request,params):
    token=get_settings().twilio_auth_token
    if not token:return
    sig=request.headers.get('X-Twilio-Signature')
    if not sig or not RequestValidator(token).validate(str(request.url),params,sig):raise HTTPException(403,'Invalid Twilio signature')
def validate_twilio_ws(websocket,params=None):
    token=get_settings().twilio_auth_token
    if not token:return
    sig=websocket.headers.get('x-twilio-signature')
    if not sig or not RequestValidator(token).validate(str(websocket.url),params or {},sig):raise HTTPException(403,'Invalid Twilio WebSocket signature')
def connect_stream_xml(ws_url,custom=None):
    r=VoiceResponse(); c=r.connect(); st=c.stream(url=ws_url)
    for k,v in (custom or {}).items():st.parameter(name=k,value=str(v))
    return str(r)
