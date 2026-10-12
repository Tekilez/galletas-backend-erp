-- =============================================================================
-- MIGRACION 006: trazabilidad vendedor snapshot en notas/devoluciones
-- Ejecuta en Supabase SQL Editor despues de 005
-- =============================================================================

-- notas_venta: añadir vendedor_nombre snapshot + created_by alias
do $$ begin
  alter table public.notas_venta add column if not exists vendedor_nombre text;
exception when duplicate_column then null; end $$;
do $$ begin
  alter table public.notas_venta add column if not exists created_by uuid references public.vendedores(id) on delete set null;
exception when duplicate_column then null; end $$;
-- migrar vendedor_id existente a created_by si está vacío
update public.notas_venta set created_by = vendedor_id where created_by is null and vendedor_id is not null;
-- backfill vendedor_nombre desde vendedores
update public.notas_venta n set vendedor_nombre = v.nombre from public.vendedores v where n.vendedor_id = v.id and n.vendedor_nombre is null;
update public.notas_venta n set vendedor_nombre = v.nombre from public.vendedores v where n.created_by = v.id and n.vendedor_nombre is null;

-- devoluciones: añadir vendedor_nombre snapshot
do $$ begin
  alter table public.devoluciones add column if not exists vendedor_nombre text;
exception when duplicate_column then null; end $$;
-- backfill desde notas_venta
update public.devoluciones d set vendedor_nombre = n.vendedor_nombre from public.notas_venta n where d.nota_codigo = n.codigo_barras and d.vendedor_nombre is null;
update public.devoluciones d set cliente = n.cliente from public.notas_venta n where d.nota_codigo = n.codigo_barras and d.cliente is null;

create index if not exists idx_notas_vendedor_nombre on public.notas_venta(vendedor_nombre);
create index if not exists idx_devoluciones_vendedor_nombre on public.devoluciones(vendedor_nombre);

comment on column public.notas_venta.vendedor_nombre is 'Snapshot nombre vendedor al crear, para PDF aunque lo vea otro vendedor';
comment on column public.devoluciones.vendedor_nombre is 'Snapshot vendedor de la nota original';
