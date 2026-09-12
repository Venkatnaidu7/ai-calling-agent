import json
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.providers import plivo


def test_stream_url_requires_public_https():
    with patch("app.providers.plivo.get_settings") as settings:
        settings.return_value.public_base_url = "http://localhost:8000"
        settings.return_value.secret_key = "secret"
        with pytest.raises(HTTPException) as exc:
            plivo.stream_url("call-1")
        assert exc.value.status_code == 503


def test_stream_xml_is_bidirectional_mulaw_stream():
    with patch("app.providers.plivo.get_settings") as settings:
        settings.return_value.public_base_url = "https://voice.example.com"
        settings.return_value.secret_key = "secret"
        xml = plivo.stream_xml("call-1")
    assert "<Response>" in xml
    assert 'bidirectional="true"' in xml
    assert 'keepCallAlive="true"' in xml
    assert "audio/x-mulaw;rate=8000" in xml
    assert "wss://voice.example.com/api/v1/voice/plivo/stream/call-1?token=" in xml
    assert "/api/v1/voice/plivo/stream-status" in xml


def test_audio_message_matches_plivo_protocol():
    message = json.loads(plivo.audio_message("AQID"))
    assert message == {
        "event": "playAudio",
        "media": {
            "contentType": "audio/x-mulaw",
            "sampleRate": 8000,
            "payload": "AQID",
        },
    }


def test_clear_audio_matches_plivo_protocol():
    assert json.loads(plivo.clear_audio("stream-1")) == {
        "event": "clearAudio",
        "streamId": "stream-1",
    }


def test_stream_token_is_bound_to_call():
    with patch("app.providers.plivo.get_settings") as settings:
        settings.return_value.secret_key = "secret"
        token = plivo.stream_url.__globals__["hmac"].new(
            b"secret", b"call-1", plivo.stream_url.__globals__["hashlib"].sha256
        ).hexdigest()
        assert plivo.valid_stream_token("call-1", token)
        assert not plivo.valid_stream_token("call-2", token)


def test_missing_plivo_auth_fails_closed_in_production():
    with patch("app.providers.plivo.get_settings") as settings:
        settings.return_value.plivo_auth_token = None
        settings.return_value.app_env = "production"
        request = type(
            "Request",
            (),
            {"headers": {}, "method": "POST", "url": "https://voice.example.com"},
        )()
        with pytest.raises(HTTPException) as exc:
            plivo.validate_webhook(request, {})
        assert exc.value.status_code == 503


def test_ensure_voice_application_reuses_existing_application():
    api = Mock()
    api.applications.list.return_value = {
        "objects": [
            {
                "app_name": plivo.VOICE_APP_NAME,
                "app_id": "app-123",
                "enabled": True,
                "answer_url": "https://voice.example.com/api/v1/voice/plivo/inbound",
                "hangup_url": "https://voice.example.com/api/v1/voice/plivo/status",
            }
        ]
    }
    with patch("app.providers.plivo.client", return_value=api), patch(
        "app.providers.plivo.public_url",
        side_effect=lambda path: f"https://voice.example.com{path}",
    ):
        assert plivo.ensure_voice_application() == "app-123"
    api.applications.create.assert_not_called()


def test_ensure_voice_application_creates_when_missing():
    api = Mock()
    api.applications.list.return_value = {"objects": []}
    api.applications.create.return_value = {"app_id": "app-new"}
    with patch("app.providers.plivo.client", return_value=api), patch(
        "app.providers.plivo.public_url",
        side_effect=lambda path: f"https://voice.example.com{path}",
    ):
        assert plivo.ensure_voice_application() == "app-new"
    api.applications.create.assert_called_once()


def test_attach_number_normalizes_e164():
    api = Mock()
    with patch("app.providers.plivo.client", return_value=api):
        plivo.attach_number("+14155551234", "app-123")
    api.numbers.update.assert_called_once_with(number="14155551234", app_id="app-123")
