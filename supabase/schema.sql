-- =============================================================================
-- KARDEX / POS - ESQUEMA SUPABASE (PostgreSQL 15+)
-- Arquitectura híbrida: Supabase (DB + Realtime + Auth) + FastAPI (IA)
-- Autor: Arquitecto Cloud Senior - 2026
-- Ejecutar en: Supabase Dashboard > SQL Editor
-- =============================================================================

-- 0. EXTENSIONES
create extension if not exists "pgcrypto"; -- gen_random_uuid()
create extension if not exists "pg_stat_statements";

-- 1. ENUM PARA TIPO DE TRANSACCIÓN (KARDEX)
do $$ begin
  create type tipo_transaccion as enum ('entrada', 'salida', 'ajuste');
exception when duplicate_object then null;
end $$;

-- =============================================================================
-- TABLA: productos
-- Información general del producto padre. Ej: "Polo Oversize Algodón"
-- =============================================================================
create table if not exists public.productos (
  id uuid primary key default gen_random_uuid(),
  nombre varchar(150) not null,
  descripcion text,
  categoria varchar(80), -- ej: polos, jeans, vestidos
  margen_ganancia numeric(5,2) not null default 40.00 check (margen_ganancia >= 0 and margen_ganancia <= 500),
  activo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- Búsqueda full-text
  search_vector tsvector generated always as (to_tsvector('spanish', coalesce(nombre,'') || ' ' || coalesce(descripcion,'') || ' ' || coalesce(categoria,''))) stored
);
create index if not exists idx_productos_categoria on public.productos(categoria);
create index if not exists idx_productos_search on public.productos using gin(search_vector);
create index if not exists idx_productos_activo on public.productos(activo) where activo = true;

comment on table public.productos is 'Catálogo base. El margen_ganancia es el % configurado para calcular precio_venta automáticamente.';
comment on column public.productos.margen_ganancia is 'Porcentaje ej: 40.00 = 40% sobre precio_costo';

-- =============================================================================
-- TABLA: variantes
-- SKU real vendible. Ej: Polo Oversize - Talla M - Color Negro
-- Contiene el stock y precios. Es la tabla que el POS descuenta.
-- =============================================================================
create table if not exists public.variantes (
  id uuid primary key default gen_random_uuid(),
  producto_id uuid not null references public.productos(id) on delete cascade,
  sku varchar(50) unique not null, -- ej: POL-OVR-M-NEG-001
  talla varchar(20) not null, -- XS,S,M,L,XL, 28,30,32 o "Única"
  color varchar(50) not null,
  stock_actual integer not null default 0 check (stock_actual >= 0),
  stock_minimo integer not null default 5 check (stock_minimo >= 0),
  precio_costo numeric(10,2) not null check (precio_costo >= 0),
  precio_venta numeric(10,2) not null check (precio_venta >= 0),
  imagen_url text,
  activo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_precio_venta_mayor_costo check (precio_venta >= precio_costo)
);
create index if not exists idx_variantes_producto on public.variantes(producto_id);
create index if not exists idx_variantes_sku on public.variantes(sku);
create index if not exists idx_variantes_stock on public.variantes(stock_actual);
-- Búsqueda rápida por talla/color
create index if not exists idx_variantes_talla_color on public.variantes(talla, color);

comment on table public.variantes is 'Variante vendible (SKU). stock_actual es la fuente de verdad para el Kardex. precio_venta se calcula como costo * (1 + margen/100) pero es sobreescribible.';
comment on column public.variantes.stock_actual is 'NUNCA actualizar manualmente. Usar transacciones para mantener trazabilidad.';

-- =============================================================================
-- TABLA: transacciones (KARDEX HISTÓRICO)
-- Cada entrada/salida. Inmutable y auditable. Fuente para reportes y para IA.
-- =============================================================================
create table if not exists public.transacciones (
  id uuid primary key default gen_random_uuid(),
  variante_id uuid not null references public.variantes(id) on delete restrict,
  tipo tipo_transaccion not null,
  cantidad integer not null check (cantidad > 0),
  precio_unitario numeric(10,2) not null check (precio_unitario >= 0),
  stock_anterior integer not null,
  stock_nuevo integer not null,
  motivo varchar(100), -- ej: "compra proveedor", "venta POS", "merma", "devolución"
  referencia varchar(150), -- ej: "BOLETA F001-123", "TICKET POS-889"
  notas text,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);
create index if not exists idx_transacciones_variante on public.transacciones(variante_id);
create index if not exists idx_transacciones_tipo on public.transacciones(tipo);
create index if not exists idx_transacciones_created_at on public.transacciones(created_at desc);
create index if not exists idx_transacciones_referencia on public.transacciones(referencia);

