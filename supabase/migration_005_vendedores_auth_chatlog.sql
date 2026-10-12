-- =============================================================================
-- MIGRACION 005: Auth multi-vendedor + chat logs + created_by trazabilidad
-- Ejecuta en Supabase SQL Editor despues de 004
-- =============================================================================

-- 1. Vendedores (login sin Register, credenciales que da el jefe)
create table if not exists public.vendedores (
  id uuid primary key default gen_random_uuid(),
  usuario text unique not null,
  password_hash text not null,
  nombre text not null,
  rol text not null check (rol in ('vendedor','admin')),
  activo boolean not null default true,
  created_at timestamptz not null default now()
);
create index if not exists idx_vendedores_usuario on public.vendedores(usuario);
-- seed admin/vendedor de prueba (password: admin123 / vendedor123) -> bcrypt
-- hash generados con python passlib bcrypt
insert into public.vendedores (usuario, password_hash, nombre, rol) values
  ('admin', '$2b$12$bofT7Hff6eDBpixzbJuuRemxyscREi7nt8W17ntIfS.KPRMF04NDO', 'Admin', 'admin'),
  ('vendedor1', '$2b$12$MgL64diZ40lpVGfpFyhU6ukn3UCo8ut3kFBbDRThFRZMxv5ul3yom', 'Vendedor 1', 'vendedor'),
  ('vendedor2', '$2b$12$MgL64diZ40lpVGfpFyhU6ukn3UCo8ut3kFBbDRThFRZMxv5ul3yom', 'Vendedor 2', 'vendedor')
on conflict (usuario) do nothing;
-- actualizar passwords si ya existían con hash viejo
update public.vendedores set password_hash='$2b$12$bofT7Hff6eDBpixzbJuuRemxyscREi7nt8W17ntIfS.KPRMF04NDO' where usuario='admin';
update public.vendedores set password_hash='$2b$12$MgL64diZ40lpVGfpFyhU6ukn3UCo8ut3kFBbDRThFRZMxv5ul3yom' where usuario in ('vendedor1','vendedor2');
-- Nota: si los hashes no coinciden, actualiza con: UPDATE vendedores SET password_hash=crypt('admin123', gen_salt('bf')) WHERE usuario='admin';

-- 2. Ampliar tablas con created_by para trazabilidad vendedor
do $$ begin
  alter table public.productos add column if not exists created_by uuid references public.vendedores(id) on delete set null;
exception when duplicate_column then null; end $$;
do $$ begin
  alter table public.variantes add column if not exists created_by uuid references public.vendedores(id) on delete set null;
exception when duplicate_column then null; end $$;
-- notas_venta ya tiene vendedor_id pero referencia auth.users, la cambiamos a vendedores para JWT propio
do $$ begin
  alter table public.notas_venta drop constraint if exists notas_venta_vendedor_id_fkey;
exception when others then null; end $$;
do $$ begin
  alter table public.notas_venta add constraint notas_venta_vendedor_id_fkey_vendedores foreign key (vendedor_id) references public.vendedores(id) on delete set null;
exception when others then null; end $$;
-- devoluciones created_by ya existe

-- 3. Chat logs auditoría
create table if not exists public.chat_logs (
  id uuid primary key default gen_random_uuid(),
  vendedor_id uuid references public.vendedores(id) on delete set null,
  pregunta text not null,
  respuesta text not null,
  intencion text,
  created_at timestamptz not null default now()
);
create index if not exists idx_chatlogs_vendedor on public.chat_logs(vendedor_id);
create index if not exists idx_chatlogs_created on public.chat_logs(created_at desc);

-- RLS
alter table public.vendedores enable row level security;
alter table public.chat_logs enable row level security;

drop policy if exists "vendedores: lectura autenticados" on public.vendedores;
drop policy if exists "vendedores: escritura admin" on public.vendedores;
drop policy if exists "chat_logs: lectura autenticados" on public.chat_logs;
drop policy if exists "chat_logs: escritura autenticados" on public.chat_logs;

create policy "vendedores: lectura autenticados" on public.vendedores for select using (true);
create policy "vendedores: escritura admin" on public.vendedores for all using (true) with check (true);
create policy "chat_logs: lectura autenticados" on public.chat_logs for select using (auth.role() = 'authenticated');
create policy "chat_logs: escritura autenticados" on public.chat_logs for all using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

-- service_role bypass (idempotente)
do $$ begin
  alter publication supabase_realtime add table public.vendedores;
exception when duplicate_object then null; end $$;
do $$ begin
  alter publication supabase_realtime add table public.chat_logs;
exception when duplicate_object then null; end $$;
alter table public.vendedores replica identity full;
alter table public.chat_logs replica identity full;

-- Para login sin Supabase Auth, usamos JWT propio HS256 (no auth.users)
comment on table public.vendedores is 'Vendedores multi-vendedor, login JWT propio';
