from uuid import uuid4

from app.api.voice import STATUS_MAP, stream_token, valid_stream_token
from app.core.config import Settings


def test_stream_token_is_bound():
    cid = uuid4()
    token = stream_token(cid)
    assert valid_stream_token(cid, token)
    assert not valid_stream_token(uuid4(), token)


def test_twilio_status_mapping():
    assert STATUS_MAP['in-progress'] == 'IN_PROGRESS'
    assert STATUS_MAP['answered'] == 'IN_PROGRESS'
    assert STATUS_MAP['completed'] == 'COMPLETED'
    assert STATUS_MAP['no-answer'] == 'NO_ANSWER'
    assert STATUS_MAP['busy'] == 'BUSY'
    assert STATUS_MAP['failed'] == 'FAILED'


def test_realtime_model_default():
    assert Settings().openai_realtime_model == 'gpt-realtime-2.1'
