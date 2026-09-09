from app.core.security import hash_password,verify_password,create_token,decode_token
from uuid import uuid4
def test_password_roundtrip():
    h=hash_password('test-password');assert verify_password('test-password',h);assert not verify_password('wrong',h)
def test_token_claims():
    uid,tid=uuid4(),uuid4();claims=decode_token(create_token(uid,tid,'TENANT_OWNER'));assert claims['sub']==str(uid);assert claims['tenant_id']==str(tid)
