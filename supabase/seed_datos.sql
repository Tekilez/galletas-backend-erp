-- =============================================================================
-- SEED DATOS - Kardex Galletas (ejecutar despues de schema.sql y migration_002)
-- Supabase Dashboard > SQL Editor > Run
-- Incluye: Galleta Chocochips PAQ12 (caso principal), Vainilla PAQ6, Avena BOLSA500G
-- NOTA: misma logica que version ropa, solo cambian nombres/categorias/SKUs.
-- Columnas talla (=presentacion) y color (=sabor) se mantienen por compatibilidad.
-- =============================================================================

-- 1. PRODUCTOS
INSERT INTO public.productos (id, nombre, descripcion, categoria, margen_ganancia) VALUES
  (gen_random_uuid(), 'Galleta Chocochips Clasica', 'Galleta con chispas de chocolate - Presentaciones PAQ6 a CAJA24', 'clasicas', 45.00),
  (gen_random_uuid(), 'Galleta Vainilla Francesa', 'Galleta de vainilla estilo frances - Presentaciones PAQ6 a BOLSA1KG', 'clasicas', 40.00),
  (gen_random_uuid(), 'Galleta Avena Integral', 'Galleta de avena integral saludable', 'saludables', 50.00)
ON CONFLICT DO NOTHING;

-- Ver ids generados (copia ids para variantes si necesitas)
-- SELECT id, nombre FROM public.productos;

-- 2. VARIANTES (SKU vendible) - talla=presentacion, color=sabor
-- Usa subselect por nombre para no hardcodear UUID
DO $$
DECLARE
  pid_choco uuid;
  pid_vain uuid;
  pid_avena uuid;
BEGIN
  SELECT id INTO pid_choco FROM public.productos WHERE nombre='Galleta Chocochips Clasica' LIMIT 1;
  SELECT id INTO pid_vain  FROM public.productos WHERE nombre='Galleta Vainilla Francesa' LIMIT 1;
  SELECT id INTO pid_avena FROM public.productos WHERE nombre='Galleta Avena Integral' LIMIT 1;

  -- Chocochips: presentaciones PAQ6, PAQ12, CAJA24, BOLSA500G
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_choco, 'GALL-CHOCO-PAQ6',     'PAQ6',      'CHOCOCHIPS', 8, 2, 8.50, 12.50),
    (pid_choco, 'GALL-CHOCO-PAQ12',    'PAQ12',     'CHOCOCHIPS', 5, 2, 15.00, 21.75),
    (pid_choco, 'GALL-CHOCO-CAJA24',   'CAJA24',    'CHOCOCHIPS', 6, 2, 28.00, 40.60),
    (pid_choco, 'GALL-CHOCO-500G',     'BOLSA500G', 'CHOCOCHIPS', 10, 2, 12.00, 17.40),
    (pid_choco, 'GALL-CHOCO-1KG',      'BOLSA1KG',  'CHOCOCHIPS', 4, 2, 22.00, 31.90),
    (pid_choco, 'GALL-CHOCO-PAQ12-VAIN', 'PAQ12',   'VAINILLA', 7, 2, 15.00, 21.00)
  ON CONFLICT (sku) DO NOTHING;

  -- Vainilla: PAQ6 / PAQ12 / BOLSA1KG
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_vain, 'GALL-VAIN-PAQ6',   'PAQ6',      'VAINILLA', 12, 3, 7.50, 10.50),
    (pid_vain, 'GALL-VAIN-PAQ12',  'PAQ12',     'VAINILLA', 15, 3, 14.00, 19.60),
    (pid_vain, 'GALL-VAIN-CAJA24', 'CAJA24',    'VAINILLA', 10, 3, 26.00, 36.40),
    (pid_vain, 'GALL-VAIN-500G',   'BOLSA500G', 'VAINILLA', 8, 3, 11.00, 15.40),
    (pid_vain, 'GALL-VAIN-1KG',    'BOLSA1KG',  'VAINILLA', 5, 3, 20.00, 28.00)
  ON CONFLICT (sku) DO NOTHING;

  -- Avena: BOLSA500G principal
  INSERT INTO public.variantes (producto_id, sku, talla, color, stock_actual, stock_minimo, precio_costo, precio_venta) VALUES
    (pid_avena, 'GALL-AVENA-500G', 'BOLSA500G', 'AVENA', 20, 5, 13.00, 19.50)
  ON CONFLICT (sku) DO NOTHING;
END $$;

-- 3. TRANSACCIONES (KARDEX) - ejemplo: compra proveedor + venta POS
-- IMPORTANTE: stock_anterior debe ser el stock_actual actual, stock_nuevo = anterior + cantidad (para entrada)
-- El trigger aplicar_transaccion_kardex actualiza variantes.stock_actual automaticamente
DO $$
DECLARE
  v_id uuid;
  v_stock int;
BEGIN
  SELECT id, stock_actual INTO v_id, v_stock FROM public.variantes WHERE sku='GALL-CHOCO-PAQ12' LIMIT 1;
  IF v_id IS NOT NULL THEN
    INSERT INTO public.transacciones (variante_id, tipo, cantidad, precio_unitario, stock_anterior, stock_nuevo, motivo, referencia)
    VALUES (v_id, 'entrada', 6, 15.00, v_stock, v_stock + 6, 'compra proveedor', 'BOLETA F001-001')
    ON CONFLICT DO NOTHING;
  END IF;

  SELECT id, stock_actual INTO v_id, v_stock FROM public.variantes WHERE sku='GALL-VAIN-PAQ12' LIMIT 1;
  IF v_id IS NOT NULL THEN
    INSERT INTO public.transacciones (variante_id, tipo, cantidad, precio_unitario, stock_anterior, stock_nuevo, motivo, referencia)
    VALUES (v_id, 'salida', 2, 19.60, v_stock, v_stock - 2, 'venta POS', 'TICKET POS-001')
    ON CONFLICT DO NOTHING;
  END IF;
END $$;

-- 4. VERIFICACION
SELECT p.nombre, v.sku, v.talla, v.color, v.stock_actual FROM public.variantes v JOIN public.productos p ON p.id=v.producto_id ORDER BY p.nombre, v.talla;
SELECT * FROM public.v_kardex_detalle ORDER BY created_at DESC LIMIT 10;
