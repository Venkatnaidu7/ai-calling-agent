from unittest.mock import AsyncMock, patch

import pytest

from app.providers.openai_realtime import RealtimeBridge


@pytest.mark.asyncio
async def test_realtime_requires_key():
    with patch('app.providers.openai_realtime.get_settings') as settings:
        settings.return_value.openai_api_key = None
        with pytest.raises(RuntimeError, match='OPENAI_API_KEY'):
            await RealtimeBridge('hello').connect()


@pytest.mark.asyncio
async def test_realtime_connect_calls_provider():
    ws = AsyncMock()
    with patch('app.providers.openai_realtime.websockets.connect', new=AsyncMock(return_value=ws)):
        with patch('app.providers.openai_realtime.get_settings') as settings:
            settings.return_value.openai_api_key = 'key'
            settings.return_value.openai_realtime_url = 'wss://example.test/realtime'
            settings.return_value.openai_realtime_model = 'gpt-realtime-2.1'
            await RealtimeBridge('hello').connect()
    assert ws.send.await_count == 1
