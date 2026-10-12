"""Adapter primario: Auth multi-vendedor (sin Register)."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.infrastructure.auth.jwt_handler import create_access_token, verify_password, get_current_vendedor
from app.infrastructure.persistence.supabase_client import require_supabase

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    usuario: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/login", response_model=LoginResponse, summary="Login vendedor (credenciales que da el jefe)")
def login(payload: LoginRequest):
    sb = require_supabase()
    try:
        res = sb.table("vendedores").select("*").eq("usuario", payload.usuario).single().execute()
        if not res.data:
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        v = res.data
        if not v.get("activo"):
            raise HTTPException(status_code=401, detail="Usuario inactivo")
        if not verify_password(payload.password, v["password_hash"]):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        token = create_access_token({"sub": v["id"], "usuario": v["usuario"], "rol": v["rol"]})
        return {"access_token": token, "token_type": "bearer", "user": {"id": v["id"], "usuario": v["usuario"], "nombre": v["nombre"], "rol": v["rol"]}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh", summary="Refresh JWT (opcional)")
def refresh(vendedor=Depends(get_current_vendedor)):
    token = create_access_token({"sub": vendedor["id"], "usuario": vendedor["usuario"], "rol": vendedor["rol"]})
    return {"access_token": token, "token_type": "bearer", "user": {"id": vendedor["id"], "usuario": vendedor["usuario"], "nombre": vendedor["nombre"], "rol": vendedor["rol"]}}

@router.get("/me", summary="Usuario actual via JWT")
def me(vendedor=Depends(get_current_vendedor)):
    return {"id": vendedor["id"], "usuario": vendedor["usuario"], "nombre": vendedor["nombre"], "rol": vendedor["rol"]}

@router.get("/vendedores", summary="Lista vendedores (solo admin)")
def list_vendedores(vendedor=Depends(get_current_vendedor)):
    if vendedor.get("rol") != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Solo admin")
    sb = require_supabase()
    res = sb.table("vendedores").select("id,usuario,nombre,rol,activo,created_at").order("created_at").execute()
    return res.data
