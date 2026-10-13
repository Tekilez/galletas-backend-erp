"""
Kardex IA Microservice - FastAPI (Hexagonal / Ports & Adapters)
Arquitectura hexagonal: domain (core) -> application (use_cases) -> infrastructure (adapters) -> interfaces (api)

Flujo hexagonal:
  interfaces/api/routers (adapter primario) -> application/use_cases -> domain/ports -> infrastructure/persistence (adapter secundario Supabase)
  + OCR/LLM: interfaces -> application -> domain/ports -> infrastructure/ocr|llm

Compatibilidad: app/routers y app/services son shims que re-exportan la implementación hexagonal.
Endpoints:
 - POST /api/v1/scan-receipt
 - POST /api/v1/inventory-insights
 - CRUD /api/v1/productos, /variantes, /transacciones
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.infrastructure.config.settings import get_settings
# Adapters primarios (interfaces)
from app.interfaces.api.routers import ocr, insights, productos, variantes, transacciones, chat, clientes, notas, auth, devoluciones, asistencia, vendedores
from app.interfaces.api.schemas import HealthResponse

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validar config, warm-up opcional
    print(f"[{settings.app_name}] v{settings.app_version} env={settings.env} llm={settings.llm_provider} ocr={settings.ocr_provider}")
    if settings.llm_provider == "google" and not settings.google_api_key:
        print("⚠️  LLM_PROVIDER=google pero GOOGLE_API_KEY vacío -> fallback a mock")
    if settings.ocr_provider == "google" and not settings.google_api_key:
        print("⚠️  OCR_PROVIDER=google pero GOOGLE_API_KEY vacío -> fallback a mock")
    yield
    print("Shutting down...")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Microservicio IA para Kardex/POS: OCR de boletas + Insights de inventario con LLM.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS - en prod restringir a tu frontend Vercel/Supabase
origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins != "*" else ["*"]
# allow_credentials no puede ser True con "*" (spec CORS). Si es wildcard, desactiva credentials.
allow_credentials = False if origins == ["*"] else True
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers IA
app.include_router(ocr.router)
app.include_router(insights.router)
app.include_router(chat.router)
# Routers CRUD Kardex/POS
app.include_router(productos.router)
app.include_router(variantes.router)
app.include_router(transacciones.router)
# Routers Vendedor (Ingresos/Reportes)
app.include_router(clientes.router)
app.include_router(notas.router)
# Routers Auth + Devoluciones + Asistencia (los archivos existian pero no estaban montados -> 404)
app.include_router(auth.router)
app.include_router(devoluciones.router)
app.include_router(asistencia.router)
app.include_router(vendedores.router)

# Health & Root
@app.get("/", tags=["Health"])
async def root():
    return {"message": "Kardex IA Microservice up", "docs": "/docs", "health": "/health"}

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        llm_provider=settings.llm_provider,
        ocr_provider=settings.ocr_provider,
    )

# Error handler global - NO captura HTTPException (deja que FastAPI retorne 400/404/409 correctos)
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "error": str(exc.errors())})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.env == "development":
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc), "path": str(request.url)})
    return JSONResponse(status_code=500, content={"success": False, "error": "Internal server error"})

# Para `python -m app.main` local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