comment on table public.transacciones is 'Kardex inmutable. Cada fila representa un movimiento. stock_anterior/nuevo permiten auditoría y reconstrucción.';
comment on column public.transacciones.tipo is 'entrada=compra/inventario inicial, salida=venta, ajuste=merma/corrección';

-- =============================================================================
-- FUNCIONES Y TRIGGERS
-- =============================================================================

-- Trigger genérico para updated_at
create or replace function public.handle_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end; $$;

drop trigger if exists trg_productos_updated_at on public.productos;
create trigger trg_productos_updated_at before update on public.productos
for each row execute function public.handle_updated_at();

drop trigger if exists trg_variantes_updated_at on public.variantes;
create trigger trg_variantes_updated_at before update on public.variantes
for each row execute function public.handle_updated_at();

-- Función: Calcular precio_venta automáticamente al insertar/actualizar variante
-- Si no se provee precio_venta, lo calcula desde margen del producto.
create or replace function public.calcular_precio_venta()
returns trigger language plpgsql as $$
declare
  v_margen numeric(5,2);
begin
  -- Si precio_venta es null o no ha sido modificado manualmente, recalcular
  select margen_ganancia into v_margen from public.productos where id = new.producto_id;
  -- Solo auto-calcula si precio_venta es igual al costo (insert sin margen) o si el costo cambió
  -- Para permitir override manual, solo calcula si el usuario no lo provee explícitamente distinto
  -- Estrategia: si TG_OP = INSERT y precio_venta = precio_costo, aplicar margen
  if TG_OP = 'INSERT' and new.precio_venta = new.precio_costo then
    new.precio_venta := round(new.precio_costo * (1 + v_margen/100), 2);
  end if;
  return new;
end; $$;

drop trigger if exists trg_variantes_precio on public.variantes;
create trigger trg_variantes_precio before insert on public.variantes
for each row execute function public.calcular_precio_venta();

-- Función: Validar y aplicar movimiento de Kardex (evita stock negativo y race conditions)
-- Uso: insert en transacciones -> trigger actualiza variantes.stock_actual
create or replace function public.aplicar_transaccion_kardex()
returns trigger language plpgsql as $$
declare
  v_stock_actual integer;
  v_nuevo_stock integer;
begin
  -- Bloqueo pesimista por fila para evitar ventas concurrentes que dejen stock negativo
  select stock_actual into v_stock_actual from public.variantes where id = new.variante_id for update;

  if not found then
    raise exception 'Variante % no existe', new.variante_id;
  end if;

  -- Validar coherencia de stock_anterior
  if new.stock_anterior != v_stock_actual then
    raise exception 'Stock desincronizado: esperado %, recibido %', v_stock_actual, new.stock_anterior
      using hint = 'Refresca el stock antes de reintentar. Posible venta concurrente.';
  end if;

  if new.tipo = 'entrada' then
    v_nuevo_stock := v_stock_actual + new.cantidad;
  elsif new.tipo = 'salida' then
    v_nuevo_stock := v_stock_actual - new.cantidad;
    if v_nuevo_stock < 0 then
      raise exception 'Stock insuficiente para variante %: disponible %, solicitado %', new.variante_id, v_stock_actual, new.cantidad;
    end if;
  elsif new.tipo = 'ajuste' then
    -- ajuste: stock_nuevo ya es el valor final deseado, cantidad es delta informativo
    v_nuevo_stock := new.stock_nuevo;
  end if;

  -- Asegurar que stock_nuevo enviado coincida con el calculado (excepto ajuste donde es libre pero validamos)
  if new.tipo in ('entrada','salida') and new.stock_nuevo != v_nuevo_stock then
    raise exception 'stock_nuevo incongruente: calculado %, recibido %', v_nuevo_stock, new.stock_nuevo;
  end if;

  -- Aplicar
  update public.variantes set stock_actual = v_nuevo_stock where id = new.variante_id;

  return new;
end; $$;

drop trigger if exists trg_transacciones_kardex on public.transacciones;
create trigger trg_transacciones_kardex before insert on public.transacciones
for each row execute function public.aplicar_transaccion_kardex();

-- Vista útil: Kardex enriquecido para la IA y reportes
create or replace view public.v_kardex_detalle as
select
  t.id as transaccion_id,
  t.tipo,
  t.cantidad,
  t.precio_unitario,
  t.stock_anterior,
  t.stock_nuevo,
  t.motivo,
  t.referencia,
  t.created_at,
  v.id as variante_id,
  v.sku,
  v.talla,
  v.color,
  v.stock_actual,
  p.id as producto_id,
  p.nombre as producto_nombre,
  p.categoria
