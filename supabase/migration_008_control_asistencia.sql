-- =============================================================================
-- MIGRACION 008: Control de Asistencia y Turnos (Entrada y Salida de Vendedores)
-- =============================================================================

create table if not exists public.control_asistencia (
  id uuid primary key default gen_random_uuid(),
  vendedor_id uuid references public.vendedores(id) on delete set null,
  usuario text not null,
  nombre text not null,
  fecha date not null default current_date,
  entrada_at timestamptz not null default now(),
  salida_at timestamptz,
  minutos_trabajados integer default 0,
  estado text not null default 'activo' check (estado in ('activo', 'cerrado')),
  observaciones text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_asistencia_vendedor on public.control_asistencia(vendedor_id);
create index if not exists idx_asistencia_fecha on public.control_asistencia(fecha desc);
create index if not exists idx_asistencia_estado on public.control_asistencia(estado);

-- RLS
alter table public.control_asistencia enable row level security;
drop policy if exists "control_asistencia: lectura todos" on public.control_asistencia;
drop policy if exists "control_asistencia: escritura todos" on public.control_asistencia;

create policy "control_asistencia: lectura todos" on public.control_asistencia for select using (true);
create policy "control_asistencia: escritura todos" on public.control_asistencia for all using (true) with check (true);

-- Realtime
do $$ begin
  alter publication supabase_realtime add table public.control_asistencia;
exception when duplicate_object then null; end $$;
alter table public.control_asistencia replica identity full;

comment on table public.control_asistencia is 'Registro de entrada, salida y tiempo laborado por vendedor';
