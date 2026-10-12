-- =============================================================================
-- MIGRACION 007: trigger kardex soporta tipo 'devolucion' (repone stock)
-- Ejecuta en Supabase SQL Editor despues de 006
-- =============================================================================

create or replace function public.aplicar_transaccion_kardex()
returns trigger language plpgsql as $$
declare
  v_stock_actual integer;
  v_nuevo_stock integer;
begin
  select stock_actual into v_stock_actual from public.variantes where id = new.variante_id for update;

  if not found then
    raise exception 'Variante % no existe', new.variante_id;
  end if;

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
    v_nuevo_stock := new.stock_nuevo;
  elsif new.tipo = 'devolucion' then
    -- devolucion repone stock como entrada
    v_nuevo_stock := v_stock_actual + new.cantidad;
  else
    raise exception 'Tipo de transaccion no soportado: %', new.tipo;
  end if;

  if new.tipo in ('entrada','salida','devolucion') and new.stock_nuevo != v_nuevo_stock then
    raise exception 'stock_nuevo incongruente: calculado %, recibido %', v_nuevo_stock, new.stock_nuevo;
  end if;

  update public.variantes set stock_actual = v_nuevo_stock where id = new.variante_id;

  return new;
end; $$;
