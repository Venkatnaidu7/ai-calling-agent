import json
from unittest.mock import AsyncMock, patch

import pytest

from app.providers.openai_realtime import RealtimeBridge


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send(self, value):
        self.sent.append(json.loads(value))


@pytest.mark.asyncio
async def test_bridge_configures_pcmu_and_vad():
    fake = FakeWebSocket()
    with patch('app.providers.openai_realtime.websockets.connect', new=AsyncMock(return_value=fake)):
        with patch('app.providers.openai_realtime.get_settings') as settings:
            settings.return_value.openai_api_key = 'test-key'
            settings.return_value.openai_realtime_url = 'wss://api.openai.com/v1/realtime'
            settings.return_value.openai_realtime_model = 'gpt-realtime-2.1'
            bridge = RealtimeBridge('Be concise', 'marin', 'en')
            await bridge.connect()

    session = fake.sent[0]['session']
    assert session['output_modalities'] == ['audio']
    assert session['audio']['input']['format']['type'] == 'audio/pcmu'
    assert session['audio']['output']['format']['type'] == 'audio/pcmu'
    assert session['audio']['input']['turn_detection']['type'] == 'server_vad'


@pytest.mark.asyncio
async def test_bridge_sends_audio_and_tool_output():
    fake = FakeWebSocket()
    bridge = RealtimeBridge('Hello')
    bridge.ws = fake
    await bridge.send_audio('abc123')
    await bridge.tool_result('call-1', {'ok': True})
    assert fake.sent[0] == {'type': 'input_audio_buffer.append', 'audio': 'abc123'}
    assert fake.sent[1]['item']['call_id'] == 'call-1'
    assert json.loads(fake.sent[1]['item']['output']) == {'ok': True}
    assert fake.sent[2]['type'] == 'response.create'
