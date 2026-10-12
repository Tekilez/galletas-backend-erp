# Kardex IA Microservice — Galletas (Hexagonal / Ports & Adapters)

Microservicio FastAPI para POS/Kardex tienda de galletas (Galletar Store). Misma logica, solo cambian nombres. Arquitectura hexagonal mantiene todo lo existente pero desacoplado.

## Arquitectura Hexagonal

```
ai-microservice/app/
├── domain/                 # Núcleo puro (sin deps externas)
│   ├── entities/           # Producto, Variante, Transaccion (dataclasses)
│   └── ports/              # Interfaces (ABC): ProductoRepositoryPort, VarianteRepositoryPort, TransaccionRepositoryPort, OcrPort, LlmPort
├── application/            # Casos de uso (orquesta domain + ports)
│   ├── use_cases/          # producto_use_cases.py, variante_use_cases.py, transaccion_use_cases.py, ocr_use_cases.py, insights_use_cases.py
│   └── dto/                # re-exporta schemas
├── infrastructure/         # Adapters secundarios (implementan ports)
│   ├── config/settings.py  # Settings (pydantic-settings) — fuente única
│   ├── persistence/        # supabase_client.py + supabase_*_repository.py (Supabase/PostgREST)
│   ├── ocr/ocr_adapter.py  # Mock -> Google Vision -> HF (presentacion PAQ12 vs PAQ6)
│   └── llm/llm_adapter.py  # Mock -> Gemini -> Ollama
├── interfaces/             # Adapters primarios (entrada)
│   └── api/
│       ├── schemas.py      # Contratos Pydantic (talla=presentacion PAQ12, color=sabor)
│       ├── routers/        # productos.py, variantes.py, transacciones.py, ocr.py, insights.py -> llaman use_cases vía DI
│       └── dependencies.py # Container DI (get_*_use_cases)
├── main.py                 # App factory hexagonal (FastAPI + CORS + lifespan)
├── container.py            # Wiring
├── config.py               # Shim compat -> infrastructure.config.settings
├── schemas.py              # Shim compat -> interfaces.api.schemas
├── routers/                # Shim compat -> interfaces.api.routers
└── services/               # Shim compat -> infrastructure
```

**Regla:** `domain` no importa nada de `infrastructure` ni `interfaces`. `application` solo conoce `domain/ports`. `infrastructure` implementa ports. `interfaces` inyecta use_cases.

Compatibilidad: imports antiguos `from app.routers import productos` y `from app.services.supabase_client import require_supabase` siguen funcionando vía shims.

## Diagrama flujo

```
[HTTP/FastAPI] -> interfaces/api/routers (adapter primario)
                -> application/use_cases (orquesta)
                -> domain/ports (interfaz)
                -> infrastructure/persistence/ocr/llm (adapter secundario)
                -> Supabase / Gemini / Ollama
```

Presentaciones galletas: `variantes.talla varchar(20)` acepta `PAQ6,PAQ12,CAJA24,BOLSA500G,BOLSA1KG,UNIDAD` y `color` = sabor (`CHOCOCHIPS,VAINILLA,AVENA...`) — trigger `normalizar_talla()` en `supabase/migration_002_tallas_flexibles.sql`. Nombres de columna se mantienen por compatibilidad.

## Quickstart local

```powershell
cd ai-microservice
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000  # local
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload  # para celular en misma WiFi
# Docs: http://localhost:8000/docs  Celular: http://192.168.1.28:8000/docs (tu IP Wi-Fi)
```

Health: `http://localhost:8000/health` -> `{"status":"ok"}`

## Test endpoints (hexagonal mantiene URLs idénticas)

```powershell
# Listar chocochips PAQ12 (post-migración)
curl "http://localhost:8000/api/v1/variantes?talla=PAQ12&color=CHOCOCHIPS"

# Listar vainilla PAQ6
curl "http://localhost:8000/api/v1/variantes?talla=PAQ6&color=VAINILLA"

# Crear variante galleta PAQ12
curl -X POST http://localhost:8000/api/v1/variantes -H "Content-Type: application/json" -d '{"producto_id":"...","sku":"GALL-CHOCO-PAQ12-TEST","talla":"PAQ12","color":"CHOCOCHIPS","precio_costo":15,"precio_venta":21.75}'

# OCR (mock, sin API key) — detecta PAQ12 vs PAQ6
curl -X POST http://localhost:8000/api/v1/scan-receipt -F "file=@boleta.jpg"

# Insights
curl -X POST http://localhost:8000/api/v1/inventory-insights -H "Content-Type: application/json" -d @payload.json
```

## Switch a producción IA

- **Google AI Studio**: `LLM_PROVIDER=google`, `GOOGLE_API_KEY=...`, `GOOGLE_MODEL=gemini-2.0-flash`
- **Ollama local**: `LLM_PROVIDER=ollama`, `ollama serve` + `ollama pull llama3.1:8b`
- **OCR Google Vision**: `OCR_PROVIDER=google` (mismo API key)

`app/infrastructure/config/settings.py:1` y `app/infrastructure/llm|ocr/*` leen estas env vars.

## Supabase

Ejecuta en **Supabase Dashboard > SQL Editor**:

1. `supabase/schema.sql` (base)
2. `supabase/migration_002_tallas_flexibles.sql` (presentaciones PAQ6/PAQ12/CAJA24 + trigger + seeds Chocochips y Vainilla)
3. `supabase/migration_009_galletas_nombres.sql` (solo si tu DB ya tenia datos de ropa: convierte nombres)

## Deploy

Dockerfile sigue `COPY ./app ./app` y CMD `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` — sin cambios.

- **Render**: New Web Service -> Dockerfile -> env vars. Health check `/health`.
- **Fly.io**: `fly launch --dockerfile Dockerfile`
