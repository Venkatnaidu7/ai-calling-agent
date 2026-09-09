from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from app.core.security import decode_token
security=HTTPBearer(auto_error=False)
def current_claims(creds:HTTPAuthorizationCredentials=Depends(security)):
    if not creds: raise HTTPException(status.HTTP_401_UNAUTHORIZED,'Authentication required')
    try: return decode_token(creds.credentials)
    except Exception: raise HTTPException(401,'Invalid or expired token')
def tenant_id(claims=Depends(current_claims)): return claims['tenant_id']
def require_roles(*roles):
    def dep(claims=Depends(current_claims)):
        if claims.get('role') not in roles: raise HTTPException(403,'Insufficient permissions')
        return claims
    return dep
