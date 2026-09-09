from uuid import uuid4
from app.api.voice import stream_token,valid_stream_token
def test_stream_token_is_bound():
    cid=uuid4();token=stream_token(cid);assert valid_stream_token(cid,token);assert not valid_stream_token(uuid4(),token)
