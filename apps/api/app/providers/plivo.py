import base64
import hashlib
import hmac
import html

from fastapi import HTTPException
from plivo import RestClient
from plivo.utils import validate_v3_signature

from app.core.config import get_settings


def client() -> RestClient:
    s = get_settings()
    if not s.plivo_auth_id or not s.plivo_auth_token:
        raise HTTPException(503, 'Plivo is not configured')
    return RestClient(s.plivo_auth_id, s.plivo_auth_token)


def public_url(path: str) -> str:
    base = get_settings().public_base_url.rstrip('/')
    if not base.startswith('https://'):
        raise HTTPException(503, 'public_base_url must use HTTPS for Plivo webhooks')
    return f'{base}{path}'


def stream_url(call_id) -> str:
    base = get_settings().public_base_url.rstrip('/')
    if not base.startswith('https://'):
        raise HTTPException(503, 'public_base_url must use HTTPS for Plivo audio streaming')
    token = hmac.new(get_settings().secret_key.encode(), str(call_id).encode(), hashlib.sha256).hexdigest()
    return base.replace('https://', 'wss://', 1) + f'/api/v1/voice/plivo/stream/{call_id}?token={token}'


def valid_stream_token(call_id, token: str | None) -> bool:
    expected = hmac.new(get_settings().secret_key.encode(), str(call_id).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token or '')


def stream_xml(call_id) -> str:
    ws = html.escape(stream_url(call_id), quote=True)
    status = html.escape(public_url('/api/v1/voice/plivo/stream-status'), quote=True)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        f'<Stream bidirectional="true" keepCallAlive="true" '
        f'contentType="audio/x-mulaw;rate=8000" '
        f'statusCallbackUrl="{status}" statusCallbackMethod="POST">{ws}</Stream>'
        '</Response>'
    )


def validate_webhook(request, params: dict):
    s = get_settings()
    token = s.plivo_auth_token
    if not token:
        if s.app_env.lower() == 'production':
            raise HTTPException(503, 'Plivo authentication is not configured')
        return
    signature = request.headers.get('X-Plivo-Signature-V3')
    nonce = request.headers.get('X-Plivo-Signature-V3-Nonce')
    if not signature or not nonce:
        raise HTTPException(403, 'Invalid Plivo signature')
    if not validate_v3_signature(request.method, str(request.url), nonce, token, signature, params if request.method.upper() == 'POST' else None):
        raise HTTPException(403, 'Invalid Plivo signature')


def validate_websocket(websocket):
    s = get_settings()
    token = s.plivo_auth_token
    if not token:
        if s.app_env.lower() == 'production':
            raise HTTPException(503, 'Plivo authentication is not configured')
        return
    signature = websocket.headers.get('x-plivo-signature-v3')
    nonce = websocket.headers.get('x-plivo-signature-v3-nonce')
    if not signature or not nonce:
        raise HTTPException(403, 'Invalid Plivo websocket signature')
    if not validate_v3_signature('GET', str(websocket.url), nonce, token, signature):
        raise HTTPException(403, 'Invalid Plivo websocket signature')


def audio_message(payload: str) -> str:
    return __import__('json').dumps({
        'event': 'playAudio',
        'media': {'contentType': 'audio/x-mulaw', 'sampleRate': 8000, 'payload': payload},
    })


def clear_audio(stream_id: str) -> str:
    return __import__('json').dumps({'event': 'clearAudio', 'streamId': stream_id})
