from datetime import datetime,timedelta,timezone
import hashlib,secrets,jwt
from pwdlib import PasswordHash
from app.core.config import get_settings
password_hash=PasswordHash.recommended()
def hash_password(v): return password_hash.hash(v)
def verify_password(v,h): return password_hash.verify(v,h)
def create_token(user_id,tenant_id,role):
    now=datetime.now(timezone.utc); return jwt.encode({'sub':str(user_id),'tenant_id':str(tenant_id),'role':role,'iat':now,'exp':now+timedelta(hours=8)},get_settings().secret_key,algorithm='HS256')
def decode_token(t): return jwt.decode(t,get_settings().secret_key,algorithms=['HS256'])
def hash_secret(v): return hashlib.sha256(v.encode()).hexdigest()
def new_api_key(): return 'avk_'+secrets.token_urlsafe(32)
