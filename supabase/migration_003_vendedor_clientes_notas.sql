-- =============================================================================
-- MIGRACION 003: Vendedor - Clientes + Notas de Venta con codigo_barras
-- Fecha: 2026-09-20
-- Ejecuta en: Supabase Dashboard > SQL Editor
-- =============================================================================

-- 1. CLIENTES
create table if not exists public.clientes (
  id uuid primary key default gen_random_uuid(),
  nombre varchar(150) not null,
  dni varchar(20),
  telefono varchar(20),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_clientes_nombre on public.clientes using gin (to_tsvector('spanish', nombre));
create index if not exists idx_clientes_dni on public.clientes(dni);
create index if not exists idx_clientes_telefono on public.clientes(telefono);

drop trigger if exists trg_clientes_updated_at on public.clientes;
create trigger trg_clientes_updated_at before update on public.clientes
for each row execute function public.handle_updated_at();

-- 2. NOTAS_VENTA (cabecera)
create table if not exists public.notas_venta (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid references public.clientes(id) on delete set null,
  vendedor_id uuid references auth.users(id) on delete set null,
  codigo_barras varchar(30) unique not null, -- NV-YYYYMMDD-XXXX
  total numeric(10,2) not null check (total >= 0),
  created_at timestamptz not null default now()
);
create index if not exists idx_notas_cliente on public.notas_venta(cliente_id);
create index if not exists idx_notas_vendedor on public.notas_venta(vendedor_id);
create index if not exists idx_notas_codigo on public.notas_venta(codigo_barras);
create index if not exists idx_notas_created on public.notas_venta(created_at desc);

-- 3. DETALLE_NOTA (lineas)
create table if not exists public.detalle_nota (
  id uuid primary key default gen_random_uuid(),
  nota_id uuid not null references public.notas_venta(id) on delete cascade,
  variante_id uuid not null references public.variantes(id) on delete restrict,
  cantidad integer not null check (cantidad > 0),
  precio_unitario numeric(10,2) not null check (precio_unitario >= 0),
  created_at timestamptz not null default now()
);
create index if not exists idx_detalle_nota on public.detalle_nota(nota_id);
create index if not exists idx_detalle_variante on public.detalle_nota(variante_id);

-- 4. RLS
alter table public.clientes enable row level security;
alter table public.notas_venta enable row level security;
alter table public.detalle_nota enable row level security;

drop policy if exists "clientes: lectura publica" on public.clientes;
drop policy if exists "clientes: escritura autenticados" on public.clientes;
drop policy if exists "notas: lectura autenticados" on public.notas_venta;
drop policy if exists "notas: escritura autenticados" on public.notas_venta;
drop policy if exists "detalle: lectura autenticados" on public.detalle_nota;
drop policy if exists "detalle: escritura autenticados" on public.detalle_nota;

create policy "clientes: lectura publica" on public.clientes for select using (true);
create policy "clientes: escritura autenticados" on public.clientes for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');
create policy "notas: lectura autenticados" on public.notas_venta for select using (auth.role() = 'authenticated');
create policy "notas: escritura autenticados" on public.notas_venta for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');
create policy "detalle: lectura autenticados" on public.detalle_nota for select using (auth.role() = 'authenticated');
create policy "detalle: escritura autenticados" on public.detalle_nota for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

-- service_role bypass RLS automatico

-- 5. REALTIME
alter publication supabase_realtime add table public.clientes;
alter publication supabase_realtime add table public.notas_venta;
alter publication supabase_realtime add table public.detalle_nota;
alter table public.clientes replica identity full;
alter table public.notas_venta replica identity full;
alter table public.detalle_nota replica identity full;

-- 6. INDICES variantes para filtros rápidos (categoria/talla/color) - ya existen pero asegurar
create index if not exists idx_variantes_categoria on public.variantes using btree (( (select categoria from public.productos where id = producto_id) ));
-- Alternativa simple: indice compuesto ya existe idx_variantes_talla_color, añadimos para categoria via join se usa seq scan, mejor vista
-- Para filtros rápidos, asegurar indices en variantes
create index if not exists idx_variantes_talla on public.variantes(talla);
create index if not exists idx_variantes_color on public.variantes(color);

comment on table public.clientes is 'Clientes para notas de venta vendedor';
comment on table public.notas_venta is 'Cabecera nota de venta con codigo_barras NV-YYYYMMDD-XXXX';
comment on column public.notas_venta.codigo_barras is 'Unico, generado en backend con python-barcode';
