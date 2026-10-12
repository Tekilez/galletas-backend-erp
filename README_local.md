# Control de Inventario Galletas (Kardex) + POS - Backend Híbrido

Arquitectura: **Supabase (PostgreSQL + Realtime + Auth + RLS)** + **FastAPI (IA Microservice)**

Dominio: galletas. Misma logica que version ropa, solo cambian nombres (talla=presentacion, color=sabor).

## Estructura del repo
```
back-inventario/
  supabase/
    schema.sql          # PARTE 1: DDL completo (ejecutar en SQL Editor)
  ai-microservice/      # PARTE 2: FastAPI
    app/main.py
    app/routers/ocr.py
    app/routers/insights.py
    app/services/...
    requirements.txt
    Dockerfile
```

## PARTE 1 - Supabase
1. Crea proyecto en Supabase
2. SQL Editor -> pega `supabase/schema.sql` -> Run
3. Verifica Realtime: Database -> Realtime -> variantes/transacciones enabled
4. Frontend se suscribe:
```js
supabase.channel('kardex')
  .on('postgres_changes', {event:'*', schema:'public', table:'variantes'}, console.log)
  .on('postgres_changes', {event:'INSERT', schema:'public', table:'transacciones'}, console.log)
  .subscribe()
```

## PARTE 2 - FastAPI
Ver `ai-microservice/README.md`
