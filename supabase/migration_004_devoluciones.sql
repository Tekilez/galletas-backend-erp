-- =============================================================================
-- MIGRACION 004: Devoluciones (2 casos: con y sin barcode)
-- Ejecuta en Supabase SQL Editor despues de 003
-- =============================================================================

-- Ampliar enum tipo_transaccion para devolucion (no rompe ajuste)
do $$ begin
  alter type tipo_transaccion add value if not exists 'devolucion';
exception when duplicate_object then null;
end $$;

-- Tabla devoluciones
create table if not exists public.devoluciones (
  id uuid primary key default gen_random_uuid(),
  codigo text unique not null, -- DV-YYYYMMDD-XXXX
  nota_codigo text not null references public.notas_venta(codigo_barras) on delete restrict,
  cliente jsonb, -- {nombre,dni,telefono} copia de nota
  motivo text,
  items jsonb not null, -- [{variante_id,cantidad,motivo}]
  total_devuelto numeric(10,2) not null check (total_devuelto >= 0),
  created_at timestamptz not null default now(),
  created_by uuid references auth.users(id) on delete set null
);
create index if not exists idx_devoluciones_nota on public.devoluciones(nota_codigo);
create index if not exists idx_devoluciones_codigo on public.devoluciones(codigo);
create index if not exists idx_devoluciones_created on public.devoluciones(created_at desc);
create index if not exists idx_devoluciones_cliente_gin on public.devoluciones using gin (cliente);

-- RLS
alter table public.devoluciones enable row level security;
drop policy if exists "devoluciones: lectura autenticados" on public.devoluciones;
drop policy if exists "devoluciones: escritura autenticados" on public.devoluciones;
create policy "devoluciones: lectura autenticados" on public.devoluciones for select using (auth.role() = 'authenticated');
create policy "devoluciones: escritura autenticados" on public.devoluciones for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

do $$ begin alter publication supabase_realtime add table public.devoluciones; exception when duplicate_object then null; end $$;
alter table public.devoluciones replica identity full;

-- Vista notas con cliente jsonb para búsqueda Flutter (q=nombre|dni)
-- Ya tenemos clientes tabla, pero spec pide cliente jsonb en notas_venta. Mantenemos ambas: cliente_id + cliente jsonb cache
do $$ begin
  alter table public.notas_venta add column if not exists cliente jsonb;
exception when duplicate_column then null;
end $$;
create index if not exists idx_notas_cliente_gin on public.notas_venta using gin (cliente);
create index if not exists idx_notas_codigo_barras on public.notas_venta(codigo_barras);

comment on table public.devoluciones is 'Devoluciones validadas contra nota original, repone stock via transaccion tipo devolucion';