from public.transacciones t
join public.variantes v on v.id = t.variante_id
join public.productos p on p.id = v.producto_id;

-- Vista: resumen para endpoint /inventory-insights
create or replace view public.v_productos_mas_vendidos as
select
  p.id, p.nombre, p.categoria,
  sum(case when t.tipo='salida' then t.cantidad else 0 end) as total_vendido,
  sum(case when t.tipo='entrada' then t.cantidad else 0 end) as total_comprado,
  count(t.id) as num_movimientos
from public.productos p
join public.variantes v on v.producto_id = p.id
left join public.transacciones t on t.variante_id = v.id
group by p.id;

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- Políticas base: Ajustar según tu modelo de roles.
-- Asume Supabase Auth. Si no usas auth, cambia a permissive para anon/service_role.
-- =============================================================================
alter table public.productos enable row level security;
alter table public.variantes enable row level security;
alter table public.transacciones enable row level security;

-- Limpiar políticas previas (idempotente)
drop policy if exists "productos: lectura publica" on public.productos;
drop policy if exists "productos: escritura autenticados" on public.productos;
drop policy if exists "variantes: lectura publica" on public.variantes;
drop policy if exists "variantes: escritura autenticados" on public.variantes;
drop policy if exists "transacciones: lectura autenticados" on public.transacciones;
drop policy if exists "transacciones: escritura autenticados" on public.transacciones;
drop policy if exists "transacciones: solo insert autenticados" on public.transacciones;

-- PRODUCTOS: lectura para todos (POS necesita leer sin login), escritura solo autenticados
create policy "productos: lectura publica"
  on public.productos for select using (true);
create policy "productos: escritura autenticados"
  on public.productos for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

-- VARIANTES: igual que productos
create policy "variantes: lectura publica"
  on public.variantes for select using (true);
create policy "variantes: escritura autenticados"
  on public.variantes for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

-- TRANSACCIONES: solo usuarios autenticados pueden leer/insertar. No update/delete directo (inmutabilidad).
create policy "transacciones: lectura autenticados"
  on public.transacciones for select using (auth.role() = 'authenticated');
create policy "transacciones: solo insert autenticados"
  on public.transacciones for insert with check (auth.role() = 'authenticated');
-- Nota: No se crea policy para UPDATE/DELETE -> por defecto denegado. Kardex inmutable.

-- Para service_role (backend FastAPI con service key) bypass RLS automático, no necesita policy.

-- =============================================================================
-- REALTIME
-- Habilitar Realtime para variantes (stock) y transacciones (kardex en vivo)
-- El frontend se suscribe: supabase.channel('kardex').on('postgres_changes', ...)
-- =============================================================================
-- Supabase Realtime usa la publicación supabase_realtime
do $$
begin
  -- Crear publicación si no existe (Supabase ya la crea, pero por si acaso)
  if not exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    create publication supabase_realtime;
  end if;
end $$;

alter publication supabase_realtime add table public.variantes;
alter publication supabase_realtime add table public.transacciones;
-- Opcional: también productos si quieres reflejar cambios de margen en vivo
alter publication supabase_realtime add table public.productos;

-- Configurar replica identity para que Realtime envíe old/new record completos
alter table public.variantes replica identity full;
alter table public.transacciones replica identity full;
alter table public.productos replica identity full;

-- =============================================================================
-- DATOS DE EJEMPLO (opcional, comentar en prod)
-- =============================================================================
-- insert into public.productos (nombre, descripcion, categoria, margen_ganancia) values
-- ('Polo Oversize Algodón', 'Polo unisex 100% algodón', 'polos', 45.00),
-- ('Jeans Mom Fit', 'Jeans tiro alto dama', 'jeans', 50.00);
--
-- insert into public.variantes (producto_id, sku, talla, color, stock_actual, precio_costo, precio_venta) values
-- ((select id from public.productos where nombre='Polo Oversize Algodón' limit 1), 'POL-OVR-M-NEG-001', 'M', 'Negro', 25, 35.00, 50.75),
-- ((select id from public.productos where nombre='Polo Oversize Algodón' limit 1), 'POL-OVR-L-BLA-001', 'L', 'Blanco', 10, 35.00, 50.75);

-- =============================================================================
-- NOTAS DE ARQUITECTURA
-- 1. FastAPI debe usar SUPABASE_SERVICE_ROLE_KEY para insertar transacciones (bypass RLS).
-- 2. Frontend (POS) usa SUPABASE_ANON_KEY + Auth. Las ventas concurrentes están protegidas por FOR UPDATE.
-- 3. Para auditoría, nunca hacer UPDATE/DELETE en transacciones. Usar tipo='ajuste' para correcciones.
-- =============================================================================
