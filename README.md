# galletas-backend-erp 🍪

Backend ERP para control de inventario de **galletas** (Kardex) + POS — **Supabase (PostgreSQL + Realtime + Auth + RLS)** + **FastAPI (IA Microservice)**.

> Migrado desde `back-inventario` (misma logica, solo cambian nombres: talla=presentacion, color=sabor). Repo público listo para desplegar.

## Owner

<p align="left">
  <a href="https://github.com/Tekilez">
    <img src="https://avatars.githubusercontent.com/u/87144071?v=4" width="100" height="100" alt="Tekilez avatar" style="border-radius:50%" />
  </a>
</p>

**[@Tekilez](https://github.com/Tekilez)** — Sergio André Gómez Vallejos  
Estudiante de Ingeniería de Software (UPC) · Full Stack Jr · React/Next.js · Laravel · Python/Flask · IA & Ciberseguridad

[![Tekilez](https://avatars.githubusercontent.com/u/87144071?s=64&v=4)](https://github.com/Tekilez)

## Estructura del repo

```
galletas-backend-erp/
  supabase/
    schema.sql                          # DDL base galletas (ejecutar en SQL Editor)
    migration_002_presentaciones_flexibles.sql  # presentaciones PAQ6/PAQ12/CAJA24 + trigger normalizar_presentacion
    migration_003_vendedor_clientes_notas.sql
    migration_004_devoluciones.sql
    migration_005_vendedores_auth_chatlog.sql
    migration_006_vendedor_snapshot.sql
    migration_007_trigger_devolucion.sql
    migration_008_control_asistencia.sql
    migration_009_galletas_nombres.sql  # solo si tu DB ya tenia ropa: convierte nombres
    seed_datos.sql                      # seed galletas (Chocochips/Vainilla/Avena)
  ai-microservice/      # FastAPI hexagonal (Ports & Adapters)
    app/main.py
    app/domain/         # entidades puras + ports (sin deps externas)
    app/application/    # casos de uso
    app/infrastructure/ # adapters: supabase / llm / ocr / config
    app/interfaces/api/ # routers, schemas, DI
    requirements.txt
    Dockerfile
    render.yaml
    fly.toml
```

## PARTE 1 — Supabase

1. Crea proyecto en Supabase (ej: `Galletar_Store`)
2. SQL Editor → pega `supabase/schema.sql` → Run
3. Corre migraciones en orden `migration_002` → `migration_009` (`009` solo convierte nombres si venias de ropa)
4. (Opcional) `seed_datos.sql` para datos de galletas de prueba
5. Verifica Realtime: Database → Realtime → `variantes` / `transacciones` enabled
6. Frontend se suscribe:

```js
supabase.channel('kardex')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'variantes' }, console.log)
  .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'transacciones' }, console.log)
  .subscribe()
```

## PARTE 2 — FastAPI

```powershell
cd ai-microservice
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# completa .env con tus keys (nunca commitees .env real)
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
# Health: http://localhost:8000/health
```

Ver detalle en [`ai-microservice/README.md`](ai-microservice/README.md).

### Switch IA producción

- **Google AI Studio:** `LLM_PROVIDER=google`, `GOOGLE_API_KEY=...`, `GOOGLE_MODEL=gemini-2.0-flash`
- **Ollama local:** `LLM_PROVIDER=ollama`, `ollama serve` + `ollama pull llama3.1:8b`
- **OCR Google Vision:** `OCR_PROVIDER=google`

## Deploy

- **Render:** New Web Service → Dockerfile → env vars. Health check `/health`.
- **Fly.io:** `fly launch --dockerfile Dockerfile`

## Seguridad

- `.env` está en `.gitignore` y **no** se sube a este repo público. Usa `.env.example` como plantilla.
- Si rotaste keys antes, rota `GOOGLE_API_KEY`, `SUPABASE_SERVICE_KEY` en Supabase/Google Cloud.

## Origen

- Origen privado: `back-inventario`
- Este repo: `galletas-backend-erp` (snapshot limpio sin `.env`, sin `__pycache__`, sin `.venv`)
