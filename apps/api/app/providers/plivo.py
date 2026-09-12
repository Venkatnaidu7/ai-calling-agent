import hashlib
import hmac
import html
import json

from fastapi import HTTPException
from plivo import RestClient
from plivo.utils import validate_v3_signature

from app.core.config import get_settings


VOICE_APP_NAME = "VoiceOS-Plivo-Voice"


def client() -> RestClient:
    s = get_settings()
    if not s.plivo_auth_id or not s.plivo_auth_token:
        raise HTTPException(503, "Plivo is not configured")
    return RestClient(s.plivo_auth_id, s.plivo_auth_token)


def public_url(path: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(503, "public_base_url must use HTTPS for Plivo webhooks")
    return f"{base}{path}"


def stream_url(call_id) -> str:
    base = get_settings().public_base_url.rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(503, "public_base_url must use HTTPS for Plivo audio streaming")
    token = hmac.new(
        get_settings().secret_key.encode(), str(call_id).encode(), hashlib.sha256
    ).hexdigest()
    return base.replace("https://", "wss://", 1) + (
        f"/api/v1/voice/plivo/stream/{call_id}?token={token}"
    )


def valid_stream_token(call_id, token: str | None) -> bool:
    expected = hmac.new(
        get_settings().secret_key.encode(), str(call_id).encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, token or "")


def stream_xml(call_id) -> str:
    ws = html.escape(stream_url(call_id), quote=True)
    status = html.escape(public_url("/api/v1/voice/plivo/stream-status"), quote=True)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        '<Stream bidirectional="true" keepCallAlive="true" '
        'contentType="audio/x-mulaw;rate=8000" '
        f'statusCallbackUrl="{status}" statusCallbackMethod="POST">{ws}</Stream>'
        "</Response>"
    )


def _value(response, name: str, default=None):
    if isinstance(response, dict):
        return response.get(name, default)
    return getattr(response, name, default)


def ensure_voice_application() -> str:
    """Return the shared VoiceOS Plivo application, creating it if necessary."""
    api = client()
    answer_url = public_url("/api/v1/voice/plivo/inbound")
    hangup_url = public_url("/api/v1/voice/plivo/status")
    try:
        response = api.applications.list(app_name=VOICE_APP_NAME, limit=20)
        objects = _value(response, "objects", []) or []
        for application in objects:
            if _value(application, "app_name") == VOICE_APP_NAME and _value(application, "enabled", True):
                app_id = _value(application, "app_id")
                if app_id:
                    current_answer = _value(application, "answer_url")
                    current_hangup = _value(application, "hangup_url")
                    if current_answer != answer_url or current_hangup != hangup_url:
                        api.applications.update(
                            app_id=app_id,
                            answer_url=answer_url,
                            answer_method="POST",
                            hangup_url=hangup_url,
                            hangup_method="POST",
                        )
                    return app_id
        created = api.applications.create(
            app_name=VOICE_APP_NAME,
            answer_url=answer_url,
            answer_method="POST",
            hangup_url=hangup_url,
            hangup_method="POST",
        )
        app_id = _value(created, "app_id")
        if not app_id:
            raise RuntimeError("Plivo did not return an application ID")
        return app_id
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Unable to configure Plivo Voice application: {exc}") from exc


def normalize_number(number: str) -> str:
    return number.strip().lstrip("+")


def attach_number(number: str, app_id: str) -> None:
    try:
        client().numbers.update(number=normalize_number(number), app_id=app_id)
    except Exception as exc:
        raise HTTPException(502, f"Unable to attach Plivo number to VoiceOS application: {exc}") from exc


def validate_webhook(request, params: dict):
    s = get_settings()
    token = s.plivo_auth_token
    if not token:
        if s.app_env.lower() == "production":
            raise HTTPException(503, "Plivo authentication is not configured")
        return
    signature = request.headers.get("X-Plivo-Signature-V3")
    nonce = request.headers.get("X-Plivo-Signature-V3-Nonce")
    if not signature or not nonce:
        raise HTTPException(403, "Invalid Plivo signature")
    if not validate_v3_signature(
        request.method,
        str(request.url),
        nonce,
        token,
        signature,
        params if request.method.upper() == "POST" else None,
    ):
        raise HTTPException(403, "Invalid Plivo signature")


def validate_websocket(websocket):
    s = get_settings()
    token = s.plivo_auth_token
    if not token:
        if s.app_env.lower() == "production":
            raise HTTPException(503, "Plivo authentication is not configured")
        return
    signature = websocket.headers.get("x-plivo-signature-v3")
    nonce = websocket.headers.get("x-plivo-signature-v3-nonce")
    if not signature or not nonce:
        raise HTTPException(403, "Invalid Plivo websocket signature")
    if not validate_v3_signature("GET", str(websocket.url), nonce, token, signature):
        raise HTTPException(403, "Invalid Plivo websocket signature")


def audio_message(payload: str) -> str:
    return json.dumps(
        {
            "event": "playAudio",
            "media": {
                "contentType": "audio/x-mulaw",
                "sampleRate": 8000,
                "payload": payload,
            },
        }
    )


def clear_audio(stream_id: str) -> str:
    return json.dumps({"event": "clearAudio", "streamId": stream_id})
