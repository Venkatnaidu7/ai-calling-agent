from fastapi import HTTPException
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse
from app.core.config import get_settings


def _validate(request_url, params, signature):
    token = get_settings().twilio_auth_token
    if not token:
        if get_settings().app_env.lower() == 'production':
            raise HTTPException(503, 'Twilio authentication is not configured')
        return
    if not signature or not RequestValidator(token).validate(request_url, params, signature):
        raise HTTPException(403, 'Invalid Twilio signature')


def validate_twilio(request, params):
    _validate(str(request.url), params, request.headers.get('X-Twilio-Signature'))


def validate_twilio_ws(websocket, params=None):
    _validate(str(websocket.url), params or {}, websocket.headers.get('x-twilio-signature'))


def connect_stream_xml(ws_url, custom=None):
    r = VoiceResponse()
    c = r.connect()
    st = c.stream(url=ws_url)
    for k, v in (custom or {}).items():
        st.parameter(name=k, value=str(v))
    return str(r)
