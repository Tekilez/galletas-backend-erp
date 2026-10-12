"""JWT HS256 para vendedores (sin Supabase Auth)."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

def get_jwt_secret() -> str:
    # usa JWT_SECRET o fallback a SUPABASE_SERVICE_KEY (no ideal pero funciona para dev)
    from app.infrastructure.config.settings import get_settings
    s = get_settings()
    return os.getenv("JWT_SECRET") or s.supabase_service_key or "kardex-jwt-secret-change-me"

ALGORITHM = "HS256"
EXPIRE_HOURS = 24

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}")

async def get_current_vendedor(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="No autenticado - envía Authorization: Bearer <token>")
    token = credentials.credentials
    payload = decode_token(token)
    vendedor_id = payload.get("sub")
    if not vendedor_id:
        raise HTTPException(status_code=401, detail="Token sin sub")
    # verificar vendedor existe y activo (via Supabase)
    from app.infrastructure.persistence.supabase_client import require_supabase
    sb = require_supabase()
    try:
        res = sb.table("vendedores").select("*").eq("id", vendedor_id).single().execute()
        if not res.data or not res.data.get("activo"):
            raise HTTPException(status_code=401, detail="Vendedor no existe o inactivo")
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# dependencia opcional (para endpoints que pueden ser publicos pero si hay token lo usa)
async def get_current_vendedor_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    if credentials is None:
        return None
    try:
        return await get_current_vendedor(credentials)
    except HTTPException:
        return None
