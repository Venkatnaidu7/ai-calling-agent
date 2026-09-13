from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import jwt
from pwdlib import PasswordHash
from app.core.config import get_settings

password_hash = PasswordHash.recommended()
JWT_ALGORITHM = 'HS256'
JWT_ISSUER = 'ai-voice-platform'
JWT_AUDIENCE = 'ai-voice-platform-api'

def hash_password(v):
    return password_hash.hash(v)

def verify_password(v, h):
    return password_hash.verify(v, h)

def _validate_secret():
    secret = get_settings().secret_key
    if get_settings().app_env.lower() in {'production', 'prod'} and (not secret or secret == 'change-me' or len(secret) < 32):
        raise RuntimeError('SECRET_KEY must be a unique value of at least 32 characters in production')
    return secret

def create_token(user_id, tenant_id, role):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            'sub': str(user_id),
            'tenant_id': str(tenant_id),
            'role': role,
            'iss': JWT_ISSUER,
            'aud': JWT_AUDIENCE,
            'iat': now,
            'exp': now + timedelta(hours=8),
        },
        _validate_secret(),
        algorithm=JWT_ALGORITHM,
    )

def decode_token(t):
    return jwt.decode(
        t,
        _validate_secret(),
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={'require': ['exp', 'iat', 'sub', 'tenant_id', 'role', 'iss', 'aud']},
    )

def hash_secret(v): return hashlib.sha256(v.encode()).hexdigest()
def new_api_key(): return 'avk_' + secrets.token_urlsafe(32)
